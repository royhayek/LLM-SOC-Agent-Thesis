"""Node 2: structured classification (E6-04, SCRUM-61).

Node 2 turns node 1's findings into one `Classification` — incident type, severity, affected
device and confidence (record §6.3). This is the classification H2 compares against the prompt-only
baseline. The node gets **no action catalog**, which keeps classification separate from
recommendation (§4.4). One LLM call, fresh context, no history (§4.4).

A model that returns a family name close to but not exactly an enum value is a parse failure: it is
logged (by the client) and raised, never silently mapped to a label (ticket gotcha).
"""

from __future__ import annotations

from pydantic import ValidationError

from thesis.agent.models import Classification, Findings
from thesis.agent.node_evidence import Completer
from thesis.prompts.render import render
from thesis.prompts.templates import classification as classification_template

NODE = "classification"


class ClassifyParseError(ValueError):
    """Node 2's completion did not parse into `Classification` (e.g. a label outside the enum)."""


def classify(
    findings: Findings,
    *,
    client: Completer,
    bundle_id: str,
    config_hash: str,
    repetition: int,
) -> Classification:
    """Run node 2 on node 1's findings and return the parsed `Classification`."""
    content = findings.model_dump_json()
    prompt = render(classification_template.TEMPLATE, content)
    completion = client.complete(
        prompt, node=NODE, bundle_id=bundle_id, config_hash=config_hash, repetition=repetition
    )
    try:
        return Classification.model_validate_json(completion)
    except ValidationError as error:
        raise ClassifyParseError(
            f"node 2 output did not parse into Classification: {error}"
        ) from error


__all__ = ["NODE", "Classification", "ClassifyParseError", "classify"]
