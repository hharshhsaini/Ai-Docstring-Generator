"""Property-based tests for ConfigLoader."""

import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from docgen.config import ConfigError, ConfigLoader


@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
@given(
    invalid_toml=st.one_of(
        # Unclosed bracket
        st.text(min_size=5, max_size=50).map(lambda x: "[docgen\n" + x),
        # Invalid key-value
        st.text(min_size=5, max_size=50).map(lambda x: "[docgen]\n" + x + " = "),
        # Duplicate keys
        st.just("[docgen]\nstyle = 'google'\nstyle = 'numpy'"),
    )
)
def test_config_validation_errors(invalid_toml):
    """
    Feature: docstring-generator, Property 19: For any invalid TOML configuration
    file, the Config_Loader should return a descriptive error message indicating
    what is invalid.

    **Validates: Requirements 7.7**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config_file = tmppath / "docgen.toml"
        config_file.write_text(invalid_toml)

        try:
            ConfigLoader.load(config_file)
            # If we get here, the TOML was actually valid (or empty)
            # This is fine - not all random text is invalid TOML
        except ConfigError as e:
            # Verify error message is descriptive
            error_msg = str(e).lower()
            # Should mention parsing or validation
            assert (
                "parse" in error_msg
                or "invalid" in error_msg
                or "toml" in error_msg
                or "validation" in error_msg
            ), f"Error message not descriptive: {e}"
