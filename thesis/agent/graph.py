"""The three-node agent graph runner (E6-06, SCRUM-81).

The agent is a fixed three-call topology, not a free ReAct loop — this is the agentic condition H2
tests (record §6.3). `run_graph` makes **exactly three LLM calls per bundle**, in the fixed order
evidence → classify → recommend (record §4, §6.3), each with fresh context and no history (§4.4).

Sources come only from `ExperimentConfig`, so H1's conditions differ by configuration alone (§6.1):
the bundle is reduced to the configured sources, so an unconfigured source leaves no content in any
prompt. Only each node's **parsed** fields are passed forward — never a raw completion — so no
conversation accumulates by the back door (the gotcha).

Validation and the audit log are EPIC-7; this returns a trace of the three node outputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from thesis.agent.models import Classification, Findings, Recommendation
from thesis.agent.node_classify import classify
from thesis.agent.node_evidence import Completer, analyze_evidence
from thesis.agent.node_recommend import recommend
from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, config_hash
from thesis.reduce.policy import reduce

EXPECTED_CALLS = 3


@dataclass(frozen=True)
class GraphTrace:
    """The end-to-end trace of one agentic run over one bundle (the three node outputs)."""

    bundle_id: str
    config_hash: str
    repetition: int
    sources: tuple[str, ...]
    findings: Findings
    classification: Classification
    recommendation: Recommendation


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


def run_graph(
    bundle: Bundle, config: ExperimentConfig, *, client: Completer, repetition: int
) -> GraphTrace:
    """Run the fixed evidence → classify → recommend graph on one bundle, per `config`."""
    ch = config_hash(config)
    view = reduce(bundle, sources=config.sources)
    valid_ids = {a.alert_id for a in bundle.alerts if a.source in config.sources}

    counter = _CountingClient(client)
    bid = bundle.bundle_id

    findings = analyze_evidence(
        view,
        client=counter,
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
        valid_alert_ids=valid_ids,
    )
    classification = classify(
        findings, client=counter, bundle_id=bid, config_hash=ch, repetition=repetition
    )
    evidence_ids = sorted({e for f in findings.source_findings for e in f.evidence_ids})
    recommendation = recommend(
        classification,
        evidence_ids,
        client=counter,
        bundle_id=bid,
        config_hash=ch,
        repetition=repetition,
    )

    if counter.nodes != ["evidence", "classification", "recommendation"]:
        raise AssertionError(f"graph made calls {counter.nodes}, expected the three fixed nodes")

    return GraphTrace(
        bundle_id=bundle.bundle_id,
        config_hash=ch,
        repetition=repetition,
        sources=tuple(sorted(s.value for s in config.sources)),
        findings=findings,
        classification=classification,
        recommendation=recommendation,
    )


__all__ = ["EXPECTED_CALLS", "GraphTrace", "run_graph"]
