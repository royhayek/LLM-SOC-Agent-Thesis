# E0-01 findings: walking-skeleton spike

There were 20 runs on one hand-written bundle (SSH password guessing against the honeypot `hp-ssh-01`; honeypot and flows active, MQTT `no_alerts`). There was one prompt (v1) and one schema-constrained call per run, at temperature 0 with no seed. The data is in `results.csv` and `logs/`.

| Model | Validity | Agreement | Correctness | Mean tokens in / out | Mean latency |
|---|---|---|---|---|---|
| Local: `llama3.1-8b-8k` (Llama 3.1 8B, Q4_K_M, digest 6811dcd559d9), Ollama 0.23.2 | 10/10 | 10/10 | 10/10 | 2116 / 101 | 5.44 s (4.31 s after the first run, which loaded the model) |
| Hosted: `meta-llama/Llama-3.3-70B-Instruct-Turbo` (FP8), DeepInfra | 10/10 | 10/10 | 10/10 | 2116 / 85 | 5.32 s (from 3.99 to 9.41 s) |

- **Agreement** is the share of runs equal to the modal verdict (incident type, severity, device, action).
- **Correctness** compares `incident_type` and `affected_device` only. Severity is recorded but not scored.
- **Modal verdicts:** both models gave `ssh_password_guessing`, `high` and `hp-ssh-01`. The local model recommended `reset_credentials`; the hosted model recommended `block_source_ip`.
- **Hosted cost:** about USD 0.0024 at the listed price (USD 0.10 in / 0.32 out per million tokens). The spending cap was USD 5.

**Caveats**
- **Two mechanisms, not just two models.** Validity compares Ollama's structured output with DeepInfra's `json_schema` response format, so it measures both the mechanisms and the models.
- **At temperature 0, agreement only shows run-to-run determinism.** It says nothing about stability under sampling.
- **This bundle was easy.** One clear-cut case cannot separate the two models.

## Fields the model asked for or invented

None. No output added a field, and no output cited an alert ID that is not in the bundle. Neither model has a free-text field in which to ask for anything. Below are the gaps the outputs reveal, which are this analysis, not the model's request:

1. **Device role and criticality.** The bundle does not say that `hp-ssh-01` is a honeypot, or how critical it is. The local model recommended resetting credentials on a honeypot where no login succeeded.
2. **Links between sources.** Both models cited only the six `login_failed` alerts and ignored the three flow alerts, although their source ports match the honeypot sessions. Nothing in the format ties a flow to a session.
3. **Use of source states.** The verdict has no way to show whether the model took the MQTT `no_alerts` state into account. For H1 this has to be visible.
4. **Confidence.** It was the same on every run (1.0 local, 0.9 hosted), so it carries no information here.

## Source states (input for the alert schema, E0-08)

A bundle's `sources` block gives each source one of three states:
- `active`: the source is running and sent alerts in this window.
- `no_alerts`: the source is running and saw nothing in this window.
- `not_in_config`: the source is switched off in this experiment condition. Reserved; not used in this bundle.

## Recommendations

1. **Model.** Both models are adequate on this case, so the spike cannot choose between them. Develop on the local 8B model. Decide the experiment model in E0-06 on harder pilot bundles. Weigh one point there: the hosted Turbo is FP8 and reports no revision or fingerprint, which weakens the reproducibility claim (record §4.2).
2. **Token budget.** 13 alerts already need about 2,116 input tokens, above the 2,000-token budget in record §9. Each alert costs roughly 145 tokens in indented JSON. Serialize compactly, and cap alerts per source in the reduction policy (E0-05).
3. **Alert schema (E0-08).** Add device role and criticality, a link from flows to honeypot sessions (or an explicit correlation key), and the three source states above.
