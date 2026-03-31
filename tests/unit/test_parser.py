"""Unit tests for the PythonParser component."""

import tempfile
from pathlib import Path

import pytest

from src.docgen.parser import PythonParser
from src.docgen.models import FunctionInfo, ClassInfo


class TestPythonParser:
    """Test suite for PythonParser class."""
    
    def test_parse_simple_function(self):
        """Test parsing a simple function without type hints."""
        code = """
def greet(name):
    return f"Hello, {name}!"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            assert len(classes) == 0
            
            func = functions[0]
            assert func.name == "greet"
            assert len(func.params) == 1
            assert func.params[0][0] == "name"
            assert func.params[0][1] is None  # No type hint
            assert func.return_type is None
            assert func.has_docstring is False
            assert func.parent_class is None
        finally:
            temp_path.unlink()
    
    def test_parse_function_with_type_hints(self):
        """Test parsing a function with type hints."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            assert func.name == "add"
            assert len(func.params) == 2
            assert func.params[0] == ("a", "int")
            assert func.params[1] == ("b", "int")
            assert func.return_type == "int"
        finally:
            temp_path.unlink()
    
    def test_parse_function_with_docstring(self):
        """Test parsing a function with an existing docstring."""
        code = '''
def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            assert func.has_docstring is True
            assert func.existing_docstring == "Greet a person by name."
        finally:
            temp_path.unlink()
    
    def test_parse_function_without_docstring(self):
        """Test parsing a function without a docstring."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            assert func.has_docstring is False
            assert func.existing_docstring is None
        finally:
            temp_path.unlink()
    
    def test_parse_class_with_methods(self):
        """Test parsing a class with methods."""
        code = '''
class Person:
    """A simple person class."""
    
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
    
    def introduce(self) -> str:
        return f"My name is {self.name}"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 0  # No module-level functions
            assert len(classes) == 1
            
            cls = classes[0]
            assert cls.name == "Person"
            assert cls.has_docstring is True
            assert cls.existing_docstring == "A simple person class."
            assert len(cls.methods) == 2
            
            # Check __init__ method
            init_method = cls.methods[0]
            assert init_method.name == "__init__"
            assert init_method.parent_class == "Person"
            assert len(init_method.params) == 3  # self, name, age
            
            # Check introduce method
            introduce_method = cls.methods[1]
            assert introduce_method.name == "introduce"
            assert introduce_method.parent_class == "Person"
            assert introduce_method.return_type == "str"
        finally:
            temp_path.unlink()
    
    def test_parse_body_preview(self):
        """Test that body preview captures first 5 lines."""
        code = """
def complex_function():
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    line7 = 7
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            # Body preview should have first 5 lines
            lines = func.body_preview.split('\n')
            assert len(lines) <= 5
            assert 'line1 = 1' in func.body_preview
            assert 'line5 = 5' in func.body_preview
        finally:
            temp_path.unlink()
    
    def test_parse_body_preview_excludes_docstring(self):
        """Test that body preview excludes docstring."""
        code = '''
def function_with_docstring():
    """This is a docstring."""
    line1 = 1
    line2 = 2
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            # Body preview should not include docstring
            assert 'This is a docstring' not in func.body_preview
            assert 'line1 = 1' in func.body_preview
        finally:
            temp_path.unlink()
    
    def test_parse_module_and_class_functions(self):
        """Test parsing both module-level functions and class methods."""
        code = '''
def module_function():
    pass

class MyClass:
    def class_method(self):
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            assert len(classes) == 1
            
            # Module-level function
            assert functions[0].name == "module_function"
            assert functions[0].parent_class is None
            
            # Class method
            assert classes[0].methods[0].name == "class_method"
            assert classes[0].methods[0].parent_class == "MyClass"
        finally:
            temp_path.unlink()
    
    def test_parse_complex_type_hints(self):
        """Test parsing functions with complex type hints."""
        code = """
from typing import List, Dict, Optional

def process_data(items: List[str], mapping: Dict[str, int]) -> Optional[int]:
    return None
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            assert len(functions) == 1
            func = functions[0]
            
            assert func.name == "process_data"
            assert len(func.params) == 2
            assert func.params[0][0] == "items"
            assert "List[str]" in func.params[0][1]
            assert func.params[1][0] == "mapping"
            assert "Dict[str, int]" in func.params[1][1]
            assert "Optional[int]" in func.return_type
        finally:
            temp_path.unlink()
    
    def test_parse_invalid_syntax(self):
        """Test that invalid Python syntax raises SyntaxError."""
        code = """
def invalid syntax here
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            with pytest.raises(SyntaxError):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_parse_sample_module(self):
        """Test parsing the sample module fixture."""
        sample_path = Path("tests/fixtures/sample_files/simple_module.py")
        
        parser = PythonParser()
        functions, classes = parser.parse_file(sample_path)
        
        # Should have 2 module-level functions
        assert len(functions) == 2
        assert functions[0].name == "greet"
        assert functions[1].name == "add_numbers"
        
        # Should have 1 class
        assert len(classes) == 1
        assert classes[0].name == "Person"
        
        # Class should have 3 methods
        assert len(classes[0].methods) == 3
        method_names = [m.name for m in classes[0].methods]
        assert "__init__" in method_names
        assert "introduce" in method_names
        assert "birthday" in method_names
    
    def test_parse_nested_functions(self):
        """Test parsing nested functions (inner functions)."""
        code = """
