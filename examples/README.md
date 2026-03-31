# Example Configuration Files

This directory contains example configuration files for the docstring-generator tool. These files demonstrate how to integrate the tool into your development workflow.

## Files

### 1. `docgen.toml`

The main configuration file for docstring-generator. Place this in your project root to customize tool behavior.

**Key settings:**
- `style`: Docstring format (google, numpy, sphinx)
- `provider`: LLM provider (anthropic, openai, ollama)
- `model`: Specific model to use
- `overwrite_existing`: Whether to replace existing docstrings
- `exclude.patterns`: Files/directories to skip

**Usage:**
```bash
# Copy to your project root
cp examples/docgen.toml ./docgen.toml

# Edit to match your preferences
vim docgen.toml

# Run docgen (it will automatically find docgen.toml)
docgen ./src
```

### 2. `.pre-commit-config.yaml`

Pre-commit hook configuration that automatically generates docstrings for staged files.

**Features:**
- Runs on every commit
- Only processes staged Python files
- Can be configured to enforce docstring coverage
- Integrates with other pre-commit hooks

**Usage:**
```bash
# Copy to your project root
cp examples/.pre-commit-config.yaml ./.pre-commit-config.yaml

# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# (Optional) Run on all files
pre-commit run --all-files
```

**Modes:**
- **Generate mode** (default): Adds missing docstrings automatically
- **Check mode** (commented out): Fails commit if docstrings are missing

### 3. `.github/workflows/docstring-check.yml`

GitHub Actions workflow that checks docstring coverage on pull requests.

**Features:**
- Runs on PRs that modify Python files
- Calculates and reports coverage percentage
- Posts coverage report as PR comment
- Enforces minimum coverage threshold (80% by default)
- Outputs GitHub Actions annotations for missing docstrings
- Uploads coverage reports as artifacts

**Usage:**
```bash
# Create workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy the workflow file
cp examples/.github/workflows/docstring-check.yml .github/workflows/

# Add your API key as a GitHub secret
# Go to: Settings > Secrets and variables > Actions > New repository secret
# Name: ANTHROPIC_API_KEY (or OPENAI_API_KEY)
# Value: your-api-key
```

**Customization:**
- Change `--min-coverage 80` to adjust the threshold
- Uncomment the `generate-docstrings` job to auto-generate docstrings
- Modify the PR comment format in the `actions/github-script` step

## Quick Start

To set up all three integrations:

```bash
# 1. Copy configuration files
cp examples/docgen.toml ./
cp examples/.pre-commit-config.yaml ./
mkdir -p .github/workflows
cp examples/.github/workflows/docstring-check.yml .github/workflows/

# 2. Install dependencies
pip install docstring-generator pre-commit

# 3. Set up pre-commit
pre-commit install

# 4. Configure API key (choose one)
export ANTHROPIC_API_KEY="your-key-here"
# or
export OPENAI_API_KEY="your-key-here"

# 5. Test locally
docgen ./src --dry-run

# 6. Add GitHub secret for CI/CD
# Go to repository Settings > Secrets > Actions
# Add ANTHROPIC_API_KEY or OPENAI_API_KEY
```

## Configuration Options Reference

### Docstring Styles

- **google**: Google-style docstrings (default)
  ```python
  def example(arg1: int, arg2: str) -> bool:
      """Short description.
      
      Args:
          arg1: Description of arg1
          arg2: Description of arg2
          
      Returns:
          Description of return value
      """
  ```

- **numpy**: NumPy-style docstrings
  ```python
  def example(arg1: int, arg2: str) -> bool:
      """
      Short description.
      
      Parameters
      ----------
      arg1 : int
          Description of arg1
      arg2 : str
          Description of arg2
          
      Returns
      -------
      bool
          Description of return value
      """
  ```

- **sphinx**: Sphinx-style docstrings
  ```python
  def example(arg1: int, arg2: str) -> bool:
      """
      Short description.
      
      :param arg1: Description of arg1
      :type arg1: int
      :param arg2: Description of arg2
      :type arg2: str
      :return: Description of return value
      :rtype: bool
      """
  ```

### LLM Providers

- **anthropic**: Claude models (requires ANTHROPIC_API_KEY)
  - Recommended: `claude-3-5-sonnet-20241022`
  - Alternative: `claude-3-opus-20240229`

- **openai**: GPT models (requires OPENAI_API_KEY)
  - Recommended: `gpt-4-turbo`
  - Alternatives: `gpt-4`, `gpt-3.5-turbo`

- **ollama**: Local models (no API key needed)
  - Examples: `llama2`, `codellama`, `mistral`
  - Requires Ollama running locally

## Troubleshooting

### Pre-commit hook is slow
- Use `--only-missing` to skip functions that already have docstrings
- Reduce the number of files by adding exclusion patterns

### GitHub Actions workflow fails
- Verify API key is set as a repository secret
- Check that the secret name matches the workflow (ANTHROPIC_API_KEY or OPENAI_API_KEY)
- Ensure the workflow has permissions to comment on PRs

### Coverage is lower than expected
- Check exclusion patterns in `docgen.toml`
- Verify that existing docstrings are properly formatted
- Use `docgen . --report` to see which functions are missing docstrings

## Further Reading

- [Main README](../README.md) - Full documentation
- [Requirements](../.kiro/specs/docstring-generator/requirements.md) - Feature requirements
- [Design Document](../.kiro/specs/docstring-generator/design.md) - Architecture details
