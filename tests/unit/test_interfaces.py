"""Unit tests for language-agnostic interfaces.

This module tests the abstract base classes that enable multi-language support,
including LanguageParser and LanguagePatcher interfaces, as well as file extension
configuration in FileWalker.

Validates Requirements: 14.1, 14.2, 14.3, 14.4
"""

import tempfile
from pathlib import Path
from typing import Optional

import pytest

from src.docgen.interfaces import LanguageParser, LanguagePatcher
from src.docgen.parser import PythonParser
from src.docgen.patcher import DocstringPatcher
from src.docgen.walker import FileWalker
from src.docgen.models import FunctionInfo, ClassInfo


class TestLanguageParserInterface:
    """Test suite for LanguageParser abstract interface.
    
    Validates Requirement 14.1: Parser uses interface for other languages.
    """
    
    def test_python_parser_implements_interface(self):
        """Test that PythonParser correctly implements LanguageParser interface."""
        parser = PythonParser()
        
        # Verify it's an instance of the interface
        assert isinstance(parser, LanguageParser)
        
        # Verify it has the required method
        assert hasattr(parser, 'parse_file')
        assert callable(parser.parse_file)
    
    def test_parser_interface_has_abstract_method(self):
        """Test that LanguageParser defines parse_file as abstract method."""
        # Attempting to instantiate abstract class should fail
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LanguageParser()
    
    def test_parser_interface_enforces_implementation(self):
        """Test that subclasses must implement parse_file method."""
        # Create incomplete implementation
        class IncompleteParser(LanguageParser):
            pass
        
        # Should fail to instantiate without implementing abstract method
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteParser()
    
    def test_parser_interface_signature(self):
        """Test that parse_file has correct signature."""
        code = """
def test_func():
    pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            result = parser.parse_file(temp_path)
            
            # Verify return type is tuple of (list[FunctionInfo], list[ClassInfo])
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], list)
            assert isinstance(result[1], list)
            
            # Verify list contents are correct types
            if result[0]:
                assert all(isinstance(f, FunctionInfo) for f in result[0])
            if result[1]:
                assert all(isinstance(c, ClassInfo) for c in result[1])
        finally:
            temp_path.unlink()
    
    def test_custom_parser_implementation(self):
        """Test that custom parser can implement the interface."""
        # Create a minimal custom parser implementation
        class MockParser(LanguageParser):
            def parse_file(self, file_path: Path) -> tuple[list[FunctionInfo], list[ClassInfo]]:
                # Return empty lists for testing
                return [], []
        
        # Should be able to instantiate
        parser = MockParser()
        assert isinstance(parser, LanguageParser)
        
        # Should be able to call parse_file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        try:
            functions, classes = parser.parse_file(temp_path)
            assert functions == []
            assert classes == []
        finally:
            temp_path.unlink()


class TestLanguagePatcherInterface:
    """Test suite for LanguagePatcher abstract interface.
    
    Validates Requirement 14.4: Patcher uses interface for other languages.
    """
    
    def test_docstring_patcher_implements_interface(self):
        """Test that DocstringPatcher correctly implements LanguagePatcher interface."""
        patcher = DocstringPatcher()
        
        # Verify it's an instance of the interface
        assert isinstance(patcher, LanguagePatcher)
        
        # Verify it has the required methods
        assert hasattr(patcher, 'inject_docstring')
        assert callable(patcher.inject_docstring)
        assert hasattr(patcher, 'write_file')
        assert callable(patcher.write_file)
    
    def test_patcher_interface_has_abstract_methods(self):
        """Test that LanguagePatcher defines abstract methods."""
        # Attempting to instantiate abstract class should fail
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LanguagePatcher()
    
    def test_patcher_interface_enforces_implementation(self):
        """Test that subclasses must implement required methods."""
        # Create incomplete implementation (missing write_file)
        class IncompletePatcher(LanguagePatcher):
            def inject_docstring(
                self,
                file_path: Path,
                func_name: str,
                docstring: str,
                parent_class: Optional[str] = None,
            ) -> str:
                return ""
        
        # Should fail to instantiate without implementing all abstract methods
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompletePatcher()
    
    def test_patcher_interface_init_signature(self):
        """Test that patcher __init__ accepts overwrite_existing parameter."""
        patcher_default = DocstringPatcher()
        assert patcher_default.overwrite_existing is False
        
        patcher_overwrite = DocstringPatcher(overwrite_existing=True)
        assert patcher_overwrite.overwrite_existing is True
    
    def test_patcher_interface_inject_signature(self):
        """Test that inject_docstring has correct signature and return type."""
        code = """
