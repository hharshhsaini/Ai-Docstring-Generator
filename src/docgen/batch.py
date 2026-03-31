"""Batch processing with error recovery."""

from pathlib import Path

from docgen.config import Config
from docgen.diff import generate_diff, display_diff
from docgen.formatter import DocstringFormatter
from docgen.llm import LLMClient, LLMError
from docgen.models import ProcessingStats
from docgen.parser import PythonParser
from docgen.patcher import DocstringPatcher
from docgen.prompt import PromptBuilder


class ParseError(Exception):
    """Error parsing Python file."""

    pass


class PatchError(Exception):
    """Error patching file."""

    pass


def process_files_batch(
    files: list[Path],
    config: Config,
    dry_run: bool = False,
    only_missing: bool = False,
) -> tuple[ProcessingStats, list[str]]:
    """
    Process multiple files with error recovery.

    Args:
        files: List of file paths to process
        config: Configuration object
        dry_run: If True, preview changes without modifying files
        only_missing: If True, skip functions that already have docstrings

    Returns:
        Tuple of (statistics, error_messages)
    """
    stats = ProcessingStats()
    errors: list[str] = []

    # Initialize components
    parser = PythonParser()
    prompt_builder = PromptBuilder(style=config.style)
    llm_client = LLMClient(config.to_llm_config())
    formatter = DocstringFormatter(style=config.style)
    patcher = DocstringPatcher(overwrite_existing=config.overwrite_existing)

    for file_path in files:
        try:
            # Parse file
            try:
                functions, classes = parser.parse_file(file_path)
            except Exception as e:
                raise ParseError(f"Failed to parse file: {e}")

            stats.files_processed += 1

            # Collect all functions (module-level + class methods)
            all_functions = list(functions)
            for cls in classes:
                all_functions.extend(cls.methods)

            # Process each function
            for func in all_functions:
                if only_missing and func.has_docstring:
                    continue

                try:
                    # Generate docstring
                    prompt = prompt_builder.build_prompt(func)
                    docstring_text = llm_client.generate(prompt)

                    # Validate
                    is_valid, error_msg = formatter.validate(docstring_text)
                    if not is_valid:
                        errors.append(
                            f"{file_path}:{func.line_number} - Validation failed: {error_msg}"
                        )
                        stats.increment_error()
                        continue

                    # Format
                    formatted_docstring = formatter.format(docstring_text)

                    # Apply or preview
                    if dry_run:
                        diff = generate_diff(file_path, func, formatted_docstring)
                        display_diff(diff)
                    else:
                        try:
                            modified_code = patcher.inject_docstring(
                                file_path,
                                func.name,
                                formatted_docstring,
                                func.parent_class,
                            )
                            
                            # Write the modified code back to the file
                            patcher.write_file(file_path, modified_code)

                            if func.has_docstring:
                                stats.increment_updated()
                            else:
                                stats.increment_added()
                        except Exception as e:
                            raise PatchError(f"Failed to patch file: {e}")

                except LLMError as e:
                    errors.append(f"{file_path}:{func.line_number} - LLM error: {e}")
                    stats.increment_error()
                    continue

                except PatchError as e:
                    errors.append(f"{file_path}:{func.line_number} - Patch error: {e}")
                    stats.increment_error()
                    continue

                except Exception as e:
                    errors.append(
                        f"{file_path}:{func.line_number} - Unexpected error: {e}"
                    )
                    stats.increment_error()
                    continue

        except ParseError as e:
            errors.append(f"{file_path} - Parse error: {e}")
            stats.increment_error()
            continue

        except Exception as e:
            errors.append(f"{file_path} - Unexpected error: {e}")
            stats.increment_error()
            continue

    return stats, errors
