"""Unit tests for diff generation."""

import tempfile
from pathlib import Path

from docgen.diff import generate_diff, display_diff
from docgen.models import FunctionInfo


def test_generate_diff_no_existing_docstring():
    """Test diff generation for function without existing docstring."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """def add(a: int, b: int) -> int:
    return a + b
"""
        )
        temp_path = Path(f.name)

    try:
        func_info = FunctionInfo(
            name="add",
            params=[("a", "int"), ("b", "int")],
            return_type="int",
            body_preview="return a + b",
            has_docstring=False,
            existing_docstring=None,
            line_number=1,
            parent_class=None,
        )

        docstring = "Add two integers."

        diff = generate_diff(temp_path, func_info, docstring)

        # Verify diff contains expected markers
        assert "---" in diff
        assert "+++" in diff
        assert "+    " in diff  # Added line marker
        assert "Add two integers" in diff

    finally:
        temp_path.unlink()


def test_generate_diff_with_existing_docstring():
    """Test diff generation for function with existing docstring."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            '''def add(a: int, b: int) -> int:
    """Old docstring."""
    return a + b
'''
        )
        temp_path = Path(f.name)

    try:
        func_info = FunctionInfo(
            name="add",
            params=[("a", "int"), ("b", "int")],
            return_type="int",
            body_preview="return a + b",
            has_docstring=True,
            existing_docstring="Old docstring.",
            line_number=1,
            parent_class=None,
        )

        docstring = "Add two integers."

        diff = generate_diff(temp_path, func_info, docstring)

        # Verify diff shows replacement
        assert "---" in diff
        assert "+++" in diff
        assert "-    " in diff  # Removed line marker
        assert "+    " in diff  # Added line marker
        assert "Old docstring" in diff
        assert "Add two integers" in diff

    finally:
        temp_path.unlink()


def test_display_diff_empty():
    """Test display_diff with empty diff."""
    # Should not raise an error
    display_diff("")


def test_display_diff_with_content():
    """Test display_diff with actual diff content."""
    diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,3 @@
 def foo():
+    \"\"\"Docstring.\"\"\"
     pass
"""
    # Should not raise an error
    display_diff(diff)
