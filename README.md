# kontxt

**Context engineering for production AI systems**

Most AI projects fail not because of bad models, but because of bad context. kontxt solves this.

## The Problem

**85% of AI projects fail to deliver on their promises** (Gartner). The root cause isn't model quality—it's context engineering:

- ❌ **Context overload** - Passing too much irrelevant data → hallucinations, high costs
- ❌ **Missing context** - Omitting critical information → poor decisions
- ❌ **No memory** - Long conversations overflow context windows → agent amnesia
- ❌ **Poor formatting** - Unstructured data → model confusion
- ❌ **No observability** - Can't debug production failures

> *"Context engineering is the new skill in AI. It is about providing the right information and tools, in the right format, at the right time."* — Philipp Schmid

## The Solution

**kontxt** is a lightweight library that gives you production-grade context control:

- 🎯 **Budget control** - Set token limits, auto-trim intelligently
- 🧠 **Memory primitives** - Scratchpads, vector stores, persistence
- 🔄 **Multi-phase flows** - Coordinate complex agent workflows
- 📊 **Token observability** - Track usage, debug context issues
- 🔌 **Vendor-agnostic** - Works with OpenAI, Anthropic, Gemini, or any LLM
- 🔒 **Type-safe** - Full type hints, IDE autocomplete, zero magic

## Key Features

- **Context composition** with ordered sections, lazy evaluation, and multiple render formats (OpenAI, Anthropic, Gemini)
- **Memory primitives** including scratchpads, vector stores, and configurable backends
- **Phase templates** for multi-stage flows with transition validation
- **Token budgeting** with automatic trimming and priority management
- **State management** for session tracking and workflow coordination
- **Production-ready** with comprehensive tests and typed APIs

## Installation

> **⚠️ Alpha Release**: This is an alpha version (0.1.0a1) for early testing. APIs may change before the stable 0.1.0 release.

```bash
pip install kontxt
```

Or install from source:

```bash
uv pip install -e .
```

Development tooling:

```bash
uv pip install -e '.[dev]'
```

## Quick Start

```python
from kontxt import Context, SystemPrompt

context = Context()

# Type-safe section references (recommended)
context.add(SystemPrompt, "You are a dental triage assistant.")

# Or use strings (also works)
context.add("instructions", "Answer using the provided chart.")
context.add("patient", {"name": "Alex", "age": 41})
context.add("messages", {"role": "user", "content": "My tooth aches."})

prompt = context.render()
# -> XML-style prompt that preserves section boundaries
```

### Memory Integration

```python
from kontxt import Memory

memory = Memory()
memory.store("patient:123", {"allergy": "penicillin"}, meta={"patient_id": "123"})
memory.scratchpad.write("plan", ["Collect symptoms", "Check red flags"])

plan = memory.scratchpad.read("plan")
allergies = memory.retrieve("penicillin", filters={"patient_id": "123"})
```

### Gemini Integration

```python
from kontxt import Context, Memory, SystemPrompt, Format

# Create context with memory
memory = Memory()
ctx = Context(memory=memory)

# Type-safe section references
ctx.add(SystemPrompt, "You are a helpful AI assistant")

# Convenient helper for user messages
ctx.add_user_message("Explain quantum computing")

# Render for Gemini
payload = ctx.render(
    format=Format.GEMINI,  # Type-safe enum with IDE autocomplete
    generation_config={"temperature": 0.7}
)

# Call Gemini API (you control the API call)
from google import genai
client = genai.Client(api_key="...")
response = client.models.generate_content(model="gemini-2.0-flash-exp", **payload)

# Add response back to context
ctx.add_response(response.text)
```

### Multi-Phase Workflows with State

```python
from enum import Enum
from kontxt import Context, State, SystemPrompt, ChatMessages, Format

# Define workflow phases
class Phases(str, Enum):
    INTAKE = "intake"
    ASSESSMENT = "assessment"
    COMPLETE = "complete"

# Initialize state with phase validation
state = State(
    initial={"session": {"phase": "intake"}},
    phases=Phases  # Validates phase values at runtime
)

# Initialize context with state
ctx = Context(state=state)
ctx.add(SystemPrompt, "You are a medical triage assistant")

# Configure phases with type-safe section references
ctx.phase(Phases.INTAKE).configure(
    instructions="Gather patient information",
    includes=[SystemPrompt, ChatMessages],  # Type-safe!
    transitions_to=["assessment"],  # Only assessment allowed from intake
    max_history=10
)

ctx.phase(Phases.ASSESSMENT).configure(
    instructions="Assess patient condition",
    includes=[SystemPrompt, ChatMessages],
    transitions_to=["complete"],
    max_history=5
)

# Use in workflow
ctx.add_user_message("I have a headache")
payload = ctx.render(phase=state.phase(), format=Format.GEMINI)

# ... call LLM, get response ...

ctx.add_response(response.text)

# Advance phase with validation
ctx.advance_phase(Phases.ASSESSMENT)  # ✅ Validates transition is allowed
```

