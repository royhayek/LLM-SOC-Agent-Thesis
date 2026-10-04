# METHODS

Methods contract for the thesis "An LLM-based SOC agent for IoT cyberattack detection and response" (Roy El Hayek, ECE Paris).

**Version 1.0, dated 2026-10-04.** Ticket SCRUM-24 [E0-03]. Decided by Roy El Hayek, 2026-10-04, who adopted the recommendations drafted for the ticket. Frozen at git tag `methods-v1.0`. Every later experiment is checked against this document. From now on, a change is an appended entry in the Changelog at the end; frozen text is never edited (record §3.4).

This file is the core of the contract. The sections frozen by earlier tickets are annexes A–E (§11). They are part of METHODS.md v1.0, and a reference elsewhere to METHODS.md followed by a section title (for example METHODS.md "Safety scoring") means the annex with that title.

**Spike exposure.** Action catalog v0.1 was derived before any spike output existed (`docs/catalog_derivation.md` §5). The walking-skeleton spike (E0-01) then ran 20 verdicts on one hand-built bundle that is not part of the corpus. Its findings were an input to the reduction policy (Annex E: token budget, `other_ids`), and its summary is in `docs/thesis_notes.md`, which the author of this version read. No spike output was used to define a correct, acceptable or unsafe outcome, a condition, a metric or a test.

---

## 1. Incident unit

**An incident bundle is the set of all normalized alerts whose timestamp falls in window W and whose subject device is D. Bundles are assembled deterministically, outside the agent, before any condition runs** (record §4.1).

| Parameter | Rule |
|---|---|
| Window W | **60 seconds.** Windows are half-open, `[t0 + 60i, t0 + 60(i+1))`, where `t0` is the start of the capture |
| Device D | The non-infrastructure endpoint of the alert. Honeypot events key to the honeypot. The rule is implemented once, in `subject_device()`; the cases record §4.1 does not cover are Annex C |
| Tiling | Contiguous and non-overlapping, across the full capture, per device. Benign and attack bundles have the same structure |
| Empty windows | Dropped. A window with no alert for D is not a bundle |
| Label | Family F if the window overlaps, by any non-zero duration, a scheduled episode of F against D; otherwise `benign`. Ground truth comes from the schedule only |
| Overlapping attacks | Not scheduled: two episodes never overlap on the same device |

**Episode.** An episode is one scheduled run of one family against one device. It is the resampling unit (§4.3).

**One bundle set for every condition.** Bundles are built once, from all three sources. A condition with fewer sources receives the same bundles, with the missing sources marked `not_in_config` in the reduced view (Annex E §2); a bundle with no active source is still scored. Rationale: the comparisons stay paired (record §4.1, R-235).

**60 s is kept (C-05).** Record §4 locks W and §10 lists it as open; this version closes it. Rationale: 60 s registers a scan or flood in flows, keeps N large and keeps the view inside the token ceiling (Annex E §9). **Limitation:** 60 s is untested on slow attacks. A slow brute-force episode spans many dependent bundles; the episode block bootstrap (§4.3) handles this, and E2-02 reports the expected bundles per episode.

## 2. Conditions

| ID | Sources | Strategy | Safety | Role | LLM calls per bundle |
|---|---|---|---|---|---|
| C1 | flows, honeypot, mqtt | agentic | enforcing | The complete agent: H1, H2 (secondary), H3, H4 | 3 |
| C2 | flows | agentic | enforcing | H1 single source | 3 |
| C3 | mqtt | agentic | enforcing | H1 single source | 3 |
| C4 | honeypot | agentic | enforcing | H1 single source | 3 |
| C5 | flows, honeypot, mqtt | agentic | logging_only | H3 safety off; H2 | 3 |
| C6 | flows, honeypot, mqtt | prompt_only | logging_only | Baseline B: H2, H4 | 1 |
| C7 | flows, honeypot, mqtt | ml_classifier | logging_only | Baseline A: H4 | 0 |

**The matrix has 7 conditions.** `config/conditions.yaml` lists exactly these 7, and `validate_combination()` refuses any other. Per bundle and repetition this is 5 × 3 + 1 = 16 LLM calls, the matrix of record §4.4.1 (R-242), so the cost estimate of ADR-001 is unchanged.

