# ADR-0000: Toolchain and architecture rules

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-18 [E0-02]

## Context

Every later code ticket assumes linting, type checking, tests and a place to record decisions (backlog, E0-02). The project record locks the architecture in §6 and the toolchain in §8 (ticket 2). This ADR records both once, so no later ticket has to restate them. It supports risk #5 (reproducibility).

## Decision

### Toolchain

| Concern | Choice |
|---|---|
| Project and dependency management | uv, with `uv.lock` committed. Python 3.12, pinned in `.python-version` |
| Package | `thesis`, until a system name is chosen (record §4, §11.4) |
| Lint and format | ruff |
| Type checking | mypy, strict, scoped to `thesis/`. `spikes/` is excluded |
| Tests | pytest. Tests marked `slow` are excluded from CI (record §6.9) |
| Hooks | pre-commit. ruff and mypy run from the locked project environment. No hook touches `spikes/` |
| CI | GitHub Actions: install from the lock file, run pre-commit on all files, run `pytest -m "not slow"` |
| Secrets | `.env` is gitignored and never logged (record §6.11). CI fails if `.env` is tracked. `.env.example` holds placeholders only |

### Architecture rules

1. **Modular monolith** with hard internal seams. The experimental conditions are injected at runtime from `ExperimentConfig` (record §6.1).
2. **No microservices, no Postgres, no message queue, and no orchestration beyond Docker Compose** (record §6.7).
3. **No OpenTelemetry and no Prometheus.** Structured JSON logging with structlog is the only observability mechanism (record §6.10).
4. **No agent framework** (no LangChain, LlamaIndex or LangGraph) **and no vector database** (record §6.2).
5. **No new dependency, service or tool without an accepted ADR** in `docs/adr/` (`docs/WORKING_RULES.md`, "Never add"; `docs/DOD.md`, Code tickets).

## Alternatives considered

| Option | For | Against |
|---|---|---|
| uv | One fast tool for Python, environments and the lock file. Already installed. Fast CI installs | Younger than Poetry |
| Poetry | Mature, widely known | Not installed. Slower resolver. Python itself managed separately |
| Microservices or a single tangled application | — | Rejected by record §6.1: no operational need for distributed services, and the conditions need clean substitution points |

## Consequences

- Every code ticket must pass pre-commit and CI before merge (`docs/DOD.md`).
- Anything that calls Ollama is marked `slow` and does not run in CI.
- Adding any dependency, including a development tool, starts with an ADR from `docs/adr/template.md`.
- Rule 5 is cited from `docs/WORKING_RULES.md` and `docs/DOD.md`. The ticket text cites record §14, which does not state it.
