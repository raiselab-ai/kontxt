# Changelog

All notable changes to kontxt will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0a3] - 2025-01-12

### Added
- **State**: `current_phase` parameter for cleaner initialization
  - `State(current_phase="intake", phases=Phases)` instead of nested dict
  - Single source of truth for workflow phase
  - Supports both string and Enum values
- **Context**: `current_phase()` method to get phase from state
  - Returns current phase name or None if no state configured
  - Provides public API to check workflow state

### Changed
- **BREAKING**: `Context.render()` now automatically uses `state.phase()` when no phase specified
  - Old: `ctx.render(phase=state.phase())` required explicit phase
  - New: `ctx.render()` automatically uses current phase from state
  - Explicit phase parameter still supported to override
- **Context.token_count()** now respects current phase
  - `ctx.token_count()` uses current phase from state
  - `ctx.token_count(phase="other")` can override for specific phase
- **Context**: Enhanced phase validation
  - Errors immediately if state has phase but Context doesn't have it configured
  - Clear error messages with configuration hints

### Improved
- **Phase API**: Full Enum support for type-safe workflows
  - `transitions_to` parameter now accepts Enum values: `transitions_to=[Phases.ASSESSMENT]`
  - Enums are converted to strings internally for storage
  - Mixed Enum and string values supported: `transitions_to=[Phases.NEXT, "other"]`
  - Better IDE autocomplete and compile-time type checking
  - Fully backward compatible - strings still work everywhere

### Fixed
- State and Context phase synchronization is now automatic
  - No more manual phase passing between state and render
  - Workflow phase is single source of truth

### Developer Experience
- 30 tests passing (10 new tests for v0.1.0a3 features)
- Updated `multi_phase_workflow.py` example to demonstrate new API
- Cleaner, more intuitive workflow API with full Enum support

### Migration Guide
```python
# OLD API (v0.1.0a1-a2)
state = State(
    initial={"session": {"phase": "intake"}},
    phases=Phases
)
ctx = Context(state=state)
ctx.render(phase=state.phase())  # Must specify phase

# NEW API (v0.1.0a3)
state = State(current_phase="intake", phases=Phases)  # Cleaner!
ctx = Context(state=state)
ctx.render()  # Automatically uses current phase!
```

## [0.1.0a2] - 2025-01-12

### Fixed
- **Type checking**: Fixed all mypy type errors across the codebase
  - Fixed `deepcopy` type compatibility in `State.__init__()`
  - Fixed return type annotations in `BudgetManager.enforce()`
  - Fixed type assignments in `Context` methods
- **Linting**: Auto-fixed 18 ruff linting errors (unused imports, f-strings without placeholders)
- **CI Pipeline**: Added missing `twine` dependency and fixed build job configuration

### Changed
- **CI/CD**: Added `uv sync --all-extras` to build job to ensure dev dependencies are installed
- **Dependencies**: Added `twine>=5.0` to dev dependencies for package metadata validation

### Internal
- All 43 tests passing
- Clean mypy type checking (0 errors)
- Clean ruff linting (0 errors)
- Package builds successfully and passes twine validation

## [0.1.0a1] - 2025-01-10

### Added (Alpha Release)

#### Core Features
- **Context**: Composable context management with ordered sections
  - Support for lazy callables in sections
  - Multiple render formats (text, openai, anthropic, gemini)
  - `add_response()` helper method for LLM response integration
  - `add_user_message()` helper method for user messages
  - Token counting and budget management
  - Output schema support via Pydantic models
  - State integration for phase-aware rendering
  - `advance_phase()` method with transition validation

- **Memory**: Memory primitives for data outside context window
  - Scratchpad for ephemeral key-value storage
  - Vector store with similarity search
  - Pluggable backends (in-memory, filesystem)
  - Cache utilities for semantic deduplication

- **State**: Session state management
  - JSON-path access to nested state
  - Phase tracking with enum validation
  - `phases` parameter for runtime validation
  - Supports both Enum members and strings
  - Immutable snapshots for debugging

- **Phases**: Multi-step workflow coordination
  - Phase templates with scoped instructions
  - Section inclusion rules with `SectionType` support
  - Memory integration via `memory_includes`
  - `max_history` for conversation trimming
  - Callable instructions for dynamic prompts
  - `transitions_to` for workflow validation

#### Render Formats
- **Format.TEXT**: Plain text with XML-like section tags
- **Format.OPENAI**: OpenAI chat completion API format
- **Format.ANTHROPIC**: Anthropic messages API format
- **Format.GEMINI**: Google Gemini API format with `generation_config` support

#### Type Safety
- **SectionType**: Type-safe section identifiers
  - Built-in instances: `SystemPrompt`, `ChatMessages`, `Instructions`, `Tools`
  - Custom section types supported
  - Works with `Context.add()` and phase `includes`
  - IDE autocomplete and typo prevention
- **Format** enum for type-safe render format selection
- **Enum support** for phase definitions
- Full type hints across the API
- Support for both type-safe and string-based APIs (backward compatible)
- Dual import patterns (explicit and convenience)

#### Phase Transition Validation
- `Context.advance_phase()` validates transitions against `transitions_to` config
- `State` validates phase values against `phases` enum
- Dual-layer validation ensures workflow integrity
- Clear error messages for invalid transitions

#### Examples
- `simple_rag.py`: Basic RAG workflow demonstrating core features
- `multi_phase_workflow.py`: Multi-phase workflow with state management and type-safe API

#### Developer Experience
- Comprehensive test suite (43 tests passing)
- Type-safe APIs with full IDE autocomplete
- Detailed documentation and examples
- Production-ready packaging with Hatch build backend
- 100% backward compatible with string-based APIs

[0.1.0a3]: https://github.com/raise-lab/kontxt/releases/tag/v0.1.0a3
[0.1.0a2]: https://github.com/raise-lab/kontxt/releases/tag/v0.1.0a2
[0.1.0a1]: https://github.com/raise-lab/kontxt/releases/tag/v0.1.0a1


