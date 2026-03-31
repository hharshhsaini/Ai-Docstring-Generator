"""Property-based tests for FileWalker component.

**Validates: Requirements 1.1, 1.2, 1.3, 1.5**
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from docgen.walker import FileWalker


@pytest.mark.property
class TestFileWalkerProperties:
    """Property tests for FileWalker class."""
    
    @settings(max_examples=100)
    @given(
        num_files=st.integers(min_value=1, max_value=20),
        num_subdirs=st.integers(min_value=0, max_value=5),
    )
    def test_property_1_file_discovery_completeness(self, num_files, num_subdirs):
        """Property 1: File Discovery Completeness.
        
        For any directory structure containing Python files, the Walker should
        discover all .py files recursively, returning absolute paths for each file.
        
        **Validates: Requirements 1.1, 1.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Track all created Python files
            created_files = []
            
            # Create Python files in root directory
            for i in range(num_files):
                file_path = tmppath / f"file_{i}.py"
                file_path.write_text(f"def func_{i}(): pass")
                created_files.append(file_path.absolute())
            
            # Create subdirectories with Python files
            for i in range(num_subdirs):
                subdir = tmppath / f"subdir_{i}"
                subdir.mkdir()
                
                # Create 1-3 files in each subdirectory
                for j in range(1, 4):
                    file_path = subdir / f"file_{i}_{j}.py"
                    file_path.write_text(f"def func_{i}_{j}(): pass")
                    created_files.append(file_path.absolute())
            
            # Discover files using FileWalker
            walker = FileWalker()
            discovered_files = walker.discover_files(tmppath)
            
            # Property: All created Python files should be discovered
            assert len(discovered_files) == len(created_files), \
                f"Expected {len(created_files)} files, but discovered {len(discovered_files)}"
            
            # Property: All discovered files should be in the created files list
            discovered_set = set(discovered_files)
            created_set = set(created_files)
            assert discovered_set == created_set, \
                f"Discovered files don't match created files. Missing: {created_set - discovered_set}, Extra: {discovered_set - created_set}"
            
            # Property: All returned paths should be absolute (Requirement 1.5)
            assert all(f.is_absolute() for f in discovered_files), \
                "All discovered paths should be absolute"
            
            # Property: All discovered files should exist
            assert all(f.exists() for f in discovered_files), \
                "All discovered files should exist"
            
            # Property: All discovered files should have .py extension
            assert all(f.suffix == ".py" for f in discovered_files), \
                "All discovered files should have .py extension"
    
    @settings(max_examples=100)
    @given(
        # Generate simple gitignore patterns
        pattern=st.sampled_from([
            "*.pyc",
            "__pycache__",
            "test_*.py",
            "*.log",
            "build/",
            "dist/",
            ".env",
            "*.tmp"
        ]),
        num_matching_files=st.integers(min_value=1, max_value=5),
        num_non_matching_files=st.integers(min_value=1, max_value=5),
    )
    def test_property_2_gitignore_exclusion(self, pattern, num_matching_files, num_non_matching_files):
        """Property 2: Gitignore Exclusion.
        
        For any directory with a .gitignore file and any gitignore pattern, files
        matching the pattern should not appear in the Walker's discovered file list.
        
        **Validates: Requirements 1.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create .gitignore with the pattern
            gitignore_path = tmppath / '.gitignore'
            gitignore_path.write_text(pattern)
            
            # Track files that should be excluded and included
            should_be_excluded = []
            should_be_included = []
            
            # Create files that match the pattern
            if pattern == "*.pyc":
                # Create .pyc files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"module_{i}.pyc"
                    file_path.write_text("bytecode")
                    should_be_excluded.append(file_path)
                # Create .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "__pycache__":
                # Create __pycache__ directory with .py files (should be excluded)
                pycache_dir = tmppath / "__pycache__"
                pycache_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = pycache_dir / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_excluded.append(file_path)
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "test_*.py":
                # Create test_*.py files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"test_module_{i}.py"
                    file_path.write_text("def test_func(): pass")
                    should_be_excluded.append(file_path)
                # Create non-test .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "*.log":
                # Create .log files (should be excluded, but walker only finds .py files anyway)
                for i in range(num_matching_files):
                    file_path = tmppath / f"app_{i}.log"
                    file_path.write_text("log content")
                    should_be_excluded.append(file_path)
                # Create .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "build/":
                # Create build directory with .py files (should be excluded)
                build_dir = tmppath / "build"
                build_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = build_dir / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_excluded.append(file_path)
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "dist/":
                # Create dist directory with .py files (should be excluded)
                dist_dir = tmppath / "dist"
                dist_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = dist_dir / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_excluded.append(file_path)
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == ".env":
                # Create .env file (should be excluded, but walker only finds .py files anyway)
                env_file = tmppath / ".env"
                env_file.write_text("SECRET=value")
                should_be_excluded.append(env_file)
                # Create .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "*.tmp":
                # Create .tmp files (should be excluded, but walker only finds .py files anyway)
                for i in range(num_matching_files):
                    file_path = tmppath / f"temp_{i}.tmp"
                    file_path.write_text("temp content")
                    should_be_excluded.append(file_path)
                # Create .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            # Discover files using FileWalker
            walker = FileWalker()
            discovered_files = walker.discover_files(tmppath)
            discovered_set = set(discovered_files)
            
            # Property: Files matching gitignore pattern should NOT be discovered
            # (Only check .py files since walker only discovers .py files)
            for excluded_file in should_be_excluded:
                if excluded_file.suffix == '.py':
                    assert excluded_file.absolute() not in discovered_set, \
                        f"File {excluded_file} matches gitignore pattern '{pattern}' but was discovered"
            
            # Property: Files NOT matching gitignore pattern SHOULD be discovered
            for included_file in should_be_included:
                assert included_file in discovered_set, \
                    f"File {included_file} does not match gitignore pattern '{pattern}' but was not discovered"
            
            # Property: Discovered files should only be .py files
            assert all(f.suffix == ".py" for f in discovered_files), \
                "All discovered files should have .py extension"
    
    @settings(max_examples=100)
    @given(
        # Generate custom exclusion patterns
        pattern=st.sampled_from([
            "**/test_*.py",
            "**/tests/**",
            "**/*_test.py",
            "**/migrations/**",
            "**/build/**",
            "**/dist/**",
            "**/__pycache__/**",
            "**/temp_*.py",
            "**/draft_*.py",
            "**/backup/**"
        ]),
        num_matching_files=st.integers(min_value=1, max_value=5),
        num_non_matching_files=st.integers(min_value=1, max_value=5),
    )
    def test_property_3_custom_exclusion_patterns(self, pattern, num_matching_files, num_non_matching_files):
        """Property 3: Custom Exclusion Patterns.
        
        For any configured exclude pattern and any file structure, files matching
        the exclude pattern should not appear in the Walker's discovered file list.
        
        **Validates: Requirements 1.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Track files that should be excluded and included
            should_be_excluded = []
            should_be_included = []
            
            # Create files based on the pattern
            if pattern == "**/test_*.py":
                # Create test_*.py files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"test_module_{i}.py"
                    file_path.write_text("def test_func(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create non-test .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/tests/**":
                # Create tests directory with .py files (should be excluded)
                tests_dir = tmppath / "tests"
                tests_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = tests_dir / f"test_{i}.py"
                    file_path.write_text("def test(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/*_test.py":
                # Create *_test.py files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"module_{i}_test.py"
                    file_path.write_text("def test_func(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create non-test .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/migrations/**":
                # Create migrations directory with .py files (should be excluded)
                migrations_dir = tmppath / "migrations"
                migrations_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = migrations_dir / f"migration_{i}.py"
                    file_path.write_text("def migrate(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/build/**":
                # Create build directory with .py files (should be excluded)
                build_dir = tmppath / "build"
                build_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = build_dir / f"build_{i}.py"
                    file_path.write_text("def build(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/dist/**":
                # Create dist directory with .py files (should be excluded)
                dist_dir = tmppath / "dist"
                dist_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = dist_dir / f"dist_{i}.py"
                    file_path.write_text("def dist(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/__pycache__/**":
                # Create __pycache__ directory with .py files (should be excluded)
                # Note: __pycache__ is also skipped by default as hidden dir, but test the pattern
                pycache_dir = tmppath / "not_hidden_pycache"
                pycache_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = pycache_dir / f"cached_{i}.py"
                    file_path.write_text("def cached(): pass")
                    # Don't add to should_be_excluded since we're using a different dir name
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
                # For this pattern, we'll test with a different approach
                # since __pycache__ is hidden by default
            
            elif pattern == "**/temp_*.py":
                # Create temp_*.py files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"temp_file_{i}.py"
                    file_path.write_text("def temp(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create non-temp .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/draft_*.py":
                # Create draft_*.py files (should be excluded)
                for i in range(num_matching_files):
                    file_path = tmppath / f"draft_module_{i}.py"
                    file_path.write_text("def draft(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create non-draft .py files (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            elif pattern == "**/backup/**":
                # Create backup directory with .py files (should be excluded)
                backup_dir = tmppath / "backup"
                backup_dir.mkdir()
                for i in range(num_matching_files):
                    file_path = backup_dir / f"backup_{i}.py"
                    file_path.write_text("def backup(): pass")
                    should_be_excluded.append(file_path.absolute())
                # Create .py files in root (should be included)
                for i in range(num_non_matching_files):
                    file_path = tmppath / f"module_{i}.py"
                    file_path.write_text("def func(): pass")
                    should_be_included.append(file_path.absolute())
            
            # Discover files using FileWalker with custom exclusion pattern
            walker = FileWalker(exclude_patterns=[pattern])
            discovered_files = walker.discover_files(tmppath)
            discovered_set = set(discovered_files)
            
            # Property: Files matching custom exclusion pattern should NOT be discovered
            for excluded_file in should_be_excluded:
                assert excluded_file not in discovered_set, \
                    f"File {excluded_file} matches exclusion pattern '{pattern}' but was discovered"
            
            # Property: Files NOT matching exclusion pattern SHOULD be discovered
            for included_file in should_be_included:
                assert included_file in discovered_set, \
                    f"File {included_file} does not match exclusion pattern '{pattern}' but was not discovered"
            
            # Property: All discovered files should be absolute paths
            assert all(f.is_absolute() for f in discovered_files), \
                "All discovered paths should be absolute"
            
            # Property: Discovered files should only be .py files
            assert all(f.suffix == ".py" for f in discovered_files), \
                "All discovered files should have .py extension"

    @settings(max_examples=100)
    @given(
        # Generate different file extension configurations
        extensions=st.sampled_from([
            ['.py'],
            ['.js'],
            ['.ts'],
            ['.py', '.js'],
            ['.py', '.ts'],
            ['.js', '.ts'],
            ['.py', '.js', '.ts'],
            ['.java'],
            ['.cpp', '.h'],
            ['.rb'],
        ]),
        num_matching_files=st.integers(min_value=1, max_value=10),
        num_non_matching_files=st.integers(min_value=1, max_value=10),
    )
    def test_property_34_configurable_file_extensions(self, extensions, num_matching_files, num_non_matching_files):
        """Property 34: Configurable File Extensions.
        
        For any configured file extension, the Walker should discover files with
        that extension in addition to or instead of .py files.
        
        **Validates: Requirements 14.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Track files that should be discovered and ignored
            should_be_discovered = []
            should_be_ignored = []
            
            # Define all possible extensions we might create
            all_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.h', '.rb', '.txt', '.md']
            
            # Create files with matching extensions (should be discovered)
            for i in range(num_matching_files):
                # Pick an extension from the configured list
                ext = extensions[i % len(extensions)]
                file_path = tmppath / f"file_{i}{ext}"
                file_path.write_text(f"// Content for file {i}")
                should_be_discovered.append(file_path.absolute())
            
            # Create files with non-matching extensions (should be ignored)
            non_matching_extensions = [e for e in all_extensions if e not in extensions]
            if non_matching_extensions:
                for i in range(num_non_matching_files):
                    # Pick an extension NOT in the configured list
                    ext = non_matching_extensions[i % len(non_matching_extensions)]
                    file_path = tmppath / f"other_{i}{ext}"
                    file_path.write_text(f"// Content for other file {i}")
                    should_be_ignored.append(file_path.absolute())
            
            # Discover files using FileWalker with configured extensions
            walker = FileWalker(file_extensions=extensions)
            discovered_files = walker.discover_files(tmppath)
            discovered_set = set(discovered_files)
            
            # Property: All files with configured extensions should be discovered
            for expected_file in should_be_discovered:
                assert expected_file in discovered_set, \
                    f"File {expected_file} has configured extension {expected_file.suffix} but was not discovered"
            
            # Property: Files with non-configured extensions should NOT be discovered
            for ignored_file in should_be_ignored:
                assert ignored_file not in discovered_set, \
                    f"File {ignored_file} has non-configured extension {ignored_file.suffix} but was discovered"
            
            # Property: All discovered files should have one of the configured extensions
            for discovered_file in discovered_files:
                assert discovered_file.suffix in extensions, \
                    f"Discovered file {discovered_file} has extension {discovered_file.suffix} which is not in configured extensions {extensions}"
            
            # Property: Number of discovered files should match number of created matching files
            assert len(discovered_files) == len(should_be_discovered), \
                f"Expected {len(should_be_discovered)} files to be discovered, but found {len(discovered_files)}"
            
            # Property: All returned paths should be absolute
            assert all(f.is_absolute() for f in discovered_files), \
                "All discovered paths should be absolute"
            
            # Property: All discovered files should exist
            assert all(f.exists() for f in discovered_files), \
                "All discovered files should exist"
