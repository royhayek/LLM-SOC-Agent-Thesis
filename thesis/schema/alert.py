"""Alert schema v0.1: the one normalized format every source is turned into (Arch §5).

Shaped by the E0-01 spike (`spikes/FINDINGS.md`); see `docs/schema/CHANGELOG.md`.
Draft only: v1 is settled on the pilot capture by E3-01.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

SCHEMA_VERSION: Final = "alert-v0.1"


class Source(StrEnum):
    FLOWS = "flows"
    MQTT = "mqtt"
    HONEYPOT = "honeypot"


class SourceState(StrEnum):
    """State of one source in a bundle's `sources` block (FINDINGS.md, "Source states")."""

    ACTIVE = "active"  # running, and sent alerts in this window
    NO_ALERTS = "no_alerts"  # running, and saw nothing in this window
    NOT_IN_CONFIG = "not_in_config"  # switched off in this experiment condition


class _Strict(BaseModel):
    # Unknown fields are rejected so drift between sources fails loudly.
    model_config = ConfigDict(extra="forbid", frozen=True)


# Flows and honeypot sessions share the field names src_ip, src_port, dst_ip, dst_port and
# protocol, so a flow can be tied to the session with the same tuple (FINDINGS.md, gap 2).


class FlowDetail(_Strict):
    flow_start: AwareDatetime
    duration_s: float
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    protocol: str
    packets_fwd: int
    packets_bwd: int
    bytes_fwd: int
    bytes_bwd: int
    tcp_flags: str | None = None


class MqttDetail(_Strict):
    event: str
    client_id: str
    src_ip: str
    dst_ip: str
    src_port: int | None = None
    dst_port: int | None = None
    topic: str | None = None
    qos: int | None = None
    payload_bytes: int | None = None


class HoneypotDetail(_Strict):
    event: str
    session_id: str
    src_ip: str
    src_port: int | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    protocol: str | None = None
    username: str | None = None
    password: str | None = None
    command: str | None = None
    client_version: str | None = None


_DETAIL_FOR_SOURCE: dict[Source, type[_Strict]] = {
    Source.FLOWS: FlowDetail,
    Source.MQTT: MqttDetail,
    Source.HONEYPOT: HoneypotDetail,
}


class Alert(_Strict):
    schema_version: Literal["alert-v0.1"] = SCHEMA_VERSION
    alert_id: str
    source: Source
    ts: AwareDatetime
    subject_device: str
    detail: FlowDetail | MqttDetail | HoneypotDetail

    @model_validator(mode="after")
    def _detail_matches_source(self) -> Self:
        expected = _DETAIL_FOR_SOURCE[self.source]
        if not isinstance(self.detail, expected):
            raise ValueError(f"source {self.source} needs {expected.__name__}")
        return self

    def to_json(self) -> str:
        """Canonical serialisation: unset optional fields are left out to save tokens."""
        return self.model_dump_json(exclude_none=True)


__all__ = [
    "SCHEMA_VERSION",
    "Alert",
    "FlowDetail",
    "HoneypotDetail",
    "MqttDetail",
    "Source",
    "SourceState",
]
