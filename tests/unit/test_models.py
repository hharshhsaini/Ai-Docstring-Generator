"""Unit tests for core data models."""

import os
import pytest
from pydantic import ValidationError

from docgen.models import (
    FunctionInfo,
    ClassInfo,
    Config,
    LLMConfig,
    LLMResponse,
    CoverageReport,
    ProcessingStats,
)


class TestFunctionInfo:
    """Tests for FunctionInfo model."""
    
    def test_function_info_creation(self):
        """Test creating a FunctionInfo instance with valid data."""
        func = FunctionInfo(
            name="test_func",
            params=[("x", "int"), ("y", "str")],
            return_type="bool",
            body_preview="return True",
            has_docstring=False,
            line_number=10,
        )
        
        assert func.name == "test_func"
        assert func.params == [("x", "int"), ("y", "str")]
        assert func.return_type == "bool"
        assert func.has_docstring is False
        assert func.line_number == 10
        assert func.parent_class is None
    
    def test_function_info_with_parent_class(self):
        """Test FunctionInfo for a class method."""
        func = FunctionInfo(
            name="method",
            params=[("self", None)],
            return_type=None,
            body_preview="pass",
            has_docstring=True,
            existing_docstring="Method docstring",
            line_number=20,
            parent_class="MyClass",
        )
        
        assert func.parent_class == "MyClass"
        assert func.existing_docstring == "Method docstring"
    
    def test_body_preview_truncation(self):
        """Test that body preview is truncated to 5 lines."""
        long_body = "\n".join([f"line {i}" for i in range(10)])
        
        func = FunctionInfo(
            name="test",
            params=[],
            return_type=None,
            body_preview=long_body,
            has_docstring=False,
            line_number=1,
        )
        
        lines = func.body_preview.split('\n')
        assert len(lines) == 5
        assert lines[0] == "line 0"
        assert lines[4] == "line 4"
    
    def test_body_preview_no_truncation_needed(self):
        """Test that short body preview is not modified."""
        short_body = "line 1\nline 2"
        
        func = FunctionInfo(
            name="test",
            params=[],
            return_type=None,
            body_preview=short_body,
            has_docstring=False,
            line_number=1,
        )
        
        assert func.body_preview == short_body


class TestClassInfo:
    """Tests for ClassInfo model."""
    
    def test_class_info_creation(self):
        """Test creating a ClassInfo instance."""
        method1 = FunctionInfo(
            name="method1",
            params=[("self", None)],
            return_type=None,
            body_preview="pass",
            has_docstring=False,
            line_number=5,
            parent_class="TestClass",
        )
        
        method2 = FunctionInfo(
            name="method2",
            params=[("self", None), ("x", "int")],
            return_type="str",
            body_preview="return str(x)",
            has_docstring=True,
            existing_docstring="Convert to string",
            line_number=10,
            parent_class="TestClass",
        )
        
        cls = ClassInfo(
            name="TestClass",
            methods=[method1, method2],
            has_docstring=True,
            existing_docstring="Test class docstring",
            line_number=1,
        )
        
        assert cls.name == "TestClass"
        assert len(cls.methods) == 2
        assert cls.has_docstring is True
        assert cls.existing_docstring == "Test class docstring"
        assert cls.line_number == 1


class TestLLMConfig:
    """Tests for LLMConfig model."""
    
    def test_llm_config_anthropic(self):
        """Test LLMConfig for Anthropic provider."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )
        
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.api_key == "test-key"
        assert config.max_retries == 3
        assert config.timeout == 30
    
    def test_llm_config_openai(self):
        """Test LLMConfig for OpenAI provider."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"
    
    def test_llm_config_ollama(self):
        """Test LLMConfig for Ollama provider."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            base_url="http://localhost:11434",
        )
        
        assert config.provider == "ollama"
        assert config.base_url == "http://localhost:11434"
        assert config.api_key is None
    
    def test_llm_config_invalid_provider(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="invalid",
                model="test",
            )
        
        assert "provider" in str(exc_info.value)
    
    def test_llm_config_custom_retries(self):
        """Test custom max_retries value."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
            max_retries=5,
        )
        
        assert config.max_retries == 5
    
    def test_llm_config_invalid_retries(self):
        """Test that invalid max_retries raises validation error."""
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="anthropic",
                model="test",
                api_key="test-key",
                max_retries=0,  # Below minimum
            )
        
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="anthropic",
                model="test",
                api_key="test-key",
                max_retries=11,  # Above maximum
            )
    
    def test_llm_config_custom_timeout(self):
        """Test custom timeout value."""
        config = LLMConfig(
            provider="anthropic",
            model="test",
            api_key="test-key",
            timeout=60,
        )
        
        assert config.timeout == 60
    
    def test_llm_config_invalid_timeout(self):
        """Test that invalid timeout raises validation error."""
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="anthropic",
                model="test",
                api_key="test-key",
                timeout=1,  # Below minimum
            )