### Import Patterns

```python
# ✅ Recommended: Import from kontxt
from kontxt import Context, Memory, State, Format, SystemPrompt, ChatMessages

# ✅ Or explicit from types (for organization)
from kontxt import Context, Memory, State
from kontxt.types import Format, SystemPrompt, ChatMessages
```

### Available Render Formats

```python
Format.TEXT       # Plain text with XML-like tags
Format.OPENAI     # OpenAI chat completion format
Format.ANTHROPIC  # Anthropic messages API format
Format.GEMINI     # Google Gemini API format
```

### Built-in Section Types

```python
from kontxt import SystemPrompt, ChatMessages, Instructions, Tools

# Use for type safety and IDE autocomplete
ctx.add(SystemPrompt, "You are helpful")
ctx.add(ChatMessages, {"role": "user", "content": "Hello"})

# Or create custom section types
from kontxt import SectionType
PatientData = SectionType("patient")
ctx.add(PatientData, {"name": "John", "age": 30})
```

See [`examples/`](examples/) for complete examples:
- [`simple_rag.py`](examples/simple_rag.py) - Basic RAG workflow
- [`multi_phase_workflow.py`](examples/multi_phase_workflow.py) - Multi-phase workflow with state management

## Why kontxt vs LangChain/LlamaIndex?

**Most frameworks abstract the wrong things.**

They abstract the LLM (doesn't matter—all models work similarly).
They don't abstract context (matters most—it's complex and error-prone).

**kontxt inverts this:**
- ✅ LLM is your responsibility (use any vendor, local models, whatever)
- ✅ Context is our responsibility (we make it production-grade)

| Feature | kontxt | LangChain | LlamaIndex |
|---------|--------|-----------|------------|
| **Learning curve** | 5 minutes | Hours | Hours |
| **Dependencies** | 2 (pydantic, tiktoken) | 20+ | 15+ |
| **Token budgets** | ✅ Built-in | ❌ Manual | ❌ Manual |
| **Multi-phase flows** | ✅ Native | ⚠️ Custom | ⚠️ Custom |
| **Memory operations** | ✅ 4 primitives | ⚠️ Complex | ⚠️ Complex |
| **Vendor lock-in** | ❌ None | ⚠️ High | ⚠️ High |
| **Type safety** | ✅ Full | ⚠️ Partial | ⚠️ Partial |

**TL;DR:** We do one thing (context engineering) and do it perfectly. They try to do everything, and context becomes an afterthought.

## Built for Production

kontxt is built on research-backed context engineering principles:

### The Four Operations (Lance Martin, 2025)

1. **WRITE** - Externalize context beyond the window
2. **SELECT** - Retrieve relevant context intelligently
3. **COMPRESS** - Reduce tokens while preserving signal
4. **ISOLATE** - Partition context for clarity

```python
mem.scratchpad.write("plan", data)           # WRITE
notes = mem.retrieve("plan", filters={...})  # SELECT
ctx.set_budget(max_tokens=4000, priority=[]) # COMPRESS
sub = ctx.fork(include=["system"])           # ISOLATE
```

### Why This Matters

Research shows:
- **Context position matters**: LLMs exhibit attention bias—details in the middle get lost
- **More ≠ better**: A model given 46 tools fails; given 19 tools succeeds (same context window)
- **Format matters**: How you structure data affects model performance as much as what data you include

kontxt handles these nuances so you don't have to.

## Who This Is For

Choose kontxt if you're building:
- 🏥 **Multi-phase agents** (medical triage, customer support, legal analysis)
- 💬 **Long conversations** (therapy bots, tutoring, extended troubleshooting)
- 💰 **Cost-sensitive systems** (token budgets matter, can't blow $500 on one session)
- 🔍 **Observable AI** (need to debug why agents fail in production)
- 🔌 **Vendor-agnostic apps** (might switch from GPT-4 to Claude to Gemini)

**If your AI needs to work in production, not just demos, use kontxt.**

## Documentation

Documentation scaffolding lives under `docs/`. We plan to publish the first
version once the API stabilises. Contributions are welcome—open an issue if you
spot gaps or inconsistencies.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

See [CONTRIBUTING](CONTRIBUTING.md) for detailed guidance.

## Roadmap

- Additional storage backends (Qdrant, Pinecone, etc.)
- Built-in compression helpers powered by user-supplied LLMs
- Observability hooks for prompt debugging and token telemetry
- Async APIs once ergonomics questions are resolved

## License

Licensed under the Apache 2.0 License. See [LICENSE](LICENSE) for details.
