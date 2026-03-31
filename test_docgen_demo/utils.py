def format_name(first: str, last: str) -> str:
    """Formats a person's name with a space in between first and last names.

Arguments:
    first (str): The first name of the person.
    last (str): The last name of the person.

Returns:
    str: A string representing the formatted full name, e.g. "John Doe"."""
    return f"{first} {last}"

def calculate_age(birth_year: int, current_year: int) -> int:
    """Calculates the age of a person given their birth year and the current year.

   Args:
      birth_year (int): The birth year of the person.
      current_year (int): The current year in which the function is called.

   Returns:
      int: The age of the person, calculated as current_year - birth_year.

   Raises:
      None"""
    return current_year - birth_year

class StringHelper:
    def uppercase(self, text: str) -> str:
        """Converts a given string to uppercase.

Args:
    self (object): The instance of the class (if applicable).
    text (str): The input string to be converted to uppercase.

Returns:
    str: A new string with all characters in uppercase.

Raises:
    TypeError: If `text` is not a string."""
        return text.upper()
    
    def lowercase(self, text: str) -> str:
        """Lowercases a given string.

Arguments:
    text (str): The input string to be converted to lowercase.

Returns:
    str: A new string with all uppercase characters converted to lowercase.

Raises:
    TypeError: If the input is not a string."""
        return text.lower()
