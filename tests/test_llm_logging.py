"""Tests for the LLM-call log (E0-10, record §6.10, §6.7, §6.11)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from thesis.obs.logging import log_llm_call

FAKE_KEY = "sk-test-0123456789abcdef"


def call_values() -> dict[str, Any]:
    return {
        "node": "classify",
        "model": "qwen2.5-7b-instruct",
        "model_revision": "a09a3545",
        "tokens_in": 1834,
        "tokens_out": 172,
        "latency_ms": 2412.5,
        "prompt": "System: you are a SOC analyst.\nBundle: ...",
        "completion": '{"incident_type": "port_scan"}',
        "parse_outcome": "ok",
        "config_hash": "3f2a" * 16,
        "bundle_id": "bundle-0001",
        "repetition": 2,
    }


def test_one_line_holds_all_twelve_fields(tmp_path: Path) -> None:
    log = tmp_path / "llm_calls.jsonl"
    log_llm_call(**call_values(), path=log)

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == call_values()


@pytest.mark.parametrize("missing", sorted(call_values()))
def test_missing_field_raises_before_writing(tmp_path: Path, missing: str) -> None:
    log = tmp_path / "llm_calls.jsonl"
    values = call_values()
    del values[missing]

    with pytest.raises(TypeError):
        log_llm_call(**values, path=log)
    assert not log.exists()


def test_api_key_value_never_reaches_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    log = tmp_path / "llm_calls.jsonl"
    values = call_values()
    values["prompt"] = f"Authorization: Bearer {FAKE_KEY}"
    values["completion"] = f"echo {FAKE_KEY}"

    log_llm_call(**values, path=log)
    log_llm_call(**call_values(), path=log)

    assert FAKE_KEY not in log.read_text(encoding="utf-8")


def test_second_call_leaves_first_line_byte_identical(tmp_path: Path) -> None:
    log = tmp_path / "llm_calls.jsonl"
    log_llm_call(**call_values(), path=log)
    first = log.read_bytes()

    second = call_values() | {"repetition": 3}
    log_llm_call(**second, path=log)

    after = log.read_bytes()
    assert after.startswith(first)
    assert after.splitlines()[0] == first.splitlines()[0]
    assert len(after.splitlines()) == 2
