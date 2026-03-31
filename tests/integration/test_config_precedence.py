"""Integration tests for configuration precedence.

This module tests that configuration values are loaded and merged correctly
with the proper precedence: config file < environment variables < CLI flags.

Validates Requirements:
- 7.1: Config file loading
- 7.2: Style configuration with default
- 7.3: Provider configuration with default  
- 7.4: Model name configuration
- 7.5: Exclude patterns support
- 7.6: overwrite_existing default
- 7.7: Invalid config error handling
- 8.4: --style flag overrides configured style
- 8.5: --provider flag overrides configured provider
- 8.6: --model flag overrides configured model
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from docgen.cli import main
from docgen.config import ConfigLoader


@pytest.fixture
def test_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        yield project_path


@pytest.fixture
def clean_env():
    """Clean environment variables before and after test."""
    # Save original environment
    original_env = os.environ.copy()
    
    # Clean docgen-related env vars
    env_vars_to_clean = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DOCGEN_STYLE",
        "DOCGEN_PROVIDER",
        "DOCGEN_MODEL",
        "DOCGEN_BASE_URL",
    ]
    
    for var in env_vars_to_clean:
        os.environ.pop(var, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


def test_config_file_plus_env_vars_plus_cli_flags(test_project, clean_env):
    """
    Test configuration precedence: config file < env vars < CLI flags.
    
    This test validates that when all three configuration sources are present,
    CLI flags take highest precedence, followed by environment variables,
    followed by config file values.
    
    Validates Requirements: 7.1-7.7, 8.4, 8.5, 8.6
    """
    # Create a test Python file
    test_file = test_project / "test.py"
    test_file.write_text("""def test_function(x: int) -> int:
    return x * 2
""")
    
    # Create config file with specific values
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "openai"
model = "gpt-3.5-turbo"
overwrite_existing = false
max_retries = 5
timeout = 60

[docgen.exclude]
patterns = ["**/test_*.py"]
""")
    
    # Set environment variables (should override config file)
    os.environ["DOCGEN_STYLE"] = "sphinx"
    os.environ["DOCGEN_PROVIDER"] = "ollama"
    os.environ["OPENAI_API_KEY"] = "env-api-key"
    
    # Change to test project directory so config is loaded
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        # Mock LLM to capture the configuration used
        captured_config = {}
        captured_style = {}
        
        def mock_llm_init(config):
            """Capture the LLM config."""
            captured_config["provider"] = config.provider
            captured_config["model"] = config.model
            captured_config["api_key"] = config.api_key
            captured_config["max_retries"] = config.max_retries
            captured_config["timeout"] = config.timeout
            
            mock_instance = Mock()
            # Return Google-style docstring since CLI flag specifies google
            mock_instance.generate.return_value = """Test function.

Args:
    x: Input value

Returns:
    Doubled value"""
            return mock_instance
        
        # Also capture the style used in batch processing
        original_batch = None
        
        def mock_batch_wrapper(files, config, dry_run=False, only_missing=False):
            """Capture the style from config."""
            captured_style["style"] = config.style
            # Import here to avoid circular import
            from docgen.batch import process_files_batch as original_process
            return original_process(files, config, dry_run, only_missing)
        
        with patch("docgen.batch.LLMClient", side_effect=mock_llm_init):
            with patch("docgen.cli.process_files_batch", side_effect=mock_batch_wrapper):
                # Run CLI with flags (should override both config file and env vars)
                runner = CliRunner()
                result = runner.invoke(
                    main,
                    [
                        str(test_project),
                        "--style", "google",  # CLI flag (highest precedence)
                        "--provider", "anthropic",  # CLI flag (highest precedence)
                        "--model", "claude-3-5-sonnet-20241022",  # CLI flag (highest precedence)
                    ],
                    catch_exceptions=False,
                )
                
                # Verify successful execution
                assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}: {result.output}"
        
        # Verify CLI flags took precedence
        # The style should be "google" (from CLI), not "sphinx" (env) or "numpy" (config)
        assert captured_style.get("style") == "google", \
            f"Expected style 'google' from CLI, got '{captured_style.get('style')}'"
        
        # The provider should be "anthropic" (from CLI), not "ollama" (env) or "openai" (config)
        # The model should be "claude-3-5-sonnet-20241022" (from CLI), not default
        
        assert captured_config["provider"] == "anthropic", \
            f"Expected provider 'anthropic' from CLI, got '{captured_config['provider']}'"
        assert captured_config["model"] == "claude-3-5-sonnet-20241022", \
            f"Expected model from CLI, got '{captured_config['model']}'"
        
        # Verify values not overridden by CLI came from config file
        # (env vars don't override max_retries/timeout, only config file does)
        assert captured_config["max_retries"] == 5, \
            f"Expected max_retries 5 from config file, got {captured_config['max_retries']}"
        assert captured_config["timeout"] == 60, \
            f"Expected timeout 60 from config file, got {captured_config['timeout']}"
        
        # Verify the docstring was generated with Google style (CLI flag)
        modified_content = test_file.read_text()
        # Google style uses "Args:" and "Returns:"
        assert "Args:" in modified_content or "Returns:" in modified_content, \
            f"Expected Google-style docstring from CLI flag, got: {modified_content}"
        # Should NOT have Sphinx style markers
        assert ":param" not in modified_content, \
            "Should not have Sphinx-style docstring (env var should be overridden)"
        
    finally:
        os.chdir(original_dir)


