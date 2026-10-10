# Power calculation and target N (E2-02, SCRUM-25)

Fixes the number of bundles in the corpus **before any corpus is generated** (record §3, risk #2;
§10 "How many scenarios for statistical validity?"). Every number here is reproduced by
[`power_calculation.py`](power_calculation.py):

```
python docs/power/power_calculation.py
```

The result is frozen in METHODS.md v1.1 (changelog entry 8, tag `methods-v1.1`). Nothing in this
calculation reads any agent or baseline output.

## 1. What is being sized

The hypothesis tests are **paired**: every bundle is processed under every condition, so one
corpus of `N_eval` **evaluation** bundles serves all tests (METHODS §4.1). `N_eval` is the number
this calculation fixes. Baseline A's **training** bundles are extra and disjoint (E2-01); they are
added in §6, and they carry no LLM calls.

The tests to be powered (METHODS §4.2):

| Hypothesis | Contrast(s) | Outcome | Test | Holm family size |
|---|---|---|---|---|
| H1 | C1 vs C2, C3, C4 | DET, CLS | McNemar | 6 |
| H2 | C5 vs C6 | CLS | McNemar | 1 |
| H3 | C1 vs C5 | CU; usefulness | Wilcoxon; non-inferiority (δ = 0.05) | 1 (+ non-inf, outside) |
| H4 | C1 vs C7, C1 vs C6 | DET, CLS, CU | McNemar; Wilcoxon (CU) | 6 |

## 2. Assumptions, each with its source

