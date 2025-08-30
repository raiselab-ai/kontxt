from kontxt import MemoryManager

mem = MemoryManager()
mem.put("User likes bikes", scope="user", tags=["profile"], thread_id="u-1", episode_id=None, ttl_seconds=3600)
print([r.text for r in mem.get(scope="user", tags=["profile"])])
