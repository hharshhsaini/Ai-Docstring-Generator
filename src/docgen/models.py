"""Core data models for the docstring generator.

This module defines Pydantic models for all data structures used throughout
the docstring generation pipeline, ensuring type safety and validation.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field


class FunctionInfo(BaseModel):
    """Metadata extracted from a function definition.
    
    Attributes:
        name: Function name
        params: List of (parameter_name, type_hint) tuples
        return_type: Return type annotation if present
        body_preview: First 5 lines of function body (excluding docstring)
        has_docstring: Whether function has an existing docstring
        existing_docstring: Existing docstring text if present
        line_number: Line number where function is defined
        parent_class: Class name if function is a method, None for module-level functions
    """
    
    name: str
    params: list[tuple[str, Optional[str]]]
    return_type: Optional[str] = None
    body_preview: str
    has_docstring: bool
    existing_docstring: Optional[str] = None
    line_number: int
    parent_class: Optional[str] = None
    
    @field_validator('body_preview')
    @classmethod
    def truncate_body(cls, v: str) -> str:
        """Truncate body preview to first 5 lines."""
        lines = v.split('\n')[:5]
        return '\n'.join(lines)


class ClassInfo(BaseModel):
    """Metadata extracted from a class definition.
    
    Attributes:
        name: Class name
        methods: List of method metadata
        has_docstring: Whether class has an existing docstring
        existing_docstring: Existing docstring text if present
        line_number: Line number where class is defined
    """
    
    name: str
    methods: list[FunctionInfo]
    has_docstring: bool
    existing_docstring: Optional[str] = None
    line_number: int


class LLMConfig(BaseModel):
    """Configuration for LLM provider.
    
    Attributes:
        provider: LLM provider name (anthropic, openai, ollama)
        model: Model name/identifier
        api_key: API key for cloud providers (optional for Ollama)
        base_url: Base URL for API (primarily for Ollama)
        max_retries: Maximum number of retry attempts on failure
        timeout: Request timeout in seconds
    """
    
    provider: str = Field(pattern="^(anthropic|openai|ollama)$")
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=30, ge=5, le=300)


class Config(BaseModel):
    """Tool configuration.
    
    Attributes:
        style: Docstring style (google, numpy, sphinx)
        provider: LLM provider (anthropic, openai, ollama)
        model: Model name
        api_key: API key for cloud providers
        base_url: Base URL for API (primarily for Ollama)
        exclude: List of glob patterns for file exclusion
        overwrite_existing: Whether to overwrite existing docstrings
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
    """
    
    style: str = Field(default="google", pattern="^(google|numpy|sphinx)$")
    provider: str = Field(default="anthropic", pattern="^(anthropic|openai|ollama)$")
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    exclude: list[str] = Field(default_factory=list)
    overwrite_existing: bool = False
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=30, ge=5, le=300)
    
    @model_validator(mode='after')
    def validate_api_key(self) -> 'Config':
        """Validate API key and fall back to environment variable if not provided."""
        # If API key is already provided, use it
        if self.api_key:
            return self
        
        # For cloud providers, try to get from environment
        if self.provider in ['anthropic', 'openai']:
            env_var = f"{self.provider.upper()}_API_KEY"
            env_value = os.getenv(env_var)
            if env_value:
                self.api_key = env_value
        
        # For Ollama, API key is optional (leave as None)
        return self
    
    def to_llm_config(self) -> LLMConfig:
        """Convert to LLMConfig for use with LLM client."""
        return LLMConfig(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=self.max_retries,
            timeout=self.timeout
        )


class LLMResponse(BaseModel):
    """Response from LLM provider.
    
    Attributes:
        docstring: Generated docstring text
        provider: Provider that generated the response
        model: Model that generated the response
        tokens_used: Number of tokens used (if available)
    """
    
    docstring: str
    provider: str
    model: str
    tokens_used: Optional[int] = None


class CoverageReport(BaseModel):
    """Docstring coverage statistics.
    
    Attributes:
        total_functions: Total number of functions analyzed
        documented_functions: Number of functions with docstrings
        coverage_percentage: Percentage of documented functions
        missing_docstrings: List of (file_path, line_number) for missing docstrings
    """
    
    total_functions: int
    documented_functions: int
    missing_docstrings: list[tuple[str, int]] = Field(default_factory=list)
    
    @computed_field
    @property
    def coverage_percentage(self) -> float:
        """Calculate coverage percentage."""
        if self.total_functions == 0:
            return 0.0
        return (self.documented_functions / self.total_functions) * 100


class ProcessingStats(BaseModel):
    """Statistics from processing run.
    
    Attributes:
        files_processed: Number of files processed
        docstrings_added: Number of new docstrings added
        docstrings_updated: Number of existing docstrings updated
        errors: Number of errors encountered
    """
    
    files_processed: int = 0
    docstrings_added: int = 0
    docstrings_updated: int = 0
    errors: int = 0
    
    def increment_added(self) -> None:
        """Increment the count of added docstrings."""
        self.docstrings_added += 1
    
    def increment_updated(self) -> None:
        """Increment the count of updated docstrings."""
        self.docstrings_updated += 1
    
    def increment_error(self) -> None:
        """Increment the error count."""
        self.errors += 1
