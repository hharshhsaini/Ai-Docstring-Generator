"""Property-based tests for Config default values.

**Validates: Requirements 7.2, 7.3, 7.6**
"""

import pytest
from hypothesis import given, strategies as st

from docgen.models import Config


@pytest.mark.property
class TestConfigDefaultValues:
    """Property tests for Config default values."""
    
    @given(
        style=st.one_of(st.none(), st.sampled_from(["google", "numpy", "sphinx"])),
        provider=st.one_of(st.none(), st.sampled_from(["anthropic", "openai", "ollama"])),
        overwrite_existing=st.one_of(st.none(), st.booleans()),
    )
    def test_property_18_config_default_values(
        self,
        style,
        provider,
        overwrite_existing,
    ):
        """Property 18: Config Default Values.
        
        For any missing configuration value, the Config model should use the
        documented default value (google for style, anthropic for provider,
        false for overwrite_existing).
        
        **Validates: Requirements 7.2, 7.3, 7.6**
        """
        # Build config dict with only non-None values
        config_dict = {}
        if style is not None:
            config_dict["style"] = style
        if provider is not None:
            config_dict["provider"] = provider
        if overwrite_existing is not None:
            config_dict["overwrite_existing"] = overwrite_existing
        
        # Create config instance
        config = Config(**config_dict)
        
        # Verify defaults are applied for missing values
        # Requirement 7.2: style defaults to "google"
        if style is None:
            assert config.style == "google", "style should default to 'google'"
        else:
            assert config.style == style
        
        # Requirement 7.3: provider defaults to "anthropic"
        if provider is None:
            assert config.provider == "anthropic", "provider should default to 'anthropic'"
        else:
            assert config.provider == provider
        
        # Requirement 7.6: overwrite_existing defaults to False
        if overwrite_existing is None:
            assert config.overwrite_existing is False, "overwrite_existing should default to False"
        else:
            assert config.overwrite_existing == overwrite_existing
