"""Language-agnostic interfaces for multi-language support.

This module defines abstract base classes that enable the docstring generator
to support multiple programming languages beyond Python.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .models import FunctionInfo, ClassInfo


class LanguageParser(ABC):
    """Abstract base class for language-specific parsers.
    
    Implementations of this interface should extract function and class metadata
    from source files in a specific programming language.
    """
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> tuple[list[FunctionInfo], list[ClassInfo]]:
        """Parse source file and extract all functions and classes.
        
        Args:
            file_path: Path to the source file to parse
            
        Returns:
            Tuple of (functions, classes) where functions is a list of FunctionInfo
            and classes is a list of ClassInfo
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SyntaxError: If the file contains invalid syntax for the language
        """
        pass


class LanguagePatcher(ABC):
    """Abstract base class for language-specific docstring patchers.
    
    Implementations of this interface should inject docstrings into source files
    while preserving the original formatting and structure.
    """
    
    def __init__(self, overwrite_existing: bool = False):
        """Initialize patcher with overwrite policy.
        
        Args:
            overwrite_existing: If True, replace existing docstrings. 
                              If False, skip functions with docstrings.
        """
        self.overwrite_existing = overwrite_existing
    
    @abstractmethod
    def inject_docstring(
        self,
        file_path: Path,
        func_name: str,
        docstring: str,
        parent_class: Optional[str] = None,
    ) -> str:
        """Inject docstring into function in file.
        
        Args:
            file_path: Path to source file
            func_name: Name of function to patch
            docstring: Docstring text to inject
            parent_class: Class name if function is a method
            
        Returns:
            Modified source code
        """
        pass
    
    @abstractmethod
    def write_file(self, file_path: Path, source_code: str) -> None:
        """Write modified source code back to file.
        
        Args:
            file_path: Path to file to write
            source_code: Modified source code
        """
        pass
