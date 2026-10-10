# ADR-0001: LLM serving, cost and time budget

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-57 [E0-06]

## Context

Record §4.2 decided serving in principle: an open-weights instruct model on a cheap hosted inference provider, pinned by name and revision, for the experiments, and local Ollama for development. The two are switched by `LLM_BASE_URL` and `LLM_MODEL` behind one OpenAI-compatible client. Record §4.4.1 sizes the matrix and asks for a hard spending cap. The budget is under €100 (record §4.2). Pinning the model is the reproducibility claim (record §3, risk 5).

The walking-skeleton spike (E0-01, `spikes/FINDINGS.md`) ran one hand-written bundle 10 times on each of two models, at temperature 0 with no seed:

| Model | Validity | Agreement | Correctness | Mean tokens in / out | Mean latency |
|---|---|---|---|---|---|
| Local `llama3.1-8b-8k` (Llama 3.1 8B, Q4_K_M, digest 6811dcd559d9), Ollama 0.23.2 | 10/10 | 10/10 | 10/10 | 2116 / 101 | 5.44 s (4.31 s after the first run) |
| Hosted `meta-llama/Llama-3.3-70B-Instruct-Turbo` (FP8), DeepInfra | 10/10 | 10/10 | 10/10 | 2116 / 85 | 5.32 s |

The spike could not separate the two models on one easy bundle, and it noted that the hosted Turbo model reports no revision or fingerprint. FINDINGS.md recommended deciding the experiment model on harder pilot bundles. This ADR does not: no pilot bundles exist yet, and the ticket's scope excludes any model comparison. The model is chosen on the record's criteria instead (same model for development and experiments, open weights, budget, tokenizer already measured).

## Decision

### Experiment model

| Field | Value |
|---|---|
| Model | `meta-llama/Llama-3.1-8B-Instruct` (open weights, Llama 3.1 Community License) |
| Upstream revision | Hugging Face commit `0e9e39f249a16976918f6564b8830bc894c89659` (repository last modified 2024-09-25; read from the Hub API on 2026-10-04) |
| Provider | DeepInfra, serverless, OpenAI-compatible endpoint |
| Provider model ID | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` |
| Precision served | FP8 (stated on the DeepInfra model page, 2026-10-04) |
| Temperature | 0.6 |
| top_p | 0.9 |
| max_tokens | 250 (the output ceiling frozen in METHODS.md Annex E, §9) |
| Structured output | `response_format` with `json_schema`, as in the spike |
| Seed | Not supported in effect. DeepInfra's API schema for this model documents `seed` as "Seed for random number generator. If not provided, a random seed is used. Determinism is not guaranteed." (model page, read 2026-10-04); its chat overview page does not mention it. A check on 2026-10-04 (8 calls to this model at temperature 0.6, top_p 0.9, `max_tokens` 60) found the parameter accepted without error but not honoured: 3 calls with seed 42 gave 2 different completions, 2 calls with seed 7 gave 2, and 3 calls with no seed gave 3. No response carried a `system_fingerprint`. |

The temperature and top_p are Meta's reference defaults for Llama 3: `temperature: float = 0.6` and `top_p: float = 0.9` in `models/llama3/generation.py` of Meta's `meta-llama/llama-models` repository. The only reason for the choice is that these are the vendor's reference values, fixed before any output of this project existed. The effect on agreement played no part in it (METHODS.md Annex D, "Reliability and robustness": the temperature is not changed to make agreement informative). A consequence, not a reason, is that the k = 3 repetitions carry run-to-run variance from sampling.

**What the pin covers, and what it does not.** The weights are open and identified by their upstream commit, so anyone can re-serve the same model. DeepInfra serves the model by name, in FP8, and does not certify which commit it serves. Each result row therefore records the provider, the provider model ID, the precision, the upstream commit and the run date (record §4.2, "Record per run"). Seeds are not supported in effect, so the k = 3 repetitions carry all the variance. Individual completions cannot be reproduced, only their distribution.

### Development model

| Field | Value |
|---|---|
| Model | Llama 3.1 8B Instruct through Ollama, tag `llama3.1-8b-8k` (Q4_K_M, digest 6811dcd559d9), `num_ctx 8192` |
| Relation to the experiment model | Same model (record §4.2, "same model both places"): Llama 3.1 8B Instruct in both places, with the same sampling. The quantization differs: Q4_K_M locally, FP8 hosted. That both builds derive from the same weights is ASSUMPTION A1. |
| Sampling | Temperature 0.6, top_p 0.9, as in the experiment |

The Llama 3 tokenizer used for the token measurements in METHODS.md Annex E, §9 and §10 (ASSUMPTION 1) is the experiment model's own tokenizer.

### Environment variables

```
# development
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1-8b-8k

