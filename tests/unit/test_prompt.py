"""Unit tests for prompt builder.

This module contains unit tests for the PromptBuilder component, testing
specific examples, edge cases, and formatting scenarios.
"""

import pytest
from src.docgen.prompt import PromptBuilder
from src.docgen.models import FunctionInfo


class TestPromptBuilder:
    """Test suite for PromptBuilder class."""
    
    def test_init_with_google_style(self):
        """Test initialization with Google style."""
        builder = PromptBuilder(style='google')
        assert builder.style == 'google'
    
    def test_init_with_numpy_style(self):
        """Test initialization with NumPy style."""
        builder = PromptBuilder(style='numpy')
        assert builder.style == 'numpy'
    
    def test_init_with_sphinx_style(self):
        """Test initialization with Sphinx style."""
        builder = PromptBuilder(style='sphinx')
        assert builder.style == 'sphinx'
    
    def test_build_prompt_with_no_parameters(self):
        """Test prompt format for functions with no parameters."""
        func_info = FunctionInfo(
            name='get_value',
            params=[],
            return_type='int',
            body_preview='return 42',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify function signature
        assert 'def get_value() -> int:' in prompt
        
        # Verify body preview
        assert 'return 42' in prompt
        
        # Verify style is mentioned
        assert 'Google' in prompt
        
        # Verify no existing docstring context
        assert 'Existing docstring' not in prompt or \
               'Existing docstring (improve if needed):\n\n' in prompt
    
    def test_build_prompt_with_simple_parameters(self):
        """Test prompt format for functions with simple parameters."""
        func_info = FunctionInfo(
            name='add',
            params=[('a', 'int'), ('b', 'int')],
            return_type='int',
            body_preview='return a + b',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='numpy')
        prompt = builder.build_prompt(func_info)
        
        # Verify function signature with type hints
        assert 'def add(a: int, b: int) -> int:' in prompt
        
        # Verify parameters are mentioned
        assert 'a' in prompt
        assert 'b' in prompt
        
        # Verify style
        assert 'Numpy' in prompt
    
    def test_build_prompt_with_complex_type_hints(self):
        """Test prompt format for functions with complex type hints."""
        func_info = FunctionInfo(
            name='process_data',
            params=[
                ('data', 'list[dict[str, Any]]'),
                ('config', 'Optional[Config]'),
                ('callback', 'Callable[[str], None]')
            ],
            return_type='tuple[bool, str]',
            body_preview='# Process the data\nresult = []\nfor item in data:\n    result.append(item)',
            has_docstring=False,
            line_number=10
        )
        
        builder = PromptBuilder(style='sphinx')
        prompt = builder.build_prompt(func_info)
        
        # Verify complex type hints are preserved
        assert 'list[dict[str, Any]]' in prompt
        assert 'Optional[Config]' in prompt
        assert 'Callable[[str], None]' in prompt
        assert 'tuple[bool, str]' in prompt
        
        # Verify function name
        assert 'process_data' in prompt
        
        # Verify style
        assert 'Sphinx' in prompt
    
    def test_build_prompt_with_no_type_hints(self):
        """Test prompt format for functions without type hints."""
        func_info = FunctionInfo(
            name='legacy_function',
            params=[('x', None), ('y', None), ('z', None)],
            return_type=None,
            body_preview='return x + y + z',
            has_docstring=False,
            line_number=5
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify function signature without type hints
        assert 'def legacy_function(x, y, z):' in prompt
        
        # Verify no return type annotation
        assert ' -> ' not in 'def legacy_function(x, y, z):'
        
        # Verify parameters are still mentioned
        assert 'x' in prompt
        assert 'y' in prompt
        assert 'z' in prompt
    
    def test_build_prompt_with_mixed_type_hints(self):
        """Test prompt format for functions with mixed type hints."""
        func_info = FunctionInfo(
            name='mixed_function',
            params=[('a', 'int'), ('b', None), ('c', 'str')],
            return_type='bool',
            body_preview='return True',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify mixed type hints
        assert 'a: int' in prompt
        assert 'b,' in prompt or 'b)' in prompt  # b without type hint
        assert 'c: str' in prompt
        assert '-> bool' in prompt
    
    def test_build_prompt_with_existing_docstring(self):
        """Test prompt includes existing docstring for reference."""
        existing_doc = '''Calculate the sum of two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            The sum of a and b
        '''
        
        func_info = FunctionInfo(
            name='add',
            params=[('a', 'int'), ('b', 'int')],
            return_type='int',
            body_preview='return a + b',
            has_docstring=True,
            existing_docstring=existing_doc,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify existing docstring is included
        assert existing_doc in prompt
        
        # Verify context about existing docstring
        assert 'Existing docstring' in prompt
        assert 'improve' in prompt.lower()
    
    def test_build_prompt_google_style(self):
        """Test prompt format specifically for Google style."""
        func_info = FunctionInfo(
            name='test_func',
            params=[('x', 'int')],
            return_type='str',
            body_preview='return str(x)',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify Google style is mentioned
        assert 'Google' in prompt
        
        # Verify requirements mention Google conventions
        assert 'Google' in prompt and 'conventions' in prompt.lower()
    
    def test_build_prompt_numpy_style(self):
        """Test prompt format specifically for NumPy style."""
        func_info = FunctionInfo(
            name='test_func',
            params=[('x', 'int')],
            return_type='str',
            body_preview='return str(x)',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='numpy')
        prompt = builder.build_prompt(func_info)
        
        # Verify NumPy style is mentioned
        assert 'Numpy' in prompt
        
        # Verify requirements mention NumPy conventions
        assert 'Numpy' in prompt and 'conventions' in prompt.lower()
    
    def test_build_prompt_sphinx_style(self):
        """Test prompt format specifically for Sphinx style."""
        func_info = FunctionInfo(
            name='test_func',
            params=[('x', 'int')],
            return_type='str',
            body_preview='return str(x)',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='sphinx')
        prompt = builder.build_prompt(func_info)
        
        # Verify Sphinx style is mentioned
        assert 'Sphinx' in prompt
        
        # Verify requirements mention Sphinx conventions
        assert 'Sphinx' in prompt and 'conventions' in prompt.lower()
    
    def test_format_signature_simple(self):
        """Test _format_signature with simple function."""
        func_info = FunctionInfo(
            name='simple',
            params=[],
            return_type=None,
            body_preview='pass',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        signature = builder._format_signature(func_info)
        
        assert signature == 'def simple():'
    
    def test_format_signature_with_return_type(self):
        """Test _format_signature with return type."""
        func_info = FunctionInfo(
            name='get_number',
            params=[],
            return_type='int',
            body_preview='return 42',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        signature = builder._format_signature(func_info)
        
        assert signature == 'def get_number() -> int:'
    
    def test_format_signature_with_params_and_types(self):
        """Test _format_signature with parameters and type hints."""
        func_info = FunctionInfo(
            name='multiply',
            params=[('x', 'int'), ('y', 'int')],
            return_type='int',
            body_preview='return x * y',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        signature = builder._format_signature(func_info)
        
        assert signature == 'def multiply(x: int, y: int) -> int:'
    
    def test_prompt_contains_requirements_section(self):
        """Test that prompt contains requirements section."""
        func_info = FunctionInfo(
            name='test',
            params=[],
            body_preview='pass',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify requirements section exists
        assert 'Requirements:' in prompt
        
        # Verify key requirements are mentioned
        assert 'conventions' in prompt.lower()
        assert 'parameters' in prompt.lower()
        assert 'return' in prompt.lower()
    
    def test_prompt_structure(self):
        """Test overall prompt structure."""
        func_info = FunctionInfo(
            name='test',
            params=[('x', 'int')],
            return_type='str',
            body_preview='return str(x)',
            has_docstring=False,
            line_number=1
        )
        
        builder = PromptBuilder(style='google')
        prompt = builder.build_prompt(func_info)
        
        # Verify key sections are present in order
        assert 'Function signature:' in prompt
        assert 'Function body preview:' in prompt
        assert 'Requirements:' in prompt
        assert 'Generate the docstring:' in prompt
        
        # Verify order
        sig_pos = prompt.index('Function signature:')
        body_pos = prompt.index('Function body preview:')
        req_pos = prompt.index('Requirements:')
        gen_pos = prompt.index('Generate the docstring:')
        
        assert sig_pos < body_pos < req_pos < gen_pos
