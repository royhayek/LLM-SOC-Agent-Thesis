# METHODS

Methods contract for the thesis "An LLM-based SOC agent for IoT cyberattack detection and response" (Roy El Hayek, ECE Paris). **Version 1.0, dated 2026-10-04.** Ticket SCRUM-24 [E0-03]. Decided by Roy El Hayek, 2026-10-04, who adopted the recommendations drafted for the ticket. Frozen at git tag `methods-v1.0`. Every later experiment is checked against it. A change is an appended Changelog entry; frozen text is never edited (record §3.4).

This file is the core of the contract. The sections frozen by earlier tickets are annexes A–F (§11). They are part of METHODS.md v1.0, and a reference elsewhere to METHODS.md followed by a section title (for example METHODS.md "Safety scoring") means the annex with that title.

**Spike exposure.** Action catalog v0.1 was derived before any spike output existed (`docs/catalog_derivation.md` §5). The walking-skeleton spike (E0-01) later ran 20 verdicts on one hand-built bundle outside the corpus. Its findings fed the reduction policy (Annex E: token budget, `other_ids`), and the author of this version read its summary in `docs/thesis_notes.md`. No spike output was used to define a correct, acceptable or unsafe outcome, a condition, a metric or a test.

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

**Episode:** one scheduled run of one family against one device, the resampling unit (§4.3). **One bundle set for every condition.** Bundles are built once, from all three sources. A condition with fewer sources receives the same bundles, with the missing sources marked `not_in_config` in the reduced view (Annex E §2); a bundle with no active source is still scored. Rationale: the comparisons stay paired (record §4.1, R-235).

**60 s is kept (C-05).** Record §4 locks W and §10 lists it as open; this version closes it. Rationale: 60 s registers a scan or flood in flows, keeps N large and keeps the view inside the token ceiling (Annex E §9). **Limitation:** 60 s is untested on slow attacks. A slow brute-force episode spans many dependent bundles; the episode block bootstrap (§4.3) handles this, and E2-02 reports the expected bundles per episode.

## 2. Conditions

| ID | Sources | Strategy | Safety | Role |
|---|---|---|---|---|
| C1 | flows, honeypot, mqtt | agentic | enforcing | Complete agent: H1, H3, H4 |
| C2 | flows | agentic | enforcing | H1 single source |
| C3 | mqtt | agentic | enforcing | H1 single source |
| C4 | honeypot | agentic | enforcing | H1 single source |
| C5 | flows, honeypot, mqtt | agentic | logging_only | Safety off: H2, H3 |
| C6 | flows, honeypot, mqtt | prompt_only | logging_only | Baseline B: H2, H4 |
| C7 | flows, honeypot, mqtt | ml_classifier | logging_only | Baseline A: H4 |

**The matrix has 7 conditions.** `config/conditions.yaml` lists exactly these 7, and `validate_combination()` refuses any other. Agentic conditions make 3 LLM calls per bundle, Baseline B 1 and Baseline A none: 5 × 3 + 1 = 16 calls per bundle and repetition, the matrix of record §4.4.1 (R-242), so the cost estimate of ADR-001 is unchanged.

- **Baselines' safety value.** Baseline B runs with the `logging_only` mechanisms (Annex A §9). Nothing gates Baseline A's output, so it is also `logging_only`; it reads only the `flows` block (Annex E §11).
- **Repetitions: k = 3 (C-03).** Record §3 gives 3–5; this version fixes 3. Rationale: §4.4.1's budget assumes 3, Annex D reads its agreement values at k = 3, and an odd k gives every binary per-bundle outcome a strict majority (§4.1). k = 5 would add 67 % calls. Baseline A is deterministic, so its 3 repetitions are identical.
- **Pairwise H1 source sets are excluded (C-04).** MQTT+flows and flows+honeypot (record §3.2) are not conditions. Rationale: H1 compares all three sources with each single source (R-236). For a family that leaves traces in exactly two sources, the third holds no evidence of the attack, so the all-source view already plays the role of that pair; the stratified H1 report (§4.2) measures the gain from fusion per family. Two more conditions would add 37 % calls and widen the H1 test family from 6 to 10. **Limitation:** H1 cannot say whether the third source adds anything for the family visible in all three.

## 3. Metrics

### 3.1 Per-output indicators

Notation as in Annex A §1: bundle `b`, condition `c`, repetition `r`, true label `y(b)`, raw completion `R`, emitted verdict `E`, predicted label `ℓ(x)` (Annex D §2), where `⊥` is an unusable output and `∅` a withheld one.

- **Classification correct.** `CLS(x) = 1` if `ℓ(x) = y(b)`, otherwise 0.
- **Detection correct.** `DET(x) = 1` if `ℓ(x) ∉ {⊥, ∅}` and `[ℓ(x) ≠ benign] = [y(b) ≠ benign]`, otherwise 0.
- `⊥` and `∅` are always errors: a false negative on an attack bundle, a false positive on a benign bundle. Rationale: a withheld or unreadable verdict tells the analyst nothing correct, and scoring it as "benign" would reward withholding on benign bundles.

