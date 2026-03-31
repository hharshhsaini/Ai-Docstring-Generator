"""Unit tests for FileWalker component."""

import tempfile
from pathlib import Path

import pytest

from docgen.walker import FileWalker


class TestFileWalker:
    """Unit tests for FileWalker class."""
    
    def test_single_file_path_handling(self):
        """Test that Walker processes single file when file path is provided."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def foo(): pass')
            temp_path = Path(f.name)
        
        try:
            walker = FileWalker()
            files = walker.discover_files(temp_path)
            
            assert len(files) == 1
            assert files[0] == temp_path.absolute()
        finally:
            temp_path.unlink()
    
    def test_single_non_python_file(self):
        """Test that non-Python files are not discovered."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('not python')
            temp_path = Path(f.name)
        
        try:
            walker = FileWalker()
            files = walker.discover_files(temp_path)
            
            assert len(files) == 0
        finally:
            temp_path.unlink()
    
    def test_empty_directory_handling(self):
        """Test that empty directories return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            assert len(files) == 0
    
    def test_nested_directory_structures(self):
        """Test discovery in nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create nested structure
            (tmppath / 'level1').mkdir()
            (tmppath / 'level1' / 'level2').mkdir()
            
            # Create Python files at different levels
            (tmppath / 'root.py').write_text('def root(): pass')
            (tmppath / 'level1' / 'level1.py').write_text('def level1(): pass')
            (tmppath / 'level1' / 'level2' / 'level2.py').write_text('def level2(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            assert len(files) == 3
            # Verify all files are absolute paths
            assert all(f.is_absolute() for f in files)
            # Verify all discovered files exist
            assert all(f.exists() for f in files)
    
    def test_hidden_directories_skipped(self):
        """Test that hidden directories (starting with .) are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create hidden directory
            (tmppath / '.hidden').mkdir()
            (tmppath / '.hidden' / 'hidden.py').write_text('def hidden(): pass')
            
            # Create normal directory
            (tmppath / 'normal').mkdir()
            (tmppath / 'normal' / 'normal.py').write_text('def normal(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            # Should only find the normal file
            assert len(files) == 1
            assert files[0].name == 'normal.py'
    
    def test_gitignore_exclusion(self):
        """Test that .gitignore patterns are respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create .gitignore
            (tmppath / '.gitignore').write_text('ignored.py\nignored_dir/')
            
            # Create files
            (tmppath / 'included.py').write_text('def included(): pass')
            (tmppath / 'ignored.py').write_text('def ignored(): pass')
            
            # Create ignored directory
            (tmppath / 'ignored_dir').mkdir()
            (tmppath / 'ignored_dir' / 'also_ignored.py').write_text('def also_ignored(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            # Should only find included.py
            assert len(files) == 1
            assert files[0].name == 'included.py'
    
    def test_custom_exclusion_patterns(self):
        """Test that custom exclusion patterns work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create files
            (tmppath / 'test_file.py').write_text('def test(): pass')
            (tmppath / 'normal_file.py').write_text('def normal(): pass')
            
            # Create subdirectory with test files
            (tmppath / 'tests').mkdir()
            (tmppath / 'tests' / 'test_something.py').write_text('def test_something(): pass')
            
            # Exclude test files
            walker = FileWalker(exclude_patterns=['**/test_*.py', '**/tests/**'])
            files = walker.discover_files(tmppath)
            
            # Should only find normal_file.py
            assert len(files) == 1
            assert files[0].name == 'normal_file.py'
    
    def test_glob_pattern_exclusion(self):
        """Test various glob patterns for exclusion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create various files
            (tmppath / 'keep.py').write_text('def keep(): pass')
            (tmppath / 'test_exclude.py').write_text('def test(): pass')
            
            # Create migrations directory
            (tmppath / 'migrations').mkdir()
            (tmppath / 'migrations' / 'migration.py').write_text('def migrate(): pass')
            
            # Exclude test files and migrations
            walker = FileWalker(exclude_patterns=['**/test_*.py', '**/migrations/**'])
            files = walker.discover_files(tmppath)
            
            # Should only find keep.py
            assert len(files) == 1
            assert files[0].name == 'keep.py'
    
    def test_absolute_paths_returned(self):
        """Test that all returned paths are absolute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            (tmppath / 'file.py').write_text('def func(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            assert len(files) == 1
            assert files[0].is_absolute()
    
    def test_nonexistent_path(self):
        """Test handling of nonexistent paths."""
        walker = FileWalker()
        files = walker.discover_files(Path('/nonexistent/path'))
        
        assert len(files) == 0
    
    def test_multiple_python_files_in_directory(self):
        """Test discovery of multiple Python files in same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create multiple Python files
            (tmppath / 'file1.py').write_text('def func1(): pass')
            (tmppath / 'file2.py').write_text('def func2(): pass')
            (tmppath / 'file3.py').write_text('def func3(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            assert len(files) == 3
            file_names = {f.name for f in files}
            assert file_names == {'file1.py', 'file2.py', 'file3.py'}
    
    def test_gitignore_with_comments(self):
        """Test that .gitignore comments are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create .gitignore with comments
            (tmppath / '.gitignore').write_text('''
# This is a comment
ignored.py
# Another comment

# Empty lines above
keep.py  # This should NOT be ignored (comment after pattern)
''')
            
            # Create files
            (tmppath / 'ignored.py').write_text('def ignored(): pass')
            (tmppath / 'keep.py').write_text('def keep(): pass')
            (tmppath / 'other.py').write_text('def other(): pass')
            
            walker = FileWalker()
            files = walker.discover_files(tmppath)
            
            # Should find other.py (keep.py is in gitignore, ignored.py is ignored)
            file_names = {f.name for f in files}
            assert 'ignored.py' not in file_names
            assert 'other.py' in file_names
    
    def test_combined_gitignore_and_custom_exclusion(self):
        """Test that both .gitignore and custom patterns work together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create .gitignore
            (tmppath / '.gitignore').write_text('git_ignored.py')
            
            # Create files
            (tmppath / 'keep.py').write_text('def keep(): pass')
            (tmppath / 'git_ignored.py').write_text('def git_ignored(): pass')
            (tmppath / 'custom_ignored.py').write_text('def custom_ignored(): pass')
            
            # Use custom exclusion
            walker = FileWalker(exclude_patterns=['**/custom_*.py'])
            files = walker.discover_files(tmppath)
            
            # Should only find keep.py
            assert len(files) == 1
            assert files[0].name == 'keep.py'
