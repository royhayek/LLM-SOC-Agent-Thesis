"""Power calculation for the corpus target N (E2-02, SCRUM-25).

Pure-Python, no third-party dependency (so no new-dependency ADR is needed). Run it to
reproduce every number in `power_calculation.md`:

    python docs/power/power_calculation.py

The statistics implemented here:

* the standard-normal quantile (Acklam's rational approximation), for z_{alpha} and z_{beta};
* McNemar's paired-binary sample size (Connor, 1987), used for DET and CLS;
* a paired-difference sample size with the Wilcoxon efficiency penalty, used for the CU rate;
* a paired non-inferiority sample size, used for the usefulness test (margin delta = 0.05);
* the cluster design effect 1 + (m - 1) * rho, applied to every per-test N.

Every assumption is named in `power_calculation.md` with its source. The frozen result goes
into METHODS.md v1.1. Nothing here reads any agent or baseline output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def normal_quantile(p: float) -> float:
    """Inverse standard-normal CDF (Acklam, 2003); |error| < 1.15e-9 on (0, 1)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must lie strictly in (0, 1)")
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )


def z_two_sided(alpha: float) -> float:
    return normal_quantile(1.0 - alpha / 2.0)


def z_one_sided(alpha: float) -> float:
    return normal_quantile(1.0 - alpha)


def mcnemar_n(p_win: float, p_lose: float, alpha: float, power: float) -> float:
    """Number of pairs for McNemar's test (Connor, 1987, normal approximation).

    p_win  = P(condition correct, comparator wrong); p_lose = P(comparator correct, condition
    wrong). p_disc = p_win + p_lose is the discordant-pair probability; delta = p_win - p_lose
    is the marginal difference the test detects.
    """
    p_disc = p_win + p_lose
    delta = p_win - p_lose
    if delta <= 0.0:
        raise ValueError("p_win must exceed p_lose for a one-directional alternative")
    za, zb = z_two_sided(alpha), normal_quantile(power)
    return (za * math.sqrt(p_disc) + zb * math.sqrt(p_disc - delta * delta)) ** 2 / (delta * delta)


def wilcoxon_paired_n(d_z: float, alpha: float, power: float) -> float:
    """Paired-difference N for a standardized effect d_z, with the Wilcoxon ARE penalty.

    Sizes the paired t-test, then divides by 0.955, the asymptotic relative efficiency of the
    Wilcoxon signed-rank test under normality (the worst realistic case for us is >= this).
    """
    za, zb = z_two_sided(alpha), normal_quantile(power)
    return ((za + zb) / d_z) ** 2 / 0.955


def non_inferiority_paired_n(sigma_d: float, margin: float, alpha: float, power: float) -> float:
    """Paired non-inferiority N for a one-sided test at `margin`, true difference assumed 0."""
    za, zb = z_one_sided(alpha), normal_quantile(power)
    return (za + zb) ** 2 * sigma_d * sigma_d / (margin * margin)


def design_effect(m: float, rho: float) -> float:
    return 1.0 + (m - 1.0) * rho


@dataclass(frozen=True)
class TestN:
    name: str
    alpha: float
    n_independent: float
    n_clustered: float


