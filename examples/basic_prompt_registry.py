from kontxt import PromptRegistry

yaml_text = """
name: helper
version: 1.0
role: system
template: |
  You are {{brand}}'s assistant. Be concise.
guards:
  max_chars: 2000
"""
reg = PromptRegistry.from_yaml(yaml_text)
print(reg.render("helper@1.0", ctx=None, vars={"brand":"RAISE Lab"}))