### 3.2 Condition-level metrics

- **Detection:** precision, recall and F1, binary with attack as positive, over all `(b, r)`.
- **Classification:** accuracy and macro-F1 over the 7 labels (6 families + `benign`), over all `(b, r)`.
- **Safety:** the contextually unsafe rate `CU_c` (headline), usefulness, schema validity, membership, invalid, unsafe-or-invalid and the withheld rate `W_c` (Annex A §3).
- **Reliability:** pairwise agreement and unanimity on `incident_type` and action (Annex D §3), descriptive only.
- **Cost:** input and output tokens, latency and cost per bundle, from the call log (E0-10).

Every metric is computed on `R` and `E`, headline on `E`, overall, per label, and split into attack and benign bundles. Severity and affected device are reported descriptively, not scored: no true severity is defined (§4.2).

## 4. Statistical analysis

### 4.1 Per-bundle outcomes

Tests are paired and run at bundle level (record §4.1, R-256).
- **Binary outcomes** (`CLS`, `DET`): the bundle's outcome is the majority over its k = 3 repetitions, on `E`. Rejected: any correct or all correct (biased), and one test per repetition (repetitions are not independent). These outcomes are compared with **McNemar's test** (exact binomial form when the discordant pairs number fewer than 25).
- **Rates** (`CU`, `UI`): the bundle's score is its mean over the 3 repetitions, on `E`. These scores are compared with the **Wilcoxon signed-rank test**; zero differences are dropped.

All tests are two-sided at α = 0.05, except the one-sided usefulness non-inferiority test of Annex A §5. Within a hypothesis, p-values are adjusted with Holm's method over the tests listed for it below.

### 4.2 Test for each hypothesis

| Hypothesis | Contrast | Outcome | Test |
|---|---|---|---|
| **H1** all sources beat any single one | C1 vs C2, C3, C4 | `DET`, `CLS` | McNemar |
| **H2** agentic beats prompt-only | C5 vs C6 | `CLS` | McNemar |
| **H3** safety cuts unsafe output, no usefulness loss | C1 vs C5 | `CU` (headline); usefulness | Wilcoxon; non-inferiority, δ = 0.05 (Annex A §5) |
| **H4** agent beats both baselines | C1 vs C7, C1 vs C6 | `DET`, `CLS`, `CU` | McNemar; Wilcoxon for `CU` |

The Holm families have 6 tests for H1 and H4 and 1 for H2 and H3 (`CU`); the non-inferiority test is outside them.

- **H1** is supported if C1 beats every single source on both outcomes. It is also reported **stratified by family** (record §3.2): recall and accuracy per family for C1 and each single source, and the **gain from fusion**, C1 minus the best single source in which the family leaves traces (E1-02). Stratified figures are descriptive, with bootstrap intervals.
- **H2** uses C5, not C1, so the arms differ only in strategy; under `enforcing`, constrained decoding and hard fail would also change `E`. C1 vs C6 is a secondary, untested figure. **Severity accuracy is not tested in v1.0**, although H2 names it, because no ticket defines a true severity. If one is frozen before any result exists, a changelog entry adds its test.
- **H3** is supported if `CU` falls significantly and the non-inferiority test passes. Unsafe-or-invalid (`UI`), Annex A's reading of H3, is tested in the same way as a secondary outcome, outside the Holm family.
- **H4** is supported against a baseline if C1 wins on all three outcomes against it.

### 4.3 Resampling unit and decision rule

Bundles of one episode are not independent (record §4.1). **The resampling unit is the episode.** A benign bundle forms a block of its own, because benign traffic has no episode structure in the schedule. For every contrast, the 95 % interval of the paired difference comes from an episode-level block bootstrap (B = 10,000, fixed and logged seed), as in Annex A §5.

**A contrast supports its hypothesis only if the Holm-adjusted p-value is below 0.05 and the bootstrap interval excludes 0.** If only the p-value passes, the result is reported as "significant at bundle level, not robust to clustering", and the hypothesis is not claimed.

**Sensitivity analysis.** Every test is repeated without the honeypot-keyed bundles (§8). Any conclusion that changes is reported.

## 5. Target N

**The number is not fixed here. E2-02 adds it in METHODS.md v1.1** (tag `methods-v1.1`), before the corpus is generated.

**Method.** For each test of §4.2, compute the bundle count giving power 0.8 under its assumed effect, multiply by the design effect `1 + (m − 1)ρ`, and take the largest result. Raise N until every family has the positive bundles the stratified H1 report needs, then split it into per-family, benign and training counts.

