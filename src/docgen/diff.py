"""Diff generation for dry-run mode."""

import difflib
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from docgen.models import FunctionInfo
from docgen.patcher import DocstringPatcher

console = Console()


def generate_diff(file_path: Path, func_info: FunctionInfo, docstring: str) -> str:
    """
    Generate unified diff showing proposed changes.

    Args:
        file_path: Path to source file
        func_info: Function metadata
        docstring: Docstring text to inject

    Returns:
        Unified diff string
    """
    # Read original file
    with open(file_path) as f:
        original_lines = f.readlines()

    # Create modified version
    patcher = DocstringPatcher(overwrite_existing=True)
    modified_source = patcher.inject_docstring(
        file_path, func_info.name, docstring, func_info.parent_class
    )
    modified_lines = modified_source.splitlines(keepends=True)

    # Generate unified diff
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "".join(diff)


def display_diff(diff_text: str) -> None:
    """
    Display diff with syntax highlighting using rich.

    Args:
        diff_text: Unified diff text to display
    """
    if not diff_text:
        return

    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)
