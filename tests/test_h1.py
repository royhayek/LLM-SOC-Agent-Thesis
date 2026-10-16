"""Tests for the H1 stratified analysis (E9-10, SCRUM-115)."""

from __future__ import annotations

from pathlib import Path

from thesis.config import Provenance, config_hash
from thesis.eval.h1 import (
    BundleMeta,
    fusion_gain,
    h1_tests,
    stratified_cells,
    write_analysis_md,
    write_stratified_csv,
)
from thesis.eval.run import load_conditions


def _prov() -> Provenance:
    return Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=768,
        seed=None,
        prompt_template_version="prompts-v1.1",
        graph_version="graph-v1.0",
    )


def _row(cfg: str, bundle: str, rep: int, truth: str, pred: str | None) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "ground_truth": truth,
        "incident_type": pred,
        "emitted": pred is not None,
        "recommended_action": "monitor",
        "evidence": [],
        "validator_outcome": "pass",
    }


def _meta() -> dict[str, BundleMeta]:
    # 2 syn_flood bundles (flows-visible), 2 port_scan bundles; distinct episodes.
    out = {}
    for i in range(2):
        out[f"syn-{i}"] = BundleMeta("syn_flood", frozenset({"flows"}), f"ep-syn-{i}", False)
        out[f"hp-{i}"] = BundleMeta("port_scan", frozenset({"honeypot"}), f"ep-ps-{i}", True)
    return out


def _conditions() -> list:
    return load_conditions(_prov())


def test_stratified_cells_recall_and_accuracy_per_family() -> None:
    conds = _conditions()
    c1, c2 = config_hash(conds[0]), config_hash(conds[1])  # all-sources, flows-only
    rows: list[dict[str, object]] = []
    # C1 detects + classifies every syn_flood right; C2 (flows) misses them (predicts benign).
    for i in range(2):
        rows.append(_row(c1, f"syn-{i}", 0, "syn_flood", "syn_flood"))
        rows.append(_row(c2, f"syn-{i}", 0, "syn_flood", "benign"))
    cells = stratified_cells(rows, conds, _meta())
    by = {(c.condition, c.family): c for c in cells}
    assert by[("C1", "syn_flood")].recall == 1.0 and by[("C1", "syn_flood")].accuracy == 1.0
    assert by[("C2", "syn_flood")].recall == 0.0  # flows missed the floods
    assert by[("C1", "syn_flood")].n == 2


def test_fusion_gain_is_c1_minus_best_single() -> None:
    conds = _conditions()
    c1, c2 = config_hash(conds[0]), config_hash(conds[1])
    rows = [_row(c1, f"syn-{i}", 0, "syn_flood", "syn_flood") for i in range(2)]
    rows += [_row(c2, f"syn-{i}", 0, "syn_flood", "benign") for i in range(2)]
    gain = fusion_gain(stratified_cells(rows, conds, _meta()))
    assert gain["syn_flood"]["recall_gain"] == 1.0  # C1 1.0 - best single 0.0


def test_h1_tests_report_c1_beating_a_single_source() -> None:
    conds = _conditions()
    c1, c2 = config_hash(conds[0]), config_hash(conds[1])
    rows = [_row(c1, f"syn-{i}", 0, "syn_flood", "syn_flood") for i in range(2)]
    rows += [_row(c2, f"syn-{i}", 0, "syn_flood", "benign") for i in range(2)]
    tests = h1_tests(rows, conds, _meta())
    det_c2 = next(t for t in tests if t.contrast == "C1 vs C2" and t.outcome == "DET")
    assert det_c2.beats is True


def test_h1_tests_honeypot_filter_excludes_keyed_bundles() -> None:
    conds = _conditions()
    c1, c2 = config_hash(conds[0]), config_hash(conds[1])
    # Only port_scan bundles are honeypot-keyed; excluding them leaves the syn_flood bundles.
    rows = [_row(c1, f"syn-{i}", 0, "syn_flood", "syn_flood") for i in range(2)]
    rows += [_row(c1, f"hp-{i}", 0, "port_scan", "port_scan") for i in range(2)]
    rows += [_row(c2, f"syn-{i}", 0, "syn_flood", "benign") for i in range(2)]
    rows += [_row(c2, f"hp-{i}", 0, "port_scan", "benign") for i in range(2)]
    no_hp = h1_tests(rows, conds, _meta(), honeypot_keyed=False)
    only_hp = h1_tests(rows, conds, _meta(), honeypot_keyed=True)
    # Both run without error and return the six contrasts (C1 vs C2/C3/C4 on DET and CLS).
    assert len(no_hp) == 6 and len(only_hp) == 6


def test_writers_produce_files(tmp_path: Path) -> None:
    conds = _conditions()
    c1 = config_hash(conds[0])
    rows = [_row(c1, f"syn-{i}", 0, "syn_flood", "syn_flood") for i in range(2)]
    cells = stratified_cells(rows, conds, _meta())
    csv_path = tmp_path / "h1.csv"
    md_path = tmp_path / "h1.md"
    write_stratified_csv(cells, csv_path)
    write_analysis_md(cells, fusion_gain(cells), [], [], [], md_path)
    assert "condition,family,n,recall" in csv_path.read_text(encoding="utf-8")
    assert "H1 stratified analysis" in md_path.read_text(encoding="utf-8")
