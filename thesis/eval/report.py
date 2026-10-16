"""Regenerate every results table and figure for H1–H4 and cost (E9-11, SCRUM-118).

One script turns the hashed results (E9-09) into the tables and figures the results chapters cite,
so every number is reproducible and none is typed by hand. Negative results are shown with the same
prominence as positive ones (proposal, Expected Outcomes). Tables are deterministic (sorted,
rounded, no timestamps), so they are byte-identical on re-run; `docs/eval/outputs.md` lists each
output with the hypothesis it answers.

    python -m thesis.eval.report   # writes docs/thesis/tables/*.md and docs/thesis/figures/*.png
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from thesis.config import ExperimentConfig, config_hash
from thesis.eval.cost import cost_per_incident
from thesis.eval.metrics import (
    compute_classification,
    compute_detection,
    compute_reliability,
    compute_safety,
)
from thesis.eval.stats import TestResult, run_tests

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PARQUET = REPO_ROOT / "results" / "results.parquet"
TABLES_DIR = REPO_ROOT / "docs" / "thesis" / "tables"
FIGURES_DIR = REPO_ROOT / "docs" / "thesis" / "figures"
OUTPUTS_MD = REPO_ROOT / "docs" / "eval" / "outputs.md"

CONDITION_NOTE = {
    "C1": "all sources, agentic, enforcing",
    "C2": "flows only, agentic, enforcing",
    "C3": "mqtt only, agentic, enforcing",
    "C4": "honeypot only, agentic, enforcing",
    "C5": "all sources, agentic, logging_only",
    "C6": "prompt-only (Baseline B)",
    "C7": "ml-classifier (Baseline A)",
}


def _labels(conditions: Sequence[ExperimentConfig]) -> dict[str, str]:
    """config_hash → C1..C7 in the frozen condition order."""
    return {config_hash(c): f"C{i + 1}" for i, c in enumerate(conditions)}


def _num(m: Mapping[str, object], key: str) -> float:
    return float(cast("float", m.get(key, 0.0)))


def _md_table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out) + "\n"


def overall_table(
    rows: Sequence[Mapping[str, object]], conditions: Sequence[ExperimentConfig]
) -> str:
    """Per condition: detection F1, classification accuracy and macro-F1, the unsafe rate and
    schema validity. The headline comparison table across the whole matrix."""
    labels = _labels(conditions)
    det = compute_detection(rows)
    cls = compute_classification(rows)
    safety = compute_safety(rows)
    table_rows = []
    for cfg, label in sorted(labels.items(), key=lambda kv: kv[1]):
        d, c, s = det.get(cfg, {}), cls.get(cfg, {}), safety.get(cfg, {})
        table_rows.append(
            [
                label,
                CONDITION_NOTE[label],
                round(_num(d, "recall"), 3),
                round(_num(d, "f1"), 3),
                round(_num(c, "accuracy"), 3),
                round(_num(c, "macro_f1"), 3),
                round(_num(s, "CU"), 3),
                round(_num(s, "SV"), 3),
                round(_num(s, "USE"), 3),
            ]
        )
    return _md_table(
        [
            "Cond",
            "Description",
            "DET recall",
            "DET F1",
            "CLS acc",
            "CLS macroF1",
            "CU",
            "SV",
            "USE",
        ],
        table_rows,
    )


def tests_table(results: Sequence[TestResult]) -> str:
    """The frozen H1–H4 comparisons (E9-05): statistic, raw p, Holm p and effect, in fixed order."""
    rows = [
        [r.hypothesis, r.contrast, r.outcome, r.test, r.statistic, r.p_value, r.p_holm, r.effect]
        for r in results
    ]
    return _md_table(
        ["H", "Contrast", "Outcome", "Test", "Statistic", "p", "p (Holm)", "Effect"], rows
    )


def reliability_table(
    rows: Sequence[Mapping[str, object]], conditions: Sequence[ExperimentConfig]
) -> str:
    labels = _labels(conditions)
    rel = compute_reliability(rows)
    table_rows = []
    for cfg, label in sorted(labels.items(), key=lambda kv: kv[1]):
        r = rel.get(cfg, {})
        table_rows.append(
            [
                label,
                round(_num(r, "classification_pa"), 3),
                round(_num(r, "classification_unanimity"), 3),
                round(_num(r, "action_pa"), 3),
                round(_num(r, "action_unanimity"), 3),
            ]
        )
    return _md_table(
        ["Cond", "CLS agree", "CLS unanimity", "action agree", "action unanimity"], table_rows
    )


def cost_table(rows: Sequence[Mapping[str, object]]) -> str:
    table_rows = [
        [c.config_hash[:8], c.n, c.mean_tokens_in, c.mean_tokens_out, c.mean_eur, c.mean_seconds]
        for c in cost_per_incident(rows)
    ]
    return _md_table(
        ["Condition (hash)", "n", "mean in", "mean out", "mean EUR", "mean s"], table_rows
    )


def _write_figures(
    rows: Sequence[Mapping[str, object]], conditions: Sequence[ExperimentConfig], out_dir: Path
) -> list[str]:  # pragma: no cover - plotting is exercised only in the live run
    import matplotlib  # type: ignore[import-not-found]

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]

    out_dir.mkdir(parents=True, exist_ok=True)
    labels = _labels(conditions)
    ordered = [lbl for _, lbl in sorted(labels.items(), key=lambda kv: kv[1])]
    hash_of = {v: k for k, v in labels.items()}
    det, cls = compute_detection(rows), compute_classification(rows)
    written: list[str] = []

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(ordered, [float(det.get(hash_of[c], {}).get("f1", 0.0)) for c in ordered])
    ax.set_ylabel("detection F1")
    ax.set_title("Detection F1 by condition (H1, H4)")
    fig.tight_layout()
    fig.savefig(out_dir / "detection_f1.png", dpi=120)
    plt.close(fig)
    written.append("detection_f1.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(ordered, [_num(cls.get(hash_of[c], {}), "accuracy") for c in ordered])
    ax.set_ylabel("classification accuracy")
    ax.set_title("Classification accuracy by condition (H1, H2, H4)")
    fig.tight_layout()
    fig.savefig(out_dir / "classification_accuracy.png", dpi=120)
    plt.close(fig)
    written.append("classification_accuracy.png")
    return written


def write_outputs_md(
    tables: Sequence[str], figures: Sequence[str], path: Path = OUTPUTS_MD
) -> None:
    """List each output with the hypothesis it answers."""
    answers = {
        "overall_metrics.md": "H1–H4 (headline per-condition metrics)",
        "hypothesis_tests.md": "H1–H4 (the frozen paired comparisons)",
        "reliability.md": "robustness (run-to-run agreement, Annex D)",
        "cost.md": "cost per incident (§4.4)",
        "detection_f1.png": "H1, H4 (detection by condition)",
        "classification_accuracy.png": "H1, H2, H4 (classification by condition)",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Results outputs (E9-11, SCRUM-118)",
        "",
        "GENERATED by `python -m thesis.eval.report`. Every table and figure comes from the",
        "hashed results (E9-09). Tables are byte-identical on re-run. Stratified H1 is in",
        "`results/h1_stratified.csv` and `docs/eval/h1_analysis.md` (E9-10).",
        "",
        "## Tables (`docs/thesis/tables/`)",
        "",
        *(f"- `{t}` — {answers.get(t, '')}" for t in tables),
        "",
        "## Figures (`docs/thesis/figures/`)",
        "",
        *(f"- `{f}` — {answers.get(f, '')}" for f in figures),
        "",
    ]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> int:  # pragma: no cover - reads the frozen results and plots
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    from thesis.eval.results import provenance_from_rows
    from thesis.eval.run import load_conditions

    if not RESULTS_PARQUET.exists():
        print(f"no results at {RESULTS_PARQUET}; run E9-09 first")
        return 2
    rows = pq.read_table(RESULTS_PARQUET).to_pylist()
    conditions = load_conditions(provenance_from_rows(rows))

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "overall_metrics.md").write_text(
        overall_table(rows, conditions), encoding="utf-8"
    )
    (TABLES_DIR / "hypothesis_tests.md").write_text(
        tests_table(run_tests(rows, conditions)), encoding="utf-8"
    )
    (TABLES_DIR / "reliability.md").write_text(
        reliability_table(rows, conditions), encoding="utf-8"
    )
    (TABLES_DIR / "cost.md").write_text(cost_table(rows), encoding="utf-8")
    tables = ["overall_metrics.md", "hypothesis_tests.md", "reliability.md", "cost.md"]
    try:
        figures = _write_figures(rows, conditions, FIGURES_DIR)
    except ImportError:
        figures = []
        print("matplotlib not installed; wrote tables only (figures need the plotting dependency)")
    write_outputs_md(tables, figures)
    print(f"wrote {len(tables)} tables and {len(figures)} figures")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "cost_table",
    "overall_table",
    "reliability_table",
    "tests_table",
    "write_outputs_md",
]