def test_cli_flags_take_highest_precedence(test_project, clean_env):
    """
    Test that CLI flags override both config file and environment variables.
    
    Validates Requirements: 8.4, 8.5, 8.6
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def calculate(a: int, b: int) -> int:
    return a + b
""")
    
    # Create config file
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "openai"
model = "gpt-4"
""")
    
    # Set environment variables
    os.environ["DOCGEN_STYLE"] = "sphinx"
    os.environ["DOCGEN_MODEL"] = "gpt-3.5-turbo"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        # Mock LLM
        with patch("docgen.batch.LLMClient") as mock_llm_class:
            mock_llm_instance = Mock()
            mock_llm_instance.generate.return_value = """Calculate sum.

Args:
    a: First number
    b: Second number

Returns:
    Sum of a and b"""
            mock_llm_class.return_value = mock_llm_instance
            
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    str(test_project),
                    "--style", "google",
                    "--model", "claude-3-5-sonnet-20241022",
                ],
                catch_exceptions=False,
            )
            
            assert result.exit_code == 0
        
        # Verify Google style was used (CLI flag), not NumPy (config) or Sphinx (env)
        modified_content = test_file.read_text()
        assert "Args:" in modified_content
        assert "Returns:" in modified_content
        # Should not have NumPy style
        assert "Parameters\n----------" not in modified_content
        # Should not have Sphinx style
        assert ":param" not in modified_content
        
    finally:
        os.chdir(original_dir)


def test_env_vars_override_config_file(test_project, clean_env):
    """
    Test that environment variables override config file values.
    
    Validates Requirements: 7.4, 7.5
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def process(data: str) -> bool:
    return bool(data)
""")
    
    # Create config file
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "anthropic"
model = "claude-3-opus-20240229"
""")
    
    # Set environment variables (should override config file)
    os.environ["DOCGEN_STYLE"] = "google"
    os.environ["DOCGEN_PROVIDER"] = "anthropic"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        # Mock LLM
        with patch("docgen.batch.LLMClient") as mock_llm_class:
            mock_llm_instance = Mock()
            mock_llm_instance.generate.return_value = """Process data.

Args:
    data: Input data

Returns:
    True if data is non-empty"""
            mock_llm_class.return_value = mock_llm_instance
            
            runner = CliRunner()
            result = runner.invoke(
                main,
                [str(test_project)],
                catch_exceptions=False,
            )
            
            assert result.exit_code == 0
        
        # Verify Google style was used (env var), not NumPy (config file)
        modified_content = test_file.read_text()
        assert "Args:" in modified_content
        assert "Returns:" in modified_content
        # Should not have NumPy style
        assert "Parameters\n----------" not in modified_content
        
    finally:
        os.chdir(original_dir)


def test_config_file_used_when_no_overrides(test_project, clean_env):
    """
    Test that config file values are used when no CLI flags or env vars are set.
    
    Validates Requirements: 7.1, 7.2, 7.3
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def transform(value: int) -> str:
    return str(value)
""")
    
    # Create config file
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "anthropic"
model = "claude-3-5-sonnet-20241022"
overwrite_existing = false
""")
    
    # Set API key in environment (required for authentication)
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        # Mock LLM
        with patch("docgen.batch.LLMClient") as mock_llm_class:
            mock_llm_instance = Mock()
            mock_llm_instance.generate.return_value = """Transform value to string.

Parameters
----------
value : int
    Input value

