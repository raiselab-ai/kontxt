from kontxt import Context, MemoryManager

mem = MemoryManager()
ctx = Context(thread_id="u-1", episode_id="e-1", memories=mem, policies=None)
ctx.add_user("Hello! My email is foo@bar.com")
win = ctx.build_window(budget_tokens=200)
print(win.messages())
