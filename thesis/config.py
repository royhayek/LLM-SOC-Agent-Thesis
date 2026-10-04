"""The one config object that describes a run, and its reproducible hash (record §6.1, §4.2).

H1, H2 and H3 switch sources, strategy and safety on the same pipeline, so none of them is
hardcoded anywhere: they come from `ExperimentConfig`. Every result row carries the config and
`config_hash()`. Adding, removing or renaming a field changes every hash, so such a change needs
a METHODS.md changelog entry.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum, StrEnum
from pathlib import Path
from typing import Final, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from thesis.schema.alert import Source

CONDITIONS_PATH: Final = Path(__file__).resolve().parent.parent / "config" / "conditions.yaml"


class Strategy(StrEnum):
    AGENTIC = "agentic"  # three-call graph (H2)
    PROMPT_ONLY = "prompt_only"  # Baseline B: one call, no tools, no retrieval
    ML_CLASSIFIER = "ml_classifier"  # Baseline A: no LLM call


class Safety(StrEnum):
    ENFORCING = "enforcing"
    LOGGING_ONLY = "logging_only"


class _Strict(BaseModel):
    # Unknown fields are rejected so a misspelt switch fails loudly instead of being ignored.
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(_Strict):
    """What record §4.2 says to record for every LLM run."""

    model: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    temperature: float = Field(ge=0)
    top_p: float = Field(gt=0, le=1)
    max_tokens: int = Field(gt=0)
    seed: int | None  # None where the provider does not support a seed
    prompt_template_version: str = Field(min_length=1)
    graph_version: str = Field(min_length=1)


class ExperimentConfig(_Strict):
    """One experimental condition plus the provenance of the model that runs it."""

    sources: frozenset[Source] = Field(min_length=1)
    strategy: Strategy
    safety: Safety
    provenance: Provenance | None  # None only for ml_classifier, which makes no LLM call

    @model_validator(mode="after")
    def _provenance_matches_strategy(self) -> Self:
        uses_llm = self.strategy is not Strategy.ML_CLASSIFIER
        if uses_llm and self.provenance is None:
            raise ValueError(f"strategy {self.strategy.value} calls an LLM and needs provenance")
        if not uses_llm and self.provenance is not None:
            raise ValueError("strategy ml_classifier makes no LLM call; provenance must be null")
        return self


class Condition(_Strict):
    """One allowed (sources, strategy, safety) combination from `config/conditions.yaml`."""

    sources: frozenset[Source] = Field(min_length=1)
    strategy: Strategy
    safety: Safety


def _canonical(value: object) -> object:
    # Floats become strings so the hash never depends on how a Python version prints them.
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, frozenset | set):
        return sorted(_canonical(v) for v in value)  # type: ignore[type-var]
    if isinstance(value, list | tuple):
        return [_canonical(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float):
        return repr(value)
    return value


def canonical_json(config: ExperimentConfig) -> str:
    """Sorted keys, sorted source set, floats as strings, no whitespace."""
    return json.dumps(
        _canonical(config.model_dump()),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def config_hash(config: ExperimentConfig) -> str:
    """SHA-256 of the canonical JSON, as lowercase hex."""
    return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()


def _describe(sources: frozenset[Source], strategy: Strategy, safety: Safety) -> str:
    names = ",".join(sorted(s.value for s in sources))
    return f"(sources={{{names}}}, strategy={strategy.value}, safety={safety.value})"


def load_conditions(path: Path = CONDITIONS_PATH) -> list[Condition]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [Condition.model_validate(entry) for entry in data["conditions"]]


def validate_combination(config: ExperimentConfig, path: Path = CONDITIONS_PATH) -> None:
    """Raise ValueError naming the combination if it is not listed in the conditions file."""
    wanted = Condition(sources=config.sources, strategy=config.strategy, safety=config.safety)
    if wanted not in load_conditions(path):
        combination = _describe(config.sources, config.strategy, config.safety)
        raise ValueError(f"combination {combination} is not listed in {path}")