def main() -> None:
    # --- Frozen inputs (METHODS.md v1.0, E0-03) and E2-02 ASSUMPTIONs (see the .md) ---
    power = 0.80
    alpha = 0.05
    alpha_h1h4 = alpha / 6.0  # Bonferroni bound on the 6-test Holm family (conservative)
    alpha_h2 = alpha  # single test
    # Conservative minimum detectable effect for the paired-binary contrasts:
    p_win, p_lose = 0.15, 0.05  # delta = 0.10, p_disc = 0.20, odds ratio 3.0
    d_z_cu = 0.25  # CU rate: small-moderate standardized paired effect
    sigma_d_ni, margin_ni = 0.20, 0.05  # usefulness non-inferiority (Annex A sec.5)
    m, rho = 3.0, 0.5  # bundles per episode; intra-episode correlation
    deff = design_effect(m, rho)

    tests = []
    for label, a in (("H1/H4 McNemar (DET, CLS)", alpha_h1h4), ("H2 McNemar (CLS)", alpha_h2)):
        n_i = mcnemar_n(p_win, p_lose, a, power)
        tests.append(TestN(label, a, n_i, n_i * deff))
    n_cu_h4 = wilcoxon_paired_n(d_z_cu, alpha_h1h4, power)
    tests.append(TestN("H4 Wilcoxon (CU)", alpha_h1h4, n_cu_h4, n_cu_h4 * deff))
    n_cu_h3 = wilcoxon_paired_n(d_z_cu, alpha, power)
    tests.append(TestN("H3 Wilcoxon (CU)", alpha, n_cu_h3, n_cu_h3 * deff))
    n_ni = non_inferiority_paired_n(sigma_d_ni, margin_ni, alpha, power)
    tests.append(TestN("H3 usefulness (non-inferiority)", alpha, n_ni, n_ni * deff))

    n_eval = max(math.ceil(t.n_clustered) for t in tests)
    n_eval_rounded = 480  # chosen round target >= the binding requirement, split cleanly below

    print(f"design effect 1+(m-1)rho = 1+({m - 1:.0f})*{rho} = {deff:.2f}\n")
    print(f"{'test':<34}{'alpha':>9}{'N_indep':>10}{'N_clustered':>14}")
    for t in tests:
        print(f"{t.name:<34}{t.alpha:>9.5f}{t.n_independent:>10.1f}{t.n_clustered:>14.1f}")
    print(f"\nbinding N_eval (max, ceil) = {n_eval}  ->  frozen target = {n_eval_rounded}")

    # --- Split the frozen N_eval ---
    families = 6
    attack = 300  # 50 per family
    benign = n_eval_rounded - attack  # 180
    per_family = attack // families
    train_share = 0.30  # E2-01
    train_bundles = round(n_eval_rounded * train_share / (1.0 - train_share))
    total_corpus = n_eval_rounded + train_bundles
    print(
        f"\nevaluation split: {attack} attack ({per_family}/family x {families}) + {benign} benign"
    )
    print(f"per-family H1 floor = 30 positive bundles; design delivers {per_family}")
    print(f"training bundles (E2-01, 30%) = {train_bundles}; total corpus = {total_corpus}")

    # --- Cost recompute (ADR-0001), scaled from the N=250 estimate in thesis_notes ---
    calls_per_bundle = 16 * 3  # 16 calls/bundle/rep (5 agentic x3 + 1 prompt-only) x 3 reps
    full_runs = 3
    exploratory_bundles = 25
    calls = n_eval_rounded * calls_per_bundle * full_runs + exploratory_bundles * calls_per_bundle
    in_tok = calls * 3000  # ~3k input tokens/call (thesis_notes ADR entry)
    out_tok = calls * 250
    usd = in_tok / 1e6 * 0.02 + out_tok / 1e6 * 0.04  # Llama 3.1 8B DeepInfra (E0-06)
    eur = usd / 1.1225  # ECB 2026-10-02
    print(f"\nLLM calls (3 full runs + exploratory) = {calls:,}")
    print(f"tokens ~ {in_tok / 1e6:.0f}M in / {out_tok / 1e6:.1f}M out")
    print(
        f"cost ~ USD {usd:.2f} / EUR {eur:.2f}  (budget EUR 100; recommend raising cap to USD 20)"
    )

    # --- Sensitivity: N_eval over the two biggest drivers (delta, rho) at alpha=0.05/6 ---
    print("\nsensitivity of N_eval (clustered, binding H1/H4 McNemar):")
    print(f"{'delta':>7}" + "".join(f"{'rho=' + str(r):>12}" for r in (0.3, 0.5, 0.7)))
    for delta in (0.08, 0.10, 0.12):
        pw, pl = (0.20 + delta) / 2.0, (0.20 - delta) / 2.0  # hold p_disc = 0.20
        row = f"{delta:>7.2f}"
        for r in (0.3, 0.5, 0.7):
            n = mcnemar_n(pw, pl, alpha_h1h4, power) * design_effect(m, r)
            row += f"{math.ceil(n):>12}"
        print(row)


if __name__ == "__main__":
    main()
