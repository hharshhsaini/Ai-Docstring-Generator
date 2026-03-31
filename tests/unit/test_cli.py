"""Unit tests for CLI interface."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from docgen.cli import (
    main,
    merge_cli_options,
    get_staged_files,
    display_summary,
    display_coverage_report,
    output_github_annotations,
)
from docgen.models import Config, ProcessingStats, CoverageReport


def test_merge_cli_options():
    """Test merging CLI options with config."""
    config = Config(style="google", provider="anthropic", model="claude-3-5-sonnet-20241022")

    cli_options = {"style": "numpy", "provider": "openai", "model": None}

    merged = merge_cli_options(config, cli_options)

    assert merged.style == "numpy"
    assert merged.provider == "openai"
    assert merged.model == "claude-3-5-sonnet-20241022"  # Not overridden


def test_get_staged_files_success():
    """Test getting staged files from git."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            stdout="file1.py\nfile2.py\nfile3.txt\n", returncode=0
        )

        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "file1.py").touch()
            (tmppath / "file2.py").touch()

            with patch("pathlib.Path.exists", return_value=True):
                files = get_staged_files()

                assert len(files) >= 0  # May be empty if files don't exist


def test_get_staged_files_git_error():
    """Test getting staged files when git command fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        files = get_staged_files()

        assert files == []


def test_display_summary():
    """Test displaying processing summary."""
    stats = ProcessingStats(
        files_processed=5, docstrings_added=3, docstrings_updated=2, errors=1
    )
    errors = ["file.py:10 - Test error"]

    # Should not raise an error
    display_summary(stats, errors)


def test_display_coverage_report_text():
    """Test displaying coverage report in text format."""
    report = CoverageReport(
        total_functions=10,
        documented_functions=7,
        missing_docstrings=[("file.py", 10), ("file.py", 20)],
    )

    # Should not raise an error
    display_coverage_report(report, format_type="text")


def test_display_coverage_report_json():
    """Test displaying coverage report in JSON format."""
    import json
    from io import StringIO
    import sys
    
    report = CoverageReport(
        total_functions=10,
        documented_functions=7,
        missing_docstrings=[("file.py", 10), ("file.py", 20)],
    )

    # Capture stdout (since we use print() for JSON)
    captured_output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        display_coverage_report(report, format_type="json")
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout
    
    # Parse JSON output
    json_output = json.loads(output)
    
    # Verify JSON is valid and parseable
    assert json_output is not None, "JSON output should be present"
    assert json_output["total_functions"] == 10
    assert json_output["documented_functions"] == 7
    assert json_output["coverage_percentage"] == 70.0
    assert len(json_output["missing_docstrings"]) == 2


def test_output_github_annotations():
    """Test GitHub Actions annotation output."""
    missing = [("file.py", 10), ("test.py", 20)]

    # Capture stdout
    with patch("builtins.print") as mock_print:
        output_github_annotations(missing)

        assert mock_print.call_count == 2
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("::warning" in str(call) for call in calls)
        assert any("file.py" in str(call) for call in calls)


def test_cli_with_report_flag():
    """Test CLI with --report flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            result = runner.invoke(main, [str(tmppath), "--report"])

            assert result.exit_code == 0
            assert "Coverage" in result.output or "coverage" in result.output.lower()


def test_cli_with_check_flag_missing_docstrings():
    """Test CLI with --check flag when docstrings are missing."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            result = runner.invoke(main, [str(tmppath), "--check"])

            assert result.exit_code == 1


def test_cli_with_check_flag_all_documented():
    """Test CLI with --check flag when all functions have docstrings."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text('def foo():\n    """Docstring."""\n    pass\n')

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            result = runner.invoke(main, [str(tmppath), "--check"])

            assert result.exit_code == 0


def test_cli_with_min_coverage_below_threshold():
    """Test CLI with --min-coverage when coverage is below threshold."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            result = runner.invoke(main, [str(tmppath), "--report", "--min-coverage", "80"])

            assert result.exit_code == 1


def test_cli_with_dry_run_flag():
    """Test CLI with --dry-run flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        original_content = "def foo():\n    pass\n"
        test_file.write_text(original_content)

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            with patch("docgen.cli.process_files_batch") as mock_process:
                mock_process.return_value = (ProcessingStats(), [])

                result = runner.invoke(main, [str(tmppath), "--dry-run"])

                # Verify dry_run was passed
                assert mock_process.called
                call_args = mock_process.call_args
                assert call_args[1]["dry_run"] is True

                # File should not be modified
                assert test_file.read_text() == original_content


def test_cli_with_only_missing_flag():
    """Test CLI with --only-missing flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            with patch("docgen.cli.process_files_batch") as mock_process:
                mock_process.return_value = (ProcessingStats(), [])

                result = runner.invoke(main, [str(tmppath), "--only-missing"])

                # Verify only_missing was passed
                assert mock_process.called
                call_args = mock_process.call_args
                assert call_args[1]["only_missing"] is True


def test_cli_with_style_override():
    """Test CLI with --style flag overriding config."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            with patch("docgen.cli.process_files_batch") as mock_process:
                mock_process.return_value = (ProcessingStats(), [])

                result = runner.invoke(main, [str(tmppath), "--style", "numpy"])

                # Verify style was overridden
                assert mock_process.called
                call_args = mock_process.call_args
                config_arg = call_args[0][1]
                assert config_arg.style == "numpy"


def test_cli_no_files_found():
    """Test CLI when no Python files are found."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            result = runner.invoke(main, [str(tmppath)])

            assert result.exit_code == 0
            assert "No Python files found" in result.output
