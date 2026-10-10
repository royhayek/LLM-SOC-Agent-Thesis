"""Real-testbed test for attack family F5, botnet replay (E1-12). Marked slow.

Requires the botnet slice at the manifest's local_path (git-ignored), so it skips in CI where
the slice is absent. Run locally with Ollama stopped under `caffeinate -is`.
"""

from __future__ import annotations

import pytest

from tests.family_run_helpers import (
    count_flows_to_ip,
    count_honeypot_events,
    count_mqtt_topic,
    count_packets_to_ip,
    run_family_episode,
    within_tolerance,
)
from thesis.scenario.families.f5 import BotnetManifestError, load_manifest, verify_slice

FAMILY = "botnet"
DEVICE = "iot-cam-01"


@pytest.mark.slow
def test_f5_replays_botnet_traffic_in_flows_only_and_repeats() -> None:
    manifest = load_manifest()
    try:
        verify_slice(manifest)
    except BotnetManifestError as exc:
        pytest.skip(f"botnet slice not available: {exc}")

    c2 = manifest["retargeting"]["dst_ip"]
    a = run_family_episode(FAMILY, DEVICE, duration_s=90, seed=1)
    b = run_family_episode(FAMILY, DEVICE, duration_s=90, seed=1)

    pkts_a = count_packets_to_ip(a, c2)
    pkts_b = count_packets_to_ip(b, c2)
    flows_a = count_flows_to_ip(a, c2)
    flows_b = count_flows_to_ip(b, c2)

    # Predicted visibility: flows only. The replayed slice is ~10k packets to the C2.
    assert pkts_a > 5000
    assert count_honeypot_events(a) == 0  # not the honeypot
    assert count_mqtt_topic(a, "botnet") == 0 and count_mqtt_topic(a, "/flood") == 0  # no MQTT
    assert within_tolerance(FAMILY, "packets", pkts_a, pkts_b), (pkts_a, pkts_b)
    assert within_tolerance(FAMILY, "flows", flows_a, flows_b), (flows_a, flows_b)
