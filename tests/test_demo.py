"""Tests for the demo-simulator support (scenario catalog, event assembly). Deterministic only;
no model output is asserted."""

from __future__ import annotations

from thesis.api.demo import load_scenarios


def test_load_scenarios_returns_the_catalog() -> None:
    scenarios = load_scenarios()
    ids = {s.id for s in scenarios}
    assert {"ssh-bruteforce", "syn-flood", "mqtt-flood", "benign", "honest-limitation"} <= ids
    for s in scenarios:
        assert s.default_condition.startswith("C")
        assert s.episode_id or s.bundle_ids  # every scenario selects its bundles somehow
