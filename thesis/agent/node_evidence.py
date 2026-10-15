"""Node 1: evidence analysis with retrieval (E6-03, SCRUM-49).

Node 1 is where cross-source correlation happens — the core of H1 and H2 (record §6.3). It turns
one reduced bundle plus retrieved context into structured `Findings`: per-source findings,
cross-source observations, candidate hypotheses and a missing-evidence list (C-08; recorded, never
acted on).

Retrieval is deterministic code, not an LLM tool-call: hosted providers differ in tool-call support
and the design is fixed at exactly three LLM calls per bundle (record §4.4, §6.3). So node 1 calls
`retrieve()` and `device_context()` **before** its single LLM call (the gotcha's recommended choice)
and injects the trusted results into the prompt's reference-context slot, away from the untrusted
bundle. Each call gets fresh context; no history (§4.4). The retrieval query and returned doc ids
are logged by the tool. Develop on pilot/training bundles only.
"""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from thesis.agent.models import Findings, SourceFinding
from thesis.kb.retrieve import RetrievedDoc, device_context, retrieve
from thesis.prompts.render import render
from thesis.prompts.templates import evidence

NODE = "evidence"
_DOC_EXCERPT = 400


class Completer(Protocol):
    """The subset of the LLM client node 1 needs (so tests can pass a stub)."""

    def complete(
        self,
        prompt: str,
        *,
        node: str,
        bundle_id: str,
        config_hash: str,
        repetition: int,
        json_schema: dict[str, object] | None = None,
    ) -> str: ...


class EvidenceParseError(ValueError):
    """Node 1's completion did not parse into `Findings`."""


def _build_query(view: dict[str, object]) -> str:
    """A compact, deterministic retrieval query: device plus each active source's detector label."""
    parts = [str(view.get("device", ""))]
    for source in ("flows", "mqtt", "honeypot"):
        block = view.get(source)
        if isinstance(block, dict):
            detector = block.get("detector")
            if isinstance(detector, dict) and detector.get("label"):
                parts.append(f"{source}:{detector['label']}")
    return " ".join(p for p in parts if p)


def _context_block(device_ctx: dict[str, str], docs: list[RetrievedDoc]) -> str:
    device_line = "Device: " + ", ".join(f"{k}={v}" for k, v in sorted(device_ctx.items()))
    doc_lines = [f"- [{d.doc_id}] {d.text[:_DOC_EXCERPT]}" for d in docs]
    return device_line + "\nKnowledge:\n" + "\n".join(doc_lines)


def _clean_evidence(findings: Findings, valid_alert_ids: set[str]) -> Findings:
    """Drop any evidence id that does not refer to a real alert in this bundle (AC2)."""
    cleaned = [
        finding.model_copy(
            update={"evidence_ids": [e for e in finding.evidence_ids if e in valid_alert_ids]}
        )
        for finding in findings.source_findings
    ]
    return findings.model_copy(update={"source_findings": cleaned})


def analyze_evidence(
    view: dict[str, object],
    *,
    client: Completer,
    bundle_id: str,
    config_hash: str,
    repetition: int,
    valid_alert_ids: set[str],
    json_schema: dict[str, object] | None = None,
) -> Findings:
    """Run node 1 on one reduced bundle view and return validated `Findings`."""
    device = str(view.get("device", ""))
    context = _context_block(device_context(device), retrieve(_build_query(view)))
    prompt = render(evidence.TEMPLATE, json.dumps(view, separators=(",", ":")), context=context)
    completion = client.complete(
        prompt,
        node=NODE,
        bundle_id=bundle_id,
        config_hash=config_hash,
        repetition=repetition,
        json_schema=json_schema,
    )
    try:
        findings = Findings.model_validate_json(completion)
    except ValidationError as error:
        raise EvidenceParseError(f"node 1 output did not parse into Findings: {error}") from error
    return _clean_evidence(findings, valid_alert_ids)


__all__ = [
    "NODE",
    "Completer",
    "EvidenceParseError",
    "Findings",
    "SourceFinding",
    "analyze_evidence",
]
