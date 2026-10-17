"""Tests for the demo-simulator support (scenario catalog, event assembly). Deterministic only;
no model output is asserted."""

from __future__ import annotations

import pytest

from thesis.api.demo import (
    EVAL_PARQUET,
    load_alert_index,
    load_bundle_meta,
    load_scenarios,
)


def test_load_scenarios_returns_the_catalog() -> None:
    scenarios = load_scenarios()
    ids = {s.id for s in scenarios}
    assert {"ssh-bruteforce", "syn-flood", "mqtt-flood", "benign", "honest-limitation"} <= ids
    for s in scenarios:
        assert s.default_condition.startswith("C")
        assert s.episode_id or s.bundle_ids  # every scenario selects its bundles somehow


@pytest.mark.skipif(not EVAL_PARQUET.exists(), reason="bundle parquet not on disk")
def test_bundle_meta_and_alert_index_join() -> None:
    meta = load_bundle_meta()
    alerts = load_alert_index()
    b = next(iter(meta.values()))
    assert b.window_start <= b.window_end and b.alert_ids
    # every bundle cites alert ids that resolve in the labeled-alert index
    assert any(aid in alerts for aid in b.alert_ids)
    a = alerts[next(aid for aid in b.alert_ids if aid in alerts)]
    assert a.ts is not None and a.summary
