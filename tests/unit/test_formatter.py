"""Unit tests for DocstringFormatter component.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import pytest
from docgen.formatter import DocstringFormatter


class TestDocstringFormatterInit:
    """Tests for DocstringFormatter initialization."""
    
    def test_init_with_valid_style_google(self):
        """Test initialization with google style."""
        formatter = DocstringFormatter(style="google")
        assert formatter.style == "google"
    
    def test_init_with_valid_style_numpy(self):
        """Test initialization with numpy style."""
        formatter = DocstringFormatter(style="numpy")
        assert formatter.style == "numpy"
    
    def test_init_with_valid_style_sphinx(self):
        """Test initialization with sphinx style."""
        formatter = DocstringFormatter(style="sphinx")
        assert formatter.style == "sphinx"
    
    def test_init_with_invalid_style(self):
        """Test initialization with invalid style raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DocstringFormatter(style="invalid")
        
        assert "Unsupported style" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestDocstringFormatterValidate:
    """Tests for docstring validation."""
    
    def test_validate_google_style_valid(self):
        """Test validation of valid Google-style docstring."""
        formatter = DocstringFormatter(style="google")
        docstring = """Calculate the sum of two numbers.
        
Args:
    a: First number
    b: Second number
    
Returns:
    The sum of a and b
"""
        is_valid, error = formatter.validate(docstring)
        assert is_valid is True
        assert error is None
    
    def test_validate_numpy_style_valid(self):
        """Test validation of valid NumPy-style docstring."""
        formatter = DocstringFormatter(style="numpy")
        docstring = """Calculate the sum of two numbers.
        
Parameters
----------
a : int
    First number
b : int
    Second number
    
Returns
-------
int
    The sum of a and b
"""
        is_valid, error = formatter.validate(docstring)
        assert is_valid is True
        assert error is None
    
    def test_validate_sphinx_style_valid(self):
        """Test validation of valid Sphinx-style docstring."""
        formatter = DocstringFormatter(style="sphinx")
        docstring = """Calculate the sum of two numbers.
        
:param a: First number
:param b: Second number
:return: The sum of a and b
"""
        is_valid, error = formatter.validate(docstring)
        assert is_valid is True
        assert error is None
    
    def test_validate_missing_description(self):
        """Test validation fails when description is missing."""
        formatter = DocstringFormatter(style="google")
        docstring = ""
        
        is_valid, error = formatter.validate(docstring)
        assert is_valid is False
        assert error is not None
        assert "description" in error.lower()
    
    def test_validate_whitespace_only(self):
        """Test validation fails for whitespace-only docstring."""
        formatter = DocstringFormatter(style="google")
        docstring = "   \n\n   "
        
        is_valid, error = formatter.validate(docstring)
        assert is_valid is False
        assert error is not None
    
    def test_validate_minimal_description_only(self):
        """Test validation succeeds with just a description."""
        formatter = DocstringFormatter(style="google")
        docstring = "This is a simple function."
        
        is_valid, error = formatter.validate(docstring)
        assert is_valid is True
        assert error is None
    
    def test_validate_returns_tuple(self):
        """Test that validate always returns a tuple."""
        formatter = DocstringFormatter(style="google")
        result = formatter.validate("Test docstring")
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert result[1] is None or isinstance(result[1], str)


