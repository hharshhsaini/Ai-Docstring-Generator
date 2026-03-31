"""Docstring formatter and validator.

This module provides functionality to validate and format docstrings according
to different style conventions (Google, NumPy, Sphinx).
"""

import re
from typing import Optional
from docstring_parser import parse as parse_google
from docstring_parser.google import parse as parse_google_style
from docstring_parser.numpydoc import parse as parse_numpy
from docstring_parser.rest import parse as parse_sphinx


class DocstringFormatter:
    """Validates and formats docstrings according to style conventions.
    
    Attributes:
        style: Target docstring style (google, numpy, sphinx)
    """
    
    def __init__(self, style: str):
        """Initialize formatter with target style.
        
        Args:
            style: Docstring style - must be one of: google, numpy, sphinx
            
        Raises:
            ValueError: If style is not supported
        """
        if style not in ['google', 'numpy', 'sphinx']:
            raise ValueError(f"Unsupported style: {style}. Must be one of: google, numpy, sphinx")
        self.style = style
    
    def validate(self, docstring: str) -> tuple[bool, Optional[str]]:
        """Validate docstring conforms to style conventions.
        
        Args:
            docstring: Docstring text to validate
            
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
            If invalid, error_message contains a description of the validation failure.
        """
        # Check for empty or whitespace-only docstrings first
        if not docstring or not docstring.strip():
            return False, "Missing short description"
        
        try:
            # Parse docstring according to style
            if self.style == "google":
                parsed = parse_google_style(docstring)
            elif self.style == "numpy":
                parsed = parse_numpy(docstring)
            elif self.style == "sphinx":
                parsed = parse_sphinx(docstring)
            else:
                return False, f"Unknown style: {self.style}"
            
            # Check for required sections
            if not parsed.short_description or not parsed.short_description.strip():
                return False, "Missing short description"
            
            # Validation passed
            return True, None
            
        except Exception as e:
            return False, f"Parse error: {e}"
    
    def format(self, docstring: str) -> str:
        """Format docstring to clean LLM output.
        
        This method:
        - Removes code fences (```python, ```)
        - Strips leading/trailing whitespace
        - Ensures proper triple-quote wrapping
        
        Args:
            docstring: Raw docstring text from LLM
            
        Returns:
            Formatted docstring text ready for injection
        """
        # Strip leading/trailing whitespace first
        docstring = docstring.strip()
        
        # Remove outer triple quotes if present (do this first)
        if docstring.startswith('"""') and docstring.endswith('"""'):
            docstring = docstring[3:-3].strip()
        elif docstring.startswith("'''") and docstring.endswith("'''"):
            docstring = docstring[3:-3].strip()
        
        # Remove code fences - iterate until all are gone
        max_iterations = 10  # Prevent infinite loop
        for _ in range(max_iterations):
            original = docstring
            
            # Remove opening fences
            docstring = re.sub(r'^```python\s*\n?', '', docstring, flags=re.MULTILINE)
            docstring = re.sub(r'^```\s*\n?', '', docstring, flags=re.MULTILINE)
            # Remove closing fences
            docstring = re.sub(r'\n?\s*```$', '', docstring, flags=re.MULTILINE)
            docstring = docstring.strip()
            
            # If no changes were made, we're done
            if docstring == original:
                break
        
        # Remove inner triple quotes if present (after removing code fences)
        if docstring.startswith('"""') and docstring.endswith('"""'):
            docstring = docstring[3:-3].strip()
        elif docstring.startswith("'''") and docstring.endswith("'''"):
            docstring = docstring[3:-3].strip()
        
        # Final strip
        docstring = docstring.strip()
        
        # Don't add quotes here - they'll be added by the patcher
        return docstring
