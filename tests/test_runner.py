"""Tests for the scenario runner (E1-07).

The fast tests inject fakes for the three seams (testbed controller, isolation gate, attack
family runners) and a fake clock, so they exercise the orchestration without Docker. The
one slow test runs the real testbed on the two-episode example schedule.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from thesis.scenario import run as cli
from thesis.scenario.runner import (
    AttackHandle,
    EpisodeOutcome,
    RunResult,
    run_from_file,
    run_scenario,
)
from thesis.scenario.schedule import AttackFamily, Episode, Schedule
from thesis.testbed.isolation import IsolationResult

REPO_ROOT = Path(__file__).resolve().parent.parent


def _schedule() -> Schedule:
    return Schedule(
        episodes=(
            Episode(
                id="ep-001",
                family=AttackFamily.SSH_BRUTE_FORCE,
                target_device="hp-ssh-01",
                start_offset_s=5,
                duration_s=10,
                parameters={},
                seed=1,
            ),
            Episode(
                id="ep-002",
                family=AttackFamily.MQTT_PUBLISH_FLOOD,
                target_device="iot-temp-01",
                start_offset_s=5,
                duration_s=10,
                parameters={},
                seed=2,
            ),
        )
    )


class FakeHandle:
    def __init__(self, exit_status: int) -> None:
        self._exit_status = exit_status
        self.stopped = False

    def stop(self) -> int:
        self.stopped = True
        return self._exit_status


class FakeRunner:
    """A fake attack family: records which episodes it started and hands out fake handles."""

    def __init__(self, family: AttackFamily, exit_status: int = 0) -> None:
        self.family = family
        self._exit_status = exit_status
        self.started: list[str] = []
        self.handles: list[FakeHandle] = []

    def start(self, episode: Episode, run_dir: Path) -> AttackHandle:
        self.started.append(episode.id)
        handle = FakeHandle(self._exit_status)
        self.handles.append(handle)
        return handle


class RaisingRunner:
    def __init__(self, family: AttackFamily) -> None:
        self.family = family

    def start(self, episode: Episode, run_dir: Path) -> AttackHandle:
        raise RuntimeError("attack failed to start")


class FakeController:
    """Creates a run folder with empty raw-log files, like `make up` would."""

    def __init__(self, base: Path) -> None:
        self._base = base
        self.down_called = False
        self.run_dir: Path | None = None

    def up(self) -> Path:
        run_dir = self._base / "run-fake"
        for source, name in (
            ("mqtt", "mqtt.log"),
            ("flows", "flows.jsonl"),
            ("honeypot", "cowrie.json"),
        ):
            (run_dir / source).mkdir(parents=True, exist_ok=True)
            (run_dir / source / name).write_text("", encoding="utf-8")
        self.run_dir = run_dir
        return run_dir

    def down(self) -> None:
        self.down_called = True


def _ok_iso(**_kwargs: object) -> IsolationResult:
    return IsolationResult(
        passed=True,
        exit_code=0,
        timed_out=False,
        utc_ts="2026-01-01T00:00:00+00:00",
        run_id="run-fake",
    )


def _fail_iso(**_kwargs: object) -> IsolationResult:
    return IsolationResult(
        passed=False,
        exit_code=1,
        timed_out=False,
        utc_ts="2026-01-01T00:00:00+00:00",
        run_id="run-fake",
    )


class _Clock:
    """A clock that advances one second per call, so actual times are distinct and ordered."""

    def __init__(self) -> None:
        self._n = 0

    def now(self) -> datetime:
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(seconds=self._n)
        self._n += 1
        return ts


def _run(
    tmp_path: Path,
    registry: dict[AttackFamily, object] | None = None,
    isolation: object = _ok_iso,
) -> tuple[RunResult, FakeController]:
    controller = FakeController(tmp_path)
    result = run_scenario(
        _schedule(),
        registry=registry or {},  # type: ignore[arg-type]
        controller=controller,
        isolation=isolation,  # type: ignore[arg-type]
        sleep=lambda _s: None,
        now=_Clock().now,
        monotonic=lambda: 0.0,
    )
    return result, controller


def _log_lines(run_dir: Path) -> list[dict[str, object]]:
    text = (run_dir / "execution_log.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_run_folder_has_artifacts(tmp_path: Path) -> None:
    result, _ = _run(tmp_path)
    run_dir = result.run_dir
    assert (run_dir / "schedule.yaml").is_file()
    assert (run_dir / "execution_log.jsonl").is_file()
    assert (run_dir / "mqtt" / "mqtt.log").is_file()
    assert (run_dir / "flows" / "flows.jsonl").is_file()
    assert (run_dir / "honeypot" / "cowrie.json").is_file()


def test_execution_log_has_required_episode_fields(tmp_path: Path) -> None:
    registry = {
        AttackFamily.SSH_BRUTE_FORCE: FakeRunner(AttackFamily.SSH_BRUTE_FORCE),
        AttackFamily.MQTT_PUBLISH_FLOOD: FakeRunner(AttackFamily.MQTT_PUBLISH_FLOOD),
    }
    result, _ = _run(tmp_path, registry=registry)
    episodes = [line for line in _log_lines(result.run_dir) if line["event"] == "episode"]
    assert {e["id"] for e in episodes} == {"ep-001", "ep-002"}
    for e in episodes:
        for field in (
            "planned_start_utc",
            "planned_end_utc",
            "actual_start_utc",
            "actual_end_utc",
            "exit_status",
            "seed",
        ):
            assert field in e, field
        assert e["actual_start_utc"] is not None
        assert e["actual_end_utc"] is not None


def test_planned_times_follow_offsets(tmp_path: Path) -> None:
    result, _ = _run(tmp_path)
    by_id = {o.id: o for o in result.episodes}
    ep = by_id["ep-001"]
    # scenario_start is the first _Clock tick; planned = scenario_start + offset.
    assert ep.planned_start_utc == "2026-01-01T00:00:05+00:00"
    assert ep.planned_end_utc == "2026-01-01T00:00:15+00:00"


def test_nonzero_exit_marks_run_invalid(tmp_path: Path) -> None:
    registry = {
        AttackFamily.SSH_BRUTE_FORCE: FakeRunner(AttackFamily.SSH_BRUTE_FORCE, exit_status=1),
        AttackFamily.MQTT_PUBLISH_FLOOD: FakeRunner(AttackFamily.MQTT_PUBLISH_FLOOD, exit_status=0),
    }
    result, _ = _run(tmp_path, registry=registry)
    assert result.valid is False
    assert result.aborted is False
    status = [line for line in _log_lines(result.run_dir) if line["event"] == "run_status"][-1]
    assert status["valid"] is False
    failed = [o for o in result.episodes if o.id == "ep-001"][0]
    assert failed.exit_status == 1
    assert failed.status == "failed"


def test_isolation_failure_starts_no_episode(tmp_path: Path) -> None:
    ssh = FakeRunner(AttackFamily.SSH_BRUTE_FORCE)
    registry = {AttackFamily.SSH_BRUTE_FORCE: ssh}
    result, controller = _run(tmp_path, registry=registry, isolation=_fail_iso)
    assert result.aborted is True
    assert result.valid is False
    assert result.isolation_passed is False
    assert ssh.started == []  # no episode started
    assert result.episodes == ()
    assert controller.down_called is True  # testbed still torn down
    assert not (result.run_dir / "schedule.yaml").is_file()  # aborted before the copy


def test_actual_times_come_from_the_runner_clock(tmp_path: Path) -> None:
    registry = {
        AttackFamily.SSH_BRUTE_FORCE: FakeRunner(AttackFamily.SSH_BRUTE_FORCE),
        AttackFamily.MQTT_PUBLISH_FLOOD: FakeRunner(AttackFamily.MQTT_PUBLISH_FLOOD),
    }
    result, _ = _run(tmp_path, registry=registry)
    for o in result.episodes:
        assert o.actual_start_utc is not None and o.actual_start_utc.endswith("+00:00")
        assert o.actual_end_utc is not None and o.actual_end_utc.endswith("+00:00")


def test_every_started_episode_is_stopped(tmp_path: Path) -> None:
    ssh = FakeRunner(AttackFamily.SSH_BRUTE_FORCE)
    mqtt = FakeRunner(AttackFamily.MQTT_PUBLISH_FLOOD)
    registry = {AttackFamily.SSH_BRUTE_FORCE: ssh, AttackFamily.MQTT_PUBLISH_FLOOD: mqtt}
    _run(tmp_path, registry=registry)
    assert all(h.stopped for h in ssh.handles)
    assert all(h.stopped for h in mqtt.handles)


def test_unregistered_family_is_no_runner_not_invalid(tmp_path: Path) -> None:
    result, _ = _run(tmp_path, registry={})
    assert result.valid is True
    assert {o.status for o in result.episodes} == {"no_runner"}
    assert all(o.exit_status is None for o in result.episodes)


def test_testbed_is_torn_down_even_when_an_episode_errors(tmp_path: Path) -> None:
    registry = {AttackFamily.SSH_BRUTE_FORCE: RaisingRunner(AttackFamily.SSH_BRUTE_FORCE)}
    controller = FakeController(tmp_path)
    with pytest.raises(RuntimeError, match="attack failed to start"):
        run_scenario(
            _schedule(),
            registry=registry,  # type: ignore[arg-type]
            controller=controller,
            isolation=_ok_iso,  # type: ignore[arg-type]
            sleep=lambda _s: None,
            now=_Clock().now,
            monotonic=lambda: 0.0,
        )
    assert controller.down_called is True


def test_cli_exit_code_maps_validity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake(result_valid: bool, aborted: bool) -> RunResult:
        return RunResult(
            run_id="r",
            run_dir=tmp_path,
            valid=result_valid,
            aborted=aborted,
            isolation_passed=not aborted,
            episodes=(),
        )

    monkeypatch.setattr(cli, "run_from_file", lambda _p, **_k: fake(True, False))
    assert cli.main(["schedules/example_two.yaml"]) == 0
    monkeypatch.setattr(cli, "run_from_file", lambda _p, **_k: fake(False, False))
    assert cli.main(["schedules/example_two.yaml"]) == 1
    monkeypatch.setattr(cli, "run_from_file", lambda _p, **_k: fake(False, True))
    assert cli.main(["schedules/example_two.yaml"]) == 1


def test_episode_outcome_is_frozen() -> None:
    o = EpisodeOutcome(
        id="x",
        family=AttackFamily.SYN_FLOOD,
        target_device="d",
        seed=0,
        planned_start_utc="2026-01-01T00:00:00+00:00",
        planned_end_utc="2026-01-01T00:00:10+00:00",
        actual_start_utc=None,
        actual_end_utc=None,
        exit_status=None,
        status="no_runner",
    )
    with pytest.raises(ValidationError):
        o.status = "ok"  # type: ignore[misc]


@pytest.mark.slow
def test_two_episode_run_on_the_real_testbed() -> None:
    """Boots the real testbed on the two-episode example and checks the run folder.

    No attack family is registered yet (E1-08..E1-13), so both episodes are `no_runner`
    and the run is valid; the point here is the real isolation gate, folder and logs.
    """
    result = run_from_file(REPO_ROOT / "schedules" / "example_two.yaml")
    assert result.aborted is False
    assert result.valid is True
    run_dir = result.run_dir
    assert (run_dir / "schedule.yaml").is_file()
    assert (run_dir / "mqtt" / "mqtt.log").is_file()
    assert (run_dir / "flows" / "flows.jsonl").is_file()
    lines = _log_lines(run_dir)
    assert any(
        line.get("event") == "isolation_check" and line.get("result") == "pass" for line in lines
    )
    assert sum(1 for line in lines if line.get("event") == "episode") == 2
    assert [line for line in lines if line.get("event") == "run_status"][-1]["valid"] is True
