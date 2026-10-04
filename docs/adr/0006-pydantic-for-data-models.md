# ADR-0006: Pydantic for data models

- Status: Proposed
- Date: 2026-10-04
- Ticket: SCRUM-82 [E0-08]

## Context

Ticket E0-08 delivers a versioned Pydantic `Alert` model (`thesis/schema/alert.py`). The ticket names Pydantic in its goal and technical notes ("Pydantic (§6.2)"). Later tickets build more models on the same library: the `Verdict` output schema (E7-01, record §6.5), the safety layer's constrained decoding (record §6.4), and the FastAPI console (record §6.2).

The locked stack in `docs/WORKING_RULES.md` lists "Pydantic models". ADR-0000 still requires an ADR for any dependency, so this ADR records the decision the record already makes.

## Decision

The record already makes this decision. Record §6.2, Backend row: "Pydantic is the native type system, so **the safety schema and the API schema are the same object**." Record §6.4, item 2: "A structured output schema. A Pydantic model containing incident type, severity, affected device, evidence references and recommended action."

Use Pydantic v2 for every data model in `thesis/`. `pyproject.toml` requires `pydantic>=2.13.5`, and `uv.lock` pins 2.13.5, with pydantic-core 2.46.5, annotated-types 0.8.0 and typing-inspection 0.4.4.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| Pydantic v2 | Named by the record (§6.2, §6.4); native to FastAPI; emits JSON Schema for constrained decoding; validates on parse | One runtime dependency with a compiled core |
| Standard-library `dataclasses` plus hand-written validation | No new dependency | No JSON Schema output and no validation on parse; FastAPI would need Pydantic anyway, so there would be two model systems |
| msgspec or attrs with cattrs | Fast, small | Not FastAPI's native type system; contradicts record §6.2 |

## Consequences

- Pydantic becomes a runtime dependency, added in commit `bb325fa` on the SCRUM-82 branch.
- Models are checked by mypy strict without the Pydantic mypy plugin. The plugin can be added later if a model needs it.
- No second model or validation library is added for data that flows through the pipeline.