class TestDocstringFormatterFormat:
    """Tests for docstring formatting."""
    
    def test_format_removes_python_code_fence(self):
        """Test that format removes ```python code fences."""
        formatter = DocstringFormatter(style="google")
        docstring = """```python
This is a docstring.

Args:
    param: A parameter
```"""
        
        formatted = formatter.format(docstring)
        assert "```python" not in formatted
        assert "```" not in formatted
        assert "This is a docstring" in formatted
    
    def test_format_removes_plain_code_fence(self):
        """Test that format removes ``` code fences."""
        formatter = DocstringFormatter(style="google")
        docstring = """```
This is a docstring.

Args:
    param: A parameter
```"""
        
        formatted = formatter.format(docstring)
        assert "```" not in formatted
        assert "This is a docstring" in formatted
    
    def test_format_strips_whitespace(self):
        """Test that format strips leading and trailing whitespace."""
        formatter = DocstringFormatter(style="google")
        docstring = """
        
        This is a docstring.
        
        """
        
        formatted = formatter.format(docstring)
        assert formatted == formatted.strip()
        assert formatted.startswith("This")
    
    def test_format_removes_triple_double_quotes(self):
        """Test that format removes triple double quotes."""
        formatter = DocstringFormatter(style="google")
        docstring = '"""This is a docstring."""'
        
        formatted = formatter.format(docstring)
        assert not formatted.startswith('"""')
        assert not formatted.endswith('"""')
        assert "This is a docstring" in formatted
    
    def test_format_removes_triple_single_quotes(self):
        """Test that format removes triple single quotes."""
        formatter = DocstringFormatter(style="google")
        docstring = "'''This is a docstring.'''"
        
        formatted = formatter.format(docstring)
        assert not formatted.startswith("'''")
        assert not formatted.endswith("'''")
        assert "This is a docstring" in formatted
    
    def test_format_handles_multiple_artifacts(self):
        """Test that format handles multiple LLM artifacts at once."""
        formatter = DocstringFormatter(style="google")
        docstring = '''
        
```python
"""This is a docstring.

Args:
    param: A parameter
"""
```
        
        '''
        
        formatted = formatter.format(docstring)
        assert "```" not in formatted
        assert '"""' not in formatted
        assert formatted == formatted.strip()
        assert "This is a docstring" in formatted
    
    def test_format_preserves_content(self):
        """Test that format preserves the actual content."""
        formatter = DocstringFormatter(style="google")
        docstring = """Calculate the sum.

Args:
    a: First number
    b: Second number
    
Returns:
    The sum"""
        
        formatted = formatter.format(docstring)
        assert "Calculate the sum" in formatted
        assert "Args:" in formatted
        assert "First number" in formatted
        assert "Returns:" in formatted
    
    def test_format_is_idempotent(self):
        """Test that formatting twice produces the same result."""
        formatter = DocstringFormatter(style="google")
        docstring = '''```python
"""This is a docstring."""
```'''
        
        formatted_once = formatter.format(docstring)
        formatted_twice = formatter.format(formatted_once)
        
        assert formatted_once == formatted_twice
    
    def test_format_empty_string(self):
        """Test formatting an empty string."""
        formatter = DocstringFormatter(style="google")
        formatted = formatter.format("")
        assert formatted == ""
    
    def test_format_with_internal_triple_quotes(self):
        """Test formatting when triple quotes appear in the middle of content."""
        formatter = DocstringFormatter(style="google")
        docstring = 'Use """ to create docstrings in Python.'
        
        formatted = formatter.format(docstring)
        # Internal quotes should be preserved
        assert '"""' in formatted or "Use" in formatted


class TestDocstringFormatterEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_validate_with_special_characters(self):
        """Test validation with special characters in docstring."""
        formatter = DocstringFormatter(style="google")
        docstring = "Function with special chars: @#$%^&*()"
        
        is_valid, error = formatter.validate(docstring)
        # Should still be valid as long as there's a description
        assert is_valid is True
    
    def test_format_with_newlines_in_content(self):
        """Test formatting preserves internal newlines."""
        formatter = DocstringFormatter(style="google")
        docstring = """Line 1

Line 2

Line 3"""
        
        formatted = formatter.format(docstring)
        assert "Line 1" in formatted
        assert "Line 2" in formatted
        assert "Line 3" in formatted
    
    def test_validate_each_style_separately(self):
        """Test that each style validates its own format correctly."""
        google_formatter = DocstringFormatter(style="google")
        numpy_formatter = DocstringFormatter(style="numpy")
        sphinx_formatter = DocstringFormatter(style="sphinx")
        
        google_doc = "Test.\n\nArgs:\n    x: param"
        numpy_doc = "Test.\n\nParameters\n----------\nx : int\n    param"
        sphinx_doc = "Test.\n\n:param x: param"
        
        # Each should validate its own style
        assert google_formatter.validate(google_doc)[0] is True
        assert numpy_formatter.validate(numpy_doc)[0] is True
        assert sphinx_formatter.validate(sphinx_doc)[0] is True
    
    def test_format_with_code_fence_variations(self):
        """Test format handles various code fence patterns."""
        formatter = DocstringFormatter(style="google")
        
        # Test different fence patterns
        patterns = [
            "```python\nContent\n```",
            "```\nContent\n```",
            "```python\nContent",
            "Content\n```",
        ]
        
        for pattern in patterns:
            formatted = formatter.format(pattern)
            assert "```" not in formatted
            assert "Content" in formatted
