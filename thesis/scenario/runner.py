"""The scenario runner: turn a validated schedule into raw telemetry plus a record of
what actually happened (record §4.1, §6.7; proposal Objective 1).

The runner only orchestrates the isolated testbed. It brings the testbed up, proves it
isolated (the E1-01 gate), starts and stops each episode at its offset, records the
*actual* start and end times from one clock (the runner's host UTC clock, never a
container's), and leaves a run folder behind. It opens no network connection itself and
no code path here acts on anything outside the testbed: the system only records.

Labels are derived from the executed times in `execution_log.jsonl`, not from the plan
(record §4.1), so container start-up delay cannot shift a label.

Attack families (E1-08..E1-13) plug in through one interface, `AttackFamilyRunner`: each
family ticket adds one class. A family with no registered runner is recorded as
`no_runner` and does not invalidate the run, so the orchestration runs end to end before
any family exists. The identity of a family is the `AttackFamily` enum in
`thesis.scenario.schedule`; this module names the behavioural interface
`AttackFamilyRunner` so it does not shadow that enum.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

import structlog
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from thesis.scenario.schedule import AttackFamily, Episode, Schedule
from thesis.testbed.isolation import IsolationResult, current_run_id, isolation_check

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent
RAW_DIR: Final = REPO_ROOT / "data" / "raw"
EXECUTION_LOG: Final = "execution_log.jsonl"
SCHEDULE_COPY: Final = "schedule.yaml"


class AttackHandle(Protocol):
    """A started episode. `stop()` ends the attack, reaps it and returns its exit status.

    It must stop the attack for good (an attack left running past its end time silently
    extends the episode, record §4.1 gotcha). 0 means the episode ran as intended; any
    other value marks the run invalid.
    """

    def stop(self) -> int: ...


@runtime_checkable
class AttackFamilyRunner(Protocol):
    """One attack family plug-in (E1-08..E1-13 add one each).

    `start()` launches the attack for `episode` inside the testbed and returns a handle the
    runner stops at the episode's end offset. The plug-in owns neither the clock nor the
    schedule: it must not sleep for the episode's duration, and it runs only against testbed
    hosts on the isolated network (record §5, §6.11; ADR-0003).
    """

    family: AttackFamily

    def start(self, episode: Episode, run_dir: Path) -> AttackHandle: ...


class TestbedController(Protocol):
    """The testbed lifecycle. `up()` starts it and returns the run folder; `down()` stops it
    and derives the flows (ADR-0008). Abstracted so the runner is testable without Docker.
    """

    def up(self) -> Path: ...

    def down(self) -> None: ...


class MakeTestbedController:
    """The real testbed, driven by `make up` / `make down` (record §4.2; ADR-0008).

    `make up` writes the run id to `data/raw/.current_run`; the run folder is read from it.
    """

    def __init__(self, repo_root: Path = REPO_ROOT, raw_dir: Path = RAW_DIR) -> None:
        self._repo_root = repo_root
        self._raw_dir = raw_dir

    def up(self) -> Path:
        subprocess.run(["make", "up"], cwd=self._repo_root, check=True)
        run_id = current_run_id(self._raw_dir)
        if run_id is None:
            raise RuntimeError("make up did not write data/raw/.current_run")
        return self._raw_dir / run_id

    def down(self) -> None:
        subprocess.run(["make", "down"], cwd=self._repo_root, check=True)


class EpisodeOutcome(BaseModel):
    """What happened to one episode. `exit_status` is None when no runner was registered."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str
    family: AttackFamily
    target_device: str
    seed: int
    planned_start_utc: str
    planned_end_utc: str
    actual_start_utc: str | None
    actual_end_utc: str | None
    exit_status: int | None
    status: str  # "ok", "failed" or "no_runner"


class RunResult(BaseModel):
    """The result of one scenario run."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str
    run_dir: Path
    valid: bool
    aborted: bool  # true when the isolation gate failed, so no episode started
    isolation_passed: bool
    episodes: tuple[EpisodeOutcome, ...]


def _append(log_path: Path, **fields: object) -> None:
    """Append one structured JSON line to the execution log, in the isolation log's style."""
    with log_path.open("a", encoding="utf-8") as sink:
        logger = structlog.wrap_logger(
            structlog.WriteLogger(sink),
            processors=[structlog.processors.JSONRenderer(sort_keys=True)],
            wrapper_class=structlog.BoundLogger,
        )
        logger.msg(**fields)


def _copy_schedule(schedule: Schedule, run_dir: Path, schedule_src: Path | None) -> None:
    """Keep a copy of the schedule next to the raw logs. The original file (comments and
    all) is copied when its path is known; otherwise the validated schedule is dumped.
    """
    dest = run_dir / SCHEDULE_COPY
    if schedule_src is not None:
        shutil.copyfile(schedule_src, dest)
        return
    with dest.open("w", encoding="utf-8") as f:
        yaml.safe_dump(schedule.model_dump(mode="json"), f, sort_keys=False)


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    offset_s: int
    is_start: bool
    episode: Episode


