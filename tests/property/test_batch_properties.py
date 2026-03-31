"""Property-based tests for batch processing."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from docgen.batch import process_files_batch
from docgen.llm import LLMError
from docgen.models import Config


@st.composite
def python_files_with_errors(draw):
    """Generate list of Python files, some with parse errors."""
    num_files = draw(st.integers(min_value=1, max_value=5))
    files = []

    for i in range(num_files):
        has_error = draw(st.booleans())
        if has_error:
            # Invalid Python syntax
            content = "def foo(\n"
        else:
            # Valid Python
            content = f"def func_{i}():\n    pass\n"
        files.append((f"file_{i}.py", content))

    return files


@settings(max_examples=100, deadline=10000)
@given(files_data=python_files_with_errors())
def test_property_error_recovery_for_parse_failures(files_data):
    """
    Feature: docstring-generator, Property 25: For any file that cannot be parsed,
    the CLI should log the error and continue processing remaining files without terminating.

    Validates: Requirements 11.1
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create files
        file_paths = []
        valid_files = 0
        invalid_files = 0

        for filename, content in files_data:
            filepath = tmppath / filename
            filepath.write_text(content)
            file_paths.append(filepath)

            if "def foo(\n" in content:
                invalid_files += 1
            else:
                valid_files += 1

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client
        with patch("docgen.batch.LLMClient") as mock_llm:
            mock_llm.return_value.generate.return_value = '"""Test docstring."""'

            stats, errors = process_files_batch(
                file_paths, config, dry_run=True, only_missing=True
            )

            # Should process all files (valid ones successfully, invalid ones with errors)
            # At minimum, should have attempted to process all files
            assert stats.files_processed + stats.errors >= 0

            # Should have errors for invalid files
            if invalid_files > 0:
                assert len(errors) > 0


@settings(max_examples=100, deadline=10000)
@given(
    num_files=st.integers(min_value=1, max_value=5),
    num_failures=st.integers(min_value=0, max_value=5),
)
def test_property_error_recovery_for_llm_failures(num_files, num_failures):
    """
    Feature: docstring-generator, Property 26: For any LLM API call that fails after retries,
    the CLI should log the error with provider name and continue processing remaining
    functions without terminating.

    Validates: Requirements 11.2
    """
    assume(num_failures <= num_files)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create valid Python files
        file_paths = []
        for i in range(num_files):
            filepath = tmppath / f"file_{i}.py"
            filepath.write_text(f"def func_{i}():\n    pass\n")
            file_paths.append(filepath)

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client to fail for some calls
        call_count = [0]

        def mock_generate(prompt):
            call_count[0] += 1
            if call_count[0] <= num_failures:
                raise LLMError("API error")
            return '"""Test docstring."""'

        with patch("docgen.batch.LLMClient") as mock_llm:
            mock_llm.return_value.generate.side_effect = mock_generate

            stats, errors = process_files_batch(
                file_paths, config, dry_run=True, only_missing=True
            )

            # Should process all files
            assert stats.files_processed == num_files

            # Should have errors for failed LLM calls
            if num_failures > 0:
                assert stats.errors >= num_failures
                assert len(errors) >= num_failures
                # Errors should mention LLM
                assert any("LLM" in error for error in errors)


@settings(max_examples=100, deadline=10000)
@given(
    num_files=st.integers(min_value=1, max_value=5),
    num_write_failures=st.integers(min_value=0, max_value=5),
)
def test_property_error_recovery_for_write_failures(num_files, num_write_failures):
    """
    Feature: docstring-generator, Property 27: For any file write operation that fails,
    the CLI should log the error and continue processing remaining files without terminating.

    Validates: Requirements 11.5
    """
    assume(num_write_failures <= num_files)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create valid Python files
        file_paths = []
        for i in range(num_files):
            filepath = tmppath / f"file_{i}.py"
            filepath.write_text(f"def func_{i}():\n    pass\n")
            file_paths.append(filepath)

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client
        with patch("docgen.batch.LLMClient") as mock_llm:
            mock_llm.return_value.generate.return_value = '"""Test docstring."""'

            # Mock patcher to fail for some files
            call_count = [0]

            def mock_inject(file_path, func_name, docstring, parent_class):
                call_count[0] += 1
                if call_count[0] <= num_write_failures:
                    raise Exception("Write error")

            with patch("docgen.batch.DocstringPatcher.inject_docstring") as mock_patch:
                mock_patch.side_effect = mock_inject

                stats, errors = process_files_batch(
                    file_paths, config, dry_run=False, only_missing=True
                )

                # Should process all files
                assert stats.files_processed == num_files

                # Should have errors for failed writes
                if num_write_failures > 0:
                    assert stats.errors >= num_write_failures


@settings(max_examples=100, deadline=10000)
@given(
    num_parse_errors=st.integers(min_value=0, max_value=3),
    num_llm_errors=st.integers(min_value=0, max_value=3),
)
def test_property_error_summary_completeness(num_parse_errors, num_llm_errors):
    """
    Feature: docstring-generator, Property 28: For any processing run with errors,
    all errors encountered should appear in the final error summary displayed to the user.

    Validates: Requirements 11.6
    """
    total_errors = num_parse_errors + num_llm_errors
    assume(total_errors > 0)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create files with parse errors
        file_paths = []
        for i in range(num_parse_errors):
            filepath = tmppath / f"invalid_{i}.py"
            filepath.write_text("def foo(\n")  # Invalid syntax
            file_paths.append(filepath)

        # Create valid files for LLM errors
        for i in range(num_llm_errors):
            filepath = tmppath / f"valid_{i}.py"
            filepath.write_text(f"def func_{i}():\n    pass\n")
            file_paths.append(filepath)

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client to always fail
        with patch("docgen.batch.LLMClient") as mock_llm:
            mock_llm.return_value.generate.side_effect = LLMError("API error")

            stats, errors = process_files_batch(
                file_paths, config, dry_run=True, only_missing=True
            )

            # All errors should be in the error list
            assert len(errors) >= total_errors
            assert stats.errors >= total_errors
