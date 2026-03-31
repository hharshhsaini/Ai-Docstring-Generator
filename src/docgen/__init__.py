"""
Docstring Generator - Automatically generate and inject docstrings into Python codebases.

This package provides a CLI tool that uses LLM providers to generate high-quality
docstrings for Python functions and classes, then patches them back into source files
while preserving formatting.
"""

from docgen.interfaces import LanguageParser, LanguagePatcher
from docgen.models import (
    FunctionInfo,
    ClassInfo,
    Config,
    LLMConfig,
    LLMResponse,
    CoverageReport,
    ProcessingStats,
)
from docgen.walker import FileWalker
from docgen.parser import PythonParser
from docgen.llm import (
    LLMClient,
    LLMError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    AnthropicClient,
    OpenAIClient,
    OllamaClient,
)
from docgen.prompt import PromptBuilder
from docgen.formatter import DocstringFormatter
from docgen.patcher import DocstringPatcher
from docgen.config import ConfigLoader
from docgen.coverage import calculate_coverage
from docgen.diff import generate_diff, display_diff
from docgen.batch import process_files_batch

__version__ = "0.1.0"
__author__ = "Docstring Generator Team"
__all__ = [
    # Interfaces
    "LanguageParser",
    "LanguagePatcher",
    # Core models
    "FunctionInfo",
    "ClassInfo",
    "Config",
    "LLMConfig",
    "LLMResponse",
    "CoverageReport",
    "ProcessingStats",
    # Components
    "FileWalker",
    "PythonParser",
    "LLMClient",
    "PromptBuilder",
    "DocstringFormatter",
    "DocstringPatcher",
    "ConfigLoader",
    # LLM exceptions
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "TimeoutError",
    # Provider clients
    "AnthropicClient",
    "OpenAIClient",
    "OllamaClient",
    # Functions
    "calculate_coverage",
    "generate_diff",
    "display_diff",
    "process_files_batch",
]
