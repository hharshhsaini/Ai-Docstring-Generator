"""Test that the project setup is correct."""
import sys
from pathlib import Path


def test_python_version():
    """Test that Python version is 3.11 or higher."""
    assert sys.version_info >= (3, 11), "Python 3.11 or higher is required"


def test_project_structure():
    """Test that the project structure is set up correctly."""
    project_root = Path(__file__).parent.parent
    
    # Check main directories exist
    assert (project_root / "src" / "docgen").is_dir()
    assert (project_root / "tests" / "unit").is_dir()
    assert (project_root / "tests" / "property").is_dir()
    assert (project_root / "tests" / "integration").is_dir()
    assert (project_root / "tests" / "fixtures").is_dir()
    
    # Check configuration files exist
    assert (project_root / "pyproject.toml").is_file()
    assert (project_root / "pytest.ini").is_file()
    assert (project_root / "README.md").is_file()


def test_imports():
    """Test that basic imports work."""
    try:
        import docgen
        assert hasattr(docgen, "__version__")
        assert docgen.__version__ == "0.1.0"
    except ImportError as e:
        assert False, f"Failed to import docgen: {e}"