def test_func():
    pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            patcher = DocstringPatcher()
            result = patcher.inject_docstring(
                file_path=temp_path,
                func_name="test_func",
                docstring="Test docstring",
                parent_class=None
            )
            
            # Verify return type is string (modified source code)
            assert isinstance(result, str)
            assert "Test docstring" in result
        finally:
            temp_path.unlink()
    
    def test_patcher_interface_write_signature(self):
        """Test that write_file has correct signature."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# test")
            temp_path = Path(f.name)
        
        try:
            patcher = DocstringPatcher()
            modified_code = "# modified test"
            
            # Should not raise exception
            patcher.write_file(temp_path, modified_code)
            
            # Verify file was written
            with open(temp_path, 'r') as f:
                content = f.read()
            assert content == modified_code
        finally:
            temp_path.unlink()
    
    def test_custom_patcher_implementation(self):
        """Test that custom patcher can implement the interface."""
        # Create a minimal custom patcher implementation
        class MockPatcher(LanguagePatcher):
            def inject_docstring(
                self,
                file_path: Path,
                func_name: str,
                docstring: str,
                parent_class: Optional[str] = None,
            ) -> str:
                return f"// {docstring}"
            
            def write_file(self, file_path: Path, source_code: str) -> None:
                with open(file_path, 'w') as f:
                    f.write(source_code)
        
        # Should be able to instantiate
        patcher = MockPatcher()
        assert isinstance(patcher, LanguagePatcher)
        
        # Should be able to call methods
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)
        
        try:
            result = patcher.inject_docstring(temp_path, "func", "doc")
            assert result == "// doc"
            
            patcher.write_file(temp_path, "modified")
            with open(temp_path, 'r') as f:
                assert f.read() == "modified"
        finally:
            temp_path.unlink()


class TestFileExtensionConfiguration:
    """Test suite for configurable file extensions in FileWalker.
    
    Validates Requirement 14.2: Walker supports configurable file extensions.
    """
    
    def test_walker_default_python_extension(self):
        """Test that FileWalker defaults to .py extension."""
        walker = FileWalker()
        
        assert walker.file_extensions == ['.py']
    
    def test_walker_custom_single_extension(self):
        """Test that FileWalker accepts custom single extension."""
        walker = FileWalker(file_extensions=['.js'])
        
        assert walker.file_extensions == ['.js']
    
    def test_walker_custom_multiple_extensions(self):
        """Test that FileWalker accepts multiple custom extensions."""
        walker = FileWalker(file_extensions=['.py', '.js', '.ts'])
        
        assert walker.file_extensions == ['.py', '.js', '.ts']
    
    def test_walker_discovers_custom_extension_files(self):
        """Test that FileWalker discovers files with custom extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create files with different extensions
            py_file = tmppath / 'test.py'
            py_file.write_text('def foo(): pass')
            
            js_file = tmppath / 'test.js'
            js_file.write_text('function foo() {}')
            
            txt_file = tmppath / 'test.txt'
            txt_file.write_text('plain text')
            
            # Test with .js extension
            walker = FileWalker(file_extensions=['.js'])
            files = walker.discover_files(tmppath)
            
            assert len(files) == 1
            assert files[0].name == 'test.js'
    
    def test_walker_discovers_multiple_extension_files(self):
        """Test that FileWalker discovers files with multiple configured extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create files with different extensions
            py_file = tmppath / 'test.py'
            py_file.write_text('def foo(): pass')
            
            js_file = tmppath / 'test.js'
            js_file.write_text('function foo() {}')
            
            ts_file = tmppath / 'test.ts'
            ts_file.write_text('function foo(): void {}')
            
            txt_file = tmppath / 'test.txt'
            txt_file.write_text('plain text')
            
            # Test with multiple extensions
            walker = FileWalker(file_extensions=['.py', '.js', '.ts'])
            files = walker.discover_files(tmppath)
            
            assert len(files) == 3
            file_names = {f.name for f in files}
            assert file_names == {'test.py', 'test.js', 'test.ts'}
    
    def test_walker_single_file_with_matching_extension(self):
        """Test that FileWalker handles single file with matching extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write('function foo() {}')
            temp_path = Path(f.name)
        
        try:
            walker = FileWalker(file_extensions=['.js'])
            files = walker.discover_files(temp_path)
            
            assert len(files) == 1
            assert files[0] == temp_path.absolute()
        finally:
            temp_path.unlink()
    
    def test_walker_single_file_with_non_matching_extension(self):
        """Test that FileWalker skips single file with non-matching extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('plain text')
            temp_path = Path(f.name)
        
        try:
            walker = FileWalker(file_extensions=['.py'])
            files = walker.discover_files(temp_path)
            
            assert len(files) == 0
        finally:
            temp_path.unlink()
    
    def test_walker_nested_directories_with_custom_extensions(self):
        """Test that FileWalker discovers files recursively with custom extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create nested structure
            subdir = tmppath / 'subdir'
            subdir.mkdir()
            
            # Create files at different levels
            (tmppath / 'root.js').write_text('function root() {}')
            (subdir / 'nested.js').write_text('function nested() {}')
            (tmppath / 'root.py').write_text('def root(): pass')
            
            # Test with .js extension only
            walker = FileWalker(file_extensions=['.js'])
            files = walker.discover_files(tmppath)
            
            assert len(files) == 2
            file_names = {f.name for f in files}
            assert file_names == {'root.js', 'nested.js'}
    
    def test_walker_extension_with_exclusion_patterns(self):
        """Test that FileWalker respects exclusion patterns with custom extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create files
            (tmppath / 'include.js').write_text('function include() {}')
            (tmppath / 'test_exclude.js').write_text('function exclude() {}')
            
            # Test with exclusion pattern
            walker = FileWalker(
                file_extensions=['.js'],
                exclude_patterns=['**/test_*.js']
            )
            files = walker.discover_files(tmppath)
            
            assert len(files) == 1
            assert files[0].name == 'include.js'


class TestInterfaceIntegration:
    """Test suite for integration between interfaces and implementations.
    
    Validates Requirements 14.1, 14.3, 14.4: Integration of language-agnostic architecture.
    """
    
    def test_parser_and_patcher_work_together(self):
        """Test that parser and patcher interfaces work together in pipeline."""
        code = """
