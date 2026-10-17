"""Demo-simulator support: a curated scenario catalog and the replay event assembly, read-only over
the frozen run (record §2, §5). No model call happens here (the optional live run lives in app.py).
Recommend-only: nothing in this module acts on a testbed or network (§1.1)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = REPO_ROOT / "config" / "demo_scenarios.yaml"


class Scenario(BaseModel):
    """One curated replay scenario. It selects its bundles by `episode_id`, or by an explicit
    `bundle_ids` list when the bundles carry no episode (benign background traffic)."""

    id: str
    title: str
    description: str
    episode_id: str | None
    bundle_ids: list[str] | None
    attack_family: str | None
    default_condition: str
    highlight: str | None


def load_scenarios(path: Path = SCENARIOS_PATH) -> list[Scenario]:
    """Load the curated scenario catalog from `config/demo_scenarios.yaml`."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Scenario.model_validate(s) for s in data["scenarios"]]


__all__ = ["SCENARIOS_PATH", "Scenario", "load_scenarios"]
