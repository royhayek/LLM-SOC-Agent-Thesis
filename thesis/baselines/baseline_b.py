"""Baseline B: the same model in one prompt-only call (E8-04, SCRUM-71).

Baseline B (condition C6) answers "does the agentic architecture help, or is the model just good?"
(record §6.6). It uses the **same client, model and bundles** as the agent, so the only thing H2
measures is the architecture. It makes **exactly one** LLM call per bundle (no tools, retrieval,
reasoning steps or safety layer) and parses the completion into a `Verdict`.

A parse failure is a result — an invalid output — not something to retry: retrying would give
Baseline B a hidden safety layer (the gotcha). So `baseline_b_verdict` returns the parsed `Verdict`
or `None`, and the caller records `None` as invalid. The call is logged by the shared client like
every other call, with the same model and revision the agent uses.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from thesis.agent.node_evidence import Completer
from thesis.prompts.render import render
from thesis.prompts.templates import baseline_b as baseline_b_template
from thesis.schema.verdict import Verdict

NODE = "prompt_only"


def baseline_b_verdict(
    view: dict[str, object],
    *,
    client: Completer,
    bundle_id: str,
    config_hash: str,
    repetition: int,
) -> Verdict | None:
    """One prompt-only call for a reduced bundle view; return the parsed `Verdict`, or None if it
    does not parse (recorded as invalid, never retried). Baseline B has no constrained decoding."""
    prompt = render(baseline_b_template.TEMPLATE, json.dumps(view, separators=(",", ":")))
    completion = client.complete(
        prompt, node=NODE, bundle_id=bundle_id, config_hash=config_hash, repetition=repetition
    )
    try:
        return Verdict.model_validate_json(completion)
    except ValidationError:
        return None


__all__ = ["NODE", "baseline_b_verdict"]
