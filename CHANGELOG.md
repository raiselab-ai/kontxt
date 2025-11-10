# Changelog

All notable changes to kontxt will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0a1] - 2025-01-10

### Added (Alpha Release)

#### Core Features
- **Context**: Composable context management with ordered sections
  - Support for lazy callables in sections
  - Multiple render formats (text, openai, anthropic, gemini)
  - `add_response()` helper method for LLM response integration
  - Token counting and budget management
  - Output schema support via Pydantic models

- **Memory**: Memory primitives for data outside context window
  - Scratchpad for ephemeral key-value storage
  - Vector store with similarity search
  - Pluggable backends (in-memory, filesystem)
  - Cache utilities for semantic deduplication

- **State**: Session state management
  - JSON-path access to nested state
  - Phase tracking with transition validation
  - Immutable snapshots for debugging

- **Phases**: Multi-step workflow coordination
  - Phase templates with scoped instructions
  - Section inclusion rules
  - Memory integration via `memory_includes`
  - `max_history` for conversation trimming
  - Callable instructions for dynamic prompts
  - Transition validation

#### Render Formats
- **Format.TEXT**: Plain text with XML-like section tags
- **Format.OPENAI**: OpenAI chat completion API format
- **Format.ANTHROPIC**: Anthropic messages API format
- **Format.GEMINI**: Google Gemini API format with `generation_config` support

#### Type Safety
- `Format` enum for type-safe render format selection
- Full type hints across the API
- Support for both `Format.GEMINI` and `"gemini"` string formats
- Dual import patterns (explicit and convenience)

#### Examples
- `simple_rag.py`: Basic RAG workflow demonstrating core features

#### Developer Experience
- Comprehensive test suite (23 tests passing)
- Type-safe APIs with full IDE autocomplete
- Detailed documentation and examples
- Production-ready packaging with Hatch build backend

[0.1.0a1]: https://github.com/raise-lab/kontxt/releases/tag/v0.1.0a1


