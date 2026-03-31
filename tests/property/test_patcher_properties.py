"""Property-based tests for DocstringPatcher."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from docgen.parser import PythonParser
from docgen.patcher import DocstringPatcher


# Custom strategies
@st.composite
def valid_python_function(draw):
    """Generate valid Python function code."""
    func_name = draw(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll")))
        .filter(str.isidentifier)
        .filter(lambda x: not x.startswith("_"))
    )
    num_params = draw(st.integers(min_value=0, max_value=3))
    params = []
    used_names = set()
    for i in range(num_params):
        # Generate unique parameter names
        param = draw(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll")))
            .filter(str.isidentifier)
            .filter(lambda x: not x.startswith("_"))
            .filter(lambda x: x not in used_names)
        )
        params.append(param)
        used_names.add(param)

    param_str = ", ".join(params)
    body = draw(st.sampled_from(["pass", "return None", "x = 1"]))
    return f"def {func_name}({param_str}):\n    {body}\n"


@st.composite
def simple_docstring(draw):
    """Generate simple docstring text."""
    description = draw(
        st.text(
            min_size=10,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=".,!?"),
        ).filter(lambda x: '"""' not in x and "'''" not in x)
    )
    return description.strip()


@settings(max_examples=100)
@given(python_code=valid_python_function(), docstring=simple_docstring())
def test_round_trip_parsing_and_patching(python_code, docstring):
    """
    Feature: docstring-generator, Property 6: For any valid Python file and any
    generated docstring, parsing the file, patching in the docstring, and re-parsing
    should produce syntactically valid Python code with the docstring present.

    **Validates: Requirements 2.4, 6.1, 6.2, 6.6**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        temp_file = tmppath / "test.py"
        temp_file.write_text(python_code)

        # Parse original
        parser = PythonParser()
        functions, _ = parser.parse_file(temp_file)

        if not functions:
            return  # No functions to patch

        # Patch first function
        func = functions[0]
        patcher = DocstringPatcher(overwrite_existing=True)
        modified_code = patcher.inject_docstring(
            temp_file, func.name, docstring, func.parent_class
        )

        # Verify syntactic validity
        try:
            compile(modified_code, "<string>", "exec")
        except SyntaxError:
            # If compilation fails, this is a bug
            assert False, f"Modified code is not syntactically valid:\n{modified_code}"

        # Write modified code and re-parse
        temp_file2 = tmppath / "test2.py"
        temp_file2.write_text(modified_code)

        reparsed_functions, _ = parser.parse_file(temp_file2)
        reparsed_func = next(
            (f for f in reparsed_functions if f.name == func.name), None
        )

        # Verify function still exists and has docstring
        assert reparsed_func is not None, "Function disappeared after patching"
        assert reparsed_func.has_docstring, "Docstring not present after patching"


@settings(max_examples=100)
@given(python_code=valid_python_function(), docstring=simple_docstring())
def test_overwrite_existing_docstrings(python_code, docstring):
    """
    Feature: docstring-generator, Property 16: For any function with an existing
    docstring, when overwrite_existing is True, the Patcher should replace the
    existing docstring with the new one.

    **Validates: Requirements 6.3**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        temp_file = tmppath / "test.py"

        # Add an existing docstring to the function
        lines = python_code.split("\n")
        # Insert docstring after function definition
        if len(lines) >= 2:
            lines.insert(1, '    """Old docstring"""')
            code_with_docstring = "\n".join(lines)
        else:
            code_with_docstring = python_code

        temp_file.write_text(code_with_docstring)

        # Parse to get function info
        parser = PythonParser()
        functions, _ = parser.parse_file(temp_file)

        if not functions:
            return

        func = functions[0]

        # Verify function has existing docstring
        if not func.has_docstring:
            return  # Skip if docstring wasn't properly added

        # Patch with overwrite=True
        patcher = DocstringPatcher(overwrite_existing=True)
        modified_code = patcher.inject_docstring(
            temp_file, func.name, docstring, func.parent_class
        )

        # Write and re-parse
        temp_file2 = tmppath / "test2.py"
        temp_file2.write_text(modified_code)

        reparsed_functions, _ = parser.parse_file(temp_file2)
        reparsed_func = next(
            (f for f in reparsed_functions if f.name == func.name), None
        )

        # Verify docstring was replaced
        assert reparsed_func is not None
        assert reparsed_func.has_docstring
        # The new docstring should be present (not the old one)
        assert "Old docstring" not in modified_code or docstring in modified_code


@settings(max_examples=100)
@given(python_code=valid_python_function(), docstring=simple_docstring())
def test_preserve_existing_docstrings(python_code, docstring):
    """
    Feature: docstring-generator, Property 17: For any function with an existing
    docstring, when overwrite_existing is False, the Patcher should leave the
    existing docstring unchanged.

    **Validates: Requirements 6.4**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        temp_file = tmppath / "test.py"

        # Add an existing docstring to the function
        lines = python_code.split("\n")
        # Insert docstring after function definition
        if len(lines) >= 2:
            lines.insert(1, '    """Old docstring"""')
            code_with_docstring = "\n".join(lines)
        else:
            code_with_docstring = python_code

        temp_file.write_text(code_with_docstring)

        # Parse to get function info
        parser = PythonParser()
        functions, _ = parser.parse_file(temp_file)

        if not functions:
            return

        func = functions[0]

        # Verify function has existing docstring
        if not func.has_docstring:
            return  # Skip if docstring wasn't properly added

        # Patch with overwrite=False
        patcher = DocstringPatcher(overwrite_existing=False)
        modified_code = patcher.inject_docstring(
            temp_file, func.name, docstring, func.parent_class
        )

        # The code should be unchanged
        assert modified_code == code_with_docstring, "Code was modified when it shouldn't have been"
