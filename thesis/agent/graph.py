"""The three-node agent graph runner (E6-06, SCRUM-81).

The agent is a fixed three-call topology, not a free ReAct loop — this is the agentic condition H2
tests (record §6.3). `run_graph` makes **exactly three LLM calls per bundle**, in the fixed order
evidence → classify → recommend (record §4, §6.3), each with fresh context and no history (§4.4).

Sources come only from `ExperimentConfig`, so H1's conditions differ by configuration alone (§6.1):
the bundle is reduced to the configured sources, so an unconfigured source leaves no content in any
prompt. Only each node's **parsed** fields are passed forward — never a raw completion — so no
conversation accumulates by the back door (the gotcha).

The safety layer (E7-06) wraps the graph: `ExperimentConfig.safety` picks a `SafetyMode`
(config/safety_modes.yaml, the E0-12 / §6.1 list). Under `enforcing` the Verdict is generated with
constrained decoding, the validator gates it and the rejection policy applies; under `logging_only`
the Verdict is free-form, the validator only records `would_reject`, and it is emitted unchanged.
The two reasoning nodes (evidence, classify) always use structured output — they are the agent's
internal steps, not the scored Verdict whose constrained decoding §6.1 switches. The audit log is
written in both modes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from thesis.agent.models import Classification, Findings, Recommendation
from thesis.agent.node_classify import classify
from thesis.agent.node_evidence import Completer, analyze_evidence
from thesis.agent.node_recommend import recommend
from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, config_hash
from thesis.reduce.policy import reduce
from thesis.safety.audit import AuditRecord
from thesis.safety.stage import apply_safety
from thesis.safety.switch import SafetyMode
from thesis.schema.verdict import Verdict

# Node output schemas for constrained decoding (structured outputs): the model must emit compact,
# schema-valid JSON. The reasoning nodes always use them; node 3 (the Verdict) only under enforcing.
_EVIDENCE_SCHEMA = Findings.model_json_schema()
_CLASSIFY_SCHEMA = Classification.model_json_schema()
_RECOMMEND_SCHEMA = Recommendation.model_json_schema()

EXPECTED_CALLS = 3


@dataclass(frozen=True)
class GraphTrace:
    """The end-to-end trace of one agentic run: the three node outputs and the safety outcome."""

    bundle_id: str
    config_hash: str
    repetition: int
    sources: tuple[str, ...]
    findings: Findings
    classification: Classification
    recommendation: Recommendation
    safety_mode: str
    emitted: Verdict | str | None  # E: the emitted verdict, raw (logging_only), or None (hard fail)
    validator_outcome: str
    audit: AuditRecord


class _CountingClient:
    """Wraps the client to count calls and record node order, so the 3-call rule is asserted."""

    def __init__(self, client: Completer) -> None:
        self._client = client
        self.nodes: list[str] = []

    def complete(
        self,
        prompt: str,
        *,
        node: str,
        bundle_id: str,
        config_hash: str,
        repetition: int,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        self.nodes.append(node)
        return self._client.complete(
            prompt,
            node=node,
            bundle_id=bundle_id,
            config_hash=config_hash,
            repetition=repetition,
            json_schema=json_schema,
        )


def _verdict_completion(classification: Classification, recommendation: Recommendation) -> str:
    """Assemble the node-3 Verdict from the parsed classification and recommendation, as JSON."""
    return json.dumps(
        {
            "classification": {
                "incident_type": classification.incident_type.value,
                "confidence": classification.confidence,
            },
            "recommendation": {
                "recommended_action": recommendation.recommended_action.value,
                "severity": classification.severity.value,
            },
            "affected_device": classification.affected_device,
            "evidence": recommendation.evidence_ids,
        }
    )


def run_graph(
    bundle: Bundle, config: ExperimentConfig, *, client: Completer, repetition: int
) -> GraphTrace:
    """Run the fixed evidence → classify → recommend graph on one bundle, per `config`."""
    ch = config_hash(config)
    mode = SafetyMode.load(config.safety)
    view = reduce(bundle, sources=config.sources)
    valid_ids = {a.alert_id for a in bundle.alerts if a.source in config.sources}

    counter = _CountingClient(client)
    bid = bundle.bundle_id

    # The two reasoning nodes always use structured output; node 3's constrained decoding follows
    # the safety mode (the Verdict-level mechanism §6.1 switches).
    findings = analyze_evidence(
        view,
        client=counter,
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
        valid_alert_ids=valid_ids,
        json_schema=_EVIDENCE_SCHEMA,
    )
    classification = classify(
        findings,
        client=counter,
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
        json_schema=_CLASSIFY_SCHEMA,
    )
    evidence_ids = sorted({e for f in findings.source_findings for e in f.evidence_ids})
    recommendation = recommend(
        classification,
        evidence_ids,
        client=counter,
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
        json_schema=_RECOMMEND_SCHEMA if mode.constrained_decoding else None,
    )

    if counter.nodes != ["evidence", "classification", "recommendation"]:
        raise AssertionError(f"graph made calls {counter.nodes}, expected the three fixed nodes")

    completion = _verdict_completion(classification, recommendation)
    safety = apply_safety(
        completion, bundle, mode=mode, bundle_id=bid, config_hash=ch, repetition=repetition
    )

    return GraphTrace(
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
        sources=tuple(sorted(s.value for s in config.sources)),
        findings=findings,
        classification=classification,
        recommendation=recommendation,
        safety_mode=mode.name,
        emitted=safety.emitted,
        validator_outcome=safety.validator_outcome,
        audit=safety.audit,
    )


__all__ = ["EXPECTED_CALLS", "GraphTrace", "run_graph"]
