from kontxt import MemoryManager

def test_memory_put_get():
    mem = MemoryManager()
    mem.put("A", scope="episode", tags=["x"], thread_id="t", episode_id="e")
    assert mem.get(scope="episode", tags=["x"])
