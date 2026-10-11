"""The scenario schedule, the only source of ground truth (record §4.1, METHODS.md §1).

A window is labelled F when it overlaps, by a non-zero duration, an episode of F against D.
Two episodes overlapping on one device would give a window two true labels, so the validator
rejects them. Time ranges are half-open, `[start, start + duration)`, like the windows: two
episodes that touch end to start are adjacent, not overlapping.
"""

from __future__ import annotations

from enum import StrEnum
from itertools import groupby
from pathlib import Path
from typing import Any, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from thesis.schema.verdict import IncidentType


class AttackFamily(StrEnum):
    """The six frozen attack families (E1-02): `IncidentType` without `benign`."""

    SSH_BRUTE_FORCE = IncidentType.SSH_BRUTE_FORCE.value
    PORT_SCAN = IncidentType.PORT_SCAN.value
    MQTT_PUBLISH_FLOOD = IncidentType.MQTT_PUBLISH_FLOOD.value
    MQTT_BRUTE_FORCE = IncidentType.MQTT_BRUTE_FORCE.value
    SYN_FLOOD = IncidentType.SYN_FLOOD.value
    BOTNET = IncidentType.BOTNET.value


class Split(StrEnum):
    """Which half of the corpus split an item belongs to (E2-01, METHODS.md Changelog entry 7).

    The split is by episode (and by benign block), fixed by a seed before generation, so no
    episode is ever both trained on and evaluated. `None` means the item predates the split
    (the pilot and example schedules), which stays valid.
    """

    TRAIN = "train"
    EVAL = "eval"


class _Strict(BaseModel):
    # Unknown fields are rejected so a misspelt field fails loudly instead of being ignored.
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Timed(_Strict):
    id: str = Field(min_length=1)
    # Strict, so a YAML `true` is refused instead of becoming 1.
    start_offset_s: int = Field(ge=0, strict=True)  # seconds from the start of the scenario
    duration_s: int = Field(gt=0, strict=True)
    # The corpus split (E2-01). Optional, so schedules written before E2-03 stay valid.
    split: Split | None = None

    @property
    def end_offset_s(self) -> int:
        """Exclusive end of the half-open range."""
        return self.start_offset_s + self.duration_s


class Episode(_Timed):
    """One scheduled run of one family against one device (METHODS.md §1)."""

    family: AttackFamily
    # D: the device the episode is scheduled on, attacked or attacking (METHODS.md, C-01).
    target_device: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int = Field(ge=0, strict=True)

    @field_validator("family", mode="before")
    @classmethod
    def _family_in_enum(cls, value: object) -> object:
        if not isinstance(value, str) or value not in {f.value for f in AttackFamily}:
            allowed = ", ".join(f.value for f in AttackFamily)
            raise ValueError(f"unknown attack family {value!r}; allowed: {allowed}")
        return value


class BenignPeriod(_Timed):
    """A stretch of benign-only traffic. Labels come from episodes only, so it adds no rule."""


class Schedule(_Strict):
    episodes: tuple[Episode, ...]
    benign_periods: tuple[BenignPeriod, ...] = ()

    @model_validator(mode="after")
    def _ids_unique(self) -> Self:
        ids = [e.id for e in self.episodes] + [b.id for b in self.benign_periods]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate ids: {', '.join(duplicates)}")
        return self

    @model_validator(mode="after")
    def _no_overlap_on_one_device(self) -> Self:
        clashes = []
        by_device = sorted(self.episodes, key=lambda e: (e.target_device, e.start_offset_s))
        for device, group in groupby(by_device, key=lambda e: e.target_device):
            episodes = list(group)
            for i, a in enumerate(episodes):
                for b in episodes[i + 1 :]:
                    if b.start_offset_s >= a.end_offset_s:
                        break
                    clashes.append(f"{a.id} and {b.id} on {device}")
        if clashes:
            raise ValueError(f"attack episodes overlap on the same device: {'; '.join(clashes)}")
        return self


def load_schedule(path: Path) -> Schedule:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Schedule.model_validate(data)
