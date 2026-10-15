"""Verdict schema (record §6.5): the structured output that is also the API schema.

The structured output is one of the four safety mechanisms (record §6.4). The same Pydantic model
is the safety contract and the console's API schema, so they cannot drift (§6.2). A `Verdict` is
composed from a `Classification` (node 2) and a `Recommendation` (node 3), plus the affected device
and the evidence alert ids — the evidence field is never removed (§4.4). When safety is enforcing,
generation is constrained to `verdict_json_schema()` (§6.4); see `thesis.llm.client`.

The recommended-action enum is **generated from** `knowledge/action_catalog.yaml` (E0-04), never
typed by hand, so it cannot drift from the frozen catalog.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "action_catalog.yaml"


class IncidentType(StrEnum):
    """The six attack families plus `benign` (record §6.5, METHODS.md Changelog entry 1)."""

    SSH_BRUTE_FORCE = "ssh_brute_force"
    PORT_SCAN = "port_scan"
    MQTT_PUBLISH_FLOOD = "mqtt_publish_flood"
    MQTT_BRUTE_FORCE = "mqtt_brute_force"
    SYN_FLOOD = "syn_flood"
    BOTNET = "botnet"
    BENIGN = "benign"


class Severity(StrEnum):
    """Reported severity (record §6.5). Descriptive only; no true severity is scored (§4.2)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _action_ids() -> list[str]:
    catalog = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    return [str(action["id"]) for action in catalog["actions"]]


ACTION_IDS: tuple[str, ...] = tuple(_action_ids())

if TYPE_CHECKING:
    # mypy cannot type a runtime-built enum; for type-checking `Action` is any string enum. At
    # runtime it is the real enum below, generated from the catalog, so Pydantic enumerates it in
    # the JSON schema and rejects any id not in the catalog.
    Action = StrEnum
else:
    Action = StrEnum("Action", {action_id.upper(): action_id for action_id in ACTION_IDS})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Classification(_Strict):
    """Node 2's output: the incident label and the model's confidence in it."""

    incident_type: IncidentType
    confidence: float = Field(ge=0, le=1)


class Recommendation(_Strict):
    """Node 3's output: one catalog action and the reported severity."""

    recommended_action: Action
    severity: Severity


class Verdict(_Strict):
    """The validated bundle verdict (record §6.5): classification + recommendation + evidence."""

    classification: Classification
    recommendation: Recommendation
    affected_device: str = Field(min_length=1)
    evidence: list[str]  # citable alert ids; never removed (§4.4)


def verdict_json_schema() -> dict[str, object]:
    """The JSON Schema used as the constrained-decoding output constraint (§6.4)."""
    return Verdict.model_json_schema()


__all__ = [
    "ACTION_IDS",
    "Action",
    "Classification",
    "IncidentType",
    "Recommendation",
    "Severity",
    "Verdict",
    "verdict_json_schema",
]
