"""Tests for the per-call token-budget assertions (E3-08, SCRUM-99).

These exercise the code around the model: the vendored experiment tokenizer loads, and the frozen
ceilings raise. They never test LLM output quality. The tokenizer file is committed (not under
`data/`), so these run in CI.
"""

from __future__ import annotations

import pytest

from thesis.reduce.check_tokens import (
    INPUT_CEILING,
    OUTPUT_CEILING,
    TOKENIZER_PATH,
    TokenCeilingError,
    assert_input_tokens,
    assert_output_tokens,
    count_tokens,
    load_tokenizer,
    reduced_prompt,
)


def test_vendored_tokenizer_is_present_and_loads() -> None:
    assert TOKENIZER_PATH.exists(), "experiment tokenizer must be vendored (ADR-0011)"
    tok = load_tokenizer()
    # Llama 3 prepends <|begin_of_text|> (128000) and tokenizes "Hello world" to [9906, 1917].
    ids = tok.encode("Hello world").ids
    assert ids[0] == 128000
    assert count_tokens("Hello world", tok) == len(ids)


def test_small_prompt_is_within_the_input_ceiling() -> None:
    n = assert_input_tokens('{"bundle_id":"x","flows":{"count":1}}', bundle_id="x")
    assert 0 < n <= INPUT_CEILING


def test_oversized_prompt_raises_and_names_the_bundle() -> None:
    prompt = " ".join(["telemetry"] * (INPUT_CEILING + 200))  # one token each, over the ceiling
    with pytest.raises(TokenCeilingError) as exc:
        assert_input_tokens(prompt, bundle_id="iot-cam-01|2026-01-01T00:00:00+00:00")
    message = str(exc.value)
    assert "iot-cam-01|2026-01-01T00:00:00+00:00" in message
    assert str(INPUT_CEILING) in message


def test_completion_within_output_ceiling_returns_count() -> None:
    n = assert_output_tokens('{"verdict":"attack","action":"isolate_device"}')
    assert 0 < n <= OUTPUT_CEILING


def test_oversized_completion_raises() -> None:
    completion = " ".join(["word"] * (OUTPUT_CEILING + 100))
    with pytest.raises(TokenCeilingError):
        assert_output_tokens(completion)


def test_reduced_prompt_prepends_the_static_prefix() -> None:
    view: dict[str, object] = {"bundle_id": "x"}
    assert reduced_prompt(view, prefix="PREFIX\n").startswith("PREFIX\n")
    assert reduced_prompt(view).startswith("{")
