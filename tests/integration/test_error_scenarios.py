"""Integration tests for error handling scenarios.

This module tests error recovery and reporting across the complete pipeline,
ensuring the tool continues processing and provides useful error summaries.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from docgen.cli import main
from docgen.llm import LLMError


@pytest.fixture
def test_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        yield project_path


def test_error_handling_invalid_python_files(test_project):
    """
    Test handling of invalid Python files.
    
    Validates that:
    - Invalid Python files are caught and logged
    - Processing continues with other files
    - Error summary is displayed
    
    Validates Requirements: 11.1
    """
    # Create a valid file
    valid_file = test_project / "valid.py"
    valid_file.write_text("""def valid_function(x: int) -> int:
    return x * 2
""")
    
    # Create an invalid Python file (syntax error)
    invalid_file = test_project / "invalid.py"
    invalid_file.write_text("""def broken_function(
    # Missing closing parenthesis and colon
    pass
""")
    
    # Create another valid file
    another_valid = test_project / "another.py"
    another_valid.write_text("""def another_function(y: str) -> str:
    return y.upper()
""")
    
    # Mock LLM to return valid docstrings
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = """A function.

Args:
    x: Input value

Returns:
    Processed value"""
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False
        )
        
        # Should complete successfully despite parse error
        assert result.exit_code == 0
        
        # Verify error was reported in output
        assert "Errors: 1" in result.output or "error" in result.output.lower()
        
        # Verify valid files were still processed
        # Should process 2 valid files
        assert "Files processed: 2" in result.output
    
    # Verify valid files were modified
    valid_content = valid_file.read_text()
    assert '"""A function.' in valid_content
    
    another_content = another_valid.read_text()
    assert '"""A function.' in another_content
    
    # Verify invalid file was not modified (still has syntax error)
    invalid_content = invalid_file.read_text()
    assert "broken_function" in invalid_content
    assert '"""' not in invalid_content


def test_error_handling_llm_api_failures(test_project):
    """
    Test handling of LLM API failures.
    
    Validates that:
    - LLM API failures are caught and logged with provider name
    - Processing continues with other functions
    - Error summary is displayed
    
    Validates Requirements: 11.2
    """
    # Create multiple files with functions
    file1 = test_project / "module1.py"
    file1.write_text("""def function1(x: int) -> int:
    return x + 1

def function2(x: int) -> int:
    return x + 2
""")
    
    file2 = test_project / "module2.py"
    file2.write_text("""def function3(x: int) -> int:
    return x + 3
""")
    
    # Mock LLM to fail on specific functions
    call_count = 0
    
    def mock_generate(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        
        # Fail on second function
        if call_count == 2:
            raise LLMError("API rate limit exceeded")
        
        return """A function.

Args:
    x: Input value

Returns:
    Processed value"""
    
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.side_effect = mock_generate
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False
        )
        
        # Should complete successfully despite LLM error
        assert result.exit_code == 0
        
        # Verify error was reported
        assert "Errors: 1" in result.output or "error" in result.output.lower()
        
        # Verify LLM error message is in output
        assert "LLM error" in result.output or "rate limit" in result.output.lower()
        
        # Verify files were still processed
        assert "Files processed: 2" in result.output
        
        # Verify some docstrings were added (2 out of 3 functions)
        assert "Docstrings added: 2" in result.output
    
    # Verify successful functions got docstrings
    file1_content = file1.read_text()
    file2_content = file2.read_text()
    
    # Count docstrings added
    docstring_count = file1_content.count('"""A function.') + file2_content.count('"""A function.')
    assert docstring_count == 2, f"Expected 2 docstrings, found {docstring_count}"


def test_error_handling_file_write_failures(test_project):
    """
    Test handling of file write failures.
    
    Validates that:
    - File write failures are caught and logged
    - Processing continues with other files
    - Error summary is displayed
    
    Validates Requirements: 11.5
    """
    # Create test files
    file1 = test_project / "module1.py"
    file1.write_text("""def function1(x: int) -> int:
    return x + 1
""")
    
    file2 = test_project / "module2.py"
    file2.write_text("""def function2(x: int) -> int:
    return x + 2
""")
    
    # Mock LLM to return valid docstrings
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = """A function.

Args:
    x: Input value

Returns:
    Processed value"""
        mock_llm_class.return_value = mock_llm_instance
        
        # Mock patcher to fail on first file
        with patch("docgen.batch.DocstringPatcher.write_file") as mock_write:
            call_count = 0
            
            def mock_write_file(file_path, source_code):
                nonlocal call_count
                call_count += 1
                
                # Fail on first write
                if call_count == 1:
                    raise IOError("Permission denied")
                
                # Succeed on subsequent writes
                Path(file_path).write_text(source_code)
            
            mock_write.side_effect = mock_write_file
            
            runner = CliRunner()
            result = runner.invoke(
                main,
                [str(test_project)],
                catch_exceptions=False
            )
            
            # Should complete successfully despite write error
            assert result.exit_code == 0
            
            # Verify error was reported
            assert "Errors: 1" in result.output or "error" in result.output.lower()
            
            # Verify write error message is in output
            assert "Patch error" in result.output or "Permission denied" in result.output
            
            # Verify files were still processed
            assert "Files processed: 2" in result.output
            
            # Verify one docstring was added (second file succeeded)
            assert "Docstrings added: 1" in result.output


def test_error_summary_display(test_project):
    """
    Test that error summary is displayed with all errors.
    
    Validates that:
    - All errors are collected during processing
    - Error summary is displayed at the end
    - Error summary includes file paths and error messages
    
    Validates Requirements: 11.6
    """
    # Create files with various error scenarios
    valid_file = test_project / "valid.py"
    valid_file.write_text("""def valid_function(x: int) -> int:
    return x * 2
""")
    
    invalid_file = test_project / "invalid.py"
    invalid_file.write_text("""def broken_function(
    pass
""")
    
    another_file = test_project / "another.py"
    another_file.write_text("""def another_function(y: str) -> str:
    return y.upper()

def third_function(z: int) -> int:
    return z * 3
""")
    
    # Mock LLM to fail on specific functions
    call_count = 0
    
    def mock_generate(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        
        # Fail on second successful function call
        if call_count == 2:
            raise LLMError("API timeout")
        
        return """A function.

Args:
    x: Input value

Returns:
    Processed value"""
    
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.side_effect = mock_generate
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False
        )
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Verify multiple errors were reported
        # Should have: 1 parse error + 1 LLM error = 2 errors
        assert "Errors: 2" in result.output
        
        # Verify error summary section exists
        assert "error" in result.output.lower()
        
        # Verify parse error is mentioned
        assert "invalid.py" in result.output or "Parse error" in result.output
        
        # Verify LLM error is mentioned
        assert "LLM error" in result.output or "timeout" in result.output.lower()
        
        # Verify some files were still processed successfully
        assert "Files processed: 2" in result.output
        # Note: 2 docstrings added because LLM fails on 2nd call but 3rd succeeds
        assert "Docstrings added: 2" in result.output


def test_error_handling_with_dry_run(test_project):
    """
    Test that errors are handled correctly in dry-run mode.
    
    Validates that:
    - Errors are reported in dry-run mode
    - No files are modified even when errors occur
    - Processing continues after errors
    
    Validates Requirements: 11.1, 11.2, 9.1
    """
    # Create files
    valid_file = test_project / "valid.py"
    original_valid = """def valid_function(x: int) -> int:
    return x * 2
"""
    valid_file.write_text(original_valid)
    
    invalid_file = test_project / "invalid.py"
    original_invalid = """def broken_function(
    pass
"""
    invalid_file.write_text(original_invalid)
    
    # Mock LLM
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = """A function.

Args:
    x: Input value

Returns:
    Processed value"""
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project), "--dry-run"],
            catch_exceptions=False
        )
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Verify error was reported
        assert "Errors: 1" in result.output or "error" in result.output.lower()
    
    # Verify NO files were modified (dry-run mode)
    assert valid_file.read_text() == original_valid
    assert invalid_file.read_text() == original_invalid


