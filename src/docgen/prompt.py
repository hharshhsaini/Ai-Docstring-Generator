"""Prompt builder for LLM-based docstring generation.

This module constructs structured prompts from function metadata, ensuring
that LLMs receive all necessary context to generate accurate docstrings.
"""

from .models import FunctionInfo


class PromptBuilder:
    """Builds structured prompts for LLM providers from function metadata.
    
    The PromptBuilder constructs prompts that include:
    - Function signature with type hints
    - Parameter types and return type
    - Body preview for context
    - Target docstring style
    - Existing docstring (if present) for reference
    - Instructions to return only docstring text
    
    Attributes:
        style: Target docstring style (google, numpy, sphinx)
    """
    
    PROMPT_TEMPLATE = """Generate a {style} style docstring for the following Python function.

Function signature:
{signature}

Function body preview:
{body_preview}

Requirements:
- Follow {style} docstring conventions exactly
- Include descriptions for all parameters
- Include return value description
- Include raises section if exceptions are evident
- Return ONLY the docstring text (no code fences, no explanations)
- Use proper indentation for multi-line docstrings

{existing_docstring_context}

Generate the docstring:"""
    
    def __init__(self, style: str):
        """Initialize PromptBuilder with target docstring style.
        
        Args:
            style: Target docstring style (google, numpy, sphinx)
        """
        self.style = style
    
    def build_prompt(self, func_info: FunctionInfo) -> str:
        """Build a structured prompt for docstring generation.
        
        Constructs a prompt containing the function signature, parameter types,
        return type, body preview, and target style. If an existing docstring
        is present, it's included for reference.
        
        Args:
            func_info: Function metadata extracted from AST
            
        Returns:
            Formatted prompt string ready for LLM provider
        """
        signature = self._format_signature(func_info)
        body_preview = func_info.body_preview
        
        existing_context = ""
        if func_info.existing_docstring:
            existing_context = f"Existing docstring (improve if needed):\n{func_info.existing_docstring}"
        
        return self.PROMPT_TEMPLATE.format(
            style=self.style.capitalize(),
            signature=signature,
            body_preview=body_preview,
            existing_docstring_context=existing_context
        )
    
    def _format_signature(self, func_info: FunctionInfo) -> str:
        """Format function signature with type hints.
        
        Creates a readable function signature including parameter names,
        type hints, and return type annotation.
        
        Args:
            func_info: Function metadata
            
        Returns:
            Formatted function signature string
        """
        # Build parameter list with type hints
        param_strs = []
        for param_name, type_hint in func_info.params:
            if type_hint:
                param_strs.append(f"{param_name}: {type_hint}")
            else:
                param_strs.append(param_name)
        
        params = ", ".join(param_strs)
        
        # Add return type if present
        if func_info.return_type:
            signature = f"def {func_info.name}({params}) -> {func_info.return_type}:"
        else:
            signature = f"def {func_info.name}({params}):"
        
        return signature
