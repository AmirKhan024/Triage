# SOURCE_OF_TRUTH.md — Issue Triage Agent

Version 2. Working name: **Issue Triage Agent** (repo: `issue-triage-agent`). The name can change; nothing else in this document depends on it.

---

## 0. How to use this document

1. This file is the single source of truth. If code and this file disagree, one of them is wrong and must be fixed the same day.
2. Any change to a decision here is first written in `docs/DECISIONS.md` (date, what changed, why), then applied here.
3. Numbers marked **TBD** are measured, never guessed. Starting values marked **(initial)** are placeholders that a later stage replaces with measured values.
4. No stage starts until the previous stage meets its exit criteria (section 15).
5. Anything in "Non-goals" (section 2.2) is not built, even if it looks easy.

---

## 1. Summary

A system that does the first pass of triage on new GitHub issues.

For every new issue it:

1. predicts the type (`bug`, `feature`, `question`) with a trained ML classifier,
2. checks the issue against deterministic rules (is it complete, is it sensitive),
3. either labels it automatically (confident and complete) or sends it to a LangGraph workflow that looks up similar past issues and drafts a label and reply,
4. pauses for a human to approve, edit or reject anything the workflow drafted,
5. applies the approved action on GitHub,
6. records everything so the whole pipeline can be measured against known labels.

The project has three parts:

- **Benchmark system** (Stages 0–4): runs on a public labelled benchmark and produces an evaluation report. This alone is a complete project that can be shown.
- **Fresh-set replay** (Stage 5): the same pipeline run, without posting anything, on recent real issues from active public repositories, scored against what the maintainers actually did. This is what makes the results credible.
- **Live demo** (Stages 7–8): the pipeline connected to a demo repository through a webhook, with a review page. It demonstrates that the human approval step works. It is not a source of reported results.

---

## 2. Goals and non-goals

### 2.1 Goals

- G1. A classifier whose score is compared with the published baseline and the strongest published result on the same test set.
- G2. A deterministic rules layer that is unit-tested and never calls an LLM.
- G3. A LangGraph workflow with persistent state and a real human approval step.
- G4. An evaluation report that answers the questions in section 10 with measured numbers and confidence intervals.
- G5. Results on fresh, unbalanced, real issues that the LLM cannot have seen in training.
- G6. A minimal live demo on a demo repository.

### 2.2 Non-goals

| Not built | Reason |
|---|---|
| Priority or severity prediction | No priority labels exist to train or test on. |
| Duplicate detection as a feature | No labelled duplicate pairs in the benchmark. Maintainer duplicate marks are recorded in the fresh set for a possible later extension only. |
| Closing issues automatically | Too risky for an unattended action. |
| Writing code fixes or opening pull requests | A different project. |
| Multi-user accounts, billing, multi-tenant hosting | One maintainer, one allowlist of repositories. |
| Kafka, Kubernetes, microservices | One process and one container are enough. |
| Fine-tuning an LLM | The ML work is the classifier. |
| Non-English issues | The benchmark is English. |
| Posting anything to repositories you do not own | Replay is read-only. |

---

## 3. The final product

### 3.1 What a maintainer experiences (live demo)

1. Someone opens an issue on the connected repository.
2. One of three things happens:
   - **Auto path:** the issue gets a type label (`bug`, `enhancement` or `question`). Nothing else.
   - **Review path:** the issue appears in the review page with a proposed label, a drafted reply, the similar issues found, and the reasons. The maintainer clicks Approve, Edit or Reject. On approval the label and reply are posted.
   - **Escalation path:** the issue gets the `needs-triage` label and appears in the review page with no drafted reply (used for sensitive issues).
3. A metrics page shows counts per path and per decision. These counts are for demonstration only.

### 3.2 What exists at the end

| Piece | What it is |
|---|---|
| Pipeline package | Classifier, rules, workflow, actions. Runs in three modes: benchmark evaluation, fresh-set replay, live. |
| Evaluation report | `docs/EVAL_REPORT.md` with every experiment in section 10. |
| API service | FastAPI app. Receives GitHub webhooks, runs the pipeline, serves the review endpoints. |
| Review page | Streamlit app. Review queue and metrics page. |
| Database | SQLite file (triage records, reviews, action log, LangGraph checkpoints). |
| Container | One Docker image running the API and the review page. |
| GitHub side | A demo repository you own, a webhook for `issues` events, and a token limited to that repository. |

### 3.3 What a visitor to the repository sees

- README with the architecture diagram, the results table with confidence intervals, and a short demo recording.
- The evaluation report, including the results that did not go the project's way.
- A link to the demo repository.

---

## 4. Data

### 4.1 Benchmark dataset

