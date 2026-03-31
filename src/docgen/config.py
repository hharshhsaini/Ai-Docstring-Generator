"""Configuration management for docstring generator."""

import os
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pydantic import ValidationError

from docgen.models import Config


class ConfigError(Exception):
    """Configuration-related errors."""

    pass


class ConfigLoader:
    """Loads and validates configuration from TOML files."""

    @staticmethod
    def load(config_path: Optional[Path] = None) -> Config:
        """
        Load configuration from TOML file.

        Args:
            config_path: Path to docgen.toml (defaults to ./docgen.toml)

        Returns:
            Validated configuration object

        Raises:
            ConfigError: If configuration file is invalid
        """
        # Default to ./docgen.toml if not specified
        if config_path is None:
            config_path = Path("docgen.toml")

        # If config file doesn't exist, return defaults
        if not config_path.exists():
            return Config()

        # Read and parse TOML
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to parse TOML file: {e}")

        # Extract docgen section
        docgen_config = data.get("docgen", {})

        # Handle nested sections
        if "exclude" in docgen_config and isinstance(docgen_config["exclude"], dict):
            # Handle [docgen.exclude] section with patterns key
            exclude_patterns = docgen_config["exclude"].get("patterns", [])
            docgen_config["exclude"] = exclude_patterns

        if "llm" in docgen_config:
            # Merge llm section into main config
            llm_config = docgen_config.pop("llm")
            docgen_config.update(llm_config)

        # Override with environment variables
        env_overrides = ConfigLoader._load_from_env()
        docgen_config.update(env_overrides)

        # Validate and create Config object
        try:
            config = Config(**docgen_config)
        except ValidationError as e:
            raise ConfigError(f"Invalid configuration: {e}")

        return config

    @staticmethod
    def _load_from_env() -> dict:
        """
        Load configuration overrides from environment variables.

        Returns:
            Dictionary of configuration values from environment
        """
        env_config = {}

        # Check for API keys
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            env_config["api_key"] = api_key
        elif api_key := os.getenv("OPENAI_API_KEY"):
            env_config["api_key"] = api_key

        # Check for other config values
        if style := os.getenv("DOCGEN_STYLE"):
            env_config["style"] = style

        if provider := os.getenv("DOCGEN_PROVIDER"):
            env_config["provider"] = provider

        if model := os.getenv("DOCGEN_MODEL"):
            env_config["model"] = model

        if base_url := os.getenv("DOCGEN_BASE_URL"):
            env_config["base_url"] = base_url

        return env_config

    @staticmethod
    def merge_cli_options(config: Config, cli_options: dict) -> Config:
        """
        Merge CLI options with config (CLI takes precedence).

        Args:
            config: Base configuration
            cli_options: Dictionary of CLI options

        Returns:
            Merged configuration
        """
        # Create a dict from config
        config_dict = config.model_dump()

        # Override with CLI options (only if not None)
        for key, value in cli_options.items():
            if value is not None:
                config_dict[key] = value

        # Create new config with merged values
        return Config(**config_dict)
