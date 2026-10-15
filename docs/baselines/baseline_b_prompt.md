# Baseline B prompt (E8-03, SCRUM-60)

Baseline B (condition C6) answers "does the agentic architecture help, or is the model just good?"
(record §6.6). It is the **same model in a single call** with the **same output schema** as the
agent, but with none of the agentic machinery. If its prompt were weak, the agent would win for the
wrong reason and H2 would prove nothing, so Baseline B gets a prompt written to the same standard
as the agent's node prompts.

Template: `thesis/prompts/templates/baseline_b.py`, version `prompts-v1.0` (shared with the agent).
Rendered static-prefix-first in the same order as every other prompt (E6-02), with the reduced
view as the untrusted bundle.

## Section by section (why each instruction is there)

- **Role.** States the SOC-analyst role, the recommend-never-execute boundary (record §1.1) and the
  standing instruction to treat the bundle as untrusted data (record §3.3) — identical to the
  agent's role, so the two differ by architecture, not by persona.
- **Output schema.** Describes the full `Verdict` JSON (classification, recommendation, affected
  device, evidence) with the closed label and action sets, so Baseline B produces exactly the same
  structured output the agent does (§6.6). "Exactly these keys and no others" keeps it parseable.
- **Action catalog.** The eight catalog actions (id + description), read from the frozen
  `knowledge/action_catalog.yaml`. Baseline B must choose from the same closed action set as the
  agent, so H2 compares like with like.
- **Task.** Asks for one single-step answer: weigh every source present together, classify, and
  recommend the most proportionate catalog action, citing the bundle alert ids. This is the one
  place the single-call nature is stated. The shared reasoning instruction ("think step by step …
  then output exactly one JSON object") is kept verbatim, so Baseline B is not handicapped on
  reasoning relative to the agent's nodes.

## What Baseline B deliberately lacks (vs the agent)

| Capability | Agent (C1–C5) | Baseline B (C6) |
|---|---|---|
| Number of LLM calls | 3 (evidence → classify → recommend) | 1 |
| Knowledge retrieval (E5-04) | yes (node 1) | no |
| Device-context lookup | yes (node 1) | no |
| Step-by-step decomposition | yes (three nodes, fresh context each) | no (one call) |
| Safety layer (constrained decoding, validator gate, rejection) | under `enforcing` | no (scored as `logging_only`, §6.1) |

Everything else is identical: same model and revision, same reduced view, same catalog and schema,
same sampling, same static-prefix ordering (§4.1, §4.4). Baseline B is scored exactly like the
agent's `logging_only` arm (safety_scoring.md §9).

## Measurements (pilot, non-evaluation)

Developed and measured on pilot bundles only (never evaluation). On the local dev model
(`llama3.1-8b-8k`, Ollama, `json_object` structured output), over 15 pilot bundles:

- **Parse-into-`Verdict` rate: 15/15 (100%).**
- **Maximum rendered prompt size: 1,301 tokens**, within the frozen input ceiling of 2,500 (and
  below the 2,000 target), counted with the experiment tokenizer (E3-08).

## Revision rounds

To avoid weakening Baseline B by neglect (ticket gotcha), its prompt shares the agent's role and
reasoning text and was revised alongside the agent prompts: round 1 was the E0-01 walking-skeleton
single-call prompt (whose findings apply directly, record spike), round 2 fixed the schema text to
the node models (E6-07), round 3 (this ticket) set the full-Verdict schema, the single-step task
and the catalog, and confirmed the parse rate above.
