"""Unit tests for batch processing."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from docgen.batch import process_files_batch, ParseError, PatchError
from docgen.models import Config


def test_process_files_batch_success():
    """Test successful batch processing of multiple files."""
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        file1 = tmppath / "test1.py"
        file1.write_text("def foo():\n    pass\n")

        file2 = tmppath / "test2.py"
        file2.write_text("def bar():\n    pass\n")

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
                [file1, file2], config, dry_run=False, only_missing=True
            )

            assert stats.files_processed == 2
            assert stats.docstrings_added >= 0
            assert len(errors) == 0


def test_process_files_batch_with_parse_error():
    """Test batch processing with parse errors."""
    # Create temporary file with invalid Python
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        invalid_file = tmppath / "invalid.py"
        invalid_file.write_text("def foo(\n")  # Invalid syntax

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        stats, errors = process_files_batch(
            [invalid_file], config, dry_run=False, only_missing=True
        )

        # Should continue processing despite error
        assert stats.errors > 0
        assert len(errors) > 0
        assert "Parse error" in errors[0]


def test_process_files_batch_with_llm_error():
    """Test batch processing with LLM errors."""
    # Create temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client to raise error
        with patch("docgen.batch.LLMClient") as mock_llm:
            from docgen.llm import LLMError

            mock_llm.return_value.generate.side_effect = LLMError("API error")

            stats, errors = process_files_batch(
                [test_file], config, dry_run=False, only_missing=True
            )

            # Should continue processing despite error
            assert stats.files_processed == 1
            assert stats.errors > 0
            assert len(errors) > 0
            assert "LLM error" in errors[0]


def test_process_files_batch_dry_run():
    """Test batch processing in dry-run mode."""
    # Create temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        test_file = tmppath / "test.py"
        original_content = "def foo():\n    pass\n"
        test_file.write_text(original_content)

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
                [test_file], config, dry_run=True, only_missing=True
            )

            # File should not be modified in dry-run mode
            assert test_file.read_text() == original_content
            assert stats.files_processed == 1


def test_process_files_batch_only_missing():
    """Test batch processing with only_missing flag."""
    # Create temporary file with existing docstring
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        test_file = tmppath / "test.py"
        test_file.write_text('def foo():\n    """Existing."""\n    pass\n')

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client
        with patch("docgen.batch.LLMClient") as mock_llm:
            mock_llm.return_value.generate.return_value = '"""New docstring."""'

            stats, errors = process_files_batch(
                [test_file], config, dry_run=False, only_missing=True
            )

            # Should skip function with existing docstring
            assert stats.files_processed == 1
            assert stats.docstrings_added == 0
            assert stats.docstrings_updated == 0


def test_process_files_batch_error_summary():
    """Test that all errors are collected in summary."""
    # Create multiple files with different error types
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Invalid syntax file
        invalid_file = tmppath / "invalid.py"
        invalid_file.write_text("def foo(\n")

        # Valid file for LLM error
        valid_file = tmppath / "valid.py"
        valid_file.write_text("def bar():\n    pass\n")

        config = Config(
            style="google",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        # Mock LLM client to raise error
        with patch("docgen.batch.LLMClient") as mock_llm:
            from docgen.llm import LLMError

            mock_llm.return_value.generate.side_effect = LLMError("API error")

            stats, errors = process_files_batch(
                [invalid_file, valid_file], config, dry_run=False, only_missing=True
            )

            # Should collect all errors
            assert len(errors) >= 2
            assert stats.errors >= 2
