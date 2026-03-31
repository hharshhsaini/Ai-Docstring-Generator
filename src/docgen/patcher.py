"""CST-based docstring patcher for injecting docstrings into Python source files."""

from pathlib import Path
from typing import Optional

import libcst as cst

from .interfaces import LanguagePatcher


class DocstringPatcher(LanguagePatcher):
    """Patches docstrings into Python source files using libcst.
    
    Implements the LanguagePatcher interface for Python language support.
    """

    def __init__(self, overwrite_existing: bool = False):
        """
        Initialize patcher with overwrite policy.

        Args:
            overwrite_existing: If True, replace existing docstrings. If False, skip functions with docstrings.
        """
        super().__init__(overwrite_existing)

    def inject_docstring(
        self,
        file_path: Path,
        func_name: str,
        docstring: str,
        parent_class: Optional[str] = None,
    ) -> str:
        """
        Inject docstring into function in file.

        Args:
            file_path: Path to source file
            func_name: Name of function to patch
            docstring: Docstring text to inject
            parent_class: Class name if function is a method

        Returns:
            Modified source code
        """
        # Read source file
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Parse with libcst
        tree = cst.parse_module(source_code)

        # Create transformer
        transformer = DocstringInjector(
            func_name=func_name,
            docstring=docstring,
            parent_class=parent_class,
            overwrite=self.overwrite_existing,
        )

        # Transform tree
        modified_tree = tree.visit(transformer)

        # Return modified source code
        return modified_tree.code

    def write_file(self, file_path: Path, source_code: str) -> None:
        """
        Write modified source code back to file.

        Args:
            file_path: Path to file to write
            source_code: Modified source code
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(source_code)


class DocstringInjector(cst.CSTTransformer):
    """CST transformer that injects docstrings into functions."""

    def __init__(
        self,
        func_name: str,
        docstring: str,
        parent_class: Optional[str],
        overwrite: bool,
    ):
        """
        Initialize transformer.

        Args:
            func_name: Name of function to patch
            docstring: Docstring text to inject
            parent_class: Class name if function is a method
            overwrite: If True, replace existing docstrings
        """
        self.func_name = func_name
        self.docstring = docstring
        self.parent_class = parent_class
        self.overwrite = overwrite
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Track current class context."""
        self.current_class = node.name.value

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Reset class context when leaving class."""
        self.current_class = None
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Inject or replace docstring in matching function."""
        # Check if this is the target function
        if updated_node.name.value != self.func_name:
            return updated_node

        # Check if we're in the right class context
        if self.parent_class and self.current_class != self.parent_class:
            return updated_node

        # Check if function already has docstring
        has_docstring = self._has_docstring(updated_node.body)
        if has_docstring and not self.overwrite:
            return updated_node

        # Create docstring node
        docstring_node = self._create_docstring_node(self.docstring)

        # Inject or replace docstring
        if has_docstring:
            # Replace existing docstring (first statement)
            new_body = updated_node.body.with_changes(
                body=[docstring_node] + list(updated_node.body.body[1:])
            )
        else:
            # Insert new docstring as first statement
            new_body = updated_node.body.with_changes(
                body=[docstring_node] + list(updated_node.body.body)
            )

        return updated_node.with_changes(body=new_body)

    def _has_docstring(self, body: cst.IndentedBlock) -> bool:
        """
        Check if function body has a docstring.

        Args:
            body: Function body

        Returns:
            True if first statement is a string literal
        """
        if not body.body:
            return False

        first_stmt = body.body[0]

        # Check if first statement is a simple statement line with an expression
        if isinstance(first_stmt, cst.SimpleStatementLine):
            if first_stmt.body and isinstance(first_stmt.body[0], cst.Expr):
                expr = first_stmt.body[0]
                # Check if expression is a string (docstring)
                if isinstance(
                    expr.value,
                    (
                        cst.SimpleString,
                        cst.ConcatenatedString,
                        cst.FormattedString,
                    ),
                ):
                    return True

        return False

    def _create_docstring_node(self, docstring: str) -> cst.SimpleStatementLine:
        """
        Create a CST node for a docstring.

        Args:
            docstring: Docstring text

        Returns:
            SimpleStatementLine containing the docstring
        """
        # Clean docstring - remove triple quotes if present
        cleaned = docstring.strip()
        if cleaned.startswith('"""') and cleaned.endswith('"""'):
            cleaned = cleaned[3:-3]
        elif cleaned.startswith("'''") and cleaned.endswith("'''"):
            cleaned = cleaned[3:-3]

        # Create triple-quoted string
        docstring_str = f'"""{cleaned}"""'

        # Create expression statement
        return cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=docstring_str))]
        )
