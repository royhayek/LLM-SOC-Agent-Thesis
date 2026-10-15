"""Tests for the condition-matrix runner and ledger (E9-01, SCRUM-41). Client/strategies mocked."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from thesis.assemble.bundles import Bundle
from thesis.config import Provenance, config_hash
from thesis.eval.ledger import Ledger
from thesis.eval.run import (
    RunItem,
    RunResult,
    dry_run,
    load_conditions,
    run_matrix,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _prov() -> Provenance:
    return Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version="prompts-v1.0",
        graph_version="graph-v1.0",
    )


def _bundle(n: int) -> Bundle:
    return Bundle(
        bundle_id=f"bundle-{n}",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="benign",
        episode_id=None,
        sources=("flows",),
        alerts=(),
    )


def _ok(bundle: Bundle, config: object, *, client: object, repetition: int) -> RunResult:
    return RunResult(bundle.bundle_id, config_hash(config), repetition, "mock", None)  # type: ignore[arg-type]


def test_dry_run_counts_calls_and_cost() -> None:
    conditions = load_conditions(_prov())
    est = dry_run(10, conditions, k=3)
    assert est["calls_per_bundle_rep"] == 16  # 5 agentic x3 + 1 prompt_only x1 + 1 ml x0
    assert est["calls"] == 10 * 16 * 3  # bundles x (3*agentic + 1*prompt_only) x k
    assert est["usd"] > 0


def test_full_run_covers_every_item_once(tmp_path: Path) -> None:
    bundles = [_bundle(i) for i in range(3)]
    conditions = load_conditions(_prov())
    ledger = Ledger(tmp_path / "ledger.jsonl")
    seen: list[tuple[str, str, int]] = []
    run_matrix(
        bundles,
        conditions,
        client=None,
        ledger=ledger,
        sink=lambda r: seen.append((r.bundle_id, r.config_hash, r.repetition)),
        k=3,
        run_one_fn=_ok,
    )
    expected = 3 * len(conditions) * 3
    assert len(seen) == expected
    assert len(set(seen)) == expected  # each (bundle, condition, repetition) exactly once
    assert len(ledger) == expected


def test_resume_after_a_crash_reruns_nothing_finished(tmp_path: Path) -> None:
    bundles = [_bundle(i) for i in range(3)]
    conditions = load_conditions(_prov())
    ledger_path = tmp_path / "ledger.jsonl"

    # Run 1: the sink fails on the 5th result (a persistence crash mid-run). mark() runs only after
    # a successful sink, so exactly the first 4 items are recorded.
    run1_marked: list[tuple[str, str, int]] = []
    calls = {"n": 0}

    def crashing_sink(r: RunResult) -> None:
        calls["n"] += 1
        if calls["n"] == 5:
            raise RuntimeError("simulated crash")
        run1_marked.append((r.bundle_id, r.config_hash, r.repetition))

    with pytest.raises(RuntimeError):
        run_matrix(
            bundles,
            conditions,
            client=None,
            ledger=Ledger(ledger_path),
            sink=crashing_sink,
            k=3,
            max_workers=1,
            run_one_fn=_ok,
        )
    ledger_after_crash = Ledger(ledger_path)
    assert len(ledger_after_crash) == 4

    # Run 2: resume with a fresh ledger loaded from disk. Finished items are not re-run.
    resumed: list[tuple[str, str, int]] = []
    ran = run_matrix(
        bundles,
        conditions,
        client=None,
        ledger=ledger_after_crash,
        sink=lambda r: resumed.append((r.bundle_id, r.config_hash, r.repetition)),
        k=3,
        max_workers=1,
        run_one_fn=_ok,
    )
    total = 3 * len(conditions) * 3
    assert ran == total - 4  # only the unfinished items
    assert not (set(resumed) & set(run1_marked))  # nothing finished before is called again
    assert len(Ledger(ledger_path)) == total  # every item exactly once in the end


def test_ledger_key_is_bundle_config_repetition(tmp_path: Path) -> None:
    conditions = load_conditions(_prov())
    item = RunItem(_bundle(0), conditions[0], 2)
    key = item.key()
    assert key.bundle_id == "bundle-0" and key.repetition == 2
    assert key.config_hash == config_hash(conditions[0])
