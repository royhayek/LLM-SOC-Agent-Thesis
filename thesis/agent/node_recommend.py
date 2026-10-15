"""Node 3: constrained recommendation (E6-05, SCRUM-72).

Node 3 turns node 2's classification into one recommended action from the catalog, with the
evidence it cites (record §6.3). It sees the classification and the permitted catalog and nothing
else — no raw exemplars (§4.4). The explicit catalog in this prompt is what H3 depends on and is
never removed (§4.4). The agent recommends and never executes (§1.1). One LLM call, fresh context.

The available evidence ids (from node 1) are passed in the prompt so the model cites real alerts;
any id it invents anyway is counted here and caught by the validator (E7-02). Validation and the
rejection policy are E7-02/E7-04; constrained decoding is wired by the enforcing switch (E7-06).
"""

from __future__ import annotations

import json

import structlog
from pydantic import ValidationError

from thesis.agent.models import Classification, Recommendation
from thesis.agent.node_evidence import Completer
from thesis.llm.parse import json_payload
from thesis.prompts.render import render
from thesis.prompts.templates import recommendation as recommendation_template

NODE = "recommendation"

_log = structlog.get_logger("thesis.agent.node_recommend")


class RecommendParseError(ValueError):
    """Node 3's completion did not parse into `Recommendation` (e.g. an uncatalogued action)."""


def recommend(
    classification: Classification,
    available_evidence_ids: list[str],
    *,
    client: Completer,
    bundle_id: str,
    config_hash: str,
    repetition: int,
    json_schema: dict[str, object] | None = None,
) -> Recommendation:
    """Run node 3 on node 2's classification and return the parsed `Recommendation`."""
    content = json.dumps(
        {
            "classification": classification.model_dump(mode="json"),
            "available_evidence_ids": available_evidence_ids,
        },
        separators=(",", ":"),
    )
    prompt = render(recommendation_template.TEMPLATE, content)
    completion = client.complete(
        prompt,
        node=NODE,
        bundle_id=bundle_id,
        config_hash=config_hash,
        repetition=repetition,
        json_schema=json_schema,
    )
    try:
        rec = Recommendation.model_validate_json(json_payload(completion))
    except ValidationError as error:
        raise RecommendParseError(
            f"node 3 output did not parse into Recommendation: {error}"
        ) from error

    invented = [e for e in rec.evidence_ids if e not in set(available_evidence_ids)]
    if invented:  # the validator (E7-02) is the gate; node 3 only records it
        _log.info("recommend_invented_evidence", bundle_id=bundle_id, invented=invented)
    return rec


__all__ = ["NODE", "Recommendation", "RecommendParseError", "recommend"]
