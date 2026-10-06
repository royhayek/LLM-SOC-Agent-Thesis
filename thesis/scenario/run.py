"""CLI for the scenario runner (E1-07): `python -m thesis.scenario.run <schedule.yaml>`.

Exits non-zero when the run is invalid or was aborted by a failed isolation gate, so a
caller (and CI) can tell a good run from a bad one by the exit code alone.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from thesis.scenario.families import default_registry
from thesis.scenario.runner import run_from_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m thesis.scenario.run")
    parser.add_argument("schedule", type=Path, help="path to a scenario schedule YAML file")
    args = parser.parse_args(argv)

    result = run_from_file(args.schedule, registry=default_registry())
    print(
        f"run {result.run_id}: "
        f"{'aborted' if result.aborted else 'valid' if result.valid else 'invalid'} "
        f"({result.run_dir})"
    )
    return 0 if result.valid and not result.aborted else 1


if __name__ == "__main__":
    raise SystemExit(main())
