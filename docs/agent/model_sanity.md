# Dev vs experiment model sanity (E6-08, SCRUM-98)

Development runs on the local model and experiments on the hosted sibling (record §4.2). This
sanity confirms, before the matrix, that the same-family assumption holds in practice: that prompts
developed locally will behave comparably on the experiment model.

## Setup

- **Dev model:** `llama3.1-8b-8k` on local Ollama (Llama 3.1 8B Instruct, Q4_K_M, digest
  `6811dcd559d9`), ADR-0001 development model.
- **Experiment model:** `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` on DeepInfra (Llama 3.1 8B
  Instruct, FP8, upstream commit `0e9e39f2…`), the **ADR-0001 pinned** experiment model. The
  machine's `.env` pointed at `Llama-3.3-70B-Instruct-Turbo`; this run overrides it to the pinned
  8B so the sanity tests the same-family pair ADR-0001 specifies (Roy's decision, 2026-10-15).
- **Sample:** the first 20 pilot bundles by id (non-evaluation; pilot, never the test set).
- **Call:** one classification call per bundle per model on the reduced view, temperature 0.6,
  top_p 0.9, `max_tokens` 250, **`json_object` structured output** (see the finding below).
- Harness: `model_sanity.py` (scratch, not committed; makes paid calls).

## Results

| Metric | Dev (Ollama 8B) | Experiment (DeepInfra 8B) |
|---|---|---|
| Schema-validity rate (valid JSON with an in-enum `incident_type`) | **20/20 = 1.00** | **20/20 = 1.00** |

**Agreement between the models on `incident_type`: 20/20 = 1.00** (perfect agreement on this
sample). The agreed labels vary across the sample (`port_scan`, `ssh_brute_force`, `syn_flood`,
`mqtt_publish_flood`, `mqtt_brute_force`), so the agreement is genuine, not a constant answer.

(The pilot bundles happen to carry a `benign` schedule label while both models read the injected
pilot activity as attacks. True-label accuracy is not the point here and is not scored; this sanity
compares the two models to each other, and they match.)

## Structured-output finding (affects the enforcing path)

The structured-output mode matters and differs by provider:

- **`json_schema` constrained decoding** (strict schema at generation, used by E6-07's e2e and
  wired in E7-01) works on **Ollama** but **DeepInfra returns HTTP 400 for this model**:
  *"json_schema response format is not supported for model
  meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"*.
- **No structured output (free-form):** schema-validity is low on both — dev 1/20, experiment 5/20,
  with zero overlap — so free-form is not usable.
- **`json_object` mode** (valid-JSON constraint, no schema) works on **both** and gives the
  1.00/1.00 validity above.

So the portable structured-output mechanism is **`json_object` plus the deterministic validator
(E7-02)** as the hard gate, not strict `json_schema`. E7-06 (the enforcing switch) and the client
should use `json_object` for the hosted model; `json_schema` remains usable only against local
Ollama.

## Go / No-go

**GO** for running the matrix on the experiment model. The dev and experiment models are the same
family (Llama 3.1 8B Instruct) and agree on `incident_type` on 20/20 pilot bundles under identical
`json_object` structured output, so prompts developed locally are expected to behave comparably on
the experiment model. This is not a model-family problem, so **no ADR-0001 model change is needed.**

**One required adjustment before the matrix** (engineering, not an ADR-0001 change): the agent's
constrained-decoding mechanism must use `json_object` (portable) rather than strict `json_schema`,
which the hosted model does not support. Tracked as a follow-up on E7-06 / the LLM client.
