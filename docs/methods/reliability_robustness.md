<!-- METHODS.md v1.0, Annex D. Moved verbatim from METHODS.md by SCRUM-24 [E0-03]. The text below the next line is frozen and unchanged (source: `reliability-v1.0`). -->

## Reliability and robustness

Ticket SCRUM-114 [E0-13]. Decided by Roy El Hayek, 2026-10-04. Frozen at git tag `reliability-v1.0`. Answers R-020 to R-022 and conflict C-09: Objective 5 promises an evaluation of reliability, and the brief adds robustness, but neither was defined. Traces to record §3, risks 5 and 7.

Inputs: record §4.4.1 (the experiment matrix and its `k` repetitions); METHODS.md "Safety scoring" (tag `safety-scoring-v1.0`), whose notation (`b`, `c`, `r`, `k`, `N`, `R`, `E`, `∅`, `a(x)`, `⊥`, `SV`, `W_c`) is used here unchanged, except for the one extension stated in §2; METHODS.md "Rejection policy" (tag `rejection-policy-v1.0`); the output schema of record §6.5.

### 1. What reliability means here

**Reliability is the stability of a condition's output when the same bundle is run again under the same configuration.** It is measured only from the `k` repetitions that the matrix already contains (record §4.4.1). It has three parts:

1. **Validity:** how often the output is well-formed. This is schema validity `SV_c` and the withheld rate `W_c`, defined in "Safety scoring" §3 and reused here without change.
2. **Classification agreement:** how often repetitions give the same `incident_type`.
3. **Action agreement:** how often repetitions give the same recommended action.

Reliability is not reproducibility. Reproducibility, the ability to repeat the whole experiment, is handled by pinning the model by revision and recording every run's configuration (record §3 risk 5, §4.2). Reliability is not correctness either: a condition can agree with itself on a wrong answer. Agreement is therefore always reported next to the accuracy and safety figures, never instead of them.

### 2. Notation

- `ℓ(x)`: the predicted `incident_type` of output `x` (record §6.5), one of the six families or `benign`. `ℓ(x) = ⊥` when `SV(x) = 0` and `x ≠ ∅`. `ℓ(∅) = ∅`.
- `a(x)`: the recommended action after the mapping of "Safety scoring" §6.2, a catalog ID or `⊥`. `a(∅) = ∅`.
- `f`: either `ℓ` or `a`. Every formula below is computed once for each.
- `x_r = x(b, c, r)`, for `r = 1..k`.

`⊥` (unusable output) and `∅` (withheld output) are **values like any other**: two repetitions that are both withheld agree. Validity is measured by `SV_c` and `W_c`, so agreement measures stability only and does not count a failure twice. A condition that fails in the same way every time is stable, and its low validity shows beside it. The conditional figure in §3.3 removes these values.

**Extension of "Safety scoring" §1, for agreement only:** a withheld output keeps its own value `∅` instead of `⊥`, so a withheld repetition and an unmappable one disagree. Every other metric uses the "Safety scoring" definitions as they stand.

### 3. Formulas

Each formula requires `k ≥ 2`. `k` is fixed by the target-N calculation (E2-02), not here.

**3.1 Pairwise agreement (primary).** For one bundle and condition:

`PA_f(b,c) = (2 / (k(k − 1))) Σ_{1 ≤ r < s ≤ k} 1[f(x_r) = f(x_s)]`

This is the share of pairs of repetitions that give the same value. For a condition:

`PA_f,c = (1/N) Σ_b PA_f(b,c)`

**3.2 Unanimity (secondary).** `UN_f(b,c) = 1` if `f(x_1) = … = f(x_k)`, otherwise 0. `UN_f,c = (1/N) Σ_b UN_f(b,c)`.

**3.3 Conditional agreement.** `PA_f,c | usable` is `PA_f,c` computed only over the bundles where none of the `k` values of `f` is `⊥` or `∅`. The share of bundles it keeps is reported beside it. This mirrors `CU_c | a ≠ ⊥` in "Safety scoring" §3: without it, a condition that often fails the same way would look stable.

