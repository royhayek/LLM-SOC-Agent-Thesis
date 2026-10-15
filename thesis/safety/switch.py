"""The enforcing / logging_only safety switch (E7-06, SCRUM-85).

H3 compares the same agent with the safety layer on and off (proposal Methodology). The switch
turns on/off exactly the mechanisms E0-12 defined (C-16, docs/methods/safety_scoring.md §6.1) and
nothing else, so H3 isolates the effect of the constraints. The per-mode mechanism flags are read
from `config/safety_modes.yaml`, the machine-readable mirror of §6.1.

Under `logging_only` the validator still runs and records `would_reject` with its reason, but
changes nothing; the rejection policy is not applied and the completion is emitted unchanged
(E = R). The action catalog and output schema stay in the node 3 prompt in both modes (§4.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from thesis.config import Safety

MODES_PATH = Path(__file__).resolve().parents[2] / "config" / "safety_modes.yaml"


@dataclass(frozen=True)
class SafetyMode:
    """The mechanism flags for one safety mode (from config/safety_modes.yaml)."""

    name: str
    catalog_in_prompt: bool
    schema_in_prompt: bool
    constrained_decoding: bool
    validator_gate: bool
    rejection_policy: bool
    audit_log: bool

    @classmethod
    def load(cls, safety: Safety, path: Path = MODES_PATH) -> SafetyMode:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        flags = data[safety.value]
        return cls(
            name=safety.value,
            catalog_in_prompt=bool(flags["catalog_in_prompt"]),
            schema_in_prompt=bool(flags["schema_in_prompt"]),
            constrained_decoding=bool(flags["constrained_decoding"]),
            validator_gate=bool(flags["validator_gate"]),
            rejection_policy=bool(flags["rejection_policy"]),
            audit_log=bool(flags["audit_log"]),
        )


__all__ = ["MODES_PATH", "SafetyMode"]