**Inputs.** α = 0.05, Holm-adjusted per §4.2, and power 0.8. The tests of §4.2, including non-inferiority at δ = 0.05. For each contrast, the assumed discordant-pair rate and direction, each stated with its source; the conservative value wins when sources disagree (E2-02). k = 3 with the majority rule. `m`, the expected bundles per episode, from the schedule design, and `ρ`, the assumed correlation within an episode, with its source. The six families (E1-02), the benign share, the honeypot-keyed share (§8) and Baseline A's training share (E2-01). Starting point: 200–400 bundles (record §3, risk #2), ~250 in the cost estimate (§4.4.1).

## 6. Action catalog derivation (summary)

Catalog v0.1 (`knowledge/action_catalog.yaml`, tag `catalog-v0.1`) holds 8 recommendation-only actions chosen from 14 candidates. Published sources replace a second rater (record §3.4): ANSSI, CERT-FR and ENISA first, then CERT Société Générale IRM, with MITRE ATT&CK and NIST SP 800-61 in support. Each action has 3–5 citations, every quote matched against its source (`docs/catalog_derivation.md`). E1-03 builds the per-family sets under Annex A §7.

## 7. Scoping trade-offs

1. **Bundles are given, not discovered.** The agent classifies the bundles it receives; it does not find where an incident starts or ends. Rationale: otherwise each condition would produce different items, detection would need incident matching, and the comparisons would not be paired (record §4.1, R-101).
2. **A fixed graph instead of ReAct.** Exactly three LLM calls per bundle (evidence analysis, classification, recommendation), each with fresh context and no history. Free-form ReAct (proposal reference [10]) is closer to the cited work but maximises variance, unbounded tool calls and non-reproducibility. The graph still gives step-by-step reasoning, retrieval and structured output, which is what H2 tests (record §6.3).
3. **Detectors run upstream, not as agent tools (C-07).** The detectors run in the deterministic pipeline before reduction; their scores and labels are fields of the reduced view (Annex E §7). The agent's one tool is knowledge retrieval. Rationale: every condition sees identical detector evidence, and no model can change its evidence by choosing which detector to call.

## 8. Honeypot bundles are always attacks

No benign traffic reaches the honeypot, so every honeypot-keyed bundle is an attack bundle, which inflates detection figures for any condition that sees the honeypot.

**Handling.** Detection metrics (§3.2) are reported twice: over all bundles, and without the honeypot-keyed ones. Classification and safety metrics use all bundles, and headline figures use all bundles. Every hypothesis test is repeated without the honeypot-keyed bundles (§4.3), and their share is reported for each family.

## 9. The two-baselines question

**Current answer: two baselines are sufficient for H1–H4. No third baseline is added.**

Baseline A (C7), the flow classifier plus the cited severity→action lookup (E8-01), asks "Do we need an LLM at all?". Baseline B (C6), the same model in one call with no tools, retrieval or safety layer, asks "Do we need the agentic architecture, or is the model just good?" (record §6.6). Rationale: the proposal promises these two (record §1.1), each isolates one question, and H1 and H3 have their own ablations inside the agent (C2–C5). A third, rule-based baseline would answer a question no hypothesis asks and add a condition and three H4 tests. **Limitation:** an examiner may expect one; the thesis states why there is none. Both baselines are built to be strong (record §6.6): Baseline A is tuned properly (E4), and Baseline B gets a well-written prompt with the same output schema.

## 10. Open questions (record §10)

- **Decided here:** "Is a 60-second window the right unit?" (yes, §1); "Are two baselines sufficient?" (yes, §9).
- **Decided earlier:** contextual safety scoring (Annex A, E0-12); the rejection policy (hard fail, Annex B, E0-11).
- **Deferred:** the number of scenarios (§5; v1.1 by E2-02); the six families (E1-02); references [4] and [17] (before submission). The project name is not a methods question.

## 11. Annexes

Each annex is a section frozen by its own ticket, moved verbatim into `docs/methods/`, identical to its text at its tag. Kept here, they would make this file 16 pages, against record §3.4's 4–6.

| Annex | Section title (file in `docs/methods/`) | Ticket, tag |
|---|---|---|
| A | Safety scoring (`safety_scoring.md`) | E0-12, `safety-scoring-v1.0` |
| B | Rejection policy (`rejection_policy.md`) | E0-11, `rejection-policy-v1.0` |
| C | Alert schema v0.1: device mapping (draft) (`alert_schema_device_mapping.md`) | E0-08, no tag (draft) |
| D | Reliability and robustness (`reliability_robustness.md`) | E0-13, `reliability-v1.0` |
| E | Reduction policy v1.0 (`reduction_policy.md`) | E0-05, `reduction-v1.0` |
| F | Testbed capture settings (draft) (`testbed_capture_settings.md`) | E0-07, no tag (draft) |

---

## Changelog

No entries.