def test_func(x: int) -> int:
    return x * 2
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            # Parse using interface
            parser: LanguageParser = PythonParser()
            functions, _ = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            assert func.name == "test_func"
            assert not func.has_docstring
            
            # Patch using interface
            patcher: LanguagePatcher = DocstringPatcher()
            modified_code = patcher.inject_docstring(
                temp_path,
                func.name,
                "Doubles the input value."
            )
            
            # Write back
            patcher.write_file(temp_path, modified_code)
            
            # Re-parse to verify
            functions_after, _ = parser.parse_file(temp_path)
            assert len(functions_after) == 1
            assert functions_after[0].has_docstring
            assert "Doubles the input value" in functions_after[0].existing_docstring
        finally:
            temp_path.unlink()
    
    def test_walker_parser_patcher_pipeline(self):
        """Test complete pipeline with walker, parser, and patcher interfaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create test file
            test_file = tmppath / 'module.py'
            test_file.write_text("""
def func1():
    pass

def func2():
    pass
""")
            
            # Discover files
            walker = FileWalker(file_extensions=['.py'])
            files = walker.discover_files(tmppath)
            assert len(files) == 1
            
            # Parse files
            parser: LanguageParser = PythonParser()
            functions, _ = parser.parse_file(files[0])
            assert len(functions) == 2
            
            # Patch files
            patcher: LanguagePatcher = DocstringPatcher()
            for func in functions:
                modified_code = patcher.inject_docstring(
                    files[0],
                    func.name,
                    f"Docstring for {func.name}"
                )
                patcher.write_file(files[0], modified_code)
            
            # Verify all functions now have docstrings
            functions_after, _ = parser.parse_file(files[0])
            assert all(f.has_docstring for f in functions_after)
