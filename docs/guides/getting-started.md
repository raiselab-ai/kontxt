# Getting Started

This short guide walks through installing kontxt, composing a prompt, and
integrating scratchpad memory.

## Installation

kontxt uses [uv](https://docs.astral.sh/uv/) for package management, but any
modern Python environment works:

```bash
uv sync
uv run python -m pip install -e .
```

To pull in optional development tooling:

```bash
uv run python -m pip install -e '.[dev]'
```

## Compose Your First Context

```python
from kontxt import Context

ctx = Context()
ctx.add("system", "You are a support assistant.")
ctx.add("instructions", "Answer with concise explanations.")
ctx.add("messages", {"role": "user", "content": "How do I reset my password?"})

print(ctx.render())
```

## Add Memory

```python
from kontxt import Memory

memory = Memory()
memory.store("faq:password", "Reset via the account settings page.", meta={"category": "faq"})
memory.scratchpad.write("plan", ["Greet user", "Explain reset steps", "Offer help"])

related = memory.retrieve("reset", filters={"category": "faq"})
plan = memory.scratchpad.read("plan")
```

## Next Steps

- Explore the richer examples in `examples/`.
- Review the design document in the repository root for guiding principles.
- Contribute improvements by following the [contributing guide](../../CONTRIBUTING.md).


