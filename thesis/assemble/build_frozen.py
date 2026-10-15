"""Build the frozen reduced bundle set for corpus v1.0.0 and record its hash (E3-09, SCRUM-105).

Every condition — agent and both baselines — must receive the identical bundle set (record §4);
its hash is what lets any later result be traced to exactly these bundles. This runs the frozen
pipeline on corpus v1.0.0 (normalization → detectors/annotation → assembly), splits bundles into
evaluation and Baseline-A training by the E2-01 rule, writes Parquet, hashes, and checks the
counts against METHODS.md v1.1 (E2-02).

    python -m thesis.assemble.build_frozen    # writes data/bundles/v1.0.0/, prints the hashes

Split rule (E2-01, METHODS.md changelog 7). Attack bundles follow their episode's split, read from
the episode id (`ep-<fam>-eval-NNN` / `-train-NNN`). Benign bundles are counted only from the
explicit benign blocks (`bn-eval-NNN` / `bn-train-NNN`), across the continuously-publishing MQTT
devices (`config/corpus.yaml`): a benign bundle is placed in the split of the benign block its
window overlaps most. Idle benign windows during the attack phase overlap no block and are the
uncounted margin (E2-03, `docs/corpus/expected_counts.md`); they are not part of the frozen set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]

from thesis.assemble.bundles import BENIGN, Bundle, assemble, bundle_set_hash, write_bundles
from thesis.corpus.manifest import verify as verify_corpus
from thesis.detect.annotate import annotate_run
from thesis.labels.windows import labels_path as labels_path_for
from thesis.labels.windows import load_window_seconds, read_executed_episodes, read_labels
from thesis.normalize.store import read_alerts
from thesis.schema.alert import Alert, Source

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "raw" / "corpus-v1.0.0"
CORPUS_CONFIG = REPO_ROOT / "config" / "corpus.yaml"
OUT_DIR = REPO_ROOT / "data" / "bundles" / "v1.0.0"
ANNOTATED_TMP = REPO_ROOT / "data" / "bundles" / "_annotated"
REPORT_PATH = REPO_ROOT / "docs" / "corpus" / "frozen_bundle_set.md"

EVAL = "eval"
TRAIN = "train"


@dataclass(frozen=True)
class FrozenSet:
    eval_bundles: list[Bundle]
    train_bundles: list[Bundle]
    eval_hash: str
    train_hash: str


def _load_config() -> dict[str, object]:
    return cast("dict[str, object]", yaml.safe_load(CORPUS_CONFIG.read_text(encoding="utf-8")))


def _scenario_start(run_dir: Path) -> datetime:
    """Recover the run's scenario clock from the executed episodes and the planned offsets.

    `planned_start = scenario_start + offset`, so `scenario_start = actual_start - offset` per
    episode. The latest-offset episode is used, nearest the benign blocks that follow the attack
    phase, so any accumulated drift is not extrapolated past them.
    """
    schedule = yaml.safe_load((run_dir / "schedule.yaml").read_text(encoding="utf-8"))
    offset = {e["id"]: int(e["start_offset_s"]) for e in schedule.get("episodes", [])}
    executed = read_executed_episodes(run_dir / "execution_log.jsonl")
    anchored = [
        (offset[ex.id], ex.start - timedelta(seconds=offset[ex.id]))
        for ex in executed
        if ex.id in offset
    ]
    if not anchored:
        raise SystemExit(f"{run_dir.name}: no executed episode matches the schedule offsets")
    return max(anchored, key=lambda t: t[0])[1]


def _benign_blocks(run_dir: Path) -> list[tuple[datetime, datetime, str]]:
    """Absolute [start, end) and split of each benign block in the run."""
    schedule = yaml.safe_load((run_dir / "schedule.yaml").read_text(encoding="utf-8"))
    start = _scenario_start(run_dir)
    blocks = []
    for b in schedule.get("benign_periods", []):
        bs = start + timedelta(seconds=int(b["start_offset_s"]))
        be = bs + timedelta(seconds=int(b["duration_s"]))
        blocks.append((bs, be, str(b["split"])))
    return blocks


def _overlap_s(ws: datetime, we: datetime, bs: datetime, be: datetime) -> float:
    return max(0.0, (min(we, be) - max(ws, bs)).total_seconds())


def _benign_split(
    bundle: Bundle, blocks: list[tuple[datetime, datetime, str]], mqtt_devices: set[str]
) -> str | None:
    if bundle.device not in mqtt_devices:
        return None
    best_split: str | None = None
    best_overlap = 0.0
    for bs, be, split in blocks:
        ov = _overlap_s(bundle.window_start, bundle.window_end, bs, be)
        if ov > best_overlap:
            best_overlap, best_split = ov, split
    return best_split


def _attack_split(episode_id: str | None) -> str:
    return TRAIN if episode_id is not None and f"-{TRAIN}-" in episode_id else EVAL


def _run_bundles(run_dir: Path, window_s: int) -> list[Bundle]:
    annotate_run(run_dir, annotated_dir=ANNOTATED_TMP)
    alerts: list[Alert] = []
    for source in (Source.FLOWS, Source.MQTT, Source.HONEYPOT):
        path = ANNOTATED_TMP / source.value / f"{run_dir.name}.parquet"
        if path.exists():
            alerts.extend(read_alerts(path))
    labels = read_labels(labels_path_for(run_dir.name))
    if not labels:
        raise SystemExit(f"{run_dir.name}: no labels at {labels_path_for(run_dir.name)}")
    t0 = min(wl.window_start for wl in labels)  # the committed label grid's phase
    return assemble(alerts, labels, sources=set(Source), window_s=window_s, t0=t0)


def _str_list(config: dict[str, object], key: str) -> list[str]:
    return [str(v) for v in cast("list[object]", config[key])]


def build() -> FrozenSet:
    problems = verify_corpus()
    if problems:
        raise SystemExit(f"corpus manifest verify failed ({len(problems)} problems); aborting")

    config = _load_config()
    mqtt_devices = set(_str_list(config, "mqtt_devices"))
    window_s = load_window_seconds()

    eval_bundles: list[Bundle] = []
    train_bundles: list[Bundle] = []
    for run_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        blocks = _benign_blocks(run_dir)
        for b in _run_bundles(run_dir, window_s):
            if b.label != BENIGN:
                split: str | None = _attack_split(b.episode_id)
            else:
                split = _benign_split(b, blocks, mqtt_devices)
            if split == EVAL:
                eval_bundles.append(b)
            elif split == TRAIN:
                train_bundles.append(b)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_bundles(eval_bundles, OUT_DIR / "eval.parquet")
    write_bundles(train_bundles, OUT_DIR / "train.parquet")
    return FrozenSet(
        eval_bundles=eval_bundles,
        train_bundles=train_bundles,
        eval_hash=bundle_set_hash(eval_bundles),
        train_hash=bundle_set_hash(train_bundles),
    )


def _family_counts(bundles: list[Bundle]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for b in bundles:
        counts[b.label] = counts.get(b.label, 0) + 1
    return counts


def _check(result: FrozenSet, config: dict[str, object]) -> tuple[list[str], list[str]]:
    families = _str_list(config, "families")
    eval_target = int(cast(int, config["eval_bundles_per_family"]))
    benign_eval_target = int(cast(int, config["benign_eval_bundles"]))
    eval_counts = _family_counts(result.eval_bundles)
    lines, shortfalls = [], []
    for fam in families:
        n = eval_counts.get(fam, 0)
        ok = n >= eval_target
        lines.append(f"| {fam} | {n} | {eval_target} | {'ok' if ok else 'SHORT'} |")
        if not ok:
            shortfalls.append(f"{fam}: {n} < {eval_target}")
    nb = eval_counts.get(BENIGN, 0)
    ok = nb >= benign_eval_target
    lines.append(f"| benign | {nb} | {benign_eval_target} | {'ok' if ok else 'SHORT'} |")
    if not ok:
        shortfalls.append(f"benign: {nb} < {benign_eval_target}")
    return lines, shortfalls


def _write_report(result: FrozenSet, config: dict[str, object], rows: list[str]) -> None:
    ev = result.eval_bundles
    tr = result.train_bundles
    train_counts = _family_counts(tr)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Frozen bundle set — corpus v1.0.0 (E3-09, SCRUM-105)",
        "",
        "GENERATED by `python -m thesis.assemble.build_frozen`. The hashes below are recorded in",
        "METHODS.md and `docs/thesis_notes.md`; the Parquet lives under `data/bundles/v1.0.0/`",
        "(git-ignored, like the raw corpus). Counts are checked against METHODS.md v1.1 (E2-02).",
        "",
        f"- Evaluation bundles: **{len(ev)}**  (hash `{result.eval_hash}`)",
        f"- Baseline-A training bundles: **{len(tr)}**  (hash `{result.train_hash}`)",
        "",
        "## Evaluation counts vs target (METHODS.md v1.1)",
        "",
        "| Label | Eval count | Target | |",
        "|---|---|---|---|",
        *rows,
        "",
        "## Baseline-A training counts",
        "",
        "| Label | Train count |",
        "|---|---|",
        *(f"| {fam} | {train_counts.get(fam, 0)} |" for fam in _str_list(config, "families")),
        f"| benign | {train_counts.get(BENIGN, 0)} |",
    ]
    REPORT_PATH.write_text("\n".join(body) + "\n", encoding="utf-8")


def main() -> int:
    result = build()
    config = _load_config()
    rows, shortfalls = _check(result, config)
    _write_report(result, config, rows)
    print(f"eval bundles:  {len(result.eval_bundles)}  hash {result.eval_hash}")
    print(f"train bundles: {len(result.train_bundles)}  hash {result.train_hash}")
    if shortfalls:
        print("SHORTFALL vs METHODS.md v1.1 target:")
        for s in shortfalls:
            print(f"  - {s}")
        print("Record the shortfall and log a decision in the METHODS.md changelog (E3-09 AC).")
        return 1
    print("all evaluation counts at or above target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
