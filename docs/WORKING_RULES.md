# Working rules

MSc thesis of Roy EL HAYEK (ECE Paris): an LLM-based SOC agent for IoT cyberattack detection and response.

A pipeline turns three IoT telemetry streams (MQTT, network flows, honeypot logs) into one validated verdict plus a recommended action. A measurement rig then tests four hypotheses (H1–H4) against two baselines.

**The software is the instrument. The experiment is the thesis.** Every engineering choice serves the experiment.

**The agent recommends. It never executes.** No code path may act on the testbed or on any network.

## Where the rules live

| What | Where |
|---|---|
| Locked decisions (§4, §5, §6) and open questions (§10) | `docs/source/thesis_project_full_record.md` |
| Frozen methods contract | `METHODS.md` (created by ticket E0-03) |
| Definition of Done and Definition of Ready | `docs/DOD.md` |
| All 112 tickets, full text | `docs/planning/backlog_full.md` |
| Ticket reference to Jira key | `docs/planning/jira_key_map.md` |
| Architecture decisions | `docs/adr/` |
| Task board | Jira project `SCRUM` on `iot-soc-thesis.atlassian.net` |

Section numbers written as `§4.1` refer to the project record.

## How to work on a ticket

1. One ticket, one branch, one pull request. Branch name: `SCRUM-<n>-<short-slug>`. Commit messages start with the Jira key and the reference: `SCRUM-18 [E0-02] Add CI workflow`.
2. Read the ticket first: search `docs/planning/backlog_full.md` for its reference, for example `[E0-02]`.
3. The ticket's Scope "Out" list is binding. Stop when the acceptance criteria are met. Do not add extras.
4. Anything added that is not in the ticket or the record is an ASSUMPTION. List each one in the pull request description.
5. Before finishing, check the ticket against `docs/DOD.md`.
6. If the ticket produced a decision, number or figure the thesis will cite, append one line to `docs/thesis_notes.md`.

## Locked stack

- Python, package name `thesis`. Pydantic models. pytest, ruff, mypy (strict on `thesis/`), pre-commit.
- Structured JSON logging with structlog.
- Testbed: Docker Compose, fully emulated. Mosquitto broker, MQTT emulators, one honeypot, a capture sidecar.
- Detectors: LightGBM or XGBoost for flows, statistical thresholds for MQTT, parser plus rules for the honeypot.
- Retrieval: sentence-transformers embeddings in a numpy array, cosine similarity.
- LLM: one OpenAI-compatible client, switched by `LLM_BASE_URL` and `LLM_MODEL`. Local Ollama for development. A hosted open-weights model pinned by revision for experiments.
- Storage: raw files with a SHA-256 manifest, Parquet for alerts, bundles and results, SQLite for console state, append-only JSONL for the audit log.
- Console: FastAPI, React, REST plus Server-Sent Events, types generated with openapi-typescript. Localhost only.

## Never add

- An agent framework (LangChain, LlamaIndex, LangGraph). The graph is written directly.
- A vector database.
- Authentication.
- Postgres, a message queue, microservices, or orchestration beyond Docker Compose.
- OpenTelemetry or Prometheus.
- vLLM or self-hosted serving.
- WebSockets.
- Custom attack code. Attacks replay published datasets or use standard tooling.

Any other new dependency, service or tool needs an accepted ADR in `docs/adr/` first.

## Research-integrity rules

Breaking one of these invalidates results. If a task seems to require breaking one, stop.

- **Freeze before results.** Anything that defines correct, acceptable or unsafe is frozen before any agent or baseline output exists on corpus bundles: the action catalog, the action sets, the rejection policy, safety scoring, reliability metrics, target N, the reduction policy and the Baseline A lookup.
- **Spike outputs stay unread** (`spikes/results.csv`, `spikes/logs/`, `spikes/FINDINGS.md`) while the action catalog (E0-04) is being derived.
- **Every citation is checked against its source.** A citation that has not been checked is marked `UNVERIFIED`.
- **Open questions in §10 are decided by Roy** and recorded in `METHODS.md`. Code and drafts must not assume an answer.
- **Prompts** are developed on pilot or training-split bundles only, never on evaluation bundles.
- **Detectors** are tuned on training-split or benign calibration data only, never on pilot or evaluation data.
- **One reduced bundle view** for every condition, both baselines included.
- **No hardcoded conditions.** Sources, strategy and safety come from `ExperimentConfig`.
- **Exactly three LLM calls per bundle** in the agentic strategy. Each call gets fresh context. No conversation history.
- **Every LLM call** goes through the single client and logs every §6.10 field. Secrets are never logged.
- **LLM output quality is never unit-tested.** Tests cover the code around the model.
- **Locked parameters** change only through an appended `METHODS.md` changelog entry. Frozen text is never edited. If results exist, the affected conditions are re-run.
- **`spikes/` is throwaway.** Nothing imports from it.

## Machine limits

- 16 GB Apple Silicon. Never run Ollama and the Docker testbed at the same time.
- Ollama truncates silently at its default context. Set `num_ctx 8192` and verify it with the marker test.
- The testbed runs on an isolated internal Docker network. The isolation check must pass before any attack tooling runs.

## Commands

| Task | Command |
|---|---|
| Install (and set up the git hook) | `uv sync --locked && uv run pre-commit install` |
| Lint, format, type-check and file hygiene | `uv run pre-commit run --all-files` |
| Type-check only | `uv run mypy` |
| Test, as CI does | `uv run pytest -m "not slow"` |
| Test, including `slow` (needs Ollama) | `uv run pytest` |
