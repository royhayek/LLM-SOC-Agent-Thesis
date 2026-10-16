"""Tests for the full-run harness verification helpers (E9-09, SCRUM-110)."""

from __future__ import annotations

from pathlib import Path

from thesis.eval.cost import USD_PER_EUR
from thesis.eval.full_run import (
    compute_spend,
    hash_file,
    verify_row_count,
    verify_single_revision,
    write_full_run_md,
)

PINNED = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
REV = "0e9e39f249a16976918f6564b8830bc894c89659"


def _row(
    cfg: str,
    bundle: str,
    rep: int,
    *,
    strategy: str = "agentic",
    model: str = PINNED,
    revision: str = REV,
    tin: int = 0,
    tout: int = 0,
) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "strategy": strategy,
        "model": model,
        "model_revision": revision,
        "tokens_in": tin,
        "tokens_out": tout,
    }


def test_row_count_ok_and_detects_shortfall() -> None:
    # 2 bundles × 2 conditions × 2 reps = 8 rows.
    rows = [_row(c, b, r) for c in ("cA", "cB") for b in ("b1", "b2") for r in range(2)]
    assert verify_row_count(rows, 2, 2, 2) == []
    assert verify_row_count(rows[:-1], 2, 2, 2)  # one missing → problems reported


def test_row_count_detects_duplicates() -> None:
    rows = [_row("cA", "b1", 0)] * 4  # 4 rows but only 1 unique item
    problems = verify_row_count(rows, 2, 2, 1)
    assert any("unique" in p for p in problems)


def test_revision_check_passes_for_pinned_and_ignores_baseline_a() -> None:
    rows = [
        _row("c1", "b1", 0),  # agentic, pinned
        _row("c7", "b1", 0, strategy="ml_classifier", model="flow_classifier", revision="base-a"),
    ]
    assert verify_single_revision(rows, PINNED, REV) == []  # Baseline A excluded


def test_revision_check_flags_a_mid_run_model_swap() -> None:
    rows = [_row("c1", "b1", 0), _row("c1", "b2", 0, model="other-model")]
    assert verify_single_revision(rows, PINNED, REV)  # two models → problem


def test_compute_spend_hand_computed() -> None:
    rows = [_row("c1", "b1", 0, tin=1_000_000, tout=1_000_000)]  # USD 0.02 + 0.04 = 0.06
    spend = compute_spend(rows)
    assert spend["tokens_in"] == 1_000_000.0 and spend["tokens_out"] == 1_000_000.0
    assert round(spend["usd"], 4) == 0.06
    assert round(spend["eur"], 4) == round(0.06 / USD_PER_EUR, 4)


def test_hash_file_is_sha256(tmp_path: Path) -> None:
    import hashlib

    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    assert hash_file(f) == hashlib.sha256(b"hello").hexdigest()


def test_write_full_run_md_reports_status_and_spend(tmp_path: Path) -> None:
    path = tmp_path / "full_run.md"
    write_full_run_md(
        n_rows=8,
        n_bundles=2,
        n_conditions=2,
        k=2,
        eval_hash="abc",
        results_hash="def",
        spend={"tokens_in": 10, "tokens_out": 5, "usd": 0.01, "eur": 0.009},
        model=PINNED,
        revision=REV,
        problems=[],
        path=path,
    )
    text = path.read_text(encoding="utf-8")
    assert "def" in text and "abc" in text and "OK" in text
    assert REV in text and "0.01" in text


def test_write_full_run_md_lists_problems(tmp_path: Path) -> None:
    path = tmp_path / "full_run.md"
    write_full_run_md(
        n_rows=7,
        n_bundles=2,
        n_conditions=2,
        k=2,
        eval_hash="abc",
        results_hash="def",
        spend={"tokens_in": 0, "tokens_out": 0, "usd": 0.0, "eur": 0.0},
        model=PINNED,
        revision=REV,
        problems=["row count 7 != expected 8"],
        path=path,
    )
    text = path.read_text(encoding="utf-8")
    assert "PROBLEMS" in text and "row count 7" in text