class TestConfig:
    """Tests for Config model."""
    
    def test_config_defaults(self):
        """Test Config with default values."""
        config = Config()
        
        assert config.style == "google"
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.exclude == []
        assert config.overwrite_existing is False
        assert config.max_retries == 3
        assert config.timeout == 30
    
    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            style="numpy",
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            exclude=["**/test_*.py", "**/migrations/**"],
            overwrite_existing=True,
            max_retries=5,
            timeout=60,
        )
        
        assert config.style == "numpy"
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"
        assert config.exclude == ["**/test_*.py", "**/migrations/**"]
        assert config.overwrite_existing is True
        assert config.max_retries == 5
        assert config.timeout == 60
    
    def test_config_invalid_style(self):
        """Test that invalid style raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Config(style="invalid")
        
        assert "style" in str(exc_info.value)
    
    def test_config_invalid_provider(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Config(provider="invalid")
        
        assert "provider" in str(exc_info.value)
    
    def test_config_api_key_from_env(self, monkeypatch):
        """Test that API key is loaded from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        
        config = Config(provider="anthropic")
        
        assert config.api_key == "env-key"
    
    def test_config_api_key_explicit_overrides_env(self, monkeypatch):
        """Test that explicit API key overrides environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        
        config = Config(provider="anthropic", api_key="explicit-key")
        
        assert config.api_key == "explicit-key"
    
    def test_config_ollama_no_api_key_required(self):
        """Test that Ollama provider doesn't require API key."""
        config = Config(provider="ollama", model="llama2")
        
        assert config.api_key is None
    
    def test_config_to_llm_config(self):
        """Test conversion to LLMConfig."""
        config = Config(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
            max_retries=5,
            timeout=60,
        )
        
        llm_config = config.to_llm_config()
        
        assert isinstance(llm_config, LLMConfig)
        assert llm_config.provider == "anthropic"
        assert llm_config.model == "claude-3-5-sonnet-20241022"
        assert llm_config.api_key == "test-key"
        assert llm_config.max_retries == 5
        assert llm_config.timeout == 60


class TestLLMResponse:
    """Tests for LLMResponse model."""
    
    def test_llm_response_creation(self):
        """Test creating an LLMResponse instance."""
        response = LLMResponse(
            docstring="Test docstring",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            tokens_used=150,
        )
        
        assert response.docstring == "Test docstring"
        assert response.provider == "anthropic"
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.tokens_used == 150
    
    def test_llm_response_without_tokens(self):
        """Test LLMResponse without token count."""
        response = LLMResponse(
            docstring="Test docstring",
            provider="ollama",
            model="llama2",
        )
        
        assert response.tokens_used is None


class TestCoverageReport:
    """Tests for CoverageReport model."""
    
    def test_coverage_report_creation(self):
        """Test creating a CoverageReport instance."""
        report = CoverageReport(
            total_functions=10,
            documented_functions=7,
            missing_docstrings=[("file1.py", 10), ("file2.py", 20)],
        )
        
        assert report.total_functions == 10
        assert report.documented_functions == 7
        assert len(report.missing_docstrings) == 2
    
    def test_coverage_percentage_calculation(self):
        """Test coverage percentage calculation."""
        report = CoverageReport(
            total_functions=10,
            documented_functions=7,
        )
        
        assert report.coverage_percentage == 70.0
    
    def test_coverage_percentage_zero_functions(self):
        """Test coverage percentage when no functions exist."""
        report = CoverageReport(
            total_functions=0,
            documented_functions=0,
        )
        
        assert report.coverage_percentage == 0.0
    
    def test_coverage_percentage_full_coverage(self):
        """Test coverage percentage with 100% coverage."""
        report = CoverageReport(
            total_functions=5,
            documented_functions=5,
        )
        
        assert report.coverage_percentage == 100.0
    
    def test_coverage_percentage_no_coverage(self):
        """Test coverage percentage with 0% coverage."""
        report = CoverageReport(
            total_functions=5,
            documented_functions=0,
        )
        
        assert report.coverage_percentage == 0.0


class TestProcessingStats:
    """Tests for ProcessingStats model."""
    
    def test_processing_stats_defaults(self):
        """Test ProcessingStats with default values."""
        stats = ProcessingStats()
        
        assert stats.files_processed == 0
        assert stats.docstrings_added == 0
        assert stats.docstrings_updated == 0
        assert stats.errors == 0
    
    def test_processing_stats_custom_values(self):
        """Test ProcessingStats with custom values."""
        stats = ProcessingStats(
            files_processed=5,
            docstrings_added=10,
            docstrings_updated=3,
            errors=2,
        )
        
        assert stats.files_processed == 5
        assert stats.docstrings_added == 10
        assert stats.docstrings_updated == 3
        assert stats.errors == 2
    
    def test_increment_added(self):
        """Test incrementing added docstrings count."""
        stats = ProcessingStats()
        
        stats.increment_added()
        assert stats.docstrings_added == 1
        
        stats.increment_added()
        assert stats.docstrings_added == 2
    
    def test_increment_updated(self):
        """Test incrementing updated docstrings count."""
        stats = ProcessingStats()
        
        stats.increment_updated()
        assert stats.docstrings_updated == 1
        
        stats.increment_updated()
        assert stats.docstrings_updated == 2
    
    def test_increment_error(self):
        """Test incrementing error count."""
        stats = ProcessingStats()
        
        stats.increment_error()
        assert stats.errors == 1
        
        stats.increment_error()
        assert stats.errors == 2
    
    def test_multiple_increments(self):
        """Test multiple increment operations."""
        stats = ProcessingStats()
        
        stats.increment_added()
        stats.increment_added()
        stats.increment_updated()
        stats.increment_error()
        
        assert stats.docstrings_added == 2
        assert stats.docstrings_updated == 1
        assert stats.errors == 1
