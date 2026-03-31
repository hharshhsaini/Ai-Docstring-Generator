"""Property-based tests for DocstringFormatter component.

**Validates: Requirements 5.4, 5.5**
"""

import pytest
from hypothesis import given, settings, strategies as st

from docgen.formatter import DocstringFormatter


@pytest.mark.property
class TestDocstringFormatterProperties:
    """Property tests for DocstringFormatter class."""
    
    @settings(max_examples=100)
    @given(
        style=st.sampled_from(["google", "numpy", "sphinx"]),
        has_description=st.booleans(),
        has_args=st.booleans(),
        has_returns=st.booleans(),
        data=st.data(),
    )
    def test_property_14_docstring_style_validation(
        self,
        style,
        has_description,
        has_args,
        has_returns,
        data,
    ):
        """Property 14: Docstring Style Validation.
        
        For any generated docstring and target style, the Formatter should correctly
        validate whether the docstring conforms to the style conventions.
        
        **Validates: Requirements 5.4**
        """
        formatter = DocstringFormatter(style=style)
        
        # Generate a docstring based on the style
        description = data.draw(
            st.text(min_size=10, max_size=100, alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                whitelist_characters=".,!?-"
            ))
        ).strip() if has_description else ""
        
        # Ensure we have at least a minimal description
        if not description:
            description = "This is a test function."
        
        # Build docstring according to style
        if style == "google":
            docstring_parts = [description]
            
            if has_args:
                docstring_parts.append("")
                docstring_parts.append("Args:")
                docstring_parts.append("    param1: First parameter")
                docstring_parts.append("    param2: Second parameter")
            
            if has_returns:
                docstring_parts.append("")
                docstring_parts.append("Returns:")
                docstring_parts.append("    The result value")
            
            docstring = "\n".join(docstring_parts)
        
        elif style == "numpy":
            docstring_parts = [description]
            
            if has_args:
                docstring_parts.append("")
                docstring_parts.append("Parameters")
                docstring_parts.append("----------")
                docstring_parts.append("param1 : int")
                docstring_parts.append("    First parameter")
                docstring_parts.append("param2 : str")
                docstring_parts.append("    Second parameter")
            
            if has_returns:
                docstring_parts.append("")
                docstring_parts.append("Returns")
                docstring_parts.append("-------")
                docstring_parts.append("int")
                docstring_parts.append("    The result value")
            
            docstring = "\n".join(docstring_parts)
        
        else:  # sphinx
            docstring_parts = [description]
            
            if has_args:
                docstring_parts.append("")
                docstring_parts.append(":param param1: First parameter")
                docstring_parts.append(":param param2: Second parameter")
            
            if has_returns:
                docstring_parts.append(":return: The result value")
            
            docstring = "\n".join(docstring_parts)
        
        # Validate the docstring
        is_valid, error_message = formatter.validate(docstring)
        
        # Property 1: Docstring with description should be valid
        if has_description and description:
            assert is_valid is True, \
                f"Docstring with description should be valid for {style} style. Error: {error_message}"
            assert error_message is None, \
                f"Valid docstring should have no error message, got: {error_message}"
        
        # Property 2: Validation should return a tuple
        assert isinstance(is_valid, bool), \
            "First element of validation result should be a boolean"
        assert error_message is None or isinstance(error_message, str), \
            "Second element should be None or a string"
        
        # Property 3: If valid, error_message should be None
        if is_valid:
            assert error_message is None, \
                "When is_valid is True, error_message should be None"
        
        # Property 4: If invalid, error_message should be a non-empty string
        if not is_valid:
            assert error_message is not None, \
                "When is_valid is False, error_message should not be None"
            assert isinstance(error_message, str), \
                "error_message should be a string"
            assert len(error_message) > 0, \
                "error_message should not be empty"
    
    @settings(max_examples=100)
    @given(
        style=st.sampled_from(["google", "numpy", "sphinx"]),
        missing_component=st.sampled_from(["description", "empty"]),
        data=st.data(),
    )
    def test_property_15_validation_error_messages(
        self,
        style,
        missing_component,
        data,
    ):
        """Property 15: Validation Error Messages.
        
        For any invalid docstring, the Formatter should return a descriptive error
        message explaining the validation failure.
        
        **Validates: Requirements 5.5**
        """
        formatter = DocstringFormatter(style=style)
        
        # Generate invalid docstrings based on missing_component
        if missing_component == "description":
            # Empty or whitespace-only docstring (missing description)
            docstring = data.draw(st.sampled_from(["", "   ", "\n\n", "\t\t"]))
        
        elif missing_component == "empty":
            # Completely empty
            docstring = ""
        
        else:
            docstring = ""
        
        # Validate the invalid docstring
        is_valid, error_message = formatter.validate(docstring)
        
        # Property 1: Invalid docstring should not be valid
        assert is_valid is False, \
            f"Invalid docstring should not be valid for {style} style"
        
        # Property 2: Error message should be present
        assert error_message is not None, \
            "Invalid docstring should have an error message"
        
        # Property 3: Error message should be a non-empty string
        assert isinstance(error_message, str), \
            "Error message should be a string"
        assert len(error_message) > 0, \
            "Error message should not be empty"
        
        # Property 4: Error message should be descriptive
        # It should contain some indication of what went wrong
        assert any(keyword in error_message.lower() for keyword in [
            "missing", "error", "parse", "invalid", "description", "required"
        ]), f"Error message should be descriptive, got: {error_message}"
        
        # Property 5: For missing description, error should mention it
        if missing_component in ["description", "empty"]:
            assert "description" in error_message.lower() or "missing" in error_message.lower(), \
                f"Error message for missing description should mention 'description' or 'missing', got: {error_message}"
    
    @settings(max_examples=100)
    @given(
        style=st.sampled_from(["google", "numpy", "sphinx"]),
        has_code_fence=st.booleans(),
        fence_type=st.sampled_from(["python", "plain", "both"]),
        has_extra_whitespace=st.booleans(),
        has_triple_quotes=st.booleans(),
        quote_type=st.sampled_from(["double", "single"]),
        data=st.data(),
    )
    def test_property_format_cleans_llm_output(
        self,
        style,
        has_code_fence,
        fence_type,
        has_extra_whitespace,
        has_triple_quotes,
        quote_type,
        data,
    ):
        """Property: Format method cleans LLM output.
        
        The format method should remove code fences, strip whitespace, and handle
        triple quotes correctly.
        
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        formatter = DocstringFormatter(style=style)
        
        # Generate a clean docstring
        description = data.draw(
            st.text(min_size=10, max_size=100, alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                whitelist_characters=".,!?-"
            ))
        ).strip()
        
        if not description:
            description = "This is a test function."
        
        # Build a simple valid docstring
        if style == "google":
            clean_docstring = f"{description}\n\nArgs:\n    param: A parameter\n\nReturns:\n    A value"
        elif style == "numpy":
            clean_docstring = f"{description}\n\nParameters\n----------\nparam : int\n    A parameter\n\nReturns\n-------\nint\n    A value"
        else:  # sphinx
            clean_docstring = f"{description}\n\n:param param: A parameter\n:return: A value"
        
        # Add various LLM artifacts
        dirty_docstring = clean_docstring
        
        # Add code fences
        if has_code_fence:
            if fence_type == "python":
                dirty_docstring = f"```python\n{dirty_docstring}\n```"
            elif fence_type == "plain":
                dirty_docstring = f"```\n{dirty_docstring}\n```"
            else:  # both
                dirty_docstring = f"```python\n{dirty_docstring}\n```"
        
        # Add extra whitespace
        if has_extra_whitespace:
            dirty_docstring = f"\n\n  {dirty_docstring}  \n\n"
        
        # Add triple quotes
        if has_triple_quotes:
            if quote_type == "double":
                dirty_docstring = f'"""{dirty_docstring}"""'
            else:
                dirty_docstring = f"'''{dirty_docstring}'''"
        
        # Format the dirty docstring
        formatted = formatter.format(dirty_docstring)
        
        # Property 1: Code fences should be removed
        assert "```" not in formatted, \
            "Formatted docstring should not contain code fences"
        assert "```python" not in formatted, \
            "Formatted docstring should not contain python code fences"
        
        # Property 2: Leading/trailing whitespace should be stripped
        assert formatted == formatted.strip(), \
            "Formatted docstring should have no leading/trailing whitespace"
        
        # Property 3: Triple quotes should be removed (patcher will add them)
        assert not formatted.startswith('"""') and not formatted.endswith('"""'), \
            "Formatted docstring should not have triple double quotes"
        assert not formatted.startswith("'''") and not formatted.endswith("'''"), \
            "Formatted docstring should not have triple single quotes"
        
        # Property 4: Core content should be preserved
        assert description in formatted, \
            f"Formatted docstring should preserve the description. Expected '{description}' in '{formatted}'"
        
        # Property 5: Formatted output should not be empty
        assert len(formatted) > 0, \
            "Formatted docstring should not be empty"
        
        # Property 6: Format should be idempotent (formatting twice gives same result)
        formatted_twice = formatter.format(formatted)
        assert formatted == formatted_twice, \
            "Formatting should be idempotent"
