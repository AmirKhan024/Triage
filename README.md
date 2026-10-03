# Issue Triage Agent

A system that automates the first pass of triage on new GitHub issues using a hybrid architecture:
1. Fast ML classification (`bug`, `feature`, `question`)
2. Deterministic rules layer (completeness, security/sensitive escalation, body validation)
3. Agentic LangGraph workflow with retrieval of similar issues, LLM analysis, draft response generation, and human-in-the-loop approval
4. Action execution and comprehensive benchmarking

## Documentation
- [docs/SOURCE_OF_TRUTH.md](docs/SOURCE_OF_TRUTH.md) — Single source of truth for architecture, constraints, and experiments
- [docs/PROGRESS.md](docs/PROGRESS.md) — Stage-by-stage implementation tracker
- [docs/DECISIONS.md](docs/DECISIONS.md) — Architectural and design decision records
