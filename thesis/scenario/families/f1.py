"""Attack family F1: MQTT publish flood (E1-08; ADR-0003).

A compromised IoT device D floods the broker with PUBLISH messages over one connection. The
attack runs in D's own emulator container, so the traffic keys to D (record §4.1), using D's
own credentials (its `DEVICE_ID`/`PASSWORD` env). Tool: `mosquitto_pub` (already in the
emulator image), with a fixed message count, interval and payload size. Expected sources:
mqtt and flows (`attack_families.yaml`).

Bounded by the message count, so it finishes within the episode and exits 0. Parameters come
from ADR-0003; a schedule entry may override them through `episode.parameters` for tuning
during development, never for the corpus.
"""

from __future__ import annotations

from typing import Final

from thesis.scenario.families.base import ContainerAttackRunner
from thesis.scenario.schedule import AttackFamily, Episode

# Fixed parameters (ADR-0003: fixed PUBLISH count, interval and payload size, fixed topic).
COUNT: Final = 3000  # messages in the flood
INTERVAL_S: Final = 0.02  # between messages; 3000 x 0.02 s = 60 s, inside a 5-minute episode
PAYLOAD_BYTES: Final = 256
TOPIC: Final = "flood"  # published to iot/<device>/flood
QOS: Final = 0


class MqttPublishFloodRunner(ContainerAttackRunner):
    family = AttackFamily.MQTT_PUBLISH_FLOOD

    def service_for(self, episode: Episode) -> str:
        from thesis.scenario.families.base import DEVICE_SERVICE

        return DEVICE_SERVICE[episode.target_device]

    def command(self, episode: Episode) -> str:
        p = episode.parameters
        count = int(p.get("count", COUNT))
        interval = float(p.get("interval_s", INTERVAL_S))
        size = int(p.get("payload_bytes", PAYLOAD_BYTES))
        qos = int(p.get("qos", QOS))
        topic = f"iot/{episode.target_device}/{TOPIC}"
        # One connection (`--repeat` reuses it), D's own credentials from the container env.
        payload = "A" * size
        return (
            f'mosquitto_pub -h broker -u "$DEVICE_ID" -P "$PASSWORD" '
            f'-i "$DEVICE_ID-flood" -t {topic} -q {qos} '
            f"--repeat {count} --repeat-delay {interval} -m {payload}"
        )
