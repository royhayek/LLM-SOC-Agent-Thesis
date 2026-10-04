# ADR-0007: structlog for structured JSON logging

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-100 [E0-10]

## Context

Ticket E0-10 delivers `log_llm_call()` (`thesis/obs/logging.py`), which writes one append-only JSONL record per LLM call. The ticket names structlog in its technical notes ("structlog emitting JSON (§6.10)"). The same log is the audit log, the cost instrumentation and the debugging tool, and later tickets build on it: the single LLM client (E6-01) and the audit log of the safety layer (E7-05).

The locked stack in `docs/WORKING_RULES.md` lists "Structured JSON logging with structlog". ADR-0000 still requires an ADR for any dependency, so this ADR records the decision the record already makes.

## Decision

The record already makes this decision. Record §6.10: "Structured JSON logging from the first commit (`structlog`). Every LLM call logs: node, model, revision, tokens in/out, latency, full prompt, raw completion, parse outcome, condition, bundle ID, repetition." ADR-0000, rule 3: "Structured JSON logging with structlog is the only observability mechanism (record §6.10)."

Use structlog, rendering JSON, for every structured log in `thesis/`. `pyproject.toml` requires `structlog>=26.1.0`, and `uv.lock` pins 26.1.0, with no further dependencies.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| structlog | Named by the record (§6.10) and ADR-0000; processor chain renders JSON; can bind a logger to one file without changing global logging | One runtime dependency |
| Standard-library `logging` plus `json.dumps` | No new dependency | A JSON formatter must be written by hand; contradicts record §6.10 and ADR-0000 |
| Writing JSON lines with `json.dumps` only, no logging library | No new dependency, simplest sink | Leaves no shared mechanism for other structured logs; contradicts record §6.10 |
| OpenTelemetry or Prometheus | Standard tracing and metrics | Ruled out by record §6.10 ("there is no production to monitor") and ADR-0000, rule 3 |

## Consequences

- structlog becomes a runtime dependency, added to `pyproject.toml` and `uv.lock` by SCRUM-100 [E0-10].
- LLM-call records go to append-only JSONL under `logs/`, which is gitignored (record §6.7).
- No second logging or observability library is added.