def _timeline(schedule: Schedule) -> list[_Event]:
    """Start and stop events in time order. At one offset, stops come before starts, so a
    handle is freed before the next one is taken; starts of concurrent episodes (allowed on
    different devices) are ordered by episode id for a deterministic sequence.
    """
    events: list[_Event] = []
    for ep in schedule.episodes:
        events.append(_Event(offset_s=ep.start_offset_s, is_start=True, episode=ep))
        events.append(_Event(offset_s=ep.end_offset_s, is_start=False, episode=ep))
    events.sort(key=lambda e: (e.offset_s, e.is_start, e.episode.id))
    return events


def run_scenario(
    schedule: Schedule,
    *,
    schedule_src: Path | None = None,
    registry: Mapping[AttackFamily, AttackFamilyRunner] | None = None,
    controller: TestbedController | None = None,
    isolation: Callable[..., IsolationResult] = isolation_check,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> RunResult:
    """Execute `schedule` end to end against the testbed and return the run result.

    Order: bring the testbed up, run the isolation gate against it, and only if it passes
    start the episodes at their offsets. The testbed is always brought down afterwards, so
    the flows are derived and nothing is left running. A non-zero episode exit, or an
    isolation failure, makes the run invalid; the isolation failure also aborts it with no
    episode started (E1-01).
    """
    registry = registry or {}
    controller = controller or MakeTestbedController()

    run_dir = controller.up()
    run_id = run_dir.name
    log = run_dir / EXECUTION_LOG

    try:
        iso = isolation()
        if not iso.passed:
            _append(
                log,
                event="run_status",
                run_id=run_id,
                valid=False,
                aborted=True,
                reason="isolation check failed",
            )
            return RunResult(
                run_id=run_id,
                run_dir=run_dir,
                valid=False,
                aborted=True,
                isolation_passed=False,
                episodes=(),
            )

        _copy_schedule(schedule, run_dir, schedule_src)
        outcomes = _run_episodes(
            schedule, run_dir, log, registry, sleep=sleep, now=now, monotonic=monotonic
        )
    finally:
        controller.down()

    valid = all(o.exit_status in (0, None) for o in outcomes)
    _append(
        log,
        event="run_status",
        run_id=run_id,
        valid=valid,
        aborted=False,
        reason="ok" if valid else "an episode exited non-zero",
    )
    return RunResult(
        run_id=run_id,
        run_dir=run_dir,
        valid=valid,
        aborted=False,
        isolation_passed=True,
        episodes=tuple(outcomes),
    )


def _run_episodes(
    schedule: Schedule,
    run_dir: Path,
    log: Path,
    registry: Mapping[AttackFamily, AttackFamilyRunner],
    *,
    sleep: Callable[[float], None],
    now: Callable[[], datetime],
    monotonic: Callable[[], float],
) -> list[EpisodeOutcome]:
    """Walk the timeline on the runner's own clock, starting and stopping each episode."""
    scenario_start = now()
    base_mono = monotonic()

    def _iso(offset_s: int) -> str:
        return (scenario_start + timedelta(seconds=offset_s)).isoformat(timespec="seconds")

    handles: dict[str, AttackHandle] = {}
    starts: dict[str, str] = {}
    outcomes: dict[str, EpisodeOutcome] = {}

    for event in _timeline(schedule):
        sleep(max(0.0, base_mono + event.offset_s - monotonic()))
        ep = event.episode
        runner = registry.get(ep.family)

        if event.is_start:
            if runner is None:
                outcomes[ep.id] = _outcome(ep, _iso, None, None, None, "no_runner")
                _log_episode(log, outcomes[ep.id])
                continue
            handles[ep.id] = runner.start(ep, run_dir)
            starts[ep.id] = now().isoformat(timespec="seconds")
        else:
            if ep.id not in handles:
                continue  # no_runner episode: already recorded at its start event
            exit_status = handles.pop(ep.id).stop()
            status = "ok" if exit_status == 0 else "failed"
            outcomes[ep.id] = _outcome(
                ep, _iso, starts[ep.id], now().isoformat(timespec="seconds"), exit_status, status
            )
            _log_episode(log, outcomes[ep.id])

    # Keep schedule order in the returned result.
    return [outcomes[ep.id] for ep in schedule.episodes]


def _outcome(
    ep: Episode,
    iso: Callable[[int], str],
    actual_start: str | None,
    actual_end: str | None,
    exit_status: int | None,
    status: str,
) -> EpisodeOutcome:
    return EpisodeOutcome(
        id=ep.id,
        family=ep.family,
        target_device=ep.target_device,
        seed=ep.seed,
        planned_start_utc=iso(ep.start_offset_s),
        planned_end_utc=iso(ep.end_offset_s),
        actual_start_utc=actual_start,
        actual_end_utc=actual_end,
        exit_status=exit_status,
        status=status,
    )


def _log_episode(log: Path, o: EpisodeOutcome) -> None:
    _append(log, event="episode", **o.model_dump())


def run_from_file(
    schedule_path: Path,
    *,
    registry: Mapping[AttackFamily, AttackFamilyRunner] | None = None,
    controller: TestbedController | None = None,
) -> RunResult:
    """Load a schedule file and run it (the CLI entry point's body)."""
    from thesis.scenario.schedule import load_schedule

    schedule = load_schedule(schedule_path)
    return run_scenario(
        schedule, schedule_src=schedule_path, registry=registry, controller=controller
    )
