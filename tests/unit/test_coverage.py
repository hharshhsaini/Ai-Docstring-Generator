"""Unit tests for coverage calculation."""

import tempfile
from pathlib import Path

from docgen.coverage import calculate_coverage


def test_coverage_all_documented():
    """Test coverage when all functions have docstrings."""
    code = '''def func1():
    """Docstring 1"""
    pass

def func2():
    """Docstring 2"""
    pass

def func3():
    """Docstring 3"""
    pass
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        report = calculate_coverage([test_file])

        assert report.total_functions == 3
        assert report.documented_functions == 3
        assert report.coverage_percentage == 100.0
        assert len(report.missing_docstrings) == 0


def test_coverage_none_documented():
    """Test coverage when no functions have docstrings."""
    code = """def func1():
    pass

def func2():
    pass

def func3():
    pass
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        report = calculate_coverage([test_file])

        assert report.total_functions == 3
        assert report.documented_functions == 0
        assert report.coverage_percentage == 0.0
        assert len(report.missing_docstrings) == 3


def test_coverage_mixed_documentation():
    """Test coverage with mixed documentation."""
    code = '''def func1():
    """Documented"""
    pass

def func2():
    pass

def func3():
    """Documented"""
    pass

def func4():
    pass
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        report = calculate_coverage([test_file])

        assert report.total_functions == 4
        assert report.documented_functions == 2
        assert report.coverage_percentage == 50.0
        assert len(report.missing_docstrings) == 2


def test_coverage_with_classes():
    """Test coverage calculation with classes and methods."""
    code = '''class MyClass:
    """Class docstring"""
    
    def method1(self):
        """Method docstring"""
        pass
    
    def method2(self):
        pass

def func1():
    """Function docstring"""
    pass

def func2():
    pass
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        report = calculate_coverage([test_file])

        # 2 methods + 2 functions = 4 total
        assert report.total_functions == 4
        # method1 + func1 = 2 documented
        assert report.documented_functions == 2
        assert report.coverage_percentage == 50.0
        assert len(report.missing_docstrings) == 2


def test_coverage_empty_file():
    """Test coverage with empty file."""
    code = ""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        report = calculate_coverage([test_file])

        assert report.total_functions == 0
        assert report.documented_functions == 0
        assert report.coverage_percentage == 0.0
        assert len(report.missing_docstrings) == 0


def test_coverage_multiple_files():
    """Test coverage across multiple files."""
    code1 = '''def func1():
    """Documented"""
    pass

def func2():
    pass
'''

    code2 = '''def func3():
    """Documented"""
    pass

def func4():
    """Documented"""
    pass
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file1 = tmppath / "test1.py"
        test_file1.write_text(code1)
        test_file2 = tmppath / "test2.py"
        test_file2.write_text(code2)

        report = calculate_coverage([test_file1, test_file2])

        assert report.total_functions == 4
        assert report.documented_functions == 3
        assert report.coverage_percentage == 75.0
        assert len(report.missing_docstrings) == 1


def test_coverage_skips_invalid_files():
    """Test that coverage calculation skips files that can't be parsed."""
    valid_code = '''def func1():
    """Documented"""
    pass
'''

    invalid_code = "def func2(\n    invalid syntax"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        valid_file = tmppath / "valid.py"
        valid_file.write_text(valid_code)
        invalid_file = tmppath / "invalid.py"
        invalid_file.write_text(invalid_code)

        # Should not raise an error, just skip invalid file
        report = calculate_coverage([valid_file, invalid_file])

        # Only valid file should be counted
        assert report.total_functions == 1
        assert report.documented_functions == 1
        assert report.coverage_percentage == 100.0
