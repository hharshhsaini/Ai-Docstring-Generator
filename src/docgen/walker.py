"""File discovery component for the docstring generator.

This module provides the FileWalker class which discovers Python files in a directory
tree while respecting .gitignore patterns and custom exclusion patterns.
"""

import os
from pathlib import Path
from typing import Optional

import pathspec


class FileWalker:
    """Discovers source files in a directory tree with exclusion support.
    
    The FileWalker handles both single file paths and directory trees, respecting
    .gitignore patterns and custom exclusion patterns. Hidden directories (starting
    with '.') are skipped by default.
    
    Attributes:
        exclude_patterns: List of glob patterns for file exclusion
        file_extensions: List of file extensions to discover (e.g., ['.py', '.js'])
    """
    
    def __init__(
        self, 
        exclude_patterns: Optional[list[str]] = None,
        file_extensions: Optional[list[str]] = None
    ) -> None:
        """Initialize walker with optional exclusion patterns and file extensions.
        
        Args:
            exclude_patterns: List of glob patterns to exclude (e.g., '**/test_*.py')
            file_extensions: List of file extensions to discover (defaults to ['.py'])
        """
        self.exclude_patterns = exclude_patterns or []
        self.file_extensions = file_extensions or ['.py']
        self._exclude_spec: Optional[pathspec.PathSpec] = None
        if self.exclude_patterns:
            self._exclude_spec = pathspec.PathSpec.from_lines('gitignore', self.exclude_patterns)
    
    def discover_files(self, path: Path) -> list[Path]:
        """Discover all source files in path matching configured extensions.
        
        If path is a file, returns a single-item list containing that file (if it matches
        one of the configured extensions).
        If path is a directory, recursively walks the directory tree and discovers all files
        with matching extensions, respecting .gitignore and exclusion patterns.
        
        Args:
            path: Directory or file path to scan
            
        Returns:
            List of absolute paths to source files
        """
        # Handle single file case
        if path.is_file():
            if path.suffix in self.file_extensions:
                return [path.absolute()]
            return []
        
        # Handle directory case
        if not path.is_dir():
            return []
        
        # Load .gitignore if present
        gitignore_spec = self._load_gitignore(path)
        
        source_files: list[Path] = []
        
        # Walk directory tree
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            
            # Filter directories in-place to prevent traversal of excluded paths
            dirs[:] = [
                d for d in dirs
                if not self._should_exclude_dir(d, root_path, gitignore_spec)
            ]
            
            # Process files with matching extensions
            for file in files:
                file_path = root_path / file
                if file_path.suffix in self.file_extensions:
                    if not self._should_exclude_file(file_path, path, gitignore_spec):
                        source_files.append(file_path.absolute())
        
        return source_files
    
    def _load_gitignore(self, base_path: Path) -> Optional[pathspec.PathSpec]:
        """Load and parse .gitignore file if present.
        
        Args:
            base_path: Base directory to search for .gitignore
            
        Returns:
            PathSpec object if .gitignore exists, None otherwise
        """
        gitignore_path = base_path / '.gitignore'
        if not gitignore_path.exists():
            return None
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = f.read().splitlines()
            # Filter out empty lines and comments
            patterns = [p for p in patterns if p.strip() and not p.strip().startswith('#')]
            if patterns:
                return pathspec.PathSpec.from_lines('gitignore', patterns)
        except (IOError, OSError):
            # If we can't read .gitignore, just continue without it
            pass
        
        return None
    
    def _should_exclude_dir(
        self,
        dirname: str,
        parent_path: Path,
        gitignore_spec: Optional[pathspec.PathSpec]
    ) -> bool:
        """Check if a directory should be excluded from traversal.
        
        Args:
            dirname: Directory name (not full path)
            parent_path: Parent directory path
            gitignore_spec: Parsed .gitignore patterns
            
        Returns:
            True if directory should be excluded, False otherwise
        """
        # Skip hidden directories (starting with '.')
        if dirname.startswith('.'):
            return True
        
        dir_path = parent_path / dirname
        
        # Check against custom exclusion patterns
        if self._exclude_spec:
            # Get relative path for pattern matching
            try:
                rel_path = dir_path.relative_to(Path.cwd())
                if self._exclude_spec.match_file(str(rel_path)):
                    return True
                # Also check with trailing slash for directory patterns
                if self._exclude_spec.match_file(str(rel_path) + '/'):
                    return True
            except ValueError:
                # If we can't get relative path, use absolute
                if self._exclude_spec.match_file(str(dir_path)):
                    return True
        
        # Check against .gitignore patterns
        if gitignore_spec:
            try:
                rel_path = dir_path.relative_to(Path.cwd())
                if gitignore_spec.match_file(str(rel_path)):
                    return True
                # Also check with trailing slash for directory patterns
                if gitignore_spec.match_file(str(rel_path) + '/'):
                    return True
            except ValueError:
                # If we can't get relative path, use absolute
                if gitignore_spec.match_file(str(dir_path)):
                    return True
        
        return False
    
    def _should_exclude_file(
        self,
        file_path: Path,
        base_path: Path,
        gitignore_spec: Optional[pathspec.PathSpec]
    ) -> bool:
        """Check if a file should be excluded.
        
        Args:
            file_path: Full path to the file
            base_path: Base directory for relative path calculation
            gitignore_spec: Parsed .gitignore patterns
            
        Returns:
            True if file should be excluded, False otherwise
        """
        # Check against custom exclusion patterns
        if self._exclude_spec:
            # Try relative to base_path first
            try:
                rel_path = file_path.relative_to(base_path)
                if self._exclude_spec.match_file(str(rel_path)):
                    return True
            except ValueError:
                pass
            
            # Try relative to cwd
            try:
                rel_path = file_path.relative_to(Path.cwd())
                if self._exclude_spec.match_file(str(rel_path)):
                    return True
            except ValueError:
                # Fall back to absolute path
                if self._exclude_spec.match_file(str(file_path)):
                    return True
        
        # Check against .gitignore patterns
        if gitignore_spec:
            # Try relative to base_path first
            try:
                rel_path = file_path.relative_to(base_path)
                if gitignore_spec.match_file(str(rel_path)):
                    return True
            except ValueError:
                pass
            
            # Try relative to cwd
            try:
                rel_path = file_path.relative_to(Path.cwd())
                if gitignore_spec.match_file(str(rel_path)):
                    return True
            except ValueError:
                # Fall back to absolute path
                if gitignore_spec.match_file(str(file_path)):
                    return True
        
        return False
