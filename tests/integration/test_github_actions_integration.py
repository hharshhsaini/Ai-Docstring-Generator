"""Integration tests for GitHub Actions CI/CD functionality."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from docgen.cli import main


@pytest.fixture
def test_repo():
    """Create a temporary directory with test Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        yield repo_path


def parse_json_from_output(output: str) -> dict:
    """
    Parse JSON from CLI output.
    
    The JSON output is multi-line formatted and may be followed by
    GitHub Actions annotations. May also contain ANSI color codes.
    """
    import re
    
    # Strip ANSI color codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    output = ansi_escape.sub('', output)
    
    # Split by ::warning to separate JSON from annotations
    output_parts = output.split('::warning')
    json_text = output_parts[0].strip()
    
    return json.loads(json_text)


def test_json_output_generation(test_repo):
    """
    Test JSON output generation for CI/CD pipelines.
    
    Validates Requirements: 13.1, 13.2
    """
    # Create Python files with varying documentation levels
    documented_file = test_repo / "documented.py"
    documented_file.write_text('''def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y
''')
    
    undocumented_file = test_repo / "undocumented.py"
    undocumented_file.write_text('''def subtract(a: int, b: int) -> int:
    return a - b

def divide(x: int, y: int) -> float:
    return x / y
''')
    
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json"],
        catch_exceptions=False
    )
    
    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
    
    # Parse JSON output
    json_output = parse_json_from_output(result.output)
    
    # Verify JSON structure
    assert "total_functions" in json_output
    assert "documented_functions" in json_output
    assert "coverage_percentage" in json_output
    assert "missing_docstrings" in json_output
    
    # Verify values
    assert json_output["total_functions"] == 4
    assert json_output["documented_functions"] == 2
    assert json_output["coverage_percentage"] == 50.0
    assert len(json_output["missing_docstrings"]) == 2
    
    # Verify missing docstrings contain file paths and line numbers
    for file_path, line_number in json_output["missing_docstrings"]:
        assert isinstance(file_path, str)
        assert isinstance(line_number, int)
        assert "undocumented.py" in file_path


def test_coverage_threshold_checking(test_repo):
    """
    Test coverage threshold checking for CI/CD pipelines.
    
    Validates Requirements: 13.3, 13.4
    """
    # Create files with 50% coverage
    documented_file = test_repo / "documented.py"
    documented_file.write_text('''def foo():
    """A function."""
    pass
''')
    
    undocumented_file = test_repo / "undocumented.py"
    undocumented_file.write_text('''def bar():
    pass
''')
    
    runner = CliRunner()
    
    # Test 1: Coverage below threshold should exit with code 1
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--min-coverage", "75"],
        catch_exceptions=False
    )
    assert result.exit_code == 1, "Expected exit code 1 when coverage below threshold"
    assert "below minimum" in result.output.lower()
    
    # Test 2: Coverage above threshold should exit with code 0
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--min-coverage", "25"],
        catch_exceptions=False
    )
    assert result.exit_code == 0, "Expected exit code 0 when coverage above threshold"
    
    # Test 3: Coverage exactly at threshold should exit with code 0
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--min-coverage", "50"],
        catch_exceptions=False
    )
    assert result.exit_code == 0, "Expected exit code 0 when coverage equals threshold"


def test_github_actions_annotation_output(test_repo):
    """
    Test GitHub Actions annotation output format.
    
    Validates Requirements: 13.5
    """
    # Create files with missing docstrings
    file1 = test_repo / "module1.py"
    file1.write_text('''def function_a():
    pass

def function_b():
    pass
''')
    
    file2 = test_repo / "module2.py"
    file2.write_text('''def function_c():
    pass
''')
    
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json"],
        catch_exceptions=False
    )
    
    assert result.exit_code == 0
    
    # Verify GitHub Actions annotations are present
    annotations = [line for line in result.output.split('\n') if line.startswith("::warning")]
    
    assert len(annotations) == 3, f"Expected 3 annotations, got {len(annotations)}"
    
    # Verify annotation format
    for annotation in annotations:
        assert "::warning file=" in annotation
        assert ",line=" in annotation
        assert "::Missing docstring" in annotation
        
        # Extract file and line from annotation
        parts = annotation.split("::")
        assert len(parts) == 3  # ["", "warning file=...,line=...", "Missing docstring"]
        
        metadata = parts[1]
        assert "file=" in metadata
        assert "line=" in metadata