def test_error_handling_all_files_fail(test_project):
    """
    Test handling when all files fail to process.
    
    Validates that:
    - Tool completes successfully even when all files fail
    - All errors are reported
    - Appropriate summary is displayed
    
    Validates Requirements: 11.1, 11.6
    """
    # Create only invalid files
    invalid1 = test_project / "invalid1.py"
    invalid1.write_text("""def broken1(
    pass
""")
    
    invalid2 = test_project / "invalid2.py"
    invalid2.write_text("""def broken2(
    return None
""")
    
    # Mock LLM (won't be called since parsing fails)
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = '"""A function."""'
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False
        )
        
        # Should complete successfully (exit code 0)
        assert result.exit_code == 0
        
        # Verify errors were reported
        assert "Errors: 2" in result.output
        
        # Verify no files were successfully processed
        assert "Files processed: 0" in result.output
        assert "Docstrings added: 0" in result.output
        
        # Verify error summary is displayed
        assert "error" in result.output.lower()


def test_error_handling_mixed_scenarios(test_project):
    """
    Test handling of multiple error types in a single run.
    
    Validates that:
    - Multiple error types are handled correctly
    - All errors are collected and reported
    - Processing continues through all error types
    
    Validates Requirements: 11.1, 11.2, 11.5, 11.6
    """
    # Create files with different scenarios
    valid1 = test_project / "valid1.py"
    valid1.write_text("""def function1(x: int) -> int:
    return x + 1
""")
    
    invalid_syntax = test_project / "invalid.py"
    invalid_syntax.write_text("""def broken(
    pass
""")
    
    valid2 = test_project / "valid2.py"
    valid2.write_text("""def function2(x: int) -> int:
    return x + 2

def function3(x: int) -> int:
    return x + 3
""")
    
    # Mock LLM to fail on specific calls
    call_count = 0
    
    def mock_generate(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        
        # Fail on second call
        if call_count == 2:
            raise LLMError("Rate limit exceeded")
        
        return """A function.

Args:
    x: Input value

Returns:
    Processed value"""
    
    with patch("docgen.batch.LLMClient") as mock_llm_class:
        mock_llm_instance = Mock()
        mock_llm_instance.generate.side_effect = mock_generate
        mock_llm_class.return_value = mock_llm_instance
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(test_project)],
            catch_exceptions=False
        )
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Verify multiple errors were reported
        # 1 parse error + 1 LLM error = 2 errors
        assert "Errors: 2" in result.output
        
        # Verify some files were processed
        assert "Files processed: 2" in result.output
        
        # Verify some docstrings were added (2 out of 3 functions)
        assert "Docstrings added: 2" in result.output
        
        # Verify error types are mentioned
        output_lower = result.output.lower()
        assert "parse" in output_lower or "invalid" in output_lower
        assert "llm" in output_lower or "rate limit" in output_lower
