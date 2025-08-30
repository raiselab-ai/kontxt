from kontxt import Context, MemoryManager

def test_context_window():
    ctx = Context("t1","e1", memories=MemoryManager(), policies=None)
    ctx.add_user("hello")
    ctx.add_user("world")
    win = ctx.build_window(100)
    assert len(win.messages()) >= 2
