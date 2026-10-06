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
    assert "setsid" in launch and launch[3] == "setsid"
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
