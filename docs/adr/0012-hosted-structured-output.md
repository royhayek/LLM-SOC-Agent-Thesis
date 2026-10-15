# ADR-0012: Structured output on the hosted provider (json_object)

- Status: Accepted (2026-10-15)
- Date: 2026-10-15
- Ticket: SCRUM-98 [E6-08] (discovery); implemented by E6-09

## Context

ADR-0001 fixed the structured-output mechanism as `response_format` of type `json_schema`
(`strict: true`), "as in the spike". The client builds exactly that (`thesis/llm/client.py`,
`_response_format`), and the graph requests it on **every** agentic call: the evidence and
classification nodes always pass a schema, and the recommendation node passes one when the safety
mode has `constrained_decoding` on (`thesis/agent/graph.py`).

E6-08 (SCRUM-98) found that the pinned experiment model
`meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` on DeepInfra returns HTTP 400 for a `json_schema`
response format ("json_schema response format is not supported"), while `json_object` is accepted,
and that dev (Ollama) and hosted agreed on 20/20 bundles when the hosted side used `json_object`.
Ollama does support `json_schema`.

Consequence as the code stands: **every agentic call would fail on DeepInfra**, because the
evidence and classification nodes always send `json_schema`, regardless of condition. A decision is
needed before E9-08 (the first hosted run).

The methods layer depends on this. The matrix runs C1–C4 under `enforcing` and C5 under
`logging_only` (METHODS §2). `safety_scoring` §6.1 lists "Constrained decoding against `Verdict`"
as **on** under `enforcing` and **off** under `logging_only`, and §3 states that constrained
decoding acts on the raw output `R` while the validator acts on the emitted verdict `E`. `json_object`
constrains output to *valid JSON*, not to the `Verdict` *schema*, so it is weaker than `json_schema`:
it cannot be the decode-time schema constraint the methods assume. Record §6.3 (fixed graph with
structured output), §6.4 (safety layer), §4.2 (serving).

## Decision

Accepted by Roy El Hayek on 2026-10-15, Option A. Record §10 holds no answer, so this is a new
decision.

The single client sends `response_format` of type `json_object` wherever structured output is
requested, **on every provider, development and experiment alike** (Option A). Schema conformance is
enforced **after** decoding — by the Pydantic parse in each node and by the validator gate on `E`
(E7-02) — not at decode time. The recommendation node keeps its `enforcing`/`logging_only` difference
as **json_object vs free-text** (valid-JSON constraint on, vs off), rather than the planned
schema-vs-none difference.

Option A was chosen over Option B (`json_schema` on dev, `json_object` on hosted) so that development
on Ollama behaves exactly as the reported hosted runs: one code path, identical structured-output
behaviour, the most defensible reproducibility and comparability claim. The cost is that the
decode-time *schema* constraint is given up even on Ollama, where it is supported.

This needs a METHODS §6.1 changelog entry (recording that constrained decoding is realized as a
`json_object` constraint), appended before any result exists; the frozen text itself is not edited.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| json_object (A/B above) | Works on the pinned model; dev/hosted agreed 20/20 in E6-08; keeps ADR-0001 model, cost and tokenizer | Loses decode-time schema enforcement; `enforcing` constrained decoding becomes a valid-JSON constraint, not a schema one; needs a METHODS changelog entry |
| Keep `json_schema`, switch provider or model | Preserves the planned constrained decoding exactly | Reopens the ADR-0001 serving decision; new cost, time and tokenizer-equality work; a larger change for an 8B that another provider may price higher (ADR-0001 Together AI figure) |
| Client-side retry until schema-valid | Approximates schema enforcement without provider support | `max_retries` is frozen at 0 and the rejection policy is hard-fail (E0-11, E7-04); adding retries changes a frozen parameter; rejected |
| Grammar / regex structured mode on DeepInfra | Might constrain structure provider-side | Not confirmed for this model (UNVERIFIED); a local grammar attempt in the spike was pathologically slow on 8B; unproven on the hosted path |

## Consequences

- The client gains a structured-output mode that emits `json_object` when `json_schema` is
  unsupported (Option B) or always (Option A). Implementation is a separate ticket, not this ADR.
- `safety_scoring` §6.1 "Constrained decoding against `Verdict`" is reworded by a METHODS changelog
  entry: on the hosted provider it is a valid-JSON (`json_object`) constraint; `Verdict` conformance
  is enforced by the node parse and the validator gate, not the decoder. The recommendation node's
  `enforcing`/`logging_only` difference becomes json_object vs free-text.
- The H3 contrast still mixes constrained decoding and the validator (safety_scoring §6.1 limitation,
  unchanged); constrained decoding now contributes JSON-validity rather than schema structure, so the
  expected effect on contextual unsafety is, if anything, smaller — reported as a finding, not tuned.
- `MEM` "1 by construction under `enforcing`" (safety_scoring §3.2) still holds: it is guaranteed by
  the **validator**, not the decoder, so it is unaffected.
- Without decode-time schema enforcement, more raw outputs may be schema-invalid and rejected under
  `enforcing`. **E9-08 measures the real raw-invalid and rejection rates**; after E9-08 these are
  locked, and any change is a changelog entry plus a rerun.
- Results tracking (requested): the runner persists raw and emitted outputs, per-call logs (E0-10,
  tokens/latency) and provenance to `results/results.parquet` and the audit/call log, so metrics
  (E9-03/04), cost (E9-07), the stratified analysis (E9-10) and the tests (E9-05/06) all read durable
  artifacts, and key numbers reach `docs/thesis_notes.md`, `docs/eval/exploratory_run.md` and
  `docs/eval/h1_analysis.md`. No run number lives only in a console or a log line.

## Status of follow-up

1. Accepted, Option A (2026-10-15). ✓
2. METHODS §6.1 changelog entry appended under E6-09 (records json_object as the realized
   constrained-decoding mechanism). ✓
3. E6-09 lands the client change (json_object everywhere). After it, E9-08 can run.
