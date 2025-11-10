from __future__ import annotations

from kontxt import Cache, Memory, Scratchpad


def test_memory_store_and_retrieve(memory: Memory) -> None:
    memory.store("patient:123", {"allergy": "penicillin"}, meta={"patient_id": "123"})
    result = memory.retrieve("penicillin", filters={"patient_id": "123"})

    assert result and result[0]["allergy"] == "penicillin"
    assert memory.get("patient:123")["allergy"] == "penicillin"


def test_scratchpad_round_trip(memory: Memory) -> None:
    memory.scratchpad.write("plan", ["step-1", "step-2"])
    assert memory.scratchpad.read("plan") == ["step-1", "step-2"]
    memory.scratchpad.delete("plan")
    assert memory.scratchpad.read("plan") is None


def test_cache_similarity() -> None:
    cache = Cache()
    cache.set("triage", query="tooth pain", value="cached-plan")
    assert cache.get("triage", query="tooth pain?") == "cached-plan"
    assert cache.get("triage", query="sore throat") is None


