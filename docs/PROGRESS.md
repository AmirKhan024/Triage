# PROGRESS.md — Project Stage Tracker

This document tracks progress across all build stages defined in `docs/SOURCE_OF_TRUTH.md` (Section 15).
Rule: Only work on the current active stage. Do not move to the next stage until the current stage's exit criteria are fully satisfied.

---

## Current Active Stage: Stage 2 (Rules and routing)

---

## Stages Overview

### [COMPLETED] Stage 0: Setup and data
- [x] Repository initialized and Git remote configured.
- [x] `docs/SOURCE_OF_TRUTH.md`, `docs/DECISIONS.md`, and `docs/PROGRESS.md` created.
- [x] Dependencies installed and pinned for Stage 0 (`pandas==3.0.6`).
- [x] `scripts/download_data.py` created and run to download NLBSE'24 benchmark dataset into `data/`.
- [x] `scripts/make_splits.py` created to add stable `issue_id` and create stratified `train` (80%) / `val` (20%) split from the training dataset.
- [x] `results/data_report.json` generated documenting counts per repository and class.
- [x] **Exit criteria**: Section 4.2 D5 confirmed or corrected via data report (confirmed 100% matching).

### [COMPLETED] Stage 1: Classifier (M1)
- [x] Install and pin ML & lint/test dependencies: `scikit-learn==1.9.1`, `pytest==9.1.1`, `ruff==0.16.10`.
- [x] Preprocessing module implemented and unit tested (`tests/test_preprocess.py`).
- [x] M1 (TF-IDF + LogisticRegression) trained on `train` split only (`models/classifier.joblib`).
- [x] Scored on test set (E1) with bootstrap confidence intervals, compared against 0.8270 baseline and 0.8934 published result (`results/e1_results.json`).
- [x] Before scoring, updated `results/data_report.json` with official test counts and train-test duplicate row overlap count (3 rows).
- [x] **Exit criteria**: Results table in Section 10.3 of `docs/SOURCE_OF_TRUTH.md` updated with per-repository and average F1 scores next to published numbers; preprocessing unit tests pass.

### [PENDING] Stage 2: Rules and routing
- [ ] Install Pydantic.
- [ ] Completeness checks (C1-C4), hard rules (H1, H2), and routing logic (A, B, C).
- [ ] Confidence calibration check (E2).
- [ ] Hand-labelled completeness evaluated (E6).
- [ ] **Exit criteria**: Every issue in `val` gets a route; unit tests pass.

### [PENDING] Stage 3: Workflow and human approval (LangGraph)
- [ ] Embeddings & vector search index built only on `train` issues.
- [ ] LangGraph state, nodes, and interrupt mechanism implemented with database checkpointer (PostgreSQL / SQLite).
- [ ] Human review interface (CLI / API).
- [ ] **Exit criteria**: 20 `val` issues run end-to-end; persistence and resumption verified.

### [PENDING] Stage 4: Benchmark evaluation
- [ ] Run benchmark evaluation experiments (E3, E4, E5, E7a, E7b, E7c, E10).
- [ ] Generate `docs/EVAL_REPORT.md` with numbers sourced strictly from `results/*.json`.
- [ ] **Exit criteria**: Milestone 1 achieved.

### [PENDING] Stage 5: Fresh-set replay
- [ ] Fetch fresh issues from active GitHub repositories after model cutoff.
- [ ] Run replay in `ACTION_MODE=log` and measure maintainer agreement.
- [ ] **Exit criteria**: Milestone 2 achieved.

### [PENDING] Stage 6: Depth
- [ ] Cross-repository evaluation (E8) and stronger model comparison (E9).

### [PENDING] Stage 7: Live demo
- [ ] FastAPI webhook handler, Streamlit review interface, GitHub action adapter.

### [PENDING] Stage 8: Packaging & Docker
- [ ] Docker container setup with Docker Compose (PostgreSQL + App), GitHub Actions CI.