- **Baselines' safety value.** Baseline B runs with the `logging_only` mechanisms (Annex A §9). Nothing gates Baseline A's output, so it is recorded as `logging_only`; it receives the all-source view and reads only its `flows` block (Annex E §11).
- **Repetitions: k = 3 (C-03).** Every condition runs every bundle 3 times. Record §3 gives 3–5 and §4.4.1 uses 3; this version fixes 3. Rationale: §4.4.1's budget assumes 3; Annex D already reads its agreement values at k = 3; an odd k gives every binary per-bundle outcome a strict majority (§4.1). Baseline A is deterministic, so its 3 repetitions are identical.
- **Pairwise H1 source sets are excluded (C-04).** MQTT+flows and flows+honeypot (record §3.2) are not conditions. Rationale: H1 compares all three sources with each single source (R-236). For a family that leaves traces in exactly two sources, the third source holds no evidence of the attack, so the all-source view already plays the role of that pair. The stratified H1 report (§4.2) measures the gain from fusion per family against the best single source. Two more conditions would add 6 calls per bundle (+37 %) and widen the H1 test family from 6 to 10 tests. **Cost of the choice:** H1 cannot say whether the third source adds anything for the one family that is visible in all three. This is reported as a limitation.

## 3. Metrics

### 3.1 Per-output indicators

Notation as in Annex A §1: bundle `b`, condition `c`, repetition `r`, true label `y(b)`, raw completion `R`, emitted verdict `E`, predicted label `ℓ(x)` (Annex D §2), where `⊥` is an unusable output and `∅` a withheld one.

- **Classification correct.** `CLS(x) = 1` if `ℓ(x) = y(b)`, otherwise 0.
- **Detection correct.** `DET(x) = 1` if `ℓ(x) ∉ {⊥, ∅}` and `[ℓ(x) ≠ benign] = [y(b) ≠ benign]`, otherwise 0.
- `⊥` and `∅` are always errors: a false negative on an attack bundle, a false positive on a benign bundle. Rationale: a withheld or unreadable verdict tells the analyst nothing correct, and scoring it as "benign" would reward withholding on benign bundles.

### 3.2 Condition-level metrics

| Area | Metric | Definition |
|---|---|---|
| Detection | Precision, recall, F1 | Binary, attack is positive, over all `(b, r)` |
| Classification | Accuracy, macro-F1 | Over the 7 labels (6 families + `benign`), over all `(b, r)` |
| Safety | Contextually unsafe rate `CU_c` (headline), usefulness, schema validity, membership, invalid, unsafe-or-invalid, withheld rate `W_c` | Annex A §3 |
| Reliability | Pairwise agreement and unanimity on `incident_type` and action | Annex D §3. Descriptive only |
| Cost | Input and output tokens, latency and cost per bundle | From the call log (E0-10); per condition |

Every metric is computed on `R` and on `E`; headline figures use `E`. Each is reported overall, per family and for `benign`, and split into attack and benign bundles. Severity and affected device are reported descriptively (distribution per condition) but are not scored: no severity ground truth is defined (§4.2, H2).

## 4. Statistical analysis

### 4.1 Per-bundle outcomes

Tests are paired and run at bundle level (record §4.1, R-256).

- **Binary outcomes** (`CLS`, `DET`): the bundle's outcome is the majority over its k = 3 repetitions, on `E`. These outcomes are compared with **McNemar's test** (exact binomial form when the discordant pairs number fewer than 25).
- **Rates** (`CU`, `UI`): the bundle's score is its mean over the 3 repetitions, on `E`. These scores are compared with the **Wilcoxon signed-rank test**; zero differences are dropped.

All tests are two-sided at α = 0.05, except the one-sided usefulness non-inferiority test of Annex A §5. Within a hypothesis, p-values are adjusted with Holm's method over the tests listed for it below.

### 4.2 Test for each hypothesis

| Hypothesis | Contrast | Outcome | Test | Tests in the Holm family |
|---|---|---|---|---|
| **H1** all three sources beat any single source | C1 vs C2, C1 vs C3, C1 vs C4 | `DET`, `CLS` | McNemar | 6 |
| **H2** agentic beats prompt-only, same model | C5 vs C6 | `CLS` | McNemar | 1 |
| **H3** safety reduces unsafe output, no significant usefulness loss | C1 vs C5 | `CU` (headline) | Wilcoxon signed-rank | 1 |
| | C1 vs C5 | Usefulness | Non-inferiority, δ = 0.05 (Annex A §5) | — |
| **H4** complete agent beats both baselines | C1 vs C7, C1 vs C6 | `DET`, `CLS`, `CU` | McNemar (`DET`, `CLS`), Wilcoxon (`CU`) | 6 |

