"""Property-based tests for prompt builder.

This module contains property-based tests that verify universal correctness
properties of the PromptBuilder component across randomized inputs.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.docgen.prompt import PromptBuilder
from src.docgen.models import FunctionInfo


# Strategy for generating valid docstring styles
styles = st.sampled_from(['google', 'numpy', 'sphinx'])

# Strategy for generating function names (use from_regex for valid identifiers)
function_names = st.from_regex(r'[a-z][a-z0-9_]{0,29}', fullmatch=True)

# Strategy for generating parameter names (use from_regex for valid identifiers)
param_names = st.from_regex(r'[a-z][a-z0-9_]{0,19}', fullmatch=True)

# Strategy for generating type hints
type_hints = st.one_of(
    st.none(),
    st.sampled_from(['int', 'str', 'bool', 'float', 'list', 'dict', 'Any', 'Optional[str]'])
)

# Strategy for generating parameters
parameters = st.lists(
    st.tuples(param_names, type_hints),
    min_size=0,
    max_size=5
)

# Strategy for generating body preview
body_previews = st.text(min_size=1, max_size=200)

# Strategy for generating docstrings
docstrings = st.text(min_size=10, max_size=300)


@settings(max_examples=100)
@given(
    style=styles,
    func_name=function_names,
    params=parameters,
    return_type=type_hints,
    body_preview=body_previews
)
def test_property_9_prompt_contains_required_metadata(
    style, func_name, params, return_type, body_preview
):
    """Property 9: Prompt Contains Required Metadata.
    
    Feature: docstring-generator, Property 9: For any function metadata, the 
    generated prompt should contain the function signature, parameter types, 
    return type, and body preview.
    
    Validates: Requirements 3.1
    """
    # Create function info
    func_info = FunctionInfo(
        name=func_name,
        params=params,
        return_type=return_type,
        body_preview=body_preview,
        has_docstring=False,
        line_number=1
    )
    
    # Build prompt
    builder = PromptBuilder(style=style)
    prompt = builder.build_prompt(func_info)
    
    # Verify function name is in prompt
    assert func_name in prompt, f"Function name '{func_name}' not found in prompt"
    
    # Verify parameter names are in prompt
    for param_name, _ in params:
        assert param_name in prompt, f"Parameter '{param_name}' not found in prompt"
    
    # Verify return type is in prompt (if present)
    if return_type:
        assert return_type in prompt, f"Return type '{return_type}' not found in prompt"
    
    # Verify body preview is in prompt
    assert body_preview in prompt, "Body preview not found in prompt"


@settings(max_examples=100)
@given(
    style=styles,
    func_name=function_names,
    params=parameters,
    body_preview=body_previews
)
def test_property_10_prompt_includes_style(
    style, func_name, params, body_preview
):
    """Property 10: Prompt Includes Style.
    
    Feature: docstring-generator, Property 10: For any docstring style (Google, 
    NumPy, Sphinx), the generated prompt should explicitly mention the target style.
    
    Validates: Requirements 3.2, 3.4
    """
    # Create function info
    func_info = FunctionInfo(
        name=func_name,
        params=params,
        body_preview=body_preview,
        has_docstring=False,
        line_number=1
    )
    
    # Build prompt
    builder = PromptBuilder(style=style)
    prompt = builder.build_prompt(func_info)
    
    # Verify style is mentioned in prompt (case-insensitive)
    style_lower = style.lower()
    prompt_lower = prompt.lower()
    
    assert style_lower in prompt_lower, \
        f"Style '{style}' not found in prompt"
    
    # Verify style appears multiple times (in template and requirements)
    style_count = prompt_lower.count(style_lower)
    assert style_count >= 2, \
        f"Style '{style}' should appear at least twice in prompt, found {style_count} times"


@settings(max_examples=100)
@given(
    style=styles,
    func_name=function_names,
    params=parameters,
    body_preview=body_previews,
    existing_docstring=docstrings
)
def test_property_11_prompt_includes_existing_docstring(
    style, func_name, params, body_preview, existing_docstring
):
    """Property 11: Prompt Includes Existing Docstring.
    
    Feature: docstring-generator, Property 11: For any function with an existing 
    docstring, the generated prompt should include the existing docstring text 
    for reference.
    
    Validates: Requirements 3.3
    """
    # Create function info with existing docstring
    func_info = FunctionInfo(
        name=func_name,
        params=params,
        body_preview=body_preview,
        has_docstring=True,
        existing_docstring=existing_docstring,
        line_number=1
    )
    
    # Build prompt
    builder = PromptBuilder(style=style)
    prompt = builder.build_prompt(func_info)
    
    # Verify existing docstring is in prompt
    assert existing_docstring in prompt, \
        "Existing docstring not found in prompt"
    
    # Verify there's context about it being an existing docstring
    prompt_lower = prompt.lower()
    assert 'existing' in prompt_lower or 'improve' in prompt_lower, \
        "Prompt should indicate that the docstring is existing"


@settings(max_examples=100)
@given(
    style=styles,
    func_name=function_names,
    params=parameters,
    body_preview=body_previews,
    has_existing=st.booleans(),
    existing_docstring=st.one_of(st.none(), docstrings)
)
def test_property_11_prompt_excludes_missing_docstring(
    style, func_name, params, body_preview, has_existing, existing_docstring
):
    """Property 11 (negative case): Prompt excludes docstring when not present.
    
    When a function does not have an existing docstring, the prompt should not
    include docstring reference text.
    
    Validates: Requirements 3.3
    """
    # Only test when there's no existing docstring
    if has_existing or existing_docstring:
        return
    
    # Create function info without existing docstring
    func_info = FunctionInfo(
        name=func_name,
        params=params,
        body_preview=body_preview,
        has_docstring=False,
        existing_docstring=None,
        line_number=1
    )
    
    # Build prompt
    builder = PromptBuilder(style=style)
    prompt = builder.build_prompt(func_info)
    
    # Verify no existing docstring context is present
    prompt_lower = prompt.lower()
    # The existing docstring section should be empty or not present
    assert 'existing docstring' not in prompt_lower or \
           prompt.count('Existing docstring') == 0 or \
           'Existing docstring (improve if needed):\n\n' in prompt, \
        "Prompt should not include existing docstring context when none exists"


@settings(max_examples=100)
@given(
    style=styles,
    func_name=function_names,
    params=parameters,
    body_preview=body_previews
)
def test_property_12_prompt_contains_output_instructions(
    style, func_name, params, body_preview
):
    """Property 12: Prompt Contains Output Instructions.
    
    Feature: docstring-generator, Property 12: For any generated prompt, it should 
    contain instructions to return only docstring text without code fences or 
    explanations.
    
    Validates: Requirements 3.5
    """
    # Create function info
    func_info = FunctionInfo(
        name=func_name,
        params=params,
        body_preview=body_preview,
        has_docstring=False,
        line_number=1
    )
    
    # Build prompt
    builder = PromptBuilder(style=style)
    prompt = builder.build_prompt(func_info)
    
    # Verify instructions about output format
    prompt_lower = prompt.lower()
    
    # Check for "only" instruction
    assert 'only' in prompt_lower, \
        "Prompt should instruct to return ONLY docstring text"
    
    # Check for "no code fences" or similar instruction
    assert 'no code' in prompt_lower or 'code fences' in prompt_lower or \
           'no explanations' in prompt_lower, \
        "Prompt should instruct not to include code fences or explanations"
    
    # Check for "docstring" in the output instructions
    assert 'docstring' in prompt_lower, \
        "Prompt should mention 'docstring' in output instructions"