def test_github_actions_workflow_complete(test_repo):
    """
    Complete integration test for GitHub Actions workflow.
    
    Tests:
    - JSON output generation
    - Coverage threshold checking
    - Annotation output format
    
    Validates Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
    """
    # Create a realistic project structure
    src_dir = test_repo / "src"
    src_dir.mkdir()
    
    # Module with good documentation
    good_module = src_dir / "good.py"
    good_module.write_text('''"""A well-documented module."""

def add(a: int, b: int) -> int:
    """Add two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    """
    return a + b

def multiply(x: int, y: int) -> int:
    """Multiply two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Product of x and y
    """
    return x * y
''')
    
    # Module with poor documentation
    poor_module = src_dir / "poor.py"
    poor_module.write_text('''"""A poorly documented module."""

def subtract(a: int, b: int) -> int:
    return a - b

def divide(x: int, y: int) -> float:
    return x / y

def modulo(a: int, b: int) -> int:
    return a % b
''')
    
    runner = CliRunner()
    
    # Simulate GitHub Actions workflow
    # Step 1: Generate coverage report with JSON output
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json", "--min-coverage", "60"],
        catch_exceptions=False
    )
    
    # Verify exit code (should be 1 because coverage is 40% < 60%)
    assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
    
    # Parse JSON output
    json_output = parse_json_from_output(result.output)
    
    assert json_output is not None, "Expected JSON output"
    
    # Verify coverage metrics
    assert json_output["total_functions"] == 5
    assert json_output["documented_functions"] == 2
    assert json_output["coverage_percentage"] == 40.0
    assert len(json_output["missing_docstrings"]) == 3
    
    # Verify GitHub Actions annotations
    annotations = [line for line in result.output.split('\n') if line.startswith("::warning")]
    assert len(annotations) == 3, f"Expected 3 annotations for missing docstrings"
    
    # Verify each annotation has correct format
    for annotation in annotations:
        assert "::warning file=" in annotation
        assert ",line=" in annotation
        assert "::Missing docstring" in annotation
        assert "poor.py" in annotation  # All missing docstrings are in poor.py


def test_ci_workflow_with_perfect_coverage(test_repo):
    """Test CI workflow when coverage is 100%."""
    # Create fully documented module
    module = test_repo / "complete.py"
    module.write_text('''"""A complete module."""

def foo(x: int) -> int:
    """Return input.
    
    Args:
        x: Input value
        
    Returns:
        Same value
    """
    return x

def bar(y: str) -> str:
    """Return input.
    
    Args:
        y: Input string
        
    Returns:
        Same string
    """
    return y
''')
    
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json", "--min-coverage", "100"],
        catch_exceptions=False
    )
    
    # Should exit with code 0 (100% coverage)
    assert result.exit_code == 0
    
    # Parse JSON
    json_output = parse_json_from_output(result.output)
    
    assert json_output is not None
    assert json_output["coverage_percentage"] == 100.0
    assert len(json_output["missing_docstrings"]) == 0
    
    # No annotations should be output
    annotations = [line for line in result.output.split('\n') if line.startswith("::warning")]
    assert len(annotations) == 0


def test_ci_workflow_with_zero_coverage(test_repo):
    """Test CI workflow when coverage is 0%."""
    # Create completely undocumented module
    module = test_repo / "undocumented.py"
    module.write_text('''def foo(x):
    return x

def bar(y):
    return y

def baz(z):
    return z
''')
    
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json", "--min-coverage", "50"],
        catch_exceptions=False
    )
    
    # Should exit with code 1 (0% < 50%)
    assert result.exit_code == 1
    
    # Parse JSON
    json_output = parse_json_from_output(result.output)
    
    assert json_output is not None
    assert json_output["coverage_percentage"] == 0.0
    assert json_output["total_functions"] == 3
    assert json_output["documented_functions"] == 0
    assert len(json_output["missing_docstrings"]) == 3
    
    # All functions should have annotations
    annotations = [line for line in result.output.split('\n') if line.startswith("::warning")]
    assert len(annotations) == 3


def test_json_output_with_complex_file_paths(test_repo):
    """Test JSON output handles complex file paths correctly."""
    # Create nested directory structure
    nested_dir = test_repo / "src" / "utils" / "helpers"
    nested_dir.mkdir(parents=True)
    
    module = nested_dir / "functions.py"
    module.write_text('''def helper():
    pass
''')
    
    runner = CliRunner()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json"],
        catch_exceptions=False
    )
    
    assert result.exit_code == 0
    
    # Parse JSON
    json_output = parse_json_from_output(result.output)
    
    assert json_output is not None
    assert len(json_output["missing_docstrings"]) == 1
    
    file_path, line_number = json_output["missing_docstrings"][0]
    assert "functions.py" in file_path
    assert isinstance(line_number, int)
    
    # Verify annotation also has correct path
    annotations = [line for line in result.output.split('\n') if line.startswith("::warning")]
    assert len(annotations) == 1
    assert "functions.py" in annotations[0]


def test_ci_workflow_performance(test_repo):
    """Test that CI workflow completes quickly for typical projects."""
    import time
    
    # Create multiple modules
    for i in range(20):
        module = test_repo / f"module_{i}.py"
        module.write_text(f'''def func_{i}(x):
    return x * {i}
''')
    
    runner = CliRunner()
    start_time = time.time()
    result = runner.invoke(
        main,
        [str(test_repo), "--report", "--format", "json"],
        catch_exceptions=False
    )
    elapsed_time = time.time() - start_time
    
    assert result.exit_code == 0
    assert elapsed_time < 10, f"CI workflow took {elapsed_time:.2f}s, expected < 10s"
    
    # Verify JSON output is still valid
    json_output = parse_json_from_output(result.output)
    
    assert json_output is not None
    assert json_output["total_functions"] == 20
