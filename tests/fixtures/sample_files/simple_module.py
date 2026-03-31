"""Sample Python module for testing."""


def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


def add_numbers(a: int, b: int) -> int:
    return a + b


class Person:
    """A simple person class."""
    
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
    
    def introduce(self) -> str:
        return f"My name is {self.name} and I am {self.age} years old."
    
    def birthday(self) -> None:
        self.age += 1
