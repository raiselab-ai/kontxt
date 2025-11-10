# Contributing to kontxt

Thanks for your interest in improving kontxt! This project is still in its
infancy, so every contribution helps shape the architecture and developer
experience. Please review the guidelines below before opening an issue or
pull request.

## Getting Started

1. **Install uv** if you have not already. See the
   [uv documentation](https://docs.astral.sh/uv/) for installation details.
2. **Clone the repository** and create an isolated environment:
   ```bash
   uv sync
   ```
3. **Run the test suite** to ensure the project is healthy:
   ```bash
   uv run pytest
   ```

## Development Workflow

- **Branching**: Use a descriptive feature branch (e.g. `feature/phases-api`).
- **Formatting & linting**: Run
  ```bash
  uv run ruff check .
  uv run mypy src
  ```
  before submitting. We aim for consistent type coverage.
- **Tests**: Add or update tests that cover your changes. Pull requests without
  tests may be asked to include them.
- **Documentation**: Update relevant documentation in `docs/` and the examples
  directory when you introduce new behaviour.

## Pull Requests

1. Fill in the PR template with a concise summary.
2. Explain design decisions and trade-offs.
3. Link related issues or design docs when available.
4. Be responsive to review feedback—collaboration is encouraged.

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/)
Code of Conduct. Harassment or discrimination of any kind is not tolerated.

## Questions?

Open a discussion or reach out via issues. We are excited to build a robust,
production-friendly context orchestration library together.