| Symbol | Value | Meaning | Source / justification |
|---|---|---|---|
| α | 0.05 | Type-I error, two-sided | METHODS §4.1 (E0-03); ticket ASSUMPTION |
| power | 0.80 | 1 − β | ticket ASSUMPTION (field-standard) |
| Holm bound | α / 6 for H1 and H4; α for H2, H3 | multiplicity | Sizing each test at the Bonferroni bound α / (family size) **over-powers** Holm (Holm rejects the smallest p at α/m, larger p's at larger α), so this is conservative. METHODS §4.2 |
| p_win, p_lose | 0.15, 0.05 | discordant-pair probabilities for the binary contrasts: P(C1 correct, comparator wrong) and the reverse | **Minimum detectable effect.** Marginal difference δ = 0.10, discordant rate p_d = 0.20, odds ratio 3.0. A net win below ~10 percentage points is not a compelling thesis claim; the E0-01 spike (`spikes/FINDINGS.md`: 10/10 classification correct for both models on an easy bundle) shows the agent operates near ceiling, so the contest with a strong baseline is decided on a minority of hard bundles. No pilot discordance data exists, and the published IoT-IDS baselines ([6]–[9]) report no figure that can be quoted without reading the source (`knowledge/attack_families.yaml`), so the design is powered for the smallest **meaningful** effect rather than an assumed true one. ASSUMPTION. |
| d_z | 0.25 | standardized paired effect for the CU rate (Wilcoxon) | Small-to-moderate (Cohen). CU is the contextually-unsafe rate on emitted verdicts (Annex A); no pilot variance exists. ASSUMPTION; shown non-binding in §4. |
| σ_d, δ | 0.20, 0.05 | paired-difference SD and non-inferiority margin for usefulness | δ = 0.05 is frozen (Annex A §5, E0-12). σ_d is the SD of the per-bundle usefulness difference C1 − C5; because the two conditions differ only in the safety layer they agree on most bundles, so σ_d is small. ASSUMPTION; sensitivity noted in §4. |
| m | 3 | expected bundles per attack episode | W = 60 s tiling (METHODS §4.1) with episode durations varied ~1–5 min (E2-03 design intent) averages ~3 labelled bundles per episode per device. ASSUMPTION, to be confirmed by the E2-03 expected-count report. |
| ρ | 0.5 | intra-episode outcome correlation | Bundles of one episode are the same ongoing attack, so their DET/CLS outcomes are strongly correlated (record §4.1 names the clustering). ρ = 0.5 is a moderate, conservative choice. ASSUMPTION. |

Design effect for clustering: **D = 1 + (m − 1)ρ = 1 + 2 × 0.5 = 2.00** (METHODS §5). Every
per-test independent N is multiplied by D.

## 3. Formulae

- **McNemar** (Connor, 1987, normal approximation), pairs
  `N = [z_{α/2}·√p_d + z_β·√(p_d − δ²)]² / δ²`, with `p_d = p_win + p_lose`, `δ = p_win − p_lose`.
- **Wilcoxon signed-rank** (paired rate): size the paired t-test `N = ((z_{α/2}+z_β)/d_z)²` and
  divide by the ARE 0.955 (worst realistic case under near-normality).
- **Non-inferiority** (paired, one-sided, true difference 0): `N = (z_α+z_β)²·σ_d²/δ²`.
- **Clustering:** `N_clustered = N × D`.

`z` values from the standard-normal quantile: z_{0.025} = 1.960, z_{0.05/12} = 2.638 (the per-test
two-sided tail under the α/6 bound), z_{0.05, one-sided} = 1.645, z_{0.80} = 0.842.

## 4. Per-test result

| Test | α per test | N independent | N clustered (×2.00) |
|---|---|---|---|
| **H1 / H4 McNemar (DET, CLS)** | 0.00833 | 239.2 | **478.5** |
| H2 McNemar (CLS) | 0.05 | 154.6 | 309.2 |
| H4 Wilcoxon (CU) | 0.00833 | 202.9 | 405.8 |
| H3 Wilcoxon (CU) | 0.05 | 131.5 | 263.0 |
| H3 usefulness (non-inferiority) | 0.05 | 98.9 | 197.8 |

**The binding test is the H1/H4 McNemar family at 479 clustered bundles.** Every other test needs
fewer, so a corpus powered for H1/H4 powers them all.

**Frozen target: `N_eval` = 480 evaluation bundles** (479 rounded up to a count that splits
cleanly across six families).

The usefulness non-inferiority test is the most assumption-sensitive: at σ_d = 0.20 it needs 198
bundles, but if C1 and C5 disagree on usefulness far more than assumed (σ_d > 0.35 at δ = 0.05) it
would exceed 480. If the pilot or first exploratory run shows large C1–C5 usefulness disagreement,
re-open this number via a METHODS changelog entry before the full runs.

## 5. Minimum positive bundles per family (stratified H1)

The stratified H1 figures (per-family recall, accuracy, and gain-from-fusion) are **descriptive
with bootstrap intervals**, not separately powered tests (METHODS §4.2). The floor is set by
bootstrap stability, not by α/power:

- **Floor: 30 positive bundles per family** (≈ 10 attack episodes per family at m = 3, enough for
  the episode block bootstrap of METHODS §4.3 to resolve a per-family proportion to a CI half-width
  of roughly ±0.15 near p = 0.8).
- The frozen split delivers **50 positive bundles per family** (300 attack ÷ 6), comfortably above
  the floor, so no family is under-represented.

## 6. The frozen counts

| Quantity | Count | Note |
|---|---|---|
| Evaluation bundles `N_eval` | **480** | binding H1/H4 McNemar, §4 |
| — attack | 300 | 50 per family × 6 families (E1-02) |
| — benign | 180 | 37.5 % benign share |
| Minimum positive bundles / family | 30 (floor); 50 delivered | §5 |
| Expected bundles / episode `m` | 3 | clustering input, §2 |
| Clustering design effect `D` | 2.00 | 1 + (m − 1)ρ |
| Training bundles (Baseline A, E2-01) | 206 | (30 / 70) × 480, disjoint episodes, no LLM calls |
| **Total corpus** | **686** | 480 evaluation + 206 training |

Episode counts for E2-03: ~100 evaluation attack episodes (300 / 3) + ~43 training attack episodes
(~17 eval + ~7 train per family), plus benign blocks for 180 benign bundles.

## 7. Cost (ADR-0001 recompute)

LLM calls run on evaluation bundles only (training bundles feed Baseline A, which is an ML
classifier). Per full matrix run: 16 calls per bundle (5 agentic conditions × 3 graph calls + 1
prompt-only call) × k = 3 repetitions = 48 calls per bundle.

| Item | Value |
|---|---|
| Calls (3 full runs + 1 exploratory of 25 bundles) | 70,320 |
| Tokens | ≈ 211 M in / 17.6 M out (≈ 3k in / 250 out per call) |
| Unit price (Llama 3.1 8B, DeepInfra, E0-06) | USD 0.02 in / 0.04 out per 1 M |
| **Cost** | **≈ USD 4.92 / EUR 4.39** (EUR/USD 1.1225, ECB 2026-10-02) |

**EUR 4.39 ≤ EUR 100** — the AC holds with large headroom. The account's USD 5 spending cap
(ADR-0001) now sits just above the projection, so it should be **raised to USD 20** to keep a
genuine guard-rail margin while staying far under budget. This is recorded in ADR-0001.

Wall-clock for ~143 attack episodes plus benign blocks is estimated in E2-03 and checked in E2-05;
the record expects a multi-night corpus run (record §4.2).

## 8. Sensitivity of `N_eval`

Clustered binding N (H1/H4 McNemar) over the two largest drivers:

| δ (marginal effect) | ρ = 0.3 | ρ = 0.5 | ρ = 0.7 |
|---|---|---|---|
| 0.08 | 601 | 751 | 902 |
| **0.10** | 383 | **479** | 575 |
| 0.12 | 265 | 331 | 397 |

The frozen point (δ = 0.10, ρ = 0.5) is the conservative-but-meaningful choice. Powering for a
smaller effect (δ = 0.08) would need up to ~750–900 bundles — still inside the EUR 100 budget
(~EUR 7) but materially more testbed wall-clock. If a win smaller than 10 percentage points must be
claimed, raise N via a METHODS changelog entry and re-run the affected conditions.

## 9. Sources

- `docs/source/thesis_project_full_record.md` §3 (risk #2), §4.1, §4.2, §4.4.1, §10 — read this session.
- `METHODS.md` §4 (statistics), §5 (target-N method), Annex A §5 (non-inferiority δ = 0.05).
- `spikes/FINDINGS.md` — E0-01 spike correctness (read this session; E0-04 is closed, so spike
  outputs are readable).
- `knowledge/attack_families.yaml` — dataset references [6]–[9]; no citable accuracy figure quoted
  (sources not re-read here), so effect sizes are a minimum-detectable-effect design, not assumed
  published values. ASSUMPTION.
- Connor, R. J. (1987), *Sample size for testing differences in proportions for the paired-sample
  design*, Biometrics 43(1):207–211 — McNemar formula. `UNVERIFIED` (not re-read this session).
- Acklam, P. J. (2003), inverse-normal-CDF rational approximation — numerical method only.
