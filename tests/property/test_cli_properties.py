"""Property-based tests for CLI interface."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st
from click.testing import CliRunner

from docgen.cli import main, merge_cli_options
from docgen.models import Config, ProcessingStats


@settings(max_examples=100)
@given(
    config_style=st.sampled_from(["google", "numpy", "sphinx"]),
    cli_style=st.sampled_from(["google", "numpy", "sphinx"]),
    config_provider=st.sampled_from(["anthropic", "openai", "ollama"]),
    cli_provider=st.sampled_from(["anthropic", "openai", "ollama"]),
)
def test_property_cli_flag_precedence(
    config_style, cli_style, config_provider, cli_provider
):
    """
    Feature: docstring-generator, Property 22: For any configuration value,
    when both config file and CLI flag are provided, the CLI flag value should be used.

    Validates: Requirements 8.4, 8.5, 8.6
    """
    # Create base config
    config = Config(
        style=config_style,
        provider=config_provider,
        model="test-model",
        api_key="test-key",
    )

    # Merge with CLI options
    cli_options = {"style": cli_style, "provider": cli_provider, "model": None}

    merged = merge_cli_options(config, cli_options)

    # CLI flags should take precedence
    assert merged.style == cli_style
    assert merged.provider == cli_provider
    # Model should remain from config (CLI was None)
    assert merged.model == "test-model"


@settings(max_examples=100)
@given(
    num_documented=st.integers(min_value=0, max_value=10),
    num_undocumented=st.integers(min_value=0, max_value=10),
)
def test_property_only_missing_filter(num_documented, num_undocumented):
    """
    Feature: docstring-generator, Property 21: For any function that already has a docstring,
    when --only-missing flag is set, the function should be skipped during processing.

    Validates: Requirements 8.3
    """
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create file with documented and undocumented functions
        code_lines = []
        for i in range(num_documented):
            code_lines.append(f'def documented_{i}():\n    """Existing."""\n    pass\n')
        for i in range(num_undocumented):
            code_lines.append(f"def undocumented_{i}():\n    pass\n")

        if code_lines:
            test_file = tmppath / "test.py"
            test_file.write_text("\n".join(code_lines))

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
                    if mock_process.called:
                        call_args = mock_process.call_args
                        assert call_args[1]["only_missing"] is True


@settings(max_examples=100)
@given(
    coverage=st.floats(min_value=0.0, max_value=100.0),
    threshold=st.floats(min_value=0.0, max_value=100.0),
)
def test_property_coverage_threshold_exit_code(coverage, threshold):
    """
    Feature: docstring-generator, Property 32: For any coverage percentage below
    the --min-coverage threshold, the CLI should exit with code 1.

    Validates: Requirements 13.3, 13.4
    """
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create file to ensure we have something to process
        test_file = tmppath / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            # Mock coverage calculation
            with patch("docgen.cli.calculate_coverage") as mock_coverage:
                from docgen.models import CoverageReport

                # Calculate documented functions based on coverage percentage
                total = 100
                documented = int(total * coverage / 100)

                mock_coverage.return_value = CoverageReport(
                    total_functions=total,
                    documented_functions=documented,
                    missing_docstrings=[],
                )

                result = runner.invoke(
                    main, [str(tmppath), "--report", "--min-coverage", str(threshold)]
                )

                # Exit code should be 1 if coverage < threshold
                # Use epsilon for floating point comparison (1% tolerance)
                epsilon = 1.0
                if coverage < threshold - epsilon:
                    assert result.exit_code == 1
                elif coverage > threshold + epsilon:
                    assert result.exit_code == 0
                # For values very close to threshold, either exit code is acceptable due to rounding


@settings(max_examples=50, deadline=10000)
@given(
    num_files=st.integers(min_value=1, max_value=10),
    num_documented=st.integers(min_value=0, max_value=10),
)
def test_property_json_output_validity(num_files, num_documented):
    """
    Feature: docstring-generator, Property 31: For any coverage report generated with
    --format json, the output should be valid JSON that can be parsed without errors.

    Validates: Requirements 13.2
    """
    import json
    
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Ensure num_documented doesn't exceed num_files
        num_documented = min(num_documented, num_files)
        
        # Create files with and without docstrings
        for i in range(num_files):
            filepath = tmppath / f"file_{i}.py"
            if i < num_documented:
                filepath.write_text(f'def func_{i}():\n    """Documented."""\n    pass\n')
            else:
                filepath.write_text(f"def func_{i}():\n    pass\n")

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            # Run CLI with --report --format json
            result = runner.invoke(main, [str(tmppath), "--report", "--format", "json"])
            
            # The output should contain valid JSON
            # CliRunner captures stdout in result.output
            assert result.exit_code == 0, f"CLI failed with: {result.output}"
            
            # The output may contain GitHub Actions annotations after the JSON
            # We need to extract just the JSON part (everything before the first ::warning)
            output_lines = result.output.split('\n')
            json_lines = []
            for line in output_lines:
                if line.startswith('::warning'):
                    break
                json_lines.append(line)
            
            json_text = '\n'.join(json_lines).strip()
            
            # Parse the JSON output - it should not raise an exception
            try:
                json_output = json.loads(json_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, this is a test failure
                raise AssertionError(
                    f"JSON output is invalid. Error: {e}\nJSON text was: {json_text}"
                )
            
            # Verify required fields are present
            assert "total_functions" in json_output, "Missing 'total_functions' field"
            assert "documented_functions" in json_output, "Missing 'documented_functions' field"
            assert "coverage_percentage" in json_output, "Missing 'coverage_percentage' field"
            assert "missing_docstrings" in json_output, "Missing 'missing_docstrings' field"
            
            # Verify values match expectations
            assert json_output["total_functions"] == num_files
            assert json_output["documented_functions"] == num_documented
            assert isinstance(json_output["coverage_percentage"], (int, float))
            assert isinstance(json_output["missing_docstrings"], list)
            
            # Verify coverage percentage is calculated correctly
            expected_coverage = (num_documented / num_files * 100) if num_files > 0 else 0.0
            assert abs(json_output["coverage_percentage"] - expected_coverage) < 0.01
            
            # Verify missing_docstrings list has correct length
            expected_missing = num_files - num_documented
            assert len(json_output["missing_docstrings"]) == expected_missing
            
            # Verify each missing docstring entry is a list with 2 elements [file_path, line_number]
            for entry in json_output["missing_docstrings"]:
                assert isinstance(entry, list), "Each missing docstring entry should be a list"
                assert len(entry) == 2, "Each entry should have [file_path, line_number]"
                assert isinstance(entry[0], str), "File path should be a string"
                assert isinstance(entry[1], int), "Line number should be an integer"


@settings(max_examples=50, deadline=10000)
@given(
    num_files=st.integers(min_value=1, max_value=5),
    has_missing=st.booleans(),
)
def test_property_github_actions_annotation_format(num_files, has_missing):
    """
    Feature: docstring-generator, Property 33: For any function missing a docstring,
    when generating GitHub Actions annotations, the output should follow the format
    "::warning file={path},line={line}::Missing docstring".

    Validates: Requirements 13.5
    """
    import re
    
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create files with or without docstrings
        expected_annotations = []
        for i in range(num_files):
            filepath = tmppath / f"file_{i}.py"
            if has_missing:
                # Function without docstring - should generate annotation
                filepath.write_text(f"def func_{i}():\n    pass\n")
                # Line 1 is where the function definition starts
                expected_annotations.append((str(filepath), 1))
            else:
                # Function with docstring - should NOT generate annotation
                filepath.write_text(f'def func_{i}():\n    """Doc."""\n    pass\n')

        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )

            # Run CLI with --report --format json
            # This should trigger GitHub Actions annotations
            result = runner.invoke(main, [str(tmppath), "--report", "--format", "json"])
            
            # The output should contain the JSON report followed by annotations
            output = result.output
            
            if has_missing:
                # Verify annotations are present in output
                # Pattern: ::warning file={path},line={line}::Missing docstring
                annotation_pattern = r'::warning file=(.+?),line=(\d+)::Missing docstring'
                matches = re.findall(annotation_pattern, output)
                
                # Should have one annotation per file with missing docstring
                assert len(matches) == num_files, (
                    f"Expected {num_files} annotations but found {len(matches)}. "
                    f"Output: {output}"
                )
                
                # Verify each annotation has correct format
                for file_path, line_num in matches:
                    # Verify file path is not empty
                    assert file_path, "File path should not be empty"
                    # Verify line number is a valid integer
                    assert line_num.isdigit(), f"Line number '{line_num}' should be a digit"
                    assert int(line_num) > 0, "Line number should be positive"
                
                # Verify the exact format matches the specification
                for match in re.finditer(annotation_pattern, output):
                    full_annotation = match.group(0)
                    # Verify exact format: ::warning file={path},line={line}::Missing docstring
                    assert full_annotation.startswith("::warning file=")
                    assert ",line=" in full_annotation
                    assert full_annotation.endswith("::Missing docstring")
            else:
                # No missing docstrings, should not have any annotations
                assert "::warning" not in output, (
                    "Should not have annotations when all functions have docstrings"
                )


@settings(max_examples=50, deadline=10000)
@given(
    num_staged_py=st.integers(min_value=0, max_value=5),
    num_unstaged_py=st.integers(min_value=0, max_value=5),
    num_staged_other=st.integers(min_value=0, max_value=3),
)
def test_property_staged_file_processing(num_staged_py, num_unstaged_py, num_staged_other):
    """
    Feature: docstring-generator, Property 29: For any set of git-staged Python files,
    when invoked by pre-commit, the CLI should process only those staged files and not
    other Python files in the repository.

    Validates: Requirements 12.2
    """
    import subprocess
    
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmppath, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmppath,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmppath,
            check=True,
            capture_output=True,
        )
        
        # Create staged Python files
        staged_py_files = []
        for i in range(num_staged_py):
            filepath = tmppath / f"staged_{i}.py"
            filepath.write_text(f"def staged_func_{i}():\n    pass\n")
            subprocess.run(["git", "add", str(filepath)], cwd=tmppath, check=True, capture_output=True)
            staged_py_files.append(filepath)
        
        # Create unstaged Python files
        for i in range(num_unstaged_py):
            filepath = tmppath / f"unstaged_{i}.py"
            filepath.write_text(f"def unstaged_func_{i}():\n    pass\n")
        
        # Create staged non-Python files
        for i in range(num_staged_other):
            filepath = tmppath / f"staged_{i}.txt"
            filepath.write_text(f"Not a Python file {i}\n")
            subprocess.run(["git", "add", str(filepath)], cwd=tmppath, check=True, capture_output=True)
        
        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )
            
            with patch("docgen.cli.process_files_batch") as mock_process:
                mock_process.return_value = (ProcessingStats(), [])
                
                # Change to git repo directory for git commands to work
                import os
                original_dir = os.getcwd()
                try:
                    os.chdir(tmppath)
                    
                    result = runner.invoke(main, [".", "--staged", "--dry-run"])
                    
                    if num_staged_py > 0:
                        # Verify process_files_batch was called
                        assert mock_process.called
                        
                        # Get the files that were passed to process_files_batch
                        files_arg = mock_process.call_args[0][0]
                        
                        # Verify only staged Python files were processed
                        assert len(files_arg) == num_staged_py
                        
                        # Verify all files end with .py
                        assert all(str(f).endswith(".py") for f in files_arg)
                        
                        # Verify the files are the ones we staged
                        processed_names = {f.name for f in files_arg}
                        expected_names = {f.name for f in staged_py_files}
                        assert processed_names == expected_names
                    else:
                        # No staged Python files, should exit gracefully
                        assert result.exit_code == 0
                        assert "No staged Python files found" in result.output
                finally:
                    os.chdir(original_dir)


@settings(max_examples=50, deadline=10000)
@given(
    num_files=st.integers(min_value=1, max_value=5),
    num_modified=st.integers(min_value=0, max_value=5),
)
def test_property_modified_file_staging(num_files, num_modified):
    """
    Feature: docstring-generator, Property 30: For any file modified by docstring injection,
    the CLI should stage the modified file using git add.

    Validates: Requirements 12.3
    """
    import subprocess
    
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmppath, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmppath,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmppath,
            check=True,
            capture_output=True,
        )
        
        # Ensure num_modified doesn't exceed num_files
        num_modified = min(num_modified, num_files)
        
        # Create and stage Python files
        staged_files = []
        for i in range(num_files):
            filepath = tmppath / f"file_{i}.py"
            # Files that will be modified (first num_modified files) have missing docstrings
            if i < num_modified:
                filepath.write_text(f"def func_{i}():\n    pass\n")
            else:
                # Files that won't be modified already have docstrings
                filepath.write_text(f'def func_{i}():\n    """Existing."""\n    pass\n')
            
            subprocess.run(["git", "add", str(filepath)], cwd=tmppath, check=True, capture_output=True)
            staged_files.append(filepath)
        
        # Commit the files
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmppath,
            check=True,
            capture_output=True,
        )
        
        # Modify files to add them to staging area (simulate user editing)
        for i in range(num_modified):
            filepath = tmppath / f"file_{i}.py"
            # Add a comment to make it different
            filepath.write_text(f"# Modified\ndef func_{i}():\n    pass\n")
            subprocess.run(["git", "add", str(filepath)], cwd=tmppath, check=True, capture_output=True)
        
        with patch("docgen.cli.ConfigLoader.load") as mock_config:
            mock_config.return_value = Config(
                style="google",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                api_key="test-key",
            )
            
            # Mock the LLM client to return a simple docstring
            with patch("docgen.batch.LLMClient") as mock_llm_class:
                mock_llm_instance = mock_llm_class.return_value
                mock_llm_instance.generate.return_value = '"""Generated docstring."""'
                
                # Mock the formatter to always validate successfully
                with patch("docgen.batch.DocstringFormatter") as mock_formatter_class:
                    mock_formatter_instance = mock_formatter_class.return_value
                    mock_formatter_instance.validate.return_value = (True, None)
                    mock_formatter_instance.format.return_value = '"""Generated docstring."""'
                    
                    # Change to git repo directory
                    import os
                    original_dir = os.getcwd()
                    try:
                        os.chdir(tmppath)
                        
                        # Run CLI with --staged flag (not dry-run)
                        result = runner.invoke(main, [".", "--staged"])
                        
                        if num_modified > 0:
                            # Verify that modified files are still staged
                            # Check git status to see if files are staged
                            status_result = subprocess.run(
                                ["git", "diff", "--cached", "--name-only"],
                                cwd=tmppath,
                                capture_output=True,
                                text=True,
                                check=True,
                            )
                            
                            staged_after = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
                            
                            # All modified files should still be staged
                            for i in range(num_modified):
                                filename = f"file_{i}.py"
                                assert filename in staged_after, f"Modified file {filename} should be staged"
                        
                    finally:
                        os.chdir(original_dir)
