# CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration and deployment.

## Workflows

### `ci.yml` - Continuous Integration

Runs on every push and pull request to `main` and `dev` branches.

**Jobs:**
1. **Test** - Runs on Python 3.11 and 3.12
   - Linting with `ruff`
   - Type checking with `mypy`
   - Tests with `pytest` and coverage
   - Uploads coverage to Codecov

2. **Build** - Builds the package
   - Creates distribution files
   - Validates package metadata with `twine`
   - Uploads artifacts

### `publish.yml` - Publish to PyPI

Publishes the package to PyPI automatically or manually.

**Triggers:**
- **Automatic**: When a GitHub Release is published
- **Manual**: Via workflow dispatch (allows choosing Test PyPI or PyPI)

**Requirements:**

1. **Configure Trusted Publishing** (recommended, no tokens needed):
   - Go to [PyPI Trusted Publishers](https://pypi.org/manage/account/publishing/)
   - Add a new publisher:
     - Owner: `raise-lab`
     - Repository: `kontxt`
     - Workflow: `publish.yml`
     - Environment: `pypi`
   - Repeat for [Test PyPI](https://test.pypi.org/manage/account/publishing/) with environment: `testpypi`

2. **OR use API tokens** (alternative):
   - Create PyPI API token at https://pypi.org/manage/account/token/
   - Add as GitHub secret: `PYPI_API_TOKEN`
   - Create Test PyPI token at https://test.pypi.org/manage/account/token/
   - Add as GitHub secret: `TEST_PYPI_API_TOKEN`

## Publishing Workflow

### Automatic (recommended for releases)

1. Create a new release on GitHub:
   ```bash
   git tag v0.1.0a1
   git push origin v0.1.0a1
   ```
2. Go to GitHub Releases → Create a new release
3. Select the tag `v0.1.0a1`
4. Publish the release
5. The workflow will automatically publish to PyPI

### Manual (for testing)

1. Go to Actions → Publish to PyPI
2. Click "Run workflow"
3. Choose:
   - `testpypi` - Publish to Test PyPI first (recommended)
   - `pypi` - Publish to production PyPI
4. Test installation:
   ```bash
   # From Test PyPI
   pip install --index-url https://test.pypi.org/simple/ kontxt

   # From PyPI
   pip install kontxt
   ```

## Local Testing

Before pushing, run the same checks locally:

```bash
# Linting
uv run ruff check .

# Type checking
uv run mypy src/kontxt

# Tests with coverage
uv run pytest -v --cov=kontxt --cov-report=term-missing

# Build package
uv build

# Check package
uv run twine check dist/*
```

## Troubleshooting

**Build fails on `uv build`:**
- Check `pyproject.toml` is valid
- Ensure version is updated in `pyproject.toml`

**Publish fails with authentication error:**
- Verify Trusted Publishing is configured correctly
- Or check API tokens are set in GitHub secrets

**Tests fail on specific Python version:**
- Test locally with that Python version
- Use `uv python install 3.12` to install specific version
