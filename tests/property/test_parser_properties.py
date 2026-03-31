"""Property-based tests for PythonParser component.

**Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.6**
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, assume

from docgen.parser import PythonParser
from docgen.models import FunctionInfo


@pytest.mark.property
class TestPythonParserProperties:
    """Property tests for PythonParser class."""
    
    @settings(max_examples=100)
    @given(
        num_functions=st.integers(min_value=1, max_value=20),
        has_type_hints=st.booleans(),
        has_return_type=st.booleans(),
        num_params=st.integers(min_value=0, max_value=5),
        data=st.data(),
    )
    def test_property_4_function_extraction_completeness(
        self,
        num_functions,
        has_type_hints,
        has_return_type,
        num_params,
        data,
    ):
        """Property 4: Function Extraction Completeness.
        
        For any valid Python file, the Parser should extract all function definitions,
        including their name, parameters with type hints, return type, and body preview.
        
        **Validates: Requirements 2.1, 2.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test_module.py"
            
            # Generate Python code with specified number of functions
            code_lines = []
            expected_functions = []
            
            for i in range(num_functions):
                func_name = f"function_{i}"
                
                # Build parameter list
                params = []
                param_strs = []
                for j in range(num_params):
                    param_name = f"param_{j}"
                    if has_type_hints:
                        param_type = data.draw(st.sampled_from(["int", "str", "float", "bool"]))
                        param_strs.append(f"{param_name}: {param_type}")
                        params.append((param_name, param_type))
                    else:
                        param_strs.append(param_name)
                        params.append((param_name, None))
                
                # Build function signature
                param_list = ", ".join(param_strs)
                
                # Add return type if specified
                return_type_str = ""
                expected_return_type = None
                if has_return_type and has_type_hints:
                    expected_return_type = data.draw(st.sampled_from(["int", "str", "float", "bool", "None"]))
                    return_type_str = f" -> {expected_return_type}"
                
                # Build function definition
                func_def = f"def {func_name}({param_list}){return_type_str}:"
                code_lines.append(func_def)
                
                # Add function body (at least 2 lines to test body preview)
                code_lines.append(f"    line1 = {i}")
                code_lines.append(f"    line2 = {i * 2}")
                code_lines.append(f"    return {i}")
                code_lines.append("")  # Empty line between functions
                
                # Track expected function metadata
                expected_functions.append({
                    "name": func_name,
                    "params": params,
                    "return_type": expected_return_type,
                    "num_params": num_params,
                })
            
            # Write code to file
            test_file.write_text("\n".join(code_lines))
            
            # Parse the file
            parser = PythonParser()
            functions, classes = parser.parse_file(test_file)
            
            # Property 1: Parser should extract ALL functions (Requirement 2.1)
            assert len(functions) == num_functions, \
                f"Expected {num_functions} functions, but extracted {len(functions)}"
            
            # Property 2: No classes should be extracted (we only created functions)
            assert len(classes) == 0, \
                f"Expected 0 classes, but extracted {len(classes)}"
            
            # Property 3: Each function should have correct metadata (Requirement 2.2)
            for i, func in enumerate(functions):
                expected = expected_functions[i]
                
                # Verify function name
                assert func.name == expected["name"], \
                    f"Function {i}: expected name '{expected['name']}', got '{func.name}'"
                
                # Verify number of parameters
                assert len(func.params) == expected["num_params"], \
                    f"Function {i}: expected {expected['num_params']} params, got {len(func.params)}"
                
                # Verify parameter names and type hints
                for j, (param_name, param_type) in enumerate(func.params):
                    expected_param_name, expected_param_type = expected["params"][j]
                    assert param_name == expected_param_name, \
                        f"Function {i}, param {j}: expected name '{expected_param_name}', got '{param_name}'"
                    assert param_type == expected_param_type, \
                        f"Function {i}, param {j}: expected type '{expected_param_type}', got '{param_type}'"
                
                # Verify return type
                assert func.return_type == expected["return_type"], \
                    f"Function {i}: expected return type '{expected['return_type']}', got '{func.return_type}'"
                
                # Verify body preview is present and non-empty
                assert func.body_preview, \
                    f"Function {i}: body_preview should not be empty"
                
                # Verify body preview contains expected content
                assert f"line1 = {i}" in func.body_preview, \
                    f"Function {i}: body_preview should contain 'line1 = {i}'"
                
                # Verify body preview is truncated to max 5 lines
                body_lines = func.body_preview.split('\n')
                assert len(body_lines) <= 5, \
                    f"Function {i}: body_preview should have at most 5 lines, got {len(body_lines)}"
                
                # Verify function has no docstring (we didn't add any)
                assert func.has_docstring is False, \
                    f"Function {i}: should not have docstring"
                
                # Verify parent_class is None (module-level functions)
                assert func.parent_class is None, \
                    f"Function {i}: parent_class should be None for module-level functions"
            
            # Property 4: All extracted functions should be FunctionInfo instances
            assert all(isinstance(f, FunctionInfo) for f in functions), \
                "All extracted functions should be FunctionInfo instances"
            
            # Property 5: Function names should be unique and in order
            func_names = [f.name for f in functions]
            expected_names = [f"function_{i}" for i in range(num_functions)]
            assert func_names == expected_names, \
                f"Function names should be {expected_names}, got {func_names}"
    
    @settings(max_examples=100)
    @given(
        num_classes=st.integers(min_value=1, max_value=10),
        num_methods_per_class=st.integers(min_value=0, max_value=5),
        class_has_docstring=st.booleans(),
        method_has_docstring=st.booleans(),
        data=st.data(),
    )
    def test_property_5_class_extraction_completeness(
        self,
        num_classes,
        num_methods_per_class,
        class_has_docstring,
        method_has_docstring,
        data,
    ):
        """Property 5: Class Extraction Completeness.
        
        For any valid Python file containing classes, the Parser should extract all
        classes with their name, methods, and attributes.
        
        **Validates: Requirements 2.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test_classes.py"
            
            # Generate Python code with specified number of classes
            code_lines = []
            expected_classes = []
            
            for i in range(num_classes):
                class_name = f"Class_{i}"
                
                # Build class definition
                code_lines.append(f"class {class_name}:")
                
                # Add class docstring if specified
                if class_has_docstring:
                    code_lines.append(f'    """Docstring for {class_name}."""')
                
                # Track expected methods for this class
                expected_methods = []
                
                # Add methods to the class
                if num_methods_per_class == 0:
                    # Empty class needs at least a pass statement
                    code_lines.append("    pass")
                else:
                    for j in range(num_methods_per_class):
                        method_name = f"method_{j}"
                        
                        # Build method signature (simple for now)
                        code_lines.append(f"    def {method_name}(self):")
                        
                        # Add method docstring if specified
                        if method_has_docstring:
                            code_lines.append(f'        """Docstring for {method_name}."""')
                        
                        # Add method body
                        code_lines.append(f"        return {j}")
                        code_lines.append("")  # Empty line between methods
                        
                        # Track expected method metadata
                        expected_methods.append({
                            "name": method_name,
                            "parent_class": class_name,
                            "has_docstring": method_has_docstring,
                        })
                
                code_lines.append("")  # Empty line between classes
                
                # Track expected class metadata
                expected_classes.append({
                    "name": class_name,
                    "num_methods": num_methods_per_class,
                    "has_docstring": class_has_docstring,
                    "methods": expected_methods,
                })
            
            # Write code to file
            test_file.write_text("\n".join(code_lines))
            
            # Parse the file
            parser = PythonParser()
            functions, classes = parser.parse_file(test_file)
            
            # Property 1: Parser should extract ALL classes (Requirement 2.3)
            assert len(classes) == num_classes, \
                f"Expected {num_classes} classes, but extracted {len(classes)}"
            
            # Property 2: No module-level functions should be extracted (we only created classes)
            assert len(functions) == 0, \
                f"Expected 0 module-level functions, but extracted {len(functions)}"
            
            # Property 3: Each class should have correct metadata (Requirement 2.3)
            for i, cls in enumerate(classes):
                expected = expected_classes[i]
                
                # Verify class name
                assert cls.name == expected["name"], \
                    f"Class {i}: expected name '{expected['name']}', got '{cls.name}'"
                
                # Verify class has_docstring flag
                assert cls.has_docstring == expected["has_docstring"], \
                    f"Class {i}: expected has_docstring={expected['has_docstring']}, got {cls.has_docstring}"
                
                # Verify class docstring content if present
                if cls.has_docstring:
                    assert cls.existing_docstring is not None, \
                        f"Class {i}: has_docstring is True but existing_docstring is None"
                    assert f"Docstring for {expected['name']}" in cls.existing_docstring, \
                        f"Class {i}: docstring should contain 'Docstring for {expected['name']}'"
                
                # Verify number of methods
                assert len(cls.methods) == expected["num_methods"], \
                    f"Class {i}: expected {expected['num_methods']} methods, got {len(cls.methods)}"
                
                # Verify each method's metadata
                for j, method in enumerate(cls.methods):
                    expected_method = expected["methods"][j]
                    
                    # Verify method name
                    assert method.name == expected_method["name"], \
                        f"Class {i}, method {j}: expected name '{expected_method['name']}', got '{method.name}'"
                    
                    # Verify parent_class is set correctly
                    assert method.parent_class == expected_method["parent_class"], \
                        f"Class {i}, method {j}: expected parent_class '{expected_method['parent_class']}', got '{method.parent_class}'"
                    
                    # Verify method has_docstring flag
                    assert method.has_docstring == expected_method["has_docstring"], \
                        f"Class {i}, method {j}: expected has_docstring={expected_method['has_docstring']}, got {method.has_docstring}"
                    
                    # Verify method docstring content if present
                    if method.has_docstring:
                        assert method.existing_docstring is not None, \
                            f"Class {i}, method {j}: has_docstring is True but existing_docstring is None"
                        assert f"Docstring for {expected_method['name']}" in method.existing_docstring, \
                            f"Class {i}, method {j}: docstring should contain 'Docstring for {expected_method['name']}'"
                    
                    # Verify method has body_preview
                    assert method.body_preview, \
                        f"Class {i}, method {j}: body_preview should not be empty"
                    
                    # Verify method has 'self' parameter
                    assert len(method.params) >= 1, \
                        f"Class {i}, method {j}: should have at least 'self' parameter"
                    assert method.params[0][0] == "self", \
                        f"Class {i}, method {j}: first parameter should be 'self', got '{method.params[0][0]}'"
            
            # Property 4: Class names should be unique and in order
            class_names = [c.name for c in classes]
            expected_names = [f"Class_{i}" for i in range(num_classes)]
            assert class_names == expected_names, \
                f"Class names should be {expected_names}, got {class_names}"
    
    @settings(max_examples=100)
    @given(
        num_functions=st.integers(min_value=1, max_value=15),
        docstring_style=st.sampled_from(["single_line", "multi_line", "triple_single", "triple_double"]),
        data=st.data(),
    )
    def test_property_7_docstring_detection(
        self,
        num_functions,
        docstring_style,
        data,
    ):
        """Property 7: Docstring Detection.
        
        For any function with an existing docstring, the Parser should correctly
        identify has_docstring as True and extract the docstring text.
        
        **Validates: Requirements 2.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test_docstrings.py"
            
            # Generate Python code with functions that have docstrings
            code_lines = []
            expected_docstrings = []
            
            for i in range(num_functions):
                func_name = f"function_{i}"
                
                # Generate a docstring
                docstring_content = data.draw(
                    st.text(min_size=5, max_size=100, alphabet=st.characters(
                        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                        whitelist_characters=".,!?-"
                    ))
                ).strip()
                
                # Ensure docstring is not empty
                if not docstring_content:
                    docstring_content = f"Docstring for function {i}"
                
                # Build function with docstring based on style
                code_lines.append(f"def {func_name}():")
                
                if docstring_style == "single_line":
                    code_lines.append(f'    """{ docstring_content}"""')
                elif docstring_style == "multi_line":
                    code_lines.append(f'    """')
                    code_lines.append(f'    {docstring_content}')
                    code_lines.append(f'    """')
                elif docstring_style == "triple_single":
                    code_lines.append(f"    '''{docstring_content}'''")
                else:  # triple_double
                    code_lines.append(f'    """{docstring_content}"""')
                
                # Add function body
                code_lines.append(f"    return {i}")
                code_lines.append("")  # Empty line between functions
                
                # Track expected docstring
                expected_docstrings.append(docstring_content)
            
            # Write code to file
            test_file.write_text("\n".join(code_lines))
            
            # Parse the file
            parser = PythonParser()
            functions, classes = parser.parse_file(test_file)
            
            # Property 1: Parser should extract all functions
            assert len(functions) == num_functions, \
                f"Expected {num_functions} functions, but extracted {len(functions)}"
            
            # Property 2: All functions should have docstrings detected
            for i, func in enumerate(functions):
                assert func.has_docstring is True, \
                    f"Function {i} ({func.name}): has_docstring should be True"
                
                # Property 3: Docstring text should be extracted
                assert func.existing_docstring is not None, \
                    f"Function {i} ({func.name}): existing_docstring should not be None"
                
                # Property 4: Extracted docstring should match expected content
                assert expected_docstrings[i] in func.existing_docstring or \
                       func.existing_docstring in expected_docstrings[i], \
                    f"Function {i} ({func.name}): expected docstring '{expected_docstrings[i]}', got '{func.existing_docstring}'"
    
    @settings(max_examples=100)
    @given(
        num_functions=st.integers(min_value=1, max_value=15),
        has_body=st.booleans(),
        num_body_lines=st.integers(min_value=1, max_value=10),
    )
    def test_property_8_missing_docstring_detection(
        self,
        num_functions,
        has_body,
        num_body_lines,
    ):
        """Property 8: Missing Docstring Detection.
        
        For any function without a docstring, the Parser should correctly
        identify has_docstring as False.
        
        **Validates: Requirements 2.6**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test_no_docstrings.py"
            
            # Generate Python code with functions that have NO docstrings
            code_lines = []
            
            for i in range(num_functions):
                func_name = f"function_{i}"
                
                # Build function WITHOUT docstring
                code_lines.append(f"def {func_name}():")
                
                # Add function body (but no docstring)
                if has_body:
                    for j in range(num_body_lines):
                        code_lines.append(f"    line_{j} = {i * j}")
                    code_lines.append(f"    return {i}")
                else:
                    code_lines.append("    pass")
                
                code_lines.append("")  # Empty line between functions
            
            # Write code to file
            test_file.write_text("\n".join(code_lines))
            
            # Parse the file
            parser = PythonParser()
            functions, classes = parser.parse_file(test_file)
            
            # Property 1: Parser should extract all functions
            assert len(functions) == num_functions, \
                f"Expected {num_functions} functions, but extracted {len(functions)}"
            
            # Property 2: All functions should have NO docstrings detected
            for i, func in enumerate(functions):
                assert func.has_docstring is False, \
                    f"Function {i} ({func.name}): has_docstring should be False"
                
                # Property 3: existing_docstring should be None
                assert func.existing_docstring is None, \
                    f"Function {i} ({func.name}): existing_docstring should be None when has_docstring is False"
                
                # Property 4: body_preview should still be present
                assert func.body_preview, \
                    f"Function {i} ({func.name}): body_preview should not be empty even without docstring"