| Item | Value |
|---|---|
| Source | NLBSE'24 Tool Competition on Issue Report Classification |
| URL | https://github.com/nlbse2024/issue-report-classification (archived, read-only, data still available in `data/`) |
| Size | 3,000 issue reports |
| Projects | facebook/react, tensorflow/tensorflow, microsoft/vscode, bitcoin/bitcoin, opencv/opencv |
| Fields | repository, label, title, body |
| Labels | `bug`, `feature`, `question` (issues with multiple labels were excluded by the dataset authors) |
| Split | Training set 1,500, test set 1,500, both balanced across the three classes |
| Published baseline | SetFit, one classifier per repository, average F1 **0.8270** |
| Strongest published result found | AdaptIRC (adapter-based transformer, competition entry), overall F1 **0.8934** (https://wrap.warwick.ac.uk/id/eprint/187927) |

Baseline F1 by repository: react 0.8718, tensorflow 0.8644, vscode 0.8262, opencv 0.8173, bitcoin 0.7555. By class overall: bug 0.8426, feature 0.8558, question 0.7827.

Both reference numbers are always shown together. Stage 1 also checks the competition report for any higher result and records it here.

### 4.2 Data rules

- D1. The CSV files are downloaded by `scripts/download_data.py` into `data/` and are not committed. Check the dataset's LICENSE file before redistributing anything.
- D2. The dataset has no issue id. Stage 0 creates `issue_id` as a stable hash of (repository, title, body, created_at) to avoid collision on duplicate-body issues (D-005).
- D3. **The test set is never used to choose anything.** The official training set is split once into `train` (80%) and `val` (20%), stratified by repository and label, with a fixed seed. Thresholds, prompts and model choices are tuned on `val`. The test set is used only to report results.
- D4. The similar-issue index used during benchmark evaluation contains **only `train` issues**. Test and `val` issues are never indexed, because indexed issues carry their labels.
- D5. Stage 0 verifies and records the real counts per repository and per class. Expected: 300 per repository and 100 per class per repository in each official split. If the real counts differ, this section is corrected.

### 4.3 Hand-labelled completeness set

100 bug issues from `val` are hand-labelled for four yes/no fields (section 7.1). The dataset has no completeness labels, so this is needed to measure the rules (E6) and the agent's choice of action (E7b). Stored in `data/completeness_gold.csv`. This is the only manual labelling in the project.

### 4.4 Fresh set (Stage 5)

Purpose: test on real issues that are unbalanced, recent, and created after the chosen LLM's training cutoff.

| Item | Decision |
|---|---|
| Source | GitHub REST API, read-only. |
| Issues | Closed issues created on or after `FRESH_SINCE`. Pull requests are filtered out (the issues endpoint returns them too). |
| `FRESH_SINCE` | A date after the stated training cutoff of the LLM chosen in O1. Recorded in `DECISIONS.md`. |
| Repositories | Start with 2 or 3 of the five benchmark repositories whose labels map cleanly. A repository whose labels cannot be mapped cleanly is dropped and the reason logged. |
| Label map | Hand-written per repository in `config/label_maps.yaml`: which maintainer labels mean bug, feature, question, needs more information, duplicate. |
| Type ground truth | The mapped type label. Issues with no type label or more than one are excluded and counted in the report. |
| Action ground truth | `needs_info` = a maintainer applied a "needs more information" style label at any point (read from the issue's label events). `duplicate` = a maintainer marked it as a duplicate (recorded only). |
| Size | Target about 2,000 issues. Minimum 500 across at least 2 repositories. |
| Class balance | Left as it is. Not rebalanced. |
| Index for retrieval | Labelled issues from the same repository created before `FRESH_SINCE`, up to 2,000 per repository. |
| Classifier | The model trained on the benchmark `train` split. It is not retrained on fresh data. |

Rules:

- F1. Nothing is ever posted to these repositories. Replay runs with `ACTION_MODE=log`, and the allowlist (S2) blocks any other mode.
- F2. The label map is written before looking at any pipeline output on the fresh set.
- F3. If reading label events proves too slow or unreliable, fall back to the labels currently on the issue and state that limit in the report.

### 4.5 Live demo data

The demo repository's index holds a small set of issues you file yourself. Benchmark text is not re-posted unless rule S6 is applied.

---

## 5. Architecture overview

```
                      New issue
                          |
                    [ load_issue ]
                          |
                    [ classify ]            ML layer        (section 6)
                          |
                    [ check_rules ]         Rules layer     (section 7)
                          |
                      [ route ]
          ________________|_________________
         |                |                 |
      Route A          Route B           Route C
   confident and     everything        sensitive
     complete           else             issue
         |                |                 |
         |        [ retrieve_similar ]      |
         |                |                 |
         |           [ analyze ]   LLM      |
         |                |                 |
         |         [ draft_comment ] LLM    |
         |                |                 |
         |       [ validate_proposal ]      |
         |                |                 |
         |         [ human_review ] <-------+   pause until a person decides
         |                |
         +---------> [ execute ]            Actions layer   (section 9)
                          |
                      [ record ]
                          |
                         END
```

Four layers, each replaceable and testable on its own:

| Layer | Uses an LLM | Purpose |
|---|---|---|
| ML | No | Predict the type with a probability. |
| Rules | No | Check completeness, catch sensitive issues, choose the route. |
| Agent | Yes | Gather evidence and draft a proposal for uncertain or incomplete issues. |
| Actions | No | Apply the approved decision (to a log file or to GitHub). |

Honest description for interviews: Route B is a **workflow with LLM steps**, not a free-running agent. The steps are fixed. An optional experiment (E12) replaces `retrieve_similar` + `analyze` with a bounded tool-calling loop and measures whether that helps.

Run modes:

| Mode | Input | Human step | Actions |
|---|---|---|---|
| Benchmark evaluation | Benchmark test set | Skipped | Log file |
| Fresh-set replay | Fresh set | Skipped | Log file |
| Live | Webhook from the demo repository | Real | GitHub |

---

## 6. ML layer

### 6.1 Task

Input: issue title and body. Output: probabilities for `bug`, `feature`, `question`.

### 6.2 Models, in order

| Version | Model | Stage |
|---|---|---|
| M1 | TF-IDF (word and character n-grams) + logistic regression | 1 |
| M2 | Sentence-embedding or transformer model (SetFit, fine-tuned small transformer, or adapters) | 6 |

One model is trained on all five repositories together, because the product must work on a repository it has not seen. Per-repository scores are still reported so they can be placed next to the published numbers.

Comparison caveat that must appear in the report: the baseline trains one classifier per repository, this project trains one for all. Both are scored on the same test set.

### 6.3 Preprocessing

- Text = title + newline + body.
- Remove HTML comments (issue templates leave these behind).
- Replace code blocks, URLs and stack traces with placeholder tokens (`<CODE>`, `<URL>`, `<TRACE>`) for the classifier. The rules layer sees the original text.
- Truncate very long bodies to `MAX_BODY_CHARS`, keeping the start and the end.

### 6.4 Confidence and calibration

- Confidence = the highest class probability.
- Routing depends on confidence, so calibration is measured on `val` (expected calibration error and a reliability diagram). If calibration is poor, the probabilities are calibrated (scikit-learn `CalibratedClassifierCV` for M1, temperature scaling for M2) and measured again.
- Calibration is measured again on the fresh set, because the class balance there is different.

### 6.5 Outputs saved

`models/classifier.joblib`, `models/classifier_meta.json` (training date, data hash, library versions, validation scores).

---

## 7. Rules layer

Pure Python functions. No LLM. Every rule has unit tests.

### 7.1 Completeness checks (applied when the predicted type is `bug`)

| Id | Field | Passes when the issue contains |
|---|---|---|
| C1 | `version_or_env` | a version number, operating system, browser or runtime |
| C2 | `repro_steps` | reproduction steps (a "steps to reproduce" section, or a numbered list of actions) |
| C3 | `expected_vs_actual` | what was expected and what happened instead |
| C4 | `error_evidence` | an error message, stack trace or code block |

`completeness` = checks passed / 4. `missing_fields` = list of failed check names. Unfilled template headings count as missing.

### 7.2 Hard rules

| Id | Trigger | Effect |
|---|---|---|
| H1 | Security wording (for example vulnerability, exploit, CVE, leaked credentials) | Route C. No LLM call, no public reply. |
| H2 | Body shorter than `MIN_BODY_CHARS` after cleaning | Fixed template reply asking for details. No LLM call. Goes to human review. |

### 7.3 Routing (evaluated in this order)

| Order | Condition | Route |
|---|---|---|
| 1 | H1 fires | C: escalate |
| 2 | H2 fires | Template proposal, then human review |
| 3 | confidence >= `T_HIGH` and (label is not `bug` or completeness >= `C_MIN`) | A: auto label |
| 4 | anything else | B: agent, then human review |

`T_HIGH` = 0.85 **(initial)**, `C_MIN` = 0.5 **(initial)**. Both are replaced in Stage 4 by values chosen from the threshold curve on `val` (experiment E3) and recorded in `DECISIONS.md`.

---

## 8. Agent layer (LangGraph)

### 8.1 State

One state object flows through the graph. Schemas live in `src/triage/schemas.py`.

```python
from typing import Literal
from pydantic import BaseModel

Label = Literal["bug", "feature", "question"]
Route = Literal["A", "B", "C", "TEMPLATE"]
Action = Literal["label_only", "request_info", "suggest_similar", "escalate"]


class Issue(BaseModel):
    issue_id: str  # hash of repo + title + body, or repo#number for API issues
    repo: str
    number: int | None  # None for benchmark issues
    title: str
    body: str


class Classification(BaseModel):
    label: Label
    probabilities: dict[Label, float]
    confidence: float
    model_version: str


class RuleReport(BaseModel):
    completeness: float | None  # None when label is not bug
    missing_fields: list[str]
    hard_rules_fired: list[str]  # e.g. ["H1"]
    route: Route


class SimilarIssue(BaseModel):
    issue_id: str
    title: str
    label: Label
    similarity: float


class Proposal(BaseModel):
    label: Label
    action: Action
    requested_fields: list[str]  # must be a subset of RuleReport.missing_fields
    similar_issue_ids: list[str]  # must be a subset of retrieved issues
    comment: str | None
    rationale: str  # shown to the reviewer, never posted


class ReviewDecision(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_label: Label | None = None
    edited_comment: str | None = None
    reviewer: str


class TriageState(BaseModel):
    issue: Issue
    classification: Classification | None = None
    rules: RuleReport | None = None
    similar: list[SimilarIssue] = []
    knn_label: Label | None = None  # majority label of retrieved issues (control for E5)
    proposal: Proposal | None = None
    validation_errors: list[str] = []
    review: ReviewDecision | None = None
    final_label: Label | None = None
    final_action: Action | None = None
    trace: list[dict] = []  # one entry per node: name, time, summary
```

### 8.2 Nodes

| Node | Type | What it does |
|---|---|---|
| `load_issue` | code | Cleans the text, builds the `Issue`. |
| `classify` | ML | Runs the classifier. |
| `check_rules` | code | Runs sections 7.1 to 7.3. |
| `retrieve_similar` | code | Embeds the issue, returns the top `TOP_K` most similar indexed issues from the same repository, and records their majority label as `knn_label`. |
| `analyze` | LLM | Sees the issue, classifier probabilities, rule report and similar issues with their labels. Returns label, action and rationale as structured output. |
| `draft_comment` | LLM | Writes the reply when the action is `request_info` or `suggest_similar`. |
| `validate_proposal` | code | Runs the checks in 8.4. |
| `human_review` | pause | Stops the graph and waits for a `ReviewDecision`. |
| `execute` | code | Calls the action adapter (section 9). |
| `record` | code | Saves the final record. |

### 8.3 Similar-issue retrieval

- A sentence-embedding model run locally produces one vector per issue (title + cleaned body).
- Vectors are kept in a NumPy array saved to disk. Search is cosine similarity in memory. No vector database is used until an index is too large for memory.
- Search is limited to issues from the same repository.

### 8.4 Proposal validation (deterministic)

| Id | Check |
|---|---|
| V1 | `label` is one of the three allowed labels. |
| V2 | `action` is one of the four allowed actions. |
| V3 | Every id in `similar_issue_ids` was returned by retrieval. |
| V4 | `requested_fields` is a subset of `missing_fields`. |
| V5 | The comment is under `MAX_COMMENT_CHARS`, has no @mentions, and has no links outside the connected repository. |

On failure the errors are sent back to `analyze` once. If the second proposal also fails, the action becomes `escalate`.

### 8.5 Human review

- Implemented with LangGraph's interrupt mechanism and a checkpointer, so the graph can stop, survive a restart, and resume when the decision arrives. The exact API names are taken from the LangGraph documentation for the version pinned in Stage 3.
- Checkpointer: SQLite.
- Thread id = `issue_id`.
- Reviewer sees: the issue, probabilities, rule report, similar issues, proposal and rationale.
- Decisions: **approve** (apply as proposed), **edit** (apply the reviewer's label or comment), **reject** (post nothing, add `needs-triage`).
- Stage 3 interface: terminal prompt. Stage 7 interface: review page.

### 8.6 LLM rules

- L1. The provider is chosen through configuration (`LLM_MODEL`), not hard-coded. Requirement: structured output support.
- L2. Issue text is untrusted input. It is passed as clearly delimited data, and prompts state that instructions inside an issue are not to be followed. The real protection is structural: outputs are restricted to fixed choices, validated by 8.4, and approved by a human, and the LLM has no tool that can change anything.
- L3. Every LLM response is cached on disk, keyed by a hash of model name and full prompt. Re-running an experiment costs nothing.
- L4. Temperature 0 for all evaluation runs.
- L5. Prompts live in `src/triage/agent/prompts.py` with a version string. A prompt change is logged in `DECISIONS.md`.

### 8.7 Evaluation and replay modes

In benchmark evaluation and fresh-set replay, `human_review` is skipped and the proposal is scored directly against ground truth.

---

## 9. Actions layer

One interface, two implementations, selected by `ACTION_MODE`.

| Mode | Behaviour | Used in |
|---|---|---|
| `log` | Appends the intended action to `results/actions.jsonl`. | All evaluation and replay. |
| `github` | Calls the GitHub REST API. | Live demo only. |

### 9.1 Mapping to GitHub

| Decision | GitHub effect |
|---|---|
| label `bug` | add label `bug` |
| label `feature` | add label `enhancement` |
| label `question` | add label `question` |
| action `request_info` | add label `needs-info`, post the comment |
| action `suggest_similar` | post the comment |
| action `escalate` or review `reject` | add label `needs-triage` |

### 9.2 Safety rules

- S1. `DRY_RUN=true` is the default. In dry run, `github` mode logs what it would do and does nothing.
- S2. Actions are refused for any repository not in `REPO_ALLOWLIST`. Only repositories you own are ever on the allowlist.
- S3. Before acting, the action log is checked so the same action is never applied twice to the same issue.
- S4. The system never closes, locks, edits or deletes an issue.
- S5. Every posted comment ends with a line saying it was drafted by an automated triage assistant and approved by a maintainer.
- S6. Benchmark or fresh-set issue text is never re-posted to GitHub without first neutralising @mentions and issue links, so real people and real issues are not notified.

---

## 10. Evaluation

This section is the centre of the project. Results go in `docs/EVAL_REPORT.md`; raw outputs go in `results/` as JSON.

### 10.1 Experiments

| Id | Question | Measured by | Stage |
|---|---|---|---|
| E1 | How good is the classifier? | Precision, recall, F1 per class and per repository, average F1, shown next to both 0.8270 (baseline) and 0.8934 (strongest published result found). | 1 |
| E2 | Can its confidence be trusted? | Expected calibration error and reliability diagram, before and after calibration. | 2 |
| E3 | Where should the threshold be? | For `T_HIGH` from 0.50 to 0.95: share of issues auto-labelled, and accuracy on that share. | 4 |
| E4 | Why not use the LLM for everything? | Classifier only, LLM only, and hybrid on the same issues: average F1, LLM calls, cost per 1,000 issues, latency. | 4 |
| E5 | Does the LLM add anything on uncertain issues? | On Route B issues only, three systems: classifier label, **kNN vote** (majority label of the retrieved issues, no LLM), and the agent's label. | 4 |
| E6 | Do the completeness rules work? | Precision and recall of C1 to C4 on the 100 hand-labelled bugs. | 2 |
| E7a | Do proposals pass validation? | Share passing V1 to V5 on the first attempt. | 4 |
| E7b | Does the agent choose the right action? | On the 100 hand-labelled bugs: did it choose `request_info` when fields are truly missing, and precision and recall of `requested_fields` against the hand labels. | 4 |
| E7c | Are the drafted replies sound? | Manual review of 50 drafts against a fixed checklist. One rater, stated as a limit. | 4 |
| E8 | Does it work on an unseen repository? | Train on four repositories, test on the fifth, for each of the five. | 6 |
| E9 | Does a stronger model pay off? | M1 against M2 on E1 and E3. | 6 |
| E10 | Where does it fail? | Every test error read and grouped by cause. | 4 |
| E11 | Does it hold up on fresh real issues? | On the fresh set: per-class and average F1 for classifier only, LLM only and hybrid; share per route; accuracy on the auto path; calibration; agreement between the agent's `request_info` and the maintainers' needs-information label (precision and recall). | 5 |
| E12 | (Optional) Does a tool-calling loop beat the fixed workflow? | Same metrics as E5. | 6 |

### 10.2 Evaluation rules

- V-1. All benchmark numbers come from the official test set, with thresholds and prompts frozen beforehand on `val`. Nothing is tuned on the fresh set either.
- V-2. LLM experiments run on the full test set if the budget allows. Otherwise they run on a fixed 300-issue subset (20 per class per repository), stored as a list of ids. The report states which was used.
- V-3. Fixed random seeds. Library versions pinned.
- V-4. A number that is not in `results/` does not go in the report or the README.
- V-5. **Every reported score carries a 95% bootstrap confidence interval** (`BOOTSTRAP_SAMPLES` resamples of the evaluated issues). Comparisons between two systems use a paired bootstrap on the difference. If the interval of the difference includes zero, the report says "no measurable difference".
- V-6. Results are reported as they come out. If LLM-only matches the hybrid in E4, or the kNN vote matches the agent in E5, the report says so and states what follows: the remaining case for the hybrid is cost at high volume, latency, and a confidence score usable for routing, each backed by its measured number and no more.

### 10.3 Results table (filled in as stages complete)

| Metric | Value with 95% interval |
|---|---|
| M1 average F1 (benchmark test) | 0.7721 [0.7502, 0.7946] |
| M2 average F1 (benchmark test) | TBD |
| Published baseline / strongest published result | 0.8270 / 0.8934 |

#### M1 vs Published Baseline (Test Set Breakdown)

| Repository | M1 Macro F1 (95% CI) | Published Baseline F1 |
|---|---|---|
| facebook/react | 0.7915 [0.7445, 0.8336] | 0.8718 |
| tensorflow/tensorflow | 0.8152 [0.7717, 0.8531] | 0.8644 |
| opencv/opencv | 0.7616 [0.7108, 0.8079] | 0.8173 |
| bitcoin/bitcoin | 0.7500 [0.7013, 0.7986] | 0.7555 |
| microsoft/vscode | 0.7341 [0.6821, 0.7845] | 0.8262 |
| **Overall Macro F1** | **0.7721 [0.7502, 0.7946]** | **0.8270** |
| Chosen `T_HIGH` / `C_MIN` | TBD |
| Share auto-labelled at chosen threshold | TBD |
| Accuracy on auto-labelled share | TBD |
| Hybrid / LLM-only / classifier-only average F1 (benchmark) | TBD |
| Cost per 1,000 issues, hybrid vs LLM-only | TBD |
| Route B accuracy: classifier / kNN vote / agent | TBD |
| `request_info` action precision and recall (hand labels) | TBD |
| Hybrid / LLM-only / classifier-only average F1 (fresh set) | TBD |
| `request_info` agreement with maintainers (fresh set) | TBD |

---

## 11. Live demo (Stage 7 onward)

Kept deliberately small. Its job is to show the approval flow working end to end.

### 11.1 API

| Method and path | Auth | Purpose |
|---|---|---|
| `POST /webhooks/github` | GitHub signature | Receives `issues` events. Handles only `opened`. |
| `GET /reviews?status=pending` | review token | Lists the review queue. |
| `GET /reviews/{issue_id}` | review token | Full detail for one issue. |
| `POST /reviews/{issue_id}/decision` | review token | Submits a `ReviewDecision` and resumes the graph. |
| `GET /metrics` | review token | Counts per route and per decision (demonstration only). |
| `GET /health` | none | Liveness check. |

### 11.2 Webhook handling

- The signature header is verified against `GITHUB_WEBHOOK_SECRET` before anything else.
- The delivery id is stored; a repeated delivery is ignored.
- The handler acknowledges immediately and runs the pipeline as a background task.
- Events from repositories outside `REPO_ALLOWLIST` are rejected.

### 11.3 Database tables

| Table | Holds |
|---|---|
| `triage_records` | One row per issue: route, label, confidence, completeness, proposal, status, timestamps. |
| `reviews` | One row per human decision. |
| `actions_log` | Every action attempted, with mode and result. |
| `webhook_deliveries` | Delivery ids already processed. |

Status values: `auto_done`, `pending_review`, `approved`, `edited`, `rejected`, `escalated`, `failed`.

### 11.4 Review page

Two screens: the review queue (one issue at a time with Approve, Edit, Reject) and the metrics page. Protected by one shared password. Single reviewer.

### 11.5 GitHub setup

- A demo repository you own, with labels `bug`, `enhancement`, `question`, `needs-info`, `needs-triage` (created by `scripts/setup_labels.py`).
- A webhook on that repository for `issues` events.
- A fine-grained token limited to that one repository with permission to write issues.

### 11.6 Secrets

All secrets come from environment variables. `.env` is never committed. `.env.example` lists every variable with no values.

---

## 12. Technology

| Area | Choice | First used |
|---|---|---|
| Language | Python 3.11+ | Stage 0 |
| Data | pandas | 0 |
| ML | scikit-learn | 1 |
| Schemas | Pydantic | 2 |
| Tests and lint | pytest, ruff | 1 |
| Embeddings | sentence-transformers | 3 |
| Workflow | LangGraph | 3 |
| Storage | SQLite | 3 |
| GitHub access | httpx | 5 |
| Stronger classifier | SetFit, transformers or adapters | 6 |
| API | FastAPI, uvicorn | 7 |
| Review page | Streamlit | 7 |
| Packaging | Docker | 8 |
| CI | GitHub Actions (tests and lint) | 8 |

Nothing is installed before the stage that needs it. Exact versions are pinned in `pyproject.toml` when first installed.

---

## 13. Repository layout

```
issue-triage-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   └── label_maps.yaml        # Stage 5
├── docs/
│   ├── SOURCE_OF_TRUTH.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   └── EVAL_REPORT.md
├── data/                      # not committed
├── models/                    # not committed
├── results/                   # experiment outputs (JSON), committed
├── scripts/
│   ├── download_data.py
│   ├── make_splits.py
│   ├── train_classifier.py
│   ├── build_index.py
│   ├── run_eval.py
│   ├── fetch_fresh_set.py     # Stage 5
│   └── setup_labels.py        # Stage 7
├── src/triage/
│   ├── config.py
│   ├── schemas.py
│   ├── data/                  # loading, cleaning, ids, GitHub fetch
│   ├── ml/                    # features, train, calibrate, predict
│   ├── rules/                 # completeness, hard_rules, router
│   ├── retrieval/             # embed, index, knn_vote
│   ├── agent/                 # graph, nodes, prompts, validate
│   ├── actions/               # base, log_action, github_action
│   ├── eval/                  # metrics, bootstrap, experiments, report
│   ├── api/                   # Stage 7
│   └── ui/                    # Stage 7
├── tests/
└── Dockerfile                 # Stage 8
```

---

## 14. Configuration

All values are read in `src/triage/config.py` from environment variables.

| Variable | Meaning | Starting value |
|---|---|---|
| `T_HIGH` | Confidence needed for the auto path | 0.85 (initial) |
| `C_MIN` | Completeness needed for a bug on the auto path | 0.5 (initial) |
| `MIN_BODY_CHARS` | Below this, rule H2 fires | 30 (initial) |
| `MAX_BODY_CHARS` | Body truncation length | 6000 (initial) |
| `MAX_COMMENT_CHARS` | Longest allowed reply | 1200 (initial) |
| `TOP_K` | Similar issues retrieved | 5 (initial) |
| `BOOTSTRAP_SAMPLES` | Resamples for confidence intervals | 1000 |
| `FRESH_SINCE` | Earliest creation date for fresh-set issues | open decision O6 |
| `LLM_MODEL` | Provider and model | open decision O1 |
| `ACTION_MODE` | `log` or `github` | `log` |
| `DRY_RUN` | Log instead of acting | `true` |
| `REPO_ALLOWLIST` | Repositories the service may act on | empty |
| `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `REVIEW_TOKEN` | Secrets | none |

---

## 15. Build stages

Every stage ends with something that works and can be shown. Stopping after any stage from 4 onward still leaves a finished project.

### Stage 0: Setup and data
- Repository, environment, `docs/` files created.
- Data downloaded, `issue_id` added, `train`/`val` split made.
- **Exit:** a data report with counts per repository and class; section 4.2 D5 confirmed or corrected.

### Stage 1: Classifier
- M1 trained, saved, and scored (E1) with confidence intervals.
- **Exit:** per-repository and average F1 on the test set written in the results table next to both published numbers. Unit tests for preprocessing pass.

### Stage 2: Rules and routing
- Completeness checks, hard rules, router, calibration check (E2).
- 100 bugs hand-labelled; rules measured (E6).
- **Exit:** every issue in `val` gets a route; rule tests pass; E2 and E6 results saved.

### Stage 3: Workflow and human approval
- LLM provider chosen. Index built from `train`. Graph built with all nodes, including the kNN vote.
- Human review through the terminal. Actions go to the log file.
- **Exit:** 20 `val` issues run end to end, including approve, edit and reject, and one run that is stopped and resumed after restarting the program.

### Stage 4: Benchmark evaluation
- E3, E4, E5, E7a, E7b, E7c, E10 run. Thresholds chosen and frozen. `EVAL_REPORT.md` written.
- **Exit:** every benchmark row in 10.3 is filled with an interval, except M2. README shows the results.

**Milestone 1: after Stage 4 the project is ready to show.**

### Stage 5: Fresh-set replay
- `FRESH_SINCE` and repositories chosen. Label maps written. Issues and index fetched. E11 run.
- **Exit:** at least 500 fresh issues from at least 2 repositories; excluded issues counted; E11 results with intervals in the report.
- **Stop rule:** if, after three working sessions, fewer than 2 repositories map cleanly, write what failed in `DECISIONS.md` and move to Stage 6. The project remains complete at Milestone 1.

**Milestone 2: after Stage 5 the project is at full strength for interviews.**

### Stage 6: Depth
- E8 (unseen repository), E9 (stronger model). E12 optional.
- **Exit:** report updated with what changed and whether it was worth it.

### Stage 7: Live demo
- API, webhook handling, review page, GitHub action adapter, demo repository.
- **Exit:** an issue opened on the demo repository goes through each of the three paths with `DRY_RUN=false`; a repeated webhook delivery causes no second action; a demo recording is in the README.

### Stage 8: Deployment (optional)
- Dockerfile, one host, CI running tests and lint.
- **Exit:** the service runs at a public address and survives a restart with pending reviews intact.

---

## 16. Open decisions

| Id | Decision | Decide by | Constraint |
|---|---|---|---|
| O1 | LLM provider and model | Start of Stage 3 | Must support structured output and have a stated training cutoff. A local model is acceptable. |
| O2 | Embedding model | Start of Stage 3 | Runs locally on CPU. |
| O3 | M2 approach | Start of Stage 6 | Trains on the available hardware. |
| O4 | Hosting provider | Start of Stage 8 | Runs one container with a persistent disk. If none is available, SQLite is replaced by PostgreSQL and that change is logged. |
| O5 | Final project name | Before the README is published | None. |
| O6 | Fresh-set repositories and `FRESH_SINCE` | Start of Stage 5 | Date is after the O1 model's training cutoff. Repositories have type labels that map cleanly. |

When a decision is made it moves to `DECISIONS.md` and the relevant section here is updated.

---

## 17. Risks and limits

### 17.1 Known limits (state these openly in the report)

- The classification task is modest: three classes and 1,500 training issues. The project's weight is in routing, validation and evaluation, not in model training.
- The benchmark is small, balanced and public. An LLM may have seen its issues in training, so LLM scores on the benchmark may be optimistic. The fresh set exists to address this.
- With 300 test issues per repository, a single repository's score is uncertain by roughly four points either way. Small differences are not claimed.
- Fresh-set ground truth is maintainers' labels, which are sometimes wrong, missing or inconsistent between repositories.
- Fresh-set issue text is the current text. A body edited after a maintainer asked for details will look more complete than it was when opened, which makes the `request_info` agreement score look worse than the truth.
- At the volume of a small repository, the cost saving of the hybrid over LLM-only is tiny. Cost matters only at high volume.
- Completeness has ground truth for only 100 hand-labelled bugs.
- Draft quality (E7c) rests on 50 drafts judged by one person.
- Live demo counts are not results: the same person writes the issues and approves the drafts.
- English only.

### 17.2 Project risks

| Risk | Response |
|---|---|
| M1 scores below the baseline | Acceptable. Report it honestly; E9 tests a stronger model. |
| LLM-only matches the hybrid, or kNN matches the agent | Report it (V-6). A clear negative result with intervals is a valid finding. |
| Label mapping for the fresh set turns into open-ended data work | Stage 5 stop rule. Start with the repository whose labels are clearest. |
| LLM costs grow during experiments | Response cache (L3) and the fixed 300-issue subset (V-2). |
| A library API differs from what a tutorial shows | Pin versions; read the documentation for the pinned version. |
| Scope grows | Section 2.2. New ideas go to a "Later" list in `PROGRESS.md`, not into the current stage. |

### 17.3 Possible extensions (only after Stage 7)

- Duplicate detection, using the maintainer duplicate marks recorded in the fresh set.
- Live shadow mode: poll new issues daily, log what the pipeline would do, and compare weeks later with what maintainers did.
- A second rater for E7c.
- Converting the token-based integration into a GitHub App.

---

## 18. Interview map

| Likely question | Where the answer comes from |
|---|---|
| Why not use an LLM for everything? | E4, V-6 |
| Did the LLM add anything beyond nearest neighbours? | E5 |
| How did you pick the confidence threshold? | E3 |
| How do you know the confidence means anything? | E2 |
| Is that difference real or noise? | V-5 |
| How do you know the agent chose the right action? | E7b, E11 |
| Why rules instead of asking the LLM? | Section 7, E6 |
| How do you stop the LLM inventing things? | Section 8.4, E7a |
| The benchmark is public. Has the LLM seen it? | Section 4.4, E11 |
| Does it work on real, unbalanced data? | E11 |
| How does your model compare with the best published? | E1, section 4.1 |
| What about prompt injection through an issue? | Section 8.6 L2 |
| How does human approval work technically? | Section 8.5, Stage 3 exit test |
| Would it work on a new repository? | E8 |
| Where does it fail? | E10, section 17.1 |
| How did you avoid data leakage? | Section 4.2 D3 and D4, section 4.4 F2 |
| What would you do next? | Section 17.3 |

---

## 19. References

- Benchmark dataset and baseline: https://github.com/nlbse2024/issue-report-classification
- Strongest published result found (AdaptIRC, F1 0.8934): https://wrap.warwick.ac.uk/id/eprint/187927
- Reference implementation of a LangGraph issue agent with human review: https://github.com/pamelafox/issue-triager-agent
- Reference LangGraph architecture (supervisor and sub-graphs): https://github.com/langchain-ai/open_deep_research

---

## 20. Change log

| Date | Change |
|---|---|
| 2026-10-02 | Version 1. |
| 2026-10-02 | Version 2. Added the fresh-set replay as a core stage (4.4, E11, Stage 5). Added the kNN-vote control to E5. Split E7 and added action accuracy against hand labels (E7b). Required bootstrap confidence intervals (V-5) and honest reporting of null results (V-6). Cited the 0.8934 published result next to the baseline. Reduced the live service to a demo (Stage 7) and made deployment optional (Stage 8). Live counts are no longer reported as results. |
