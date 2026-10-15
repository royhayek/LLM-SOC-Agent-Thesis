"""Alert schema v1: the one normalized format every source is turned into (Arch §5).

Drafted as v0.1 from the E0-01 spike (`spikes/FINDINGS.md`) and settled as v1 on the pilot and
corpus captures by E3-01; see `docs/schema/CHANGELOG.md` and `docs/schema/v1_field_check.md`.
Every field the frozen reduction policy (E0-05, Annex E) names is present or derivable here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

SCHEMA_VERSION: Final = "alert-v1"


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
    # Initiator SYN/ACK packet counts (NFStream src2dst_syn_packets / src2dst_ack_packets), needed
    # for the reduction's syn_only_ratio (Annex E §3). Optional: non-TCP flows have none.
    syn_count_fwd: int | None = None
    ack_count_fwd: int | None = None


class MqttDetail(_Strict):
    event: str
    # Optional (v1): a publish seen on the broker's subscriber log carries only its topic and
    # payload, no client id or addresses; those are known only for connect/disconnect/auth events
    # from the broker log. The subject device is mapped from the topic, not these fields.
    client_id: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
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
    schema_version: Literal["alert-v1"] = SCHEMA_VERSION
    alert_id: str
    source: Source
    ts: AwareDatetime
    subject_device: str
    detail: FlowDetail | MqttDetail | HoneypotDetail
    # Written by the detectors (EPIC-4), read by the reduction policy (Annex E §4, §7) to rank
    # exemplars and fill each source's `detector` block. Optional: absent until a detector scores
    # the alert, so v1 is complete for the reduction without EPIC-4 changing the schema.
    detector_score: float | None = None
    detector_label: str | None = None
    detector_name: str | None = None  # which detector scored it (E4-06); set at annotation time

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