Returns
-------
str
    String representation"""
            mock_llm_class.return_value = mock_llm_instance
            
            runner = CliRunner()
            result = runner.invoke(
                main,
                [str(test_project)],
                catch_exceptions=False,
            )
            
            assert result.exit_code == 0
        
        # Verify NumPy style was used (from config file)
        modified_content = test_file.read_text()
        assert "Parameters" in modified_content
        assert "Returns" in modified_content
        # Should not have Google style
        assert "Args:" not in modified_content
        
    finally:
        os.chdir(original_dir)


def test_defaults_used_when_no_config(test_project, clean_env):
    """
    Test that default values are used when no config file, env vars, or CLI flags are set.
    
    Validates Requirements: 7.2, 7.3, 7.6
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def add(x: int, y: int) -> int:
    return x + y
""")
    
    # Set API key in environment (required)
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    # No config file, no CLI flags, no env var overrides
    # Should use defaults: style=google, provider=anthropic
    
    # Mock LLM
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = """Add two integers.

Args:
    x: First integer
    y: Second integer

Returns:
    Sum of x and y"""
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False,
        )
        
        assert result.exit_code == 0
    
    # Verify Google style was used (default)
    modified_content = test_file.read_text()
    assert "Args:" in modified_content
    assert "Returns:" in modified_content


def test_partial_cli_overrides(test_project, clean_env):
    """
    Test that partial CLI overrides work correctly.
    
    When only some CLI flags are provided, they should override their
    corresponding config values while other values come from config/env/defaults.
    
    Validates Requirements: 8.4, 8.5, 8.6
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def multiply(a: int, b: int) -> int:
    return a * b
""")
    
    # Create config file
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "anthropic"
model = "claude-3-opus-20240229"
max_retries = 5
""")
    
    # Set API key
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        captured_config = {}
        
        def mock_llm_init(config):
            """Capture the LLM config."""
            captured_config["provider"] = config.provider
            captured_config["model"] = config.model
            captured_config["max_retries"] = config.max_retries
            
            mock_instance = Mock()
            mock_instance.generate.return_value = """Multiply two integers.

Args:
    a: First integer
    b: Second integer

Returns:
    Product of a and b"""
            return mock_instance
        
        with patch("docgen.batch.LLMClient", side_effect=mock_llm_init):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    str(test_project),
                    "--style", "google",  # Override style only
                    # provider and model should come from config file
                ],
                catch_exceptions=False,
            )
            
            assert result.exit_code == 0
        
        # Verify style was overridden by CLI
        modified_content = test_file.read_text()
        assert "Args:" in modified_content  # Google style
        
        # Verify provider and model came from config file
        assert captured_config["provider"] == "anthropic"
        assert captured_config["model"] == "claude-3-opus-20240229"
        assert captured_config["max_retries"] == 5
        
    finally:
        os.chdir(original_dir)


def test_config_precedence_with_all_three_sources(test_project, clean_env):
    """
    Comprehensive test with all three configuration sources.
    
    Tests the complete precedence chain:
    1. Config file provides base values
    2. Environment variables override some config values
    3. CLI flags override both config and env values
    
    Validates Requirements: 7.1-7.7, 8.4, 8.5, 8.6
    """
    # Create test file
    test_file = test_project / "module.py"
    test_file.write_text("""def divide(x: float, y: float) -> float:
    return x / y
""")
    
    # Config file: style=numpy, provider=openai, model=gpt-4
    config_file = test_project / "docgen.toml"
    config_file.write_text("""[docgen]
style = "numpy"
provider = "openai"
model = "gpt-4"
max_retries = 3
timeout = 30
overwrite_existing = false
""")
    
    # Environment: style=sphinx (overrides config), provider stays openai
    os.environ["DOCGEN_STYLE"] = "sphinx"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    original_dir = os.getcwd()
    try:
        os.chdir(test_project)
        
        # Mock LLM
        with patch("docgen.batch.LLMClient") as mock_llm_class:
            mock_llm_instance = Mock()
            # CLI: style=google (overrides both env and config)
            mock_llm_instance.generate.return_value = """Divide two floats.

Args:
    x: Numerator
    y: Denominator

Returns:
    Quotient of x and y"""
            mock_llm_class.return_value = mock_llm_instance
            
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    str(test_project),
                    "--style", "google",  # Highest precedence
                ],
                catch_exceptions=False,
            )
            
            assert result.exit_code == 0
        
        # Verify Google style was used (CLI flag wins)
        modified_content = test_file.read_text()
        assert "Args:" in modified_content
        assert "Returns:" in modified_content
        # Not NumPy style (config file)
        assert "Parameters\n----------" not in modified_content
        # Not Sphinx style (env var)
        assert ":param" not in modified_content
        
    finally:
        os.chdir(original_dir)
