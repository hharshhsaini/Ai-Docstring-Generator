"""AST parser component for extracting function and class metadata.

This module provides the PythonParser class which uses libcst to extract
function and class metadata from Python source files while preserving
formatting information.
"""

from pathlib import Path
from typing import Optional

import libcst as cst

from .interfaces import LanguageParser
from .models import FunctionInfo, ClassInfo


class FunctionExtractor(cst.CSTVisitor):
    """CST visitor that extracts function and class metadata.
    
    This visitor traverses the CST and collects information about all functions
    and classes, including their parameters, type hints, docstrings, and body previews.
    
    Attributes:
        functions: List of extracted function metadata
        classes: List of extracted class metadata
        current_class: Name of the class currently being visited (None for module-level)
    """
    
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)
    
    def __init__(self) -> None:
        """Initialize the function extractor."""
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.current_class: Optional[str] = None
        self._current_class_methods: list[FunctionInfo] = []
        self._current_class_has_docstring: bool = False
        self._current_class_docstring: Optional[str] = None
        self._current_class_line: int = 0
    
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit a class definition and track class context.
        
        Args:
            node: The class definition node
        """
        self.current_class = node.name.value
        self._current_class_methods = []
        
        # Extract class docstring
        self._current_class_has_docstring, self._current_class_docstring = self._extract_docstring(node.body)
        
        # Get line number
        self._current_class_line = self._get_line_number(node)
    
    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        """Leave a class definition and save class metadata.
        
        Args:
            original_node: The class definition node being left
        """
        # Create ClassInfo with collected methods
        class_info = ClassInfo(
            name=self.current_class or "",
            methods=self._current_class_methods.copy(),
            has_docstring=self._current_class_has_docstring,
            existing_docstring=self._current_class_docstring,
            line_number=self._current_class_line
        )
        self.classes.append(class_info)
        
        # Reset class context
        self.current_class = None
        self._current_class_methods = []
        self._current_class_has_docstring = False
        self._current_class_docstring = None
        self._current_class_line = 0
    
    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit a function definition and extract metadata.
        
        Args:
            node: The function definition node
        """
        # Extract parameters with type hints
        params = self._extract_parameters(node.params)
        
        # Extract return type
        return_type = self._extract_type_annotation(node.returns)
        
        # Check for existing docstring
        has_docstring, existing_docstring = self._extract_docstring(node.body)
        
        # Get body preview (first 5 lines, excluding docstring)
        body_preview = self._get_body_preview(node.body, skip_docstring=has_docstring)
        
        # Get line number
        line_number = self._get_line_number(node)
        
        # Create FunctionInfo
        func_info = FunctionInfo(
            name=node.name.value,
            params=params,
            return_type=return_type,
            body_preview=body_preview,
            has_docstring=has_docstring,
            existing_docstring=existing_docstring,
            line_number=line_number,
            parent_class=self.current_class
        )
        
        # Add to appropriate list
        if self.current_class:
            self._current_class_methods.append(func_info)
        else:
            self.functions.append(func_info)
    
    def _extract_parameters(self, params: cst.Parameters) -> list[tuple[str, Optional[str]]]:
        """Extract parameter names and type hints from function parameters.
        
        Args:
            params: The function parameters node
            
        Returns:
            List of (parameter_name, type_hint) tuples
        """
        result: list[tuple[str, Optional[str]]] = []
        
        # Extract regular parameters
        for param in params.params:
            param_name = param.name.value
            type_hint = self._extract_type_annotation(param.annotation)
            result.append((param_name, type_hint))
        
        # Extract keyword-only parameters
        if params.kwonly_params:
            for param in params.kwonly_params:
                param_name = param.name.value
                type_hint = self._extract_type_annotation(param.annotation)
                result.append((param_name, type_hint))
        
        # Extract *args parameter
        if params.star_arg and isinstance(params.star_arg, cst.Param):
            param_name = params.star_arg.name.value
            type_hint = self._extract_type_annotation(params.star_arg.annotation)
            result.append((f"*{param_name}", type_hint))
        
        # Extract **kwargs parameter
        if params.star_kwarg:
            param_name = params.star_kwarg.name.value
            type_hint = self._extract_type_annotation(params.star_kwarg.annotation)
            result.append((f"**{param_name}", type_hint))
        
        return result
    
    def _extract_type_annotation(self, annotation: Optional[cst.Annotation]) -> Optional[str]:
        """Extract type hint from an annotation node.
        
        Args:
            annotation: The annotation node
            
        Returns:
            String representation of the type hint, or None if no annotation
        """
        if annotation is None:
            return None
        
        # Convert the annotation to code string using Module wrapper
        module = cst.Module(body=[])
        return module.code_for_node(annotation.annotation).strip()
    
    def _extract_docstring(self, body: cst.BaseSuite) -> tuple[bool, Optional[str]]:
        """Extract docstring from a function or class body.
        
        Checks if the first statement in the body is a string literal (docstring).
        
        Args:
            body: The function or class body
            
        Returns:
            Tuple of (has_docstring, docstring_text)
        """
        if not isinstance(body, cst.IndentedBlock):
            return False, None
        
        if not body.body:
            return False, None
        
        first_stmt = body.body[0]
        
        # Check if first statement is a simple statement line with an expression
        if isinstance(first_stmt, cst.SimpleStatementLine):
            if len(first_stmt.body) > 0:
                expr = first_stmt.body[0]
                if isinstance(expr, cst.Expr):
                    # Check if the expression is a string (docstring)
                    if isinstance(expr.value, (cst.SimpleString, cst.ConcatenatedString)):
                        # Extract the docstring text using Module wrapper
                        module = cst.Module(body=[])
                        docstring_code = module.code_for_node(expr.value)
                        # Remove quotes and clean up
                        docstring_text = self._clean_docstring(docstring_code)
                        return True, docstring_text
        
        return False, None
    
    def _clean_docstring(self, docstring_code: str) -> str:
        """Clean up docstring by removing quotes and normalizing whitespace.
        
        Args:
            docstring_code: Raw docstring code including quotes
            
        Returns:
            Cleaned docstring text
        """
        # Remove triple quotes or single quotes
        docstring = docstring_code.strip()
        
        # Remove leading/trailing quotes
        if docstring.startswith('"""') and docstring.endswith('"""'):
            docstring = docstring[3:-3]
        elif docstring.startswith("'''") and docstring.endswith("'''"):
            docstring = docstring[3:-3]
        elif docstring.startswith('"') and docstring.endswith('"'):
            docstring = docstring[1:-1]
        elif docstring.startswith("'") and docstring.endswith("'"):
            docstring = docstring[1:-1]
        
        # Strip leading/trailing whitespace
        return docstring.strip()
    
    def _get_body_preview(self, body: cst.BaseSuite, skip_docstring: bool = False) -> str:
        """Get a preview of the function body (first 5 lines, excluding docstring).
        
        Args:
            body: The function body
            skip_docstring: Whether to skip the first statement if it's a docstring
            
        Returns:
            String containing first 5 lines of the body
        """
        if not isinstance(body, cst.IndentedBlock):
            return ""
        
        # Get all statements
        statements = list(body.body)
        
        # Skip docstring if present
        if skip_docstring and statements:
            statements = statements[1:]
        
        # If no statements left, return empty
        if not statements:
            return ""
        
        # Take first 5 statements
        preview_statements = statements[:5]
        
        # Convert to code using Module wrapper
        lines = []
        module = cst.Module(body=[])
        for stmt in preview_statements:
            code = module.code_for_node(stmt)
            lines.append(code.rstrip())
        
        return '\n'.join(lines)
    
    def _get_line_number(self, node: cst.CSTNode) -> int:
        """Get the line number where a node is defined.
        
        Args:
            node: The CST node
            
        Returns:
            Line number (1-indexed), or 0 if not available
        """
        # Try to get position from metadata if available
        try:
            pos = self.get_metadata(cst.metadata.PositionProvider, node)
            if pos:
                return pos.start.line
        except (KeyError, AttributeError):
            pass
        
        # Fallback: count newlines in the code before this node
        # This is approximate but better than nothing
        return 0


class PythonParser(LanguageParser):
    """Parser for extracting function and class metadata from Python files.
    
    Uses libcst to parse Python source files and extract structured metadata
    about functions and classes, including type hints, docstrings, and body previews.
    
    Implements the LanguageParser interface for Python language support.
    """
    
    def parse_file(self, file_path: Path) -> tuple[list[FunctionInfo], list[ClassInfo]]:
        """Parse Python file and extract all functions and classes.
        
        Args:
            file_path: Path to the Python file to parse
            
        Returns:
            Tuple of (functions, classes) where functions is a list of FunctionInfo
            and classes is a list of ClassInfo
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SyntaxError: If the file contains invalid Python syntax
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Parse with libcst
        try:
            tree = cst.parse_module(source_code)
        except cst.ParserSyntaxError as e:
            raise SyntaxError(f"Failed to parse {file_path}: {e}") from e
        
        # Wrap with metadata to get line numbers
        try:
            wrapper = cst.metadata.MetadataWrapper(tree)
            extractor = FunctionExtractor()
            wrapper.visit(extractor)
        except Exception:
            # If metadata fails, fall back to visiting without metadata
            extractor = FunctionExtractor()
            tree.visit(extractor)
        
        return extractor.functions, extractor.classes
