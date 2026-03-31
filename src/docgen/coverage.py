"""Coverage calculation for docstring documentation."""

from pathlib import Path

from docgen.models import CoverageReport
from docgen.parser import PythonParser


def calculate_coverage(files: list[Path]) -> CoverageReport:
    """
    Calculate docstring coverage across all files.

    Args:
        files: List of Python file paths to analyze

    Returns:
        CoverageReport with statistics and missing docstring locations
    """
    total_functions = 0
    documented_functions = 0
    missing_docstrings: list[tuple[str, int]] = []

    parser = PythonParser()

    for file_path in files:
        try:
            functions, classes = parser.parse_file(file_path)

            # Count module-level functions
            for func in functions:
                total_functions += 1
                if func.has_docstring:
                    documented_functions += 1
                else:
                    missing_docstrings.append((str(file_path), func.line_number))

            # Count class methods
            for cls in classes:
                for method in cls.methods:
                    total_functions += 1
                    if method.has_docstring:
                        documented_functions += 1
                    else:
                        missing_docstrings.append((str(file_path), method.line_number))

        except Exception:
            # Skip files that can't be parsed
            continue

    return CoverageReport(
        total_functions=total_functions,
        documented_functions=documented_functions,
        missing_docstrings=missing_docstrings,
    )
