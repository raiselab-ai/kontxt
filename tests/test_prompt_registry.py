from kontxt import PromptRegistry

def test_registry_render():
    reg = PromptRegistry.from_yaml("name: t\nversion: 1.0\nrole: system\ntemplate: Hi {{x}}\n")
    out = reg.render("t@1.0", ctx=None, vars={"x":"there"})
    assert out[0]["content"].startswith("Hi")
