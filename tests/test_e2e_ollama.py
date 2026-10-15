"""One slow end-to-end integration test of the agent graph against local Ollama (E6-07, SCRUM-90).

This exercises the real code path — reduction, deterministic retrieval, three real LLM calls,
parsing — with a real model. It asserts only the **shape** of the result (three calls were made and
a recommendation parsed), never what the model concluded: LLM output quality is not unit-tested
(§6.9). The test is marked `slow` and excluded from CI, and skips cleanly when Ollama is not up.

    LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=llama3.1-8b-8k \
        pytest -m slow tests/test_e2e_ollama.py
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from thesis.agent.graph import run_graph
from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, Provenance, Safety, Strategy
from thesis.schema.alert import Source

FIXTURE = Path(__file__).parent / "fixtures" / "bundles" / "pilot_one.json"


def _ollama_up(base_url: str) -> bool:
    root = base_url.rsplit("/v1", 1)[0]
    try:
        with urllib.request.urlopen(f"{root}/api/tags", timeout=3):  # noqa: S310 - localhost only
            return True
    except (urllib.error.URLError, OSError):
        return False


def _config() -> ExperimentConfig:
    base_url = os.environ["LLM_BASE_URL"]
    model = os.environ["LLM_MODEL"]
    prov = Provenance(
        model=model,
        model_revision="ollama-dev",
        provider="ollama",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version="prompts-v1.0",
        graph_version="graph-v1.0",
    )
    assert _ollama_up(base_url)  # guarded by the skip below
    return ExperimentConfig(
        sources=frozenset({Source.FLOWS, Source.MQTT}),
        strategy=Strategy.AGENTIC,
        safety=Safety.LOGGING_ONLY,
        provenance=prov,
    )


@pytest.mark.slow
def test_graph_runs_end_to_end_against_ollama() -> None:
    base_url = os.environ.get("LLM_BASE_URL")
    if not base_url or not os.environ.get("LLM_MODEL"):
        pytest.skip("LLM_BASE_URL / LLM_MODEL not set; needs local Ollama")
    if not _ollama_up(base_url):
        pytest.skip(f"Ollama not running at {base_url}")

    from thesis.llm.client import LLMClient

    bundle = Bundle.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    client = LLMClient.from_env(model_revision="ollama-dev")
    # Constrained decoding, so a small dev model emits compact schema-valid JSON within the ceiling.
    trace = run_graph(bundle, _config(), client=client, repetition=0, constrain=True)

    # Shape only: three nodes ran in order and a recommendation parsed, whatever its content.
    assert trace.recommendation.recommended_action.value  # a catalog action id
    assert trace.recommendation.evidence_ids  # at least one evidence id
    assert trace.classification.incident_type.value  # a label from the enum
