"""Intermediate models passed between the agent's graph nodes (EPIC-6).

`Findings` is node 1's output (E6-03): per-source findings, cross-source observations, candidate
hypotheses and a missing-evidence list. The hypotheses and missing-evidence absorb the brief's
attack-hypothesis and missing-information requests (C-08); they are recorded, never acted on. Field
lengths are capped so node 1's output cannot push the next call over its input ceiling (§4.4).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


__all__ = ["Findings", "SourceFinding"]
