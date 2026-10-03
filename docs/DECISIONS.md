# DECISIONS.md — Architecture & Design Decisions

This document tracks all formal decisions for the Issue Triage Agent project.
Any changes to choices or configurations in `docs/SOURCE_OF_TRUTH.md` must be recorded here first.

---

## 2026-10-03: Initial Project Setup (Stage 0)

### D-001: Initial Repository & Python Version Setup
- **Decision**: Target Python 3.12 (specifically 3.12.1 detected in runtime environment).
- **Why**: Standard supported modern Python version matching Section 12 requirements (Python 3.11+).

### D-002: LLM Provider Choice (Open Decision O1)
- **Decision**: Use Groq API with `llama-3.3-70b-versatile` (or `llama-3.1-70b-versatile`) for LLM steps, configured via `GROQ_API_KEY`.
- **Why**: User provided Groq API key and specified using Groq for agentic AI steps. Stated training cutoff is late 2023, and model supports structured outputs with high inference speed.

### D-003: Database / Checkpointer Storage
- **Decision**: Support PostgreSQL (via Docker) alongside SQLite, default to PostgreSQL / SQLite as per user preference ("for database you can use postgres ( docker is installed docker desktop)").
- **Why**: User specifically requested PostgreSQL with Docker for the agent persistence/database.

### D-004: Benchmark Data Source
- **Decision**: Download benchmark datasets from the official NLBSE'24 competition repository: `https://raw.githubusercontent.com/nlbse2024/issue-report-classification/main/data/` (or equivalent mirrored paths for train and test splits).
- **Why**: Section 4.1 specifies NLBSE'24 competition benchmark dataset with 3,000 issues across 5 repos.

### D-005: Stable Issue ID Generation Including `created_at`
- **Decision**: `generate_issue_id` includes `created_at` when available: stable hash of `(repo, title, body, created_at)`.
- **Why**: In `issues_train.csv`, rows 900 and 901 (`bitcoin/bitcoin`) share identical title (`#F`) and body (`#`) but have distinct creation timestamps (`2023-09-10 04:57:29` and `2023-09-10 04:51:31`). Including `created_at` ensures 100% unique, collision-free identifiers for all 1,500 benchmark issues and guarantees zero overlap between train and val splits.

