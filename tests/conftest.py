"""Pytest configuration and shared fixtures."""
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from hypothesis import settings


# Configure Hypothesis settings
settings.register_profile("default", max_examples=100, deadline=5000)
settings.load_profile("default")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_file(temp_dir: Path) -> Path:
    """Create a sample Python file for testing."""
    file_path = temp_dir / "sample.py"
    file_path.write_text("""
def add(a: int, b: int) -> int:
    return a + b

def subtract(x: int, y: int) -> int:
    \"\"\"Subtract y from x.\"\"\"
    return x - y

class Calculator:
    def multiply(self, a: int, b: int) -> int:
        return a * b
    
    def divide(self, a: int, b: int) -> float:
        \"\"\"Divide a by b.\"\"\"
        return a / b
""")
    return file_path