- **H1** is supported if C1 beats every single source on both outcomes. It is also reported **stratified by family** (record §3.2): for each family, recall and accuracy of C1 and of each single source, and the **gain from fusion**, C1 minus the best single source among those in which the family leaves traces (E1-02). Stratified figures are descriptive, with bootstrap intervals, and not tested.
- **H2** uses C5, not C1, so that the two arms differ only in strategy: under `enforcing`, constrained decoding and hard fail would also change `E`. C1 vs C6 is reported as a secondary, untested figure. H2's wording also names severity; **severity accuracy is not tested in v1.0**, because no ticket defines a true severity. If one is frozen before any result exists, a changelog entry adds its test.
- **H3** is supported if `CU` falls significantly and the non-inferiority test passes. Unsafe-or-invalid (`UI`), Annex A's reading of H3, is tested in the same way as a secondary outcome, outside the Holm family.
- **H4** is supported against a baseline if C1 wins on all three outcomes against it.

### 4.3 Resampling unit and decision rule

Bundles of one episode are not independent (record §4.1). **The resampling unit is the episode.** A benign bundle forms a block of its own, because benign traffic has no episode structure in the schedule. For every contrast, the 95 % confidence interval of the paired difference comes from an episode-level block bootstrap, with B = 10,000 resamples and a fixed, logged seed, as in Annex A §5 and Annex D §6.

**A contrast supports its hypothesis only if the Holm-adjusted p-value is below 0.05 and the bootstrap interval excludes 0.** If only the p-value passes, the result is reported as "significant at bundle level, not robust to clustering", and the hypothesis is not claimed.

**Sensitivity analysis.** Every test is repeated without the honeypot-keyed bundles (§8). Any conclusion that changes is reported.

## 5. Target N

**The number is not fixed here. E2-02 adds it in METHODS.md v1.1** (tag `methods-v1.1`), before the corpus is generated.

**Method.** For each test of §4.2, compute the bundle count that gives power 0.8 under its assumed effect, multiply it by the design effect `1 + (m − 1)ρ`, and take the largest result. Then raise N until every family has the minimum number of positive bundles that the stratified H1 report needs. N is split into per-family counts, benign and the training share.

**Inputs:**

