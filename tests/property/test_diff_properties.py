"""Property-based tests for diff generation."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from docgen.diff import generate_diff
from docgen.models import FunctionInfo


@st.composite
def valid_python_function(draw):
    """Generate valid Python function code."""
    func_name = draw(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll")))
        .filter(str.isidentifier)
        .filter(lambda x: not x.startswith("_"))
    )
    return f"def {func_name}():\n    pass\n"


@settings(max_examples=100)
@given(
    python_code=valid_python_function(),
    docstring=st.text(min_size=1, max_size=100).filter(lambda x: '"""' not in x),
)
def test_property_dry_run_preserves_files(python_code, docstring):
    """
    Feature: docstring-generator, Property 20: For any file processed in dry-run mode,
    the original file should remain unmodified after processing completes.

    Validates: Requirements 8.2, 9.1
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(python_code)
        temp_path = Path(f.name)

    try:
        # Read original content
        original_content = temp_path.read_text()

        # Create function info
        func_info = FunctionInfo(
            name="test_func",
            params=[],
            return_type=None,
            body_preview="pass",
            has_docstring=False,
            existing_docstring=None,
            line_number=1,
            parent_class=None,
        )

        # Generate diff (simulates dry-run mode)
        diff = generate_diff(temp_path, func_info, docstring)

        # Verify file is unchanged
        assert temp_path.read_text() == original_content

        # Verify diff was generated (if function exists)
        if "def " in python_code:
            assert isinstance(diff, str)

    finally:
        temp_path.unlink()
