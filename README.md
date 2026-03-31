# Docstring Generator

A Python CLI tool that automatically generates and injects docstrings into Python codebases using LLM providers. It uses AST parsing to extract function metadata, leverages LLMs to generate contextually accurate docstrings, and patches them directly back into source files while preserving formatting.

## Features

- 🤖 **Multiple LLM Providers**: Support for Anthropic, OpenAI, and Ollama (local)
- 📝 **Multiple Docstring Styles**: Google, NumPy, and Sphinx formats
- 🔍 **AST-Based Parsing**: Accurate extraction using libcst
- 🎨 **Formatting Preservation**: Maintains original code structure and whitespace
- 🚀 **CI/CD Integration**: Pre-commit hooks and GitHub Actions support
- 📊 **Coverage Reports**: Track documentation completeness
- 🔄 **Dry-Run Mode**: Preview changes before applying
- ⚡ **Batch Processing**: Process entire codebases with error recovery
- 🎯 **Smart Filtering**: Process only missing docstrings or staged files

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Testing the Tool](#testing-the-tool)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Docstring Styles](#docstring-styles)
- [LLM Provider Setup](#llm-provider-setup)
- [Pre-commit Hook Setup](#pre-commit-hook-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/docstring-generator.git
cd docstring-generator

# Install in editable mode with dependencies
pip install -e .
```

### From PyPI (When Published)

```bash
pip install docstring-generator
```

### Verify Installation

```bash
docgen --help
```

## Quick Start

### 1. Set Up API Key

Choose one LLM provider and set your API key:

**Anthropic (Recommended):**
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

**OpenAI:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

**Ollama (Local, No API Key):**
```bash
# Install Ollama from https://ollama.ai/
ollama pull llama2
ollama serve
```

### 2. Create a Test File

```bash
mkdir -p test_project
cat > test_project/calculator.py << 'EOF'
def add(a: int, b: int) -> int:
    return a + b

def subtract(x: int, y: int) -> int:
    return x - y

class Calculator:
    def multiply(self, a: int, b: int) -> int:
        return a * b
EOF
```

### 3. Generate Docstrings

**Preview changes first (dry-run):**
```bash
docgen test_project/ --dry-run
```

**Generate docstrings:**
```bash
docgen test_project/
```

**Check the results:**
```bash
cat test_project/calculator.py
```

### Example Output

**Before:**
```python
def add(a: int, b: int) -> int:
    return a + b
```

**After (Google style):**
```python
def add(a: int, b: int) -> int:
    """Add two integers.
    
    Args:
        a: First integer to add.
        b: Second integer to add.
    
    Returns:
        Sum of a and b.
    """
    return a + b
```

## Testing the Tool

### Basic Test Scenarios

**Test 1: Dry Run (Preview Mode)**
```bash
# Preview changes without modifying files
docgen test_project/ --dry-run
```
Expected: Shows diffs of proposed changes, no files modified.

**Test 2: Generate Docstrings**
```bash
# Actually generate and inject docstrings
docgen test_project/
```
Expected: "Files processed: 1", "Docstrings added: X"

**Test 3: Only Missing Docstrings**
```bash
# Run again - should skip existing docstrings
docgen test_project/ --only-missing
```
Expected: "Docstrings added: 0" (all functions already documented)

**Test 4: Different Styles**
```bash
# Create a new file
cat > test_project/utils.py << 'EOF'
def format_name(first: str, last: str) -> str:
    return f"{first} {last}"
EOF

# Try NumPy style
docgen test_project/utils.py --style numpy

# Try Sphinx style (remove docstring first)
cat > test_project/utils.py << 'EOF'
def format_name(first: str, last: str) -> str:
    return f"{first} {last}"
EOF
docgen test_project/utils.py --style sphinx
```

**Test 5: Coverage Report**
```bash
# Check documentation coverage
docgen test_project/ --report
```
Expected output:
```
Docstring Coverage Report
=========================
Total functions: 4
Documented functions: 4
Coverage: 100.00%

✓ All functions are documented!
```

**Test 6: Coverage Check with Threshold**
```bash
# Create file with missing docstrings
cat > test_project/incomplete.py << 'EOF'
def documented():
    """Has docstring."""
    pass

def undocumented():
    pass
EOF

# Check coverage (should fail)
docgen test_project/ --check --min-coverage 100
echo "Exit code: $?"
```
Expected: Exit code 1, error about coverage below threshold.

**Test 7: JSON Output**
```bash
# Generate JSON report for CI/CD
docgen test_project/ --report --format json
```
Expected: Valid JSON with coverage statistics.

**Test 8: Configuration File**
```bash
# Create config file
cat > test_project/docgen.toml << 'EOF'
[docgen]
style = "google"
provider = "anthropic"
overwrite_existing = false

[docgen.exclude]
patterns = ["**/test_*.py"]
EOF

# Run with config
cd test_project && docgen . && cd ..
```

**Test 9: Overwrite Existing**
```bash
# Overwrite existing docstrings
docgen test_project/ --overwrite-existing
```

**Test 10: Error Handling**
```bash
# Create invalid Python file
cat > test_project/broken.py << 'EOF'
def broken(
    pass
EOF

# Tool should continue processing
docgen test_project/
```
Expected: Shows error but continues with other files.

### Verification Checklist

After testing, verify:

- ✅ Docstrings generated in correct style
- ✅ Original formatting preserved (indentation, comments)
- ✅ Type hints included in docstrings
- ✅ Parameters documented
- ✅ Return values documented
- ✅ Files remain syntactically valid: `python -m py_compile test_project/*.py`
- ✅ Coverage reports accurate
- ✅ Error handling works

### Clean Up Test Files

```bash
rm -rf test_project/
```

## Configuration

### Configuration File

Create a `docgen.toml` file in your project root:

```toml
[docgen]
# Docstring style: "google", "numpy", or "sphinx"
style = "google"

# LLM provider: "anthropic", "openai", or "ollama"
provider = "anthropic"

# Model name (provider-specific)
model = "claude-3-5-sonnet-20241022"

# Whether to overwrite existing docstrings
overwrite_existing = false

[docgen.exclude]
# Glob patterns for files to exclude
patterns = [
    "**/test_*.py",
    "**/migrations/**",
    "**/__pycache__/**",
]

[docgen.llm]
# Maximum retry attempts for API calls
max_retries = 3

# Request timeout in seconds
timeout = 30
```

### Configuration Precedence

Configuration is loaded with the following precedence (highest to lowest):

1. CLI flags (e.g., `--style google`)
2. Environment variables (e.g., `DOCGEN_STYLE=google`)
3. Config file (`docgen.toml`)
4. Default values

## CLI Reference

### Commands and Flags

```bash
docgen [PATH] [OPTIONS]
```

#### Arguments

- `PATH`: Directory or file path to process (required)

#### Options

**Generation Options:**
- `--style [google|numpy|sphinx]`: Docstring style (default: google)
- `--provider [anthropic|openai|ollama]`: LLM provider (default: anthropic)
- `--model TEXT`: Model name (provider-specific)
- `--only-missing`: Process only functions without docstrings
- `--overwrite-existing`: Replace existing docstrings

**Preview and Reporting:**
- `--dry-run`: Preview changes without modifying files
- `--report`: Generate coverage report
- `--format [text|json]`: Output format (default: text)

**CI/CD Integration:**
- `--check`: Exit with code 1 if any functions lack docstrings
- `--min-coverage FLOAT`: Minimum coverage percentage (0-100)
- `--staged`: Process only git-staged files

**Examples:**

```bash
# Use NumPy style with OpenAI
docgen ./src --style numpy --provider openai --model gpt-4

# Check coverage and fail if below 80%
docgen ./src --check --min-coverage 80

# Generate JSON report for CI
docgen ./src --report --format json > coverage.json

# Process only staged files (for pre-commit)
docgen ./src --staged --only-missing
```

## Docstring Styles

### Google Style

```python
def function(arg1: int, arg2: str) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: When invalid input is provided.
    """
```

### NumPy Style

```python
def function(arg1: int, arg2: str) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Parameters
    ----------
    arg1 : int
        Description of arg1.
    arg2 : str
        Description of arg2.
    
    Returns
    -------
    bool
        Description of return value.
    
    Raises
    ------
    ValueError
        When invalid input is provided.
    """
```

### Sphinx Style

```python
def function(arg1: int, arg2: str) -> bool:
    """Short description.
    
    Longer description if needed.
    
    :param arg1: Description of arg1.
    :type arg1: int
    :param arg2: Description of arg2.
    :type arg2: str
    :return: Description of return value.
    :rtype: bool
    :raises ValueError: When invalid input is provided.
    """
```

## LLM Provider Setup

### Anthropic (Claude)

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Set environment variable:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```
3. Configure in `docgen.toml`:
   ```toml
   [docgen]
   provider = "anthropic"
   model = "claude-3-5-sonnet-20241022"
   ```

**Supported Models:**
- `claude-3-5-sonnet-20241022` (recommended)
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

### OpenAI (GPT)

1. Get an API key from [OpenAI Platform](https://platform.openai.com/)
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```
3. Configure in `docgen.toml`:
   ```toml
   [docgen]
   provider = "openai"
   model = "gpt-4"
   ```

**Supported Models:**
- `gpt-4` (recommended)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Ollama (Local)

1. Install [Ollama](https://ollama.ai/)
2. Pull a model:
   ```bash
   ollama pull llama2
   ```
3. Start Ollama server:
   ```bash
   ollama serve
   ```
4. Configure in `docgen.toml`:
   ```toml
   [docgen]
   provider = "ollama"
   model = "llama2"
   
   [docgen.llm]
   base_url = "http://localhost:11434"
   ```

**Supported Models:**
- `llama2`
- `codellama`
- `mistral`
- Any model available in Ollama

## Pre-commit Hook Setup

### Installation

1. Install pre-commit:
   ```bash
   pip install pre-commit
   ```

2. Create `.pre-commit-config.yaml` in your project root:
   ```yaml
   repos:
     - repo: local
       hooks:
         - id: docstring-generator
           name: Generate docstrings
           entry: docgen
           args: [--staged, --only-missing, --check]
           language: system
           types: [python]
           pass_filenames: false
   ```

3. Install the hook:
   ```bash
   pre-commit install
   ```

### Configuration Options

**Enforce documentation (fail if missing):**
```yaml
args: [--staged, --only-missing, --check]
```

**Auto-generate without failing:**
```yaml
args: [--staged, --only-missing]
```

**Require minimum coverage:**
```yaml
args: [--staged, --check, --min-coverage, "80"]
```

### Usage

Once installed, the hook runs automatically on `git commit`:

```bash
git add src/mymodule.py
git commit -m "Add new feature"
# Hook runs automatically and generates docstrings
```

## GitHub Actions Setup

### Basic Workflow

Create `.github/workflows/docstring-check.yml`:

```yaml
name: Docstring Coverage Check

on:
  pull_request:
    paths:
      - '**.py'

jobs:
  check-docstrings:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install docstring-generator
        run: pip install docstring-generator
      
      - name: Check docstring coverage
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          docgen . --check --min-coverage 80
      
      - name: Generate coverage report
        if: failure()
        run: |
          docgen . --report
```

### Advanced Workflow with PR Comments

```yaml
name: Docstring Coverage Report

on:
  pull_request:
    paths:
      - '**.py'

jobs:
  coverage-report:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install docstring-generator
        run: pip install docstring-generator
      
      - name: Generate coverage report
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          docgen . --report --format json > coverage.json
          docgen . --report --format text > coverage.txt
      
      - name: Check coverage threshold
        run: |
          docgen . --check --min-coverage 80
      
      - name: Comment on PR
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const coverage = JSON.parse(fs.readFileSync('coverage.json', 'utf8'));
            const textReport = fs.readFileSync('coverage.txt', 'utf8');
            
            const comment = `## 📊 Docstring Coverage Report
            
            - **Total functions:** ${coverage.total_functions}
            - **Documented:** ${coverage.documented_functions}
            - **Coverage:** ${coverage.coverage_percentage.toFixed(2)}%
            
            ${coverage.missing_docstrings.length > 0 ? '### ⚠️ Missing Docstrings\n\n' + coverage.missing_docstrings.slice(0, 10).map(([file, line]) => `- \`${file}:${line}\``).join('\n') : '✅ All functions are documented!'}
            
            ${coverage.missing_docstrings.length > 10 ? `\n... and ${coverage.missing_docstrings.length - 10} more` : ''}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
      
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: coverage.json
```

### Setting Up Secrets

1. Go to your repository settings
2. Navigate to Secrets and variables → Actions
3. Add your API key:
   - Name: `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`)
   - Value: Your API key

## Troubleshooting

### Common Issues

**Issue: "API key not found"**
```
Error: API key required for anthropic. Set ANTHROPIC_API_KEY environment variable.
```

**Solution:**
```bash
# Set environment variable
export ANTHROPIC_API_KEY="your-api-key"

# Or add to your shell profile (~/.bashrc, ~/.zshrc)
echo 'export ANTHROPIC_API_KEY="your-api-key"' >> ~/.bashrc
```

---

**Issue: "Rate limit exceeded"**
```
Error: Anthropic rate limit exceeded
```

**Solution:**
- The tool automatically retries with exponential backoff
- Reduce batch size by processing fewer files at once
- Wait a few minutes and try again
- Consider upgrading your API plan

---

**Issue: "Invalid docstring format"**
```
Error: Validation failed: Missing short description
```

**Solution:**
- The LLM occasionally generates invalid docstrings
- The tool will skip invalid docstrings and continue
- Check the error summary at the end for details
- Consider trying a different model or provider

---

**Issue: "File parsing error"**
```
Error: Parse error: invalid syntax
```

**Solution:**
- Ensure your Python files have valid syntax
- Run `python -m py_compile yourfile.py` to check
- The tool will skip unparseable files and continue

---

**Issue: "Pre-commit hook is slow"**

**Solution:**
```yaml
# Process only staged files
args: [--staged, --only-missing]

# Or set a timeout
- id: docstring-generator
  name: Generate docstrings
  entry: timeout 30 docgen
  args: [--staged, --only-missing]
```

---

**Issue: "Ollama connection refused"**
```
Error: Connection refused to http://localhost:11434
```

**Solution:**
```bash
# Start Ollama server
ollama serve

# Or configure custom URL in docgen.toml
[docgen.llm]
base_url = "http://your-ollama-server:11434"
```

### Debug Mode

Enable verbose logging:

```bash
# Set log level
export DOCGEN_LOG_LEVEL=DEBUG

# Run with verbose output
docgen ./src --dry-run
```

### Getting Help

- Check the [GitHub Issues](https://github.com/yourusername/docstring-generator/issues)
- Read the [documentation](https://docstring-generator.readthedocs.io/)
- Join the [discussions](https://github.com/yourusername/docstring-generator/discussions)

## Contributing

We welcome contributions! Here's how to get started:

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/docstring-generator.git
   cd docstring-generator
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=docgen --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only property-based tests
pytest tests/property/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_parser.py

# Run with verbose output
pytest -v
```

### Code Style

We use:
- `black` for code formatting
- `isort` for import sorting
- `mypy` for type checking
- `ruff` for linting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type check
mypy src/

# Lint
ruff check src/ tests/
```

### Submitting Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and add tests

3. Run tests and linting:
   ```bash
   pytest
   black src/ tests/
   mypy src/
   ```

4. Commit your changes:
   ```bash
   git commit -m "Add your feature"
   ```

5. Push and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

### Guidelines

- Write tests for new features
- Update documentation for user-facing changes
- Follow existing code style
- Keep commits focused and atomic
- Write clear commit messages

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [libcst](https://github.com/Instagram/LibCST) for CST manipulation
- Uses [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing
- Inspired by the need for better documentation tooling