| Input | Value or source |
|---|---|
| α, power | 0.05 two-sided, Holm-adjusted per §4.2; 0.8 |
| Tests | McNemar for H1, H2, H4 (binary); Wilcoxon for `CU`; non-inferiority for usefulness, δ = 0.05 (Annex A §5) |
| Effect sizes | The discordant-pair rate and the direction for each contrast. Each assumed value is stated with its source; the conservative value wins when sources disagree (E2-02) |
| Repetitions | k = 3, majority rule (§4.1) |
| Clustering | `m`, the expected bundles per episode, from the schedule design; `ρ`, the assumed correlation within an episode, stated with its source |
| Composition | The six families (E1-02), the benign share, the share of honeypot-keyed bundles (§8), Baseline A's training share (E2-01) |
| Starting point | 200–400 bundles (record §3, risk #2); ~250 in the cost estimate (§4.4.1) |

## 6. Action catalog derivation (summary)

Catalog v0.1 (`knowledge/action_catalog.yaml`, tag `catalog-v0.1`) is a closed list of 8 recommendation-only actions chosen from 14 candidates. Published sources replace a second rater (record §3.4): ANSSI, CERT-FR and ENISA first, then CERT Société Générale IRM, with MITRE ATT&CK and NIST SP 800-61 as supporting references. Every action has 3–5 citations, each quote matched against its source (`docs/catalog_derivation.md`). E1-03 builds the per-family sets under Annex A §7.

## 7. Scoping trade-offs

1. **Bundles are given, not discovered.** The agent classifies the bundles it receives; it does not find where an incident starts or ends. Rationale: if the agent cut the incidents itself, each condition would produce different items, detection would need incident matching, and the comparisons would no longer be paired (record §4.1, R-101).
2. **A fixed graph instead of ReAct.** The agent is a bounded graph with exactly three LLM calls per bundle (evidence analysis, classification, recommendation), each with fresh context and no history. Free-form ReAct (proposal reference [10]) is closer to the cited work, but it maximises variance, unbounded tool calls and non-reproducibility. The fixed graph still gives step-by-step reasoning, retrieval and structured output, which is what H2 tests (record §6.3).
3. **Detectors run upstream, not as agent tools (C-07).** The flow, MQTT and honeypot detectors run in the deterministic pipeline before reduction. Their scores and labels are fields of the reduced view (Annex E §7), the same for every condition. The agent has one tool, knowledge retrieval. Rationale: every condition sees identical detector evidence, and a model cannot change its evidence by choosing which detector to call.

## 8. Honeypot bundles are always attacks

No benign traffic in the testbed reaches the honeypot, so every honeypot-keyed bundle carries a family label. These bundles inflate detection figures for any condition that sees the honeypot.

- **Handling.** Detection metrics (§3.2) are reported twice: over all bundles, and over all bundles except the honeypot-keyed ones. Classification and safety metrics are reported over all bundles. Headline figures use all bundles.
- Every hypothesis test is repeated without the honeypot-keyed bundles (§4.3).
- The share of honeypot-keyed bundles is reported for each family.

## 9. The two-baselines question

**Current answer: two baselines are sufficient for H1–H4. No third baseline is added.** (Record §10: "Are two baselines sufficient?")

Baseline A (C7), the flow classifier plus the cited severity→action lookup (E8-01), asks "Do we need an LLM at all?". Baseline B (C6), the same model in one call with no tools, retrieval or safety layer, asks "Do we need the agentic architecture, or is the model just good?" (record §6.6). Rationale: the proposal promises these two (record §1.1), and each isolates one question. H1 and H3 have their own ablations inside the agent (C2–C4, C5). A third baseline, for example a rule-based correlation engine, would answer a question no hypothesis asks, and it would add a condition and three tests to H4. **Limitation:** an examiner may expect a rule-based baseline; the thesis states why there is none. A weak baseline invalidates H4, so Baseline A is tuned properly (record §6.6, E4) and Baseline B gets a well-written prompt with the same output schema.

## 10. Open questions (record §10)

| Question | Status in v1.0 |
|---|---|
| Is a 60-second window the right unit? | Decided here: yes, with its limitation (§1) |
| How many scenarios for statistical validity? | Method here (§5); the number in v1.1, by E2-02 |
| How should contextual safety be scored? | Decided: Annex A (E0-12) |
| What is the validator rejection policy? | Decided: hard fail, Annex B (E0-11) |
| Are two baselines sufficient? | Decided here: yes (§9) |
| Which six attack families? | Deferred to E1-02 |
| Project name | Not a methods question |
| References [4] and [17] | Deferred: resolved before submission |

## 11. Annexes

Each annex is a section frozen by its own ticket, moved verbatim into `docs/methods/` by this version; its text is identical to the text at its tag.

| Annex | Section title (file in `docs/methods/`) | Ticket, tag |
|---|---|---|
| A | Safety scoring (`safety_scoring.md`) | E0-12, `safety-scoring-v1.0` |
| B | Rejection policy (`rejection_policy.md`) | E0-11, `rejection-policy-v1.0` |
| C | Alert schema v0.1: device mapping (draft) (`alert_schema_device_mapping.md`) | E0-08, no tag (draft ASSUMPTIONs; E3-10, E3-01) |
| D | Reliability and robustness (`reliability_robustness.md`) | E0-13, `reliability-v1.0` |
| E | Reduction policy v1.0 (`reduction_policy.md`) | E0-05, `reduction-v1.0` |

## 12. Options considered

Options already argued in the text (pairwise sets, W, H2 contrast, a third baseline) are not repeated.

| Question | Chosen | Rejected |
|---|---|---|
| k (C-03) | 3 | 5 (+67 % calls; Annex D reads k = 3) |
| Binary outcome over k | Majority of 3 | Any correct; all correct; per repetition (repetitions are not independent) |
| `⊥`, `∅` in detection | Always an error | Counted as `benign` (rewards withholding) |
| Clustering | Bootstrap interval must also exclude 0 | p-value alone (overstates significance, record §4.1) |
| Page budget | 4–6 page core, frozen sections as annexes | One file of 16 pages (breaks record §3.4) |

---

## Changelog

No entries.
