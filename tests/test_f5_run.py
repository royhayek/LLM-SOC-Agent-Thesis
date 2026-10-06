"""Real-testbed test for attack family F5, botnet replay (E1-12). Marked slow.

PROVISIONAL: F5 replays a dataset slice that is not redistributed (ADR-0003). Until Roy provides
the slice at the manifest's local path and sets its real SHA-256, F5 cannot run, so this test
skips. The family's visibility and repeatability tolerance are unset until then.
"""

from __future__ import annotations

import pytest

from thesis.scenario.families.f5 import BotnetManifestError, load_manifest, verify_slice


@pytest.mark.slow
def test_f5_replays_botnet_traffic_in_flows_only() -> None:
    try:
        verify_slice(load_manifest())
    except BotnetManifestError as exc:
        pytest.skip(f"botnet dataset slice not available: {exc}")
    # When the slice is provided, implement the two-run flows-only check here (mirror F6):
    # flows to the non-routable C2 with the device as source, no mqtt or honeypot traces, and
    # repeatability within the F5 tolerance (to be added to attack_tolerance.yaml from real runs).
    pytest.fail("botnet slice present but the F5 run assertions are not implemented yet (E1-12)")
