"""One append-only JSONL record per LLM call (record §6.10, §6.7, §6.11).

The same log is the audit log, the cost instrumentation and the debugging tool, so every LLM
call writes through `log_llm_call()`. The file is only ever opened for appending: earlier lines
are never rewritten. The value of `LLM_API_KEY` never reaches the file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict, Field

LOG_PATH: Final = Path(__file__).resolve().parent.parent.parent / "logs" / "llm_calls.jsonl"
API_KEY_ENV: Final = "LLM_API_KEY"
REDACTED: Final = "[REDACTED]"


class LLMCallRecord(BaseModel):
    """The 12 fields of record §6.10, with condition identified by `config_hash` (E0-09)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    node: str = Field(min_length=1)
    model: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    prompt: str
    completion: str
    parse_outcome: str = Field(min_length=1)
    config_hash: str = Field(min_length=1)
    bundle_id: str = Field(min_length=1)
    repetition: int = Field(ge=0)


def _redact(value: object, secret: str) -> object:
    if secret and isinstance(value, str):
        return value.replace(secret, REDACTED)
    return value


def log_llm_call(
    *,
    node: str,
    model: str,
    model_revision: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    prompt: str,
    completion: str,
    parse_outcome: str,
    config_hash: str,
    bundle_id: str,
    repetition: int,
    path: Path = LOG_PATH,
) -> None:
    """Append one JSON line describing one LLM call to `path`.

    Every field is required and is validated before anything is written:

    1. `node`: the graph node that made the call.
    2. `model`: the model name.
    3. `model_revision`: the pinned model revision.
    4. `tokens_in`: input tokens.
    5. `tokens_out`: output tokens.
    6. `latency_ms`: wall-clock latency of the call, in milliseconds.
    7. `prompt`: the full prompt sent.
    8. `completion`: the raw completion received.
    9. `parse_outcome`: the outcome of parsing the completion.
    10. `config_hash`: `thesis.config.config_hash()` of the run's `ExperimentConfig`.
    11. `bundle_id`: the bundle analysed.
    12. `repetition`: the repetition index.

    Any occurrence of the `LLM_API_KEY` value in a string field is replaced by `[REDACTED]`.
    """
    record = LLMCallRecord(
        node=node,
        model=model,
        model_revision=model_revision,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        prompt=prompt,
        completion=completion,
        parse_outcome=parse_outcome,
        config_hash=config_hash,
        bundle_id=bundle_id,
        repetition=repetition,
    )
    secret = os.environ.get(API_KEY_ENV, "")
    fields = {name: _redact(value, secret) for name, value in record.model_dump().items()}

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as sink:
        logger = structlog.wrap_logger(
            structlog.WriteLogger(sink),
            processors=[structlog.processors.JSONRenderer(sort_keys=True)],
            # The generic wrapper takes no positional event, so the line holds only the 12 fields.
            wrapper_class=structlog.BoundLogger,
        )
        logger.msg(**fields)
