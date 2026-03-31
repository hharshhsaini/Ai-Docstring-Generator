"""Unit tests for DocstringPatcher."""

import tempfile
from pathlib import Path

import pytest

from docgen.patcher import DocstringPatcher


def test_patch_module_level_function():
    """Test patching a module-level function."""
    code = """def greet(name):
    return f"Hello, {name}"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(
            test_file, "greet", "Greet a person by name.", None
        )

        assert '"""Greet a person by name."""' in modified
        assert "def greet(name):" in modified
        assert 'return f"Hello, {name}"' in modified


def test_patch_class_method():
    """Test patching a class method."""
    code = """class Calculator:
    def add(self, a, b):
        return a + b
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(
            test_file, "add", "Add two numbers.", "Calculator"
        )

        assert '"""Add two numbers."""' in modified
        assert "def add(self, a, b):" in modified
        assert "return a + b" in modified


def test_patch_with_existing_docstring_no_overwrite():
    """Test that existing docstring is preserved when overwrite=False."""
    code = '''def greet(name):
    """Original docstring"""
    return f"Hello, {name}"
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(
            test_file, "greet", "New docstring", None
        )

        # Original docstring should be preserved
        assert "Original docstring" in modified
        assert "New docstring" not in modified


def test_patch_with_existing_docstring_overwrite():
    """Test that existing docstring is replaced when overwrite=True."""
    code = '''def greet(name):
    """Original docstring"""
    return f"Hello, {name}"
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=True)
        modified = patcher.inject_docstring(
            test_file, "greet", "New docstring", None
        )

        # New docstring should replace original
        assert "New docstring" in modified
        assert "Original docstring" not in modified


def test_indentation_preservation():
    """Test that indentation is preserved correctly."""
    code = """class MyClass:
    def method(self):
        x = 1
        y = 2
        return x + y
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(
            test_file, "method", "A simple method.", "MyClass"
        )

        # Check that indentation is correct
        lines = modified.split("\n")
        # Find the docstring line
        docstring_line = next(
            (i for i, line in enumerate(lines) if "A simple method" in line), None
        )
        assert docstring_line is not None

        # Check that the docstring has proper indentation (8 spaces for class method)
        assert lines[docstring_line].startswith("        ")


def test_write_file():
    """Test writing modified code back to file."""
    code = """def foo():
    pass
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(test_file, "foo", "A function.", None)

        # Write back to file
        patcher.write_file(test_file, modified)

        # Read and verify
        content = test_file.read_text()
        assert '"""A function."""' in content


def test_patch_correct_method_in_multiple_classes():
    """Test patching the correct method when multiple classes have methods with same name."""
    code = """class ClassA:
    def method(self):
        return "A"

class ClassB:
    def method(self):
        return "B"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        modified = patcher.inject_docstring(
            test_file, "method", "Method in ClassB.", "ClassB"
        )

        # Check that only ClassB's method got the docstring
        lines = modified.split("\n")

        # Find ClassA's method
        class_a_method_idx = next(
            (i for i, line in enumerate(lines) if "class ClassA:" in line), None
        )
        # Find ClassB's method
        class_b_method_idx = next(
            (i for i, line in enumerate(lines) if "class ClassB:" in line), None
        )

        # Check that docstring appears after ClassB but not after ClassA
        class_a_section = "\n".join(lines[class_a_method_idx : class_b_method_idx])
        class_b_section = "\n".join(lines[class_b_method_idx:])

        assert "Method in ClassB" not in class_a_section
        assert "Method in ClassB" in class_b_section


def test_docstring_with_triple_quotes_already_present():
    """Test that docstring with triple quotes already present is handled correctly."""
    code = """def foo():
    pass
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        test_file = tmppath / "test.py"
        test_file.write_text(code)

        patcher = DocstringPatcher(overwrite_existing=False)
        # Pass docstring that already has triple quotes
        modified = patcher.inject_docstring(
            test_file, "foo", '"""A function."""', None
        )

        # Should not have double triple quotes
        assert '""""""' not in modified
        assert '"""A function."""' in modified
