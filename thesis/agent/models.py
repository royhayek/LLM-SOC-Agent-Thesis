"""Intermediate models passed between the agent's graph nodes (EPIC-6).

`Findings` is node 1's output (E6-03): per-source findings, cross-source observations, candidate
hypotheses and a missing-evidence list. The hypotheses and missing-evidence absorb the brief's
attack-hypothesis and missing-information requests (C-08); they are recorded, never acted on. Field
lengths are capped so node 1's output cannot push the next call over its input ceiling (§4.4).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from thesis.schema.verdict import Action, IncidentType, Severity

# Actions that are not a response to an incident, so they need no cited evidence (safety_scoring §6:
# "no_action and monitor are never unsafe … not responding costs usefulness, not safety"). A benign
# verdict recommends one of these and legitimately has no attack evidence to cite (METHODS changelog
# 21). Every other (active) action must cite at least one evidence id.
ACTIONS_WITHOUT_EVIDENCE = frozenset({"no_action", "monitor"})

_Short = Annotated[str, StringConstraints(max_length=300)]
_Para = Annotated[str, StringConstraints(max_length=800)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceFinding(_Strict):
    """What one source shows. `summary` states "no alerts" when the source was absent."""

    source: str = Field(min_length=1)
    summary: _Short
    evidence_ids: list[Annotated[str, StringConstraints(max_length=100)]] = Field(
        default_factory=list, max_length=20
    )


class Findings(_Strict):
    """Node 1's structured analysis of one reduced bundle plus retrieved context."""

    source_findings: list[SourceFinding] = Field(max_length=3)
    cross_source: _Para
    candidate_hypotheses: list[_Short] = Field(default_factory=list, max_length=5)
    missing_evidence: list[_Short] = Field(default_factory=list, max_length=5)


class Classification(_Strict):
    """Node 2's output (E6-04): the incident label, severity, affected device and confidence.

    An intermediate model inside the agent, reusing the frozen `IncidentType` and `Severity` enums;
    E7-01 composes the final `Verdict` from it, so the graph never depends on the verdict schema.
    The classification node sees no action catalog (§4.4), keeping it separate from recommendation.
    """

    incident_type: IncidentType
    severity: Severity
    affected_device: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class Recommendation(_Strict):
    """Node 3's output (E6-05): one catalog action and the evidence it cites.

    The agent recommends and never executes (§1.1). `recommended_action` is the catalog-generated
    `Action` enum, so an id outside the catalog fails to parse. An **active** action must cite at
    least one evidence id; the non-response actions in `ACTIONS_WITHOUT_EVIDENCE` may cite none, so
    a benign verdict is not forced to invent evidence (METHODS changelog 21).
    """

    recommended_action: Action
    evidence_ids: list[Annotated[str, StringConstraints(max_length=100)]] = Field(max_length=20)

    @model_validator(mode="after")
    def _active_actions_cite_evidence(self) -> Recommendation:
        if self.recommended_action.value not in ACTIONS_WITHOUT_EVIDENCE and not self.evidence_ids:
            raise ValueError(
                f"action {self.recommended_action.value!r} is active and must cite at least one"
                " evidence id"
            )
        return self


__all__ = ["Classification", "Findings", "Recommendation", "SourceFinding"]
