"""Real-testbed test for attack family F1, MQTT publish flood (E1-08). Marked slow."""

from __future__ import annotations

import pytest

from tests.family_run_helpers import (
    count_flows_for_ip,
    count_honeypot_events,
    count_mqtt_topic,
    device_ip,
    run_family_episode,
    within_tolerance,
)

FAMILY = "mqtt_publish_flood"
DEVICE = "iot-temp-01"


@pytest.mark.slow
def test_f1_leaves_mqtt_and_flow_traces_and_repeats() -> None:
    a = run_family_episode(FAMILY, DEVICE, duration_s=120, seed=1)
    b = run_family_episode(FAMILY, DEVICE, duration_s=120, seed=1)
    ip = device_ip(DEVICE)

    mqtt_a = count_mqtt_topic(a, f"iot/{DEVICE}/flood")
    mqtt_b = count_mqtt_topic(b, f"iot/{DEVICE}/flood")
    flows_a = count_flows_for_ip(a, ip)
    flows_b = count_flows_for_ip(b, ip)

    # Predicted visibility (attack_families.yaml): mqtt yes, flows yes, honeypot no.
    assert mqtt_a > 0 and count_flows_for_ip(a, ip) > 0
    assert count_honeypot_events(a) == 0
    # Repeatability within the F1 tolerance.
    assert within_tolerance(FAMILY, "mqtt", mqtt_a, mqtt_b), (mqtt_a, mqtt_b)
    assert within_tolerance(FAMILY, "flows", flows_a, flows_b), (flows_a, flows_b)