With `k = 3`, `PA_f(b,c)` can only be 1 (three equal values), 1/3 (two equal) or 0 (three different). Because the per-bundle values are so coarse, the share of bundles at each value is reported with the mean.

Every formula is computed on both `R` and `E`. Headline figures use `E`, as in "Safety scoring" §3. Under `enforcing`, `E` and `R` differ only where the rejection policy withheld an output (`E = ∅`).

### 4. Interpretation depends on the sampling parameters

Agreement measures how much the output varies between runs, so it depends on the sampling parameters. Those are fixed by ADR-001 (E0-06) and recorded per run (record §4.2), not here. If the experiment runs with greedy decoding (temperature 0), agreement measures only the nondeterminism left in the serving stack. In that case it is expected to be close to 1, and the report says so. The walking-skeleton spike ran at temperature 0 (`docs/thesis_notes.md`, E0-01). This section does not choose the temperature, and the temperature is not changed to make agreement informative.

### 5. Conditions and baselines

| | Agent (`enforcing` / `logging_only`, each source set) | Baseline A (classifier + E8-01 lookup) | Baseline B (same model, one call) |
|---|---|---|---|
| `SV_c`, `W_c` | "Safety scoring" §3 | 1 and 0 by construction | "Safety scoring" §3, with `E = R` |
| `PA`, `UN` on `ℓ` and `a` | §3, on `R` and `E` | 1 by construction (deterministic); reported as such, not as a result | §3, on `R` (`E = R`) |
| Conditional agreement | §3.3 | Not reported | §3.3 |

### 6. Reporting

- For each condition: `SV_c`, `W_c`, `PA_ℓ,c`, `PA_a,c`, `UN_ℓ,c`, `UN_a,c` and the two conditional figures, on `E`, plus the same table on `R`.
- Each figure is given overall, per family and for `benign`, and split into attack and benign bundles, as in "Safety scoring" §10.
- Each `PA` figure has a 95 % confidence interval from an episode-level block bootstrap: the resampling unit is the episode (record §4.1), with B = 10,000 resamples and a fixed, logged seed, as in "Safety scoring" §5.
- **Reliability is descriptive.** It is reported per condition, never as a headline, and no hypothesis (H1–H4) is tested on it.

### 7. Robustness

**Robustness is out of scope.** The only robustness test the project plans is prompt injection through honeypot text (record §3 risk 7), and that experiment is stretch-only (record §5, E9-12) and needs LLM runs beyond the planned matrix. This is reported as a limitation. The defensive design (strict delimiting, validation as a hard gate) stays in place either way. If E9-12 runs, its metric is added by a changelog entry before any of its results exist.

### 8. Cost

**These metrics need no extra LLM call.** They are computed from the `k` repetitions already in the matrix (record §4.4.1: 250 bundles × 16 calls × `k` repetitions). Robustness is out of scope, so it adds no calls either. ADR-001 (E0-06) needs no row in its cost table for this section.

### 9. Options considered

| Question | Chosen | Rejected |
|---|---|---|
| Field compared | `incident_type` and the recommended action, separately | Action only (ignores classification, which H1 and H2 measure); the whole verdict (severity, device and confidence make exact agreement almost impossible) |
| Agreement measure | Mean pairwise agreement, with unanimity as a secondary figure | Fleiss' κ (unstable at `k = 3`; its chance correction depends on the skewed label distribution); unanimity alone (too coarse) |
| `⊥` and `∅` | Values in their own right, with conditional agreement beside | Always disagreement (counts invalid output twice); excluded (hides a condition that fails often) |
| Output scored | Both `R` and `E`, headline on `E` | `E` only (hides first-attempt variation) |
| Role in the analysis | Descriptive, per condition | Headline or hypothesis test (no hypothesis claims reliability; few possible values at `k = 3`) |
| Robustness | Out of scope, stated as a limitation | Prompt-injection metric now (stretch-only experiment, runs beyond the matrix); perturbation tests on bundles (new runs and a new perturbation design) |
