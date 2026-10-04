"""Tests for ExperimentConfig, its canonical form and its hash (E0-09, record §6.1, §4.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from thesis.config import (
    CONDITIONS_PATH,
    ExperimentConfig,
    Provenance,
    canonical_json,
    config_hash,
    load_conditions,
    validate_combination,
)


def provenance_values() -> dict[str, Any]:
    return {
        "model": "qwen2.5-7b-instruct",
        "model_revision": "a09a3545",
        "provider": "ollama",
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 1024,
        "seed": 42,
        "prompt_template_version": "prompts-v0.1",
        "graph_version": "graph-v0.1",
    }


def config_values() -> dict[str, Any]:
    return {
        "sources": ["mqtt", "flows", "honeypot"],
        "strategy": "agentic",
        "safety": "enforcing",
        "provenance": provenance_values(),
    }


def make_config(**overrides: Any) -> ExperimentConfig:
    return ExperimentConfig.model_validate(config_values() | overrides)


# One changed value per field, so every field of both models is covered.
CONFIG_CHANGES: dict[str, Any] = {
    "sources": ["mqtt", "flows"],
    "strategy": "prompt_only",
    "safety": "logging_only",
}
PROVENANCE_CHANGES: dict[str, Any] = {
    "model": "qwen2.5-14b-instruct",
    "model_revision": "b17c0e21",
    "provider": "hosted",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 2048,
    "seed": 7,
    "prompt_template_version": "prompts-v0.2",
    "graph_version": "graph-v0.2",
}


def test_change_tables_cover_every_field() -> None:
    assert set(CONFIG_CHANGES) | {"provenance"} == set(ExperimentConfig.model_fields)
    assert set(PROVENANCE_CHANGES) == set(Provenance.model_fields)


def test_same_values_in_different_order_hash_equal() -> None:
    a = make_config()
    reordered = dict(reversed(list(config_values().items())))
    reordered["sources"] = ["honeypot", "flows", "mqtt"]
    reordered["provenance"] = dict(reversed(list(provenance_values().items())))
    b = ExperimentConfig.model_validate(reordered)
    assert canonical_json(a) == canonical_json(b)
    assert config_hash(a) == config_hash(b)


@pytest.mark.parametrize(("field", "value"), CONFIG_CHANGES.items())
def test_changing_a_config_field_changes_the_hash(field: str, value: Any) -> None:
    assert config_hash(make_config(**{field: value})) != config_hash(make_config())


@pytest.mark.parametrize(("field", "value"), PROVENANCE_CHANGES.items())
def test_changing_a_provenance_field_changes_the_hash(field: str, value: Any) -> None:
    changed = make_config(provenance=provenance_values() | {field: value})
    assert config_hash(changed) != config_hash(make_config())


def test_seed_none_hashes_differently_from_a_seed() -> None:
    changed = make_config(provenance=provenance_values() | {"seed": None})
    assert config_hash(changed) != config_hash(make_config())


def test_hash_is_sha256_hex() -> None:
    digest = config_hash(make_config())
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_floats_are_serialised_as_strings() -> None:
    text = canonical_json(make_config(provenance=provenance_values() | {"temperature": 0.7}))
    assert '"temperature":"0.7"' in text
    assert '"sources":["flows","honeypot","mqtt"]' in text


def test_empty_sources_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_config(sources=[])


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_config(window_seconds=60)


def test_ml_classifier_takes_no_llm_provenance() -> None:
    assert make_config(strategy="ml_classifier", provenance=None).provenance is None
    with pytest.raises(ValidationError):
        make_config(strategy="ml_classifier")


@pytest.mark.parametrize("strategy", ["agentic", "prompt_only"])
def test_llm_strategies_require_provenance(strategy: str) -> None:
    with pytest.raises(ValidationError):
        make_config(strategy=strategy, provenance=None)


def write_conditions(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "conditions.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_listed_combination_passes(tmp_path: Path) -> None:
    path = write_conditions(
        tmp_path,
        "conditions:\n"
        "  - sources: [honeypot, mqtt, flows]\n"
        "    strategy: agentic\n"
        "    safety: enforcing\n",
    )
    validate_combination(make_config(), path)


def test_unlisted_combination_names_the_combination(tmp_path: Path) -> None:
    path = write_conditions(
        tmp_path,
        "conditions:\n"
        "  - sources: [flows, honeypot, mqtt]\n"
        "    strategy: agentic\n"
        "    safety: enforcing\n",
    )
    config = make_config(sources=["mqtt"], safety="logging_only")
    with pytest.raises(
        ValueError, match=r"sources=\{mqtt\}.*strategy=agentic.*safety=logging_only"
    ):
        validate_combination(config, path)


def test_repository_conditions_file_loads() -> None:
    assert load_conditions(CONDITIONS_PATH)
