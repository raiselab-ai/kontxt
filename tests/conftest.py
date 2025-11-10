"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from kontxt import Context, Memory


@pytest.fixture
def context() -> Context:
    ctx = Context()
    ctx.add("system", "You are a helpful assistant.")
    return ctx


@pytest.fixture
def memory() -> Memory:
    return Memory()


