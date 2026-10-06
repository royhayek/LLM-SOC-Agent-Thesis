"""Tests for the attack-family plug-ins (E1-08..E1-13).

Fast tests check the registry, the command each family builds and the container resolution,
with `docker` faked. The real attacks run in the family-specific `slow` tests (test_f*_run.py
or marked here). The frozen visibility matrix is tested in test_families.py (E1-02).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from thesis.scenario.families import base as fbase
from thesis.scenario.families import default_registry
from thesis.scenario.schedule import AttackFamily, Episode

TOLERANCE = Path(__file__).resolve().parent / "attack_tolerance.yaml"


def _episode(family: AttackFamily, device: str, **params: object) -> Episode:
    return Episode(
        id="ep-x",
        family=family,
        target_device=device,
        start_offset_s=0,
        duration_s=300,
        parameters=params,
        seed=1,
    )


def test_registry_has_no_duplicate_family() -> None:
    registry = default_registry()
    assert len(registry) == len(set(registry))
    for family, runner in registry.items():
        assert runner.family is family


def test_f1_is_registered() -> None:
    assert AttackFamily.MQTT_PUBLISH_FLOOD in default_registry()


def test_f1_command_uses_the_device_and_is_bounded() -> None:
    runner = default_registry()[AttackFamily.MQTT_PUBLISH_FLOOD]
    ep = _episode(AttackFamily.MQTT_PUBLISH_FLOOD, "iot-temp-01")
    assert runner.service_for(ep) == "emulator-temp"
    cmd = runner.command(ep)
    assert "mosquitto_pub" in cmd
    assert "iot/iot-temp-01/flood" in cmd
    assert '-u "$DEVICE_ID" -P "$PASSWORD"' in cmd  # D's own credentials, not hardcoded
    assert "--repeat 3000" in cmd  # bounded, so it finishes inside the episode


def test_f1_parameters_override_the_defaults() -> None:
    runner = default_registry()[AttackFamily.MQTT_PUBLISH_FLOOD]
    cmd = runner.command(_episode(AttackFamily.MQTT_PUBLISH_FLOOD, "iot-cam-01", count=10, qos=1))
    assert "--repeat 10" in cmd
    assert "-q 1" in cmd
    assert "iot/iot-cam-01/flood" in cmd


def test_container_id_raises_when_no_container(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    def fake_run(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="no running container"):
        fbase.container_id("emulator-temp")


def test_start_launches_setsid_and_stop_signals_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    """start() resolves the container and runs the command under setsid; stop() signals the
    group and returns the exit status. docker is faked, so no container is needed."""
    import subprocess

    calls: list[list[str]] = []

    class FakeProc:
        returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    def fake_popen(args: list[str], **_k: object) -> FakeProc:
        calls.append(args)
        return FakeProc()

    def fake_run(args: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(args, 0, "deadbeef\n", "")
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = default_registry()[AttackFamily.MQTT_PUBLISH_FLOOD]
    handle = runner.start(_episode(AttackFamily.MQTT_PUBLISH_FLOOD, "iot-temp-01"), Path("/tmp"))
    launch = calls[0]
    assert launch[:3] == ["docker", "exec", "deadbeef"]
    assert launch[3:5] == ["sh", "-c"]  # no setsid: it would mask the attack's exit code
    assert "echo $$" in launch[5]  # records the process-group id for stop()
    assert handle.stop() == 0
    kill = calls[-1]
    assert kill[:3] == ["docker", "exec", "deadbeef"]
    assert "kill -TERM" in kill[-1] and "kill -KILL" in kill[-1]


def test_tolerance_file_lists_implemented_families() -> None:
    tol = yaml.safe_load(TOLERANCE.read_text(encoding="utf-8"))
    assert "mqtt_publish_flood" in tol["families"]
    for family, sources in tol["families"].items():
        assert family in {f.value for f in AttackFamily}
        assert all(0 < v <= 1 for v in sources.values())


def test_f2_is_registered() -> None:
    assert AttackFamily.MQTT_BRUTE_FORCE in default_registry()


def test_f2_command_guesses_from_the_committed_list() -> None:
    from thesis.scenario.families.f2 import load_guesses

    guesses = load_guesses()
    assert len(guesses) >= 20
    runner = default_registry()[AttackFamily.MQTT_BRUTE_FORCE]
    ep = _episode(AttackFamily.MQTT_BRUTE_FORCE, "iot-cam-01")
    assert runner.service_for(ep) == "emulator-cam"
    cmd = runner.command(ep)
    assert "mosquitto_pub" in cmd and "iot-cam-01-brute" in cmd
    # Every committed guess appears in the loop; the attack is bounded by the list.
    assert cmd.count("mosquitto_pub") == 1  # one call inside the loop
    assert all(u in cmd for u, _ in guesses)


def test_f2_guesses_are_all_wrong() -> None:
    """No guess may match a real testbed login, or the CONNECT would succeed, not be refused."""
    from pathlib import Path

    from thesis.scenario.families.f2 import load_guesses

    creds_path = Path(__file__).resolve().parent.parent / "testbed" / "broker" / "credentials.txt"
    real = set()
    for line in creds_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            real.add(tuple(line.split(":", 1)))
    assert real
    for user, password in load_guesses():
        assert (user, password) not in real, f"{user}:{password} is a real login"


def test_f3_is_registered() -> None:
    assert AttackFamily.PORT_SCAN in default_registry()


def test_f3_runs_a_connect_scan_from_the_attacker() -> None:
    runner = default_registry()[AttackFamily.PORT_SCAN]
    ep = _episode(AttackFamily.PORT_SCAN, "hp-ssh-01")
    assert runner.service_for(ep) == "attacker"
    cmd = runner.command(ep)
    assert cmd.startswith("nmap -sT")  # connect scan: completes the handshake for Cowrie
    assert "10.77.0.10" in cmd  # the honeypot, by IP
    assert "-sS" not in cmd  # never a SYN-only scan (ADR-0003 prediction_risk)


def test_f4_is_registered() -> None:
    assert AttackFamily.SSH_BRUTE_FORCE in default_registry()


def test_f4_runs_hydra_over_the_committed_lists() -> None:
    from thesis.scenario.families.f4 import load_passwords, load_users

    assert len(load_users()) >= 1 and len(load_passwords()) >= 4
    runner = default_registry()[AttackFamily.SSH_BRUTE_FORCE]
    ep = _episode(AttackFamily.SSH_BRUTE_FORCE, "hp-ssh-01")
    assert runner.service_for(ep) == "attacker"
    cmd = runner.command(ep)
    assert "hydra" in cmd and "ssh://10.77.0.10" in cmd
    assert "-f " not in cmd  # no early exit: every pair is tried, so the count is fixed


def test_f6_is_registered() -> None:
    assert AttackFamily.SYN_FLOOD in default_registry()


def test_f6_runs_a_bounded_syn_flood_from_the_attacker() -> None:
    runner = default_registry()[AttackFamily.SYN_FLOOD]
    ep = _episode(AttackFamily.SYN_FLOOD, "iot-cam-01")
    assert runner.service_for(ep) == "attacker"
    cmd = runner.command(ep)
    assert "hping3 --syn --flood" in cmd
    assert cmd.startswith("timeout ")  # bounded by wall clock, so it exits within the episode
    assert "10.77.0.22" in cmd  # iot-cam-01 by IP, targeted directly (not the broker)


def test_all_six_families_are_registered() -> None:
    assert set(default_registry()) == set(AttackFamily)


def test_f5_is_registered() -> None:
    assert AttackFamily.BOTNET in default_registry()


def test_f5_manifest_is_provisional_and_refuses_to_run() -> None:
    """Until Roy provides the dataset slice and real SHA-256, F5 cannot build a command."""
    from thesis.scenario.families.f5 import BotnetManifestError, load_manifest, verify_slice

    manifest = load_manifest()
    assert manifest["source"]["sha256"] == "UNVERIFIED-PLACEHOLDER"
    with pytest.raises(BotnetManifestError, match="provisional"):
        verify_slice(manifest)
    runner = default_registry()[AttackFamily.BOTNET]
    with pytest.raises(BotnetManifestError):
        runner.command(_episode(AttackFamily.BOTNET, "iot-cam-01"))


def test_f5_command_retargets_to_the_device_and_non_routable_c2(tmp_path: object) -> None:
    """With a real local slice whose digest matches, the command retargets source to D and
    destination to the non-routable C2, and replays at the fixed rate."""
    import hashlib
    from pathlib import Path as _P

    from thesis.scenario.families import f5

    slice_path = _P(str(tmp_path)) / "slice.pcap"
    slice_path.write_bytes(b"not a real pcap, just for digest")
    digest = hashlib.sha256(slice_path.read_bytes()).hexdigest()
    manifest = {
        "source": {"sha256": digest, "local_path": str(slice_path)},
        "retargeting": {"dst_ip": "192.0.2.1", "replay_pps": 200},
    }
    # verify_slice accepts the matching digest.
    assert f5.verify_slice(manifest) == slice_path

    runner = f5.BotnetRunner()
    import unittest.mock as mock

    with mock.patch.object(f5, "load_manifest", return_value=manifest):
        cmd = runner.command(_episode(AttackFamily.BOTNET, "iot-cam-01"))
    assert "tcprewrite" in cmd and "tcpreplay" in cmd
    assert "--srcipmap=0.0.0.0/0:10.77.0.22" in cmd  # source -> iot-cam-01
    assert "--dstipmap=0.0.0.0/0:192.0.2.1" in cmd  # destination -> non-routable C2
    assert "--pps=200" in cmd