# experiments
LLM_BASE_URL=https://api.deepinfra.com/v1/openai
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo

LLM_API_KEY=<secret, never logged>
```

### Cost

Matrix (record §4.4.1, METHODS.md §2): N bundles × 16 LLM calls × k = 3 repetitions. `N_eval` = 480 evaluation bundles, fixed by the power calculation E2-02 (METHODS.md v1.1 changelog entry 8, `docs/power/power_calculation.md`). LLM calls run on evaluation bundles only; Baseline A's 206 training bundles (E2-01) carry no LLM calls.

- Input tokens per call: 3,000. This is the record §4.4.1 estimate, kept as a conservative cost figure; the hard ceiling in METHODS.md Annex E, §9 is 2,500.
- Output tokens per call: 250, the ceiling in METHODS.md Annex E, §9.

Prices (DeepInfra pricing page, standard tier, checked 2026-10-04): USD 0.02 per million input tokens, USD 0.04 per million output tokens. Conversion: ECB reference rate of 2026-10-02, 1 EUR = 1.1225 USD.

| Run | Bundles | Calls | Input tokens | Output tokens | Price in / out (USD per 1M, checked 2026-10-04) | Cost (USD) | Cost (EUR) |
|---|---|---|---|---|---|---|---|
| Exploratory (about 5 % of bundles) | 25 | 1,200 | 3.6M | 0.3M | 0.02 / 0.04 | 0.08 | 0.07 |
| Full run 1 | 480 | 23,040 | 69.1M | 5.8M | 0.02 / 0.04 | 1.61 | 1.44 |
| Full run 2 | 480 | 23,040 | 69.1M | 5.8M | 0.02 / 0.04 | 1.61 | 1.44 |
| Full run 3 | 480 | 23,040 | 69.1M | 5.8M | 0.02 / 0.04 | 1.61 | 1.44 |
| **Total** | | **70,320** | **211.0M** | **17.6M** | | **4.92** | **4.39** |

If the exploratory run is a full pass instead, the total is 92,160 calls and about €5.6. The cost scales linearly with N: at N = 1,000 the worst case is still about €9. Both are well under €100.

### Time

The spike measured 5.32 s per hosted call (70B) and 4.31 s per local 8B call. Hosted 8B latency was not measured. At about 5 s per call, a full run of 23,040 calls takes about 32 h one call at a time, or about 4 h with 8 concurrent requests, if the provider's rate limit allows it (UNVERIFIED). Locally, the same run would take about 27 h of continuous inference on the 16 GB M2. This is why the experiments run hosted (record §4.2).

### Spending cap

- Amount: USD 20 (about €17.8 at the rate above), raised from USD 5 by E2-02 on 2026-10-10. The earlier USD 5 cap was set for the N = 250 placeholder; with N_eval = 480 the projected spend is USD 4.92, which left no guard-rail margin under USD 5, so the cap is raised to restore headroom. Still far under the €100 budget. (The original USD 5 cap was confirmed by Roy El Hayek on 2026-10-04; raising it to USD 20 on the DeepInfra account is a manual step.)
- The projected spend (USD 4.92, 3 full runs + exploratory) is well under the cap. If N rises further so the plan exceeds USD 20, the cap is raised in the same change, never removed.

The cap must be active before the first hosted call of any ticket (DoR).

### Not done

- No vLLM and no self-hosting (record §4.2).
- One base model, no model comparison (record §5).

### Assumptions

- **A1. Same weights.** The Ollama build (`llama3.1-8b-8k`, digest 6811dcd559d9) and DeepInfra's FP8 build are both assumed to derive from Meta's Llama 3.1 8B Instruct weights at Hugging Face commit `0e9e39f2`. Neither provider links its build to that commit. UNVERIFIED.
- **A2. Exploratory run size.** 25 bundles (about 5 % of N_eval = 480). The run ticket fixes the size; the cost text also gives the total for a full exploratory pass.
- **A3. N_eval = 480**, fixed by E2-02 (was a placeholder of 250). Training bundles (206, E2-01) carry no LLM calls.
- **A4. 3,000 input tokens per call**, the record §4.4.1 estimate, above the 2,500 ceiling, so the cost is overstated.
- **A5. Concurrency.** The time estimate assumes 8 concurrent requests within DeepInfra's rate limit. UNVERIFIED.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| Llama 3.3 70B Instruct Turbo on DeepInfra, with 8B for development | Stronger model; the spike already ran it; about €16 worst case | A different size and release from the development model, which needs a sanity comparison; tokenizer equality with Llama 3 unverified; FP8 with no certified commit |
| Hugging Face Inference Endpoint (dedicated) with a commit revision | The only option that pins the exact commit, at full precision; about USD 1/h on one A10G for 8B | A managed serving stack that is close to the "no self-hosted serving" rule; endpoint operations (an endpoint left running bills by the hour); throughput unverified; a structured-output mechanism the spike did not test |
| Together AI serverless | OpenAI-compatible | Llama 3.3 70B at USD 1.04 / 1.04 per 1M tokens comes to about €145 for 4 runs, over budget |
| Greedy decoding (temperature 0) | Close to deterministic | Not the vendor's reference setting, so it would need a rationale of its own; none was found that does not refer to its effect on agreement, which Annex D rules out as a reason |

## Consequences

- E6-01 implements the single client against these variables and records, in every result row, the provider, the provider model ID, the precision, the upstream commit, the sampling parameters, the seed if supported, and the date.
- The development and experiment runs use the same model and the same sampling parameters. The quantization differs, and the shared weights are ASSUMPTION A1.
- The thesis states the limit of the pin: open weights identified by commit, served by a provider that does not certify the commit. Record §4.2 (`LLM_MODEL`) and the risk table (risk 5) carry a note saying so.
- A change of model, revision, provider or sampling parameters after the freeze goes through a METHODS.md changelog entry (DoD, change control).
- E2-02 recomputed the cost with the final N (N_eval = 480): projected USD 4.92 / EUR 4.39 over 3 full runs plus an exploratory run, and the spending cap was raised from USD 5 to USD 20.

## Sources

- DeepInfra pricing, https://deepinfra.com/pricing, checked 2026-10-04.
- DeepInfra model page, https://deepinfra.com/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo, checked 2026-10-04 (precision; the `seed` description in its embedded API schema).
- DeepInfra chat documentation, https://docs.deepinfra.com/chat/overview, checked 2026-10-04.
- Hugging Face Hub API, `https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct`, field `sha`, read 2026-10-04.
- Meta reference sampling defaults: https://github.com/meta-llama/llama-models/blob/main/models/llama3/generation.py (repository HEAD `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, read 2026-10-04); the same defaults appear in https://github.com/meta-llama/llama3/blob/main/example_chat_completion.py.
- Seed check: 8 calls to `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` on DeepInfra, 2026-10-04, estimated cost USD 0.0000192.
- ECB euro reference rates, https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml, rate of 2026-10-02.
- Together AI pricing, https://www.together.ai/pricing, checked 2026-10-04.
- Hugging Face Inference Endpoints pricing and configuration, https://huggingface.co/docs/inference-endpoints/en/pricing and https://huggingface.co/docs/inference-endpoints/en/guides/configuration, checked 2026-10-04.
- `spikes/FINDINGS.md` (E0-01).
