"""CLI interface for docstring generator."""

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from docgen.batch import process_files_batch
from docgen.config import ConfigLoader
from docgen.coverage import calculate_coverage
from docgen.models import Config
from docgen.walker import FileWalker

console = Console()


def merge_cli_options(config: Config, cli_options: dict) -> Config:
    """
    Merge CLI options with config, giving CLI precedence.

    Args:
        config: Base configuration
        cli_options: CLI option overrides

    Returns:
        Merged configuration
    """
    for key, value in cli_options.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)
    return config


def get_staged_files() -> list[Path]:
    """
    Get list of staged Python files from git.

    Returns:
        List of staged Python file paths
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [
            Path(f) for f in result.stdout.splitlines() if f.endswith(".py") and Path(f).exists()
        ]
        return files
    except subprocess.CalledProcessError:
        return []


def display_summary(stats, errors: list[str]) -> None:
    """
    Display processing summary.

    Args:
        stats: Processing statistics
        errors: List of error messages
    """
    console.print("\n[bold green]Processing Summary:[/bold green]")
    console.print(f"Files processed: {stats.files_processed}")
    console.print(f"Docstrings added: {stats.docstrings_added}")
    console.print(f"Docstrings updated: {stats.docstrings_updated}")
    console.print(f"Errors: {stats.errors}")

    if errors:
        console.print("\n[bold red]Errors encountered:[/bold red]")
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Location", style="cyan")
        table.add_column("Error", style="red")

        for error in errors:
            if " - " in error:
                location, error_msg = error.split(" - ", 1)
                table.add_row(location, error_msg)
            else:
                table.add_row("", error)

        console.print(table)


def display_coverage_report(report, format_type: str = "text") -> None:
    """
    Display coverage report.

    Args:
        report: Coverage report object
        format_type: Output format ('text' or 'json')
    """
    if format_type == "json":
        output = {
            "total_functions": report.total_functions,
            "documented_functions": report.documented_functions,
            "coverage_percentage": report.coverage_percentage,
            "missing_docstrings": report.missing_docstrings,
        }
        # Use print instead of console.print for JSON to avoid ANSI codes
        print(json.dumps(output, indent=2))
    else:
        console.print("\n[bold blue]Docstring Coverage Report:[/bold blue]")
        console.print(f"Total functions: {report.total_functions}")
        console.print(f"Documented functions: {report.documented_functions}")
        console.print(
            f"Coverage: {report.coverage_percentage:.2f}%"
        )

        if report.missing_docstrings:
            console.print("\n[bold yellow]Missing Docstrings:[/bold yellow]")
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("File", style="cyan")
            table.add_column("Line", style="magenta")

            for file_path, line_number in report.missing_docstrings:
                table.add_row(file_path, str(line_number))

            console.print(table)


def output_github_annotations(missing_docstrings: list[tuple[str, int]]) -> None:
    """
    Output GitHub Actions annotations for missing docstrings.

    Args:
        missing_docstrings: List of (file_path, line_number) tuples
    """
    for file_path, line_number in missing_docstrings:
        print(f"::warning file={file_path},line={line_number}::Missing docstring")


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
@click.option(
    "--only-missing", is_flag=True, help="Process only functions without docstrings"
)
@click.option(
    "--style",
    type=click.Choice(["google", "numpy", "sphinx"]),
    help="Docstring style",
)
@click.option(
    "--provider",
    type=click.Choice(["anthropic", "openai", "ollama"]),
    help="LLM provider",
)
@click.option("--model", help="Model name")
@click.option("--report", is_flag=True, help="Generate coverage report")
@click.option(
    "--check", is_flag=True, help="Exit with code 1 if any functions lack docstrings"
)
@click.option(
    "--min-coverage", type=float, help="Minimum coverage percentage (0-100)"
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option("--staged", is_flag=True, help="Process only git staged files")
@click.option(
    "--language",
    type=click.Choice(["python"]),
    default="python",
    help="Programming language (currently only supports python)",
)
def main(
    path,
    dry_run,
    only_missing,
    style,
    provider,
    model,
    report,
    check,
    min_coverage,
    format_type,
    staged,
    language,
):
    """Generate docstrings for Python files."""
    try:
        # Determine file extensions based on language
        if language == "python":
            file_extensions = [".py"]
        else:
            # Future language support can be added here
            console.print(f"[red]Unsupported language: {language}[/red]")
            sys.exit(1)
        
        # Load configuration
        config = ConfigLoader.load()

        # Merge CLI options
        cli_options = {
            "style": style,
            "provider": provider,
            "model": model,
        }
        config = merge_cli_options(config, cli_options)

        # Get files to process
        if staged:
            files = get_staged_files()
            if not files:
                console.print("[yellow]No staged Python files found[/yellow]")
                sys.exit(0)
        else:
            walker = FileWalker(
                exclude_patterns=config.exclude,
                file_extensions=file_extensions
            )
            files = walker.discover_files(Path(path))

        if not files:
            console.print("[yellow]No Python files found[/yellow]")
            sys.exit(0)

        # Handle report mode
        if report:
            coverage_report = calculate_coverage(files)
            display_coverage_report(coverage_report, format_type)

            # Output GitHub annotations if in CI
            if format_type == "json":
                output_github_annotations(coverage_report.missing_docstrings)

            # Check coverage threshold
            if min_coverage is not None:
                if coverage_report.coverage_percentage < min_coverage:
                    console.print(
                        f"[red]Coverage {coverage_report.coverage_percentage:.2f}% "
                        f"is below minimum {min_coverage}%[/red]"
                    )
                    sys.exit(1)

            sys.exit(0)

        # Handle check mode
        if check:
            coverage_report = calculate_coverage(files)
            if coverage_report.missing_docstrings:
                console.print(
                    f"[red]Found {len(coverage_report.missing_docstrings)} "
                    f"functions without docstrings[/red]"
                )
                sys.exit(1)
            else:
                console.print("[green]All functions have docstrings[/green]")
                sys.exit(0)

        # Process files with progress bar
        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Processing {len(files)} files...", total=len(files)
            )

            stats, errors = process_files_batch(
                files, config, dry_run=dry_run, only_missing=only_missing
            )

            progress.update(task, completed=len(files))

        # Display summary
        display_summary(stats, errors)

        # Stage modified files if in staged mode and not dry-run
        if staged and not dry_run:
            for file_path in files:
                try:
                    subprocess.run(
                        ["git", "add", str(file_path)],
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    pass

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
