"""Unit tests for ConfigLoader."""

import os
import tempfile
from pathlib import Path

import pytest

from docgen.config import ConfigError, ConfigLoader
from docgen.models import Config


def test_load_valid_config():
    """Test loading a valid config file."""
    config_content = """
[docgen]
style = "numpy"
provider = "openai"
model = "gpt-4"
overwrite_existing = true

[docgen.exclude]
patterns = ["**/test_*.py", "**/migrations/**"]

[docgen.llm]
max_retries = 5
timeout = 60
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        config = ConfigLoader.load(config_file)

        assert config.style == "numpy"
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.overwrite_existing is True
        assert config.exclude == ["**/test_*.py", "**/migrations/**"]
        assert config.max_retries == 5
        assert config.timeout == 60


def test_load_missing_config_uses_defaults():
    """Test that missing config file returns default values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "nonexistent.toml"

        config = ConfigLoader.load(config_file)

        # Should use defaults
        assert config.style == "google"
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.overwrite_existing is False
        assert config.exclude == []


def test_invalid_toml_syntax():
    """Test that invalid TOML syntax raises ConfigError."""
    invalid_toml = """
[docgen
invalid toml syntax
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(invalid_toml)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.load(config_file)

        assert "parse" in str(exc_info.value).lower() or "toml" in str(
            exc_info.value
        ).lower()


def test_environment_variable_override():
    """Test that environment variables override config file."""
    config_content = """
[docgen]
style = "google"
provider = "anthropic"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        # Set environment variable
        os.environ["ANTHROPIC_API_KEY"] = "test-key-from-env"

        try:
            config = ConfigLoader.load(config_file)
            assert config.api_key == "test-key-from-env"
        finally:
            # Clean up
            del os.environ["ANTHROPIC_API_KEY"]


def test_missing_api_key_for_cloud_provider():
    """Test that missing API key for cloud provider results in None api_key."""
    config_content = """
[docgen]
provider = "anthropic"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        # Make sure no API key in environment
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)

        try:
            config = ConfigLoader.load(config_file)
            # API key should be None if not in environment
            assert config.api_key is None
        finally:
            # Restore if it existed
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key


def test_merge_cli_options():
    """Test merging CLI options with config."""
    config = Config(style="google", provider="anthropic", model="claude-3-5-sonnet-20241022")

    cli_options = {"style": "numpy", "provider": "openai", "model": None}

    merged = ConfigLoader.merge_cli_options(config, cli_options)

    # CLI options should override (except None values)
    assert merged.style == "numpy"
    assert merged.provider == "openai"
    assert merged.model == "claude-3-5-sonnet-20241022"  # Not overridden by None


def test_cli_options_take_precedence():
    """Test that CLI options take precedence over config file."""
    config_content = """
[docgen]
style = "google"
provider = "anthropic"
model = "claude-3-5-sonnet-20241022"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        config = ConfigLoader.load(config_file)

        # Merge with CLI options
        cli_options = {"style": "sphinx", "provider": "ollama"}
        merged = ConfigLoader.merge_cli_options(config, cli_options)

        assert merged.style == "sphinx"
        assert merged.provider == "ollama"
        assert merged.model == "claude-3-5-sonnet-20241022"  # Not overridden


def test_invalid_style_value():
    """Test that invalid style value raises ConfigError."""
    config_content = """
[docgen]
style = "invalid_style"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.load(config_file)

        assert "invalid" in str(exc_info.value).lower()


def test_invalid_provider_value():
    """Test that invalid provider value raises ConfigError."""
    config_content = """
[docgen]
provider = "invalid_provider"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigError) as exc_info:
            ConfigLoader.load(config_file)

        assert "invalid" in str(exc_info.value).lower()
