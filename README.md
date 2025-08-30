# Kontxt

![PyPI](https://img.shields.io/pypi/v/kontxt?color=blue)
![Python](https://img.shields.io/pypi/pyversions/kontxt)
![License](https://img.shields.io/github/license/raiselab-ai/kontxt)
![Tests](https://img.shields.io/github/actions/workflow/status/raiselab-ai/kontxt/ci.yml?label=tests)
![Coverage](https://img.shields.io/codecov/c/github/raiselab-ai/kontxt)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)
![Status](https://img.shields.io/badge/status-early%20alpha-orange)

---

**Kontxt** is an **early alpha** Python library focused exclusively on **context management for AI applications**.  

Most existing solutions (LangChain, LlamaIndex, etc.) tie memory and context handling to heavy orchestration frameworks. Kontxt aims to fill the gap by providing a **lightweight, framework-agnostic layer** dedicated to managing:

- 🗂 **Prompt registries** — versioned, declarative system and role prompts  
- 🧠 **Context stores** — structured conversation history (threads, episodes, turns, artifacts)  
- 💾 **Memory managers** — short-term & long-term memory with TTL, tags, and scopes  
- ✍️ **Summarizers** — configurable strategies (rolling, hierarchical, focus-conditioned)  
- 🛡 **Policies** — redaction, safety filters, and customizable ingest/render hooks  

In short: **Kontxt is the context brain for AI apps** — portable, observable, and deterministic.

---

## 🚧 Status

- Version: `0.1.0`  
- Maturity: **Early Alpha** — expect rapid iteration and breaking changes  
- Not production-ready yet

---

## 🌐 Project Links

- 📦 [PyPI (placeholder)](https://pypi.org/project/kontxt/)  
- 🏠 [GitHub Repository](https://github.com/raiselab-ai/kontxt)  
- 📖 Documentation (coming soon)  

---

## 🤝 Contributing

Contributions, ideas, and feedback are welcome!  
Please open an [issue](https://github.com/raiselab-ai/kontxt/issues) or submit a PR.  

---

## 📜 License

Licensed under the **Apache 2.0** License – see [LICENSE](LICENSE) for details.
