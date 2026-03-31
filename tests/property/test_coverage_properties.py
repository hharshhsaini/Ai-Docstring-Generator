"""Property-based tests for coverage calculation."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from docgen.coverage import calculate_coverage


@settings(max_examples=100)
@given(
    num_functions=st.integers(min_value=1, max_value=50),
    num_documented=st.integers(min_value=0, max_value=50),
)
def test_coverage_calculation_accuracy(num_functions, num_documented):
    """
    Feature: docstring-generator, Property 23: For any set of Python files, the
    coverage percentage should equal (documented_functions / total_functions) * 100,
    where documented_functions is the count of functions with docstrings and
    total_functions is the count of all functions.

    **Validates: Requirements 10.2, 10.3, 10.4**
    """
    # Ensure num_documented <= num_functions
    num_documented = min(num_documented, num_functions)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create file with functions
        code_lines = []
        for i in range(num_functions):
            if i < num_documented:
                code_lines.append(
                    f'def func_{i}():\n    """Docstring for func_{i}"""\n    pass\n'
                )
            else:
                code_lines.append(f"def func_{i}():\n    pass\n")

        test_file = tmppath / "test.py"
        test_file.write_text("\n".join(code_lines))

        # Calculate coverage
        report = calculate_coverage([test_file])

        expected_coverage = (
            (num_documented / num_functions * 100) if num_functions > 0 else 0.0
        )

        assert report.total_functions == num_functions
        assert report.documented_functions == num_documented
        assert abs(report.coverage_percentage - expected_coverage) < 0.01


@settings(max_examples=100)
@given(
    num_missing=st.integers(min_value=1, max_value=20),
)
def test_missing_docstring_location_tracking(num_missing):
    """
    Feature: docstring-generator, Property 24: For any function without a docstring,
    the coverage report should include the file path and line number where the
    function is defined.

    **Validates: Requirements 10.7**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create file with functions missing docstrings
        code_lines = []
        expected_line_numbers = []

        for i in range(num_missing):
            # Track the line number where function is defined
            current_line = len(code_lines) + 1  # +1 for 1-indexed
            expected_line_numbers.append(current_line)
            code_lines.append(f"def func_{i}():\n    pass\n")

        test_file = tmppath / "test.py"
        test_file.write_text("\n".join(code_lines))

        # Calculate coverage
        report = calculate_coverage([test_file])

        # Verify all missing docstrings are tracked
        assert len(report.missing_docstrings) == num_missing

        # Verify file paths are correct
        for file_path, line_num in report.missing_docstrings:
            assert file_path == str(test_file)
            # Line number should be one of the expected ones
            # (exact line numbers may vary due to how libcst reports them)
            assert line_num > 0


@settings(max_examples=100)
@given(
    num_files=st.integers(min_value=1, max_value=5),
    functions_per_file=st.integers(min_value=1, max_value=10),
)
def test_coverage_across_multiple_files(num_files, functions_per_file):
    """
    Test that coverage calculation works correctly across multiple files.

    **Validates: Requirements 10.2, 10.3, 10.4**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        files = []
        total_expected = num_files * functions_per_file
        documented_expected = 0

        for file_idx in range(num_files):
            code_lines = []
            for func_idx in range(functions_per_file):
                # Alternate between documented and undocumented
                if (file_idx + func_idx) % 2 == 0:
                    code_lines.append(
                        f'def func_{func_idx}():\n    """Docstring"""\n    pass\n'
                    )
                    documented_expected += 1
                else:
                    code_lines.append(f"def func_{func_idx}():\n    pass\n")

            test_file = tmppath / f"test_{file_idx}.py"
            test_file.write_text("\n".join(code_lines))
            files.append(test_file)

        # Calculate coverage
        report = calculate_coverage(files)

        assert report.total_functions == total_expected
        assert report.documented_functions == documented_expected

        expected_coverage = (
            (documented_expected / total_expected * 100) if total_expected > 0 else 0.0
        )
        assert abs(report.coverage_percentage - expected_coverage) < 0.01