def outer_function(x: int) -> int:
    def inner_function(y: int) -> int:
        return y * 2
    return inner_function(x)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            # Should extract both outer and inner functions
            assert len(functions) >= 1
            
            # Outer function should be extracted
            outer_func = next((f for f in functions if f.name == "outer_function"), None)
            assert outer_func is not None
            assert outer_func.name == "outer_function"
            assert len(outer_func.params) == 1
            assert outer_func.params[0] == ("x", "int")
            assert outer_func.return_type == "int"
        finally:
            temp_path.unlink()
    
    def test_parse_async_functions(self):
        """Test parsing async functions."""
        code = """
async def fetch_data(url: str) -> dict:
    return {"data": "example"}

async def process_async(items: list) -> None:
    for item in items:
        await fetch_data(item)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            # Should extract both async functions
            assert len(functions) == 2
            
            # Check first async function
            fetch_func = functions[0]
            assert fetch_func.name == "fetch_data"
            assert len(fetch_func.params) == 1
            assert fetch_func.params[0] == ("url", "str")
            assert fetch_func.return_type == "dict"
            
            # Check second async function
            process_func = functions[1]
            assert process_func.name == "process_async"
            assert len(process_func.params) == 1
            assert process_func.params[0] == ("items", "list")
            assert process_func.return_type == "None"
        finally:
            temp_path.unlink()
    
    def test_parse_generator_functions(self):
        """Test parsing generator functions."""
        code = """
def simple_generator(n: int):
    for i in range(n):
        yield i

def generator_with_return(items: list) -> int:
    for item in items:
        yield item
    return len(items)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            # Should extract both generator functions
            assert len(functions) == 2
            
            # Check first generator
            gen1 = functions[0]
            assert gen1.name == "simple_generator"
            assert len(gen1.params) == 1
            assert gen1.params[0] == ("n", "int")
            assert "yield" in gen1.body_preview
            
            # Check second generator
            gen2 = functions[1]
            assert gen2.name == "generator_with_return"
            assert len(gen2.params) == 1
            assert gen2.params[0] == ("items", "list")
            assert gen2.return_type == "int"
            assert "yield" in gen2.body_preview
        finally:
            temp_path.unlink()
    
    def test_parse_decorators(self):
        """Test parsing functions with decorators."""
        code = """
def my_decorator(func):
    return func

@my_decorator
def decorated_function(x: int) -> int:
    return x * 2

@staticmethod
def static_method(value: str) -> str:
    return value.upper()

@property
def my_property(self) -> int:
    return 42
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            # Should extract all functions including decorated ones
            assert len(functions) == 4
            
            # Check decorator function
            decorator_func = functions[0]
            assert decorator_func.name == "my_decorator"
            
            # Check decorated function
            decorated_func = functions[1]
            assert decorated_func.name == "decorated_function"
            assert len(decorated_func.params) == 1
            assert decorated_func.params[0] == ("x", "int")
            assert decorated_func.return_type == "int"
            
            # Check static method
            static_func = functions[2]
            assert static_func.name == "static_method"
            assert len(static_func.params) == 1
            assert static_func.params[0] == ("value", "str")
            
            # Check property
            property_func = functions[3]
            assert property_func.name == "my_property"
            assert property_func.return_type == "int"
        finally:
            temp_path.unlink()
    
    def test_parse_class_properties_and_static_methods(self):
        """Test parsing class properties and static methods."""
        code = """
class MyClass:
    class_var = 42
    
    def __init__(self, value: int):
        self.value = value
    
    @property
    def doubled(self) -> int:
        '''Return double the value.'''
        return self.value * 2
    
    @staticmethod
    def static_helper(x: int, y: int) -> int:
        '''Static method helper.'''
        return x + y
    
    @classmethod
    def from_string(cls, s: str):
        '''Create instance from string.'''
        return cls(int(s))
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            parser = PythonParser()
            functions, classes = parser.parse_file(temp_path)
            
            # Should extract the class
            assert len(classes) == 1
            cls = classes[0]
            assert cls.name == "MyClass"
            
            # Should extract all methods including property, static, and class methods
            assert len(cls.methods) == 4
            
            # Check __init__
            init_method = next((m for m in cls.methods if m.name == "__init__"), None)
            assert init_method is not None
            assert init_method.parent_class == "MyClass"
            assert len(init_method.params) == 2  # self, value
            
            # Check property
            property_method = next((m for m in cls.methods if m.name == "doubled"), None)
            assert property_method is not None
            assert property_method.return_type == "int"
            assert property_method.has_docstring is True
            assert "Return double the value" in property_method.existing_docstring
            
            # Check static method
            static_method = next((m for m in cls.methods if m.name == "static_helper"), None)
            assert static_method is not None
            assert len(static_method.params) == 2  # x, y (no self)
            assert static_method.return_type == "int"
            assert static_method.has_docstring is True
            
            # Check class method
            class_method = next((m for m in cls.methods if m.name == "from_string"), None)
            assert class_method is not None
            assert len(class_method.params) == 2  # cls, s
            assert class_method.has_docstring is True
        finally:
            temp_path.unlink()
