"""Tests for extracting the JSON object from a model completion (E9-08, METHODS changelog 20)."""

from __future__ import annotations

from thesis.llm.parse import extract_json_object, json_payload


def test_plain_json_is_returned_unchanged() -> None:
    assert extract_json_object('{"a": 1}') == '{"a": 1}'


def test_reasoning_prose_before_the_object_is_stripped() -> None:
    text = '## Reasoning\nThe incident looks like a flood.\n{"incident_type": "syn_flood"}'
    assert extract_json_object(text) == '{"incident_type": "syn_flood"}'


def test_markdown_code_fence_is_handled() -> None:
    text = '## Step 1\nAnalyze.\n```json\n{"action": "rate_limit_source"}\n```'
    assert extract_json_object(text) == '{"action": "rate_limit_source"}'


def test_braces_inside_strings_do_not_break_extraction() -> None:
    text = 'reasoning about it\n{"summary": "contains a } brace and a { brace"}'
    assert extract_json_object(text) == '{"summary": "contains a } brace and a { brace"}'


def test_the_last_top_level_object_wins() -> None:
    # The prompts put the answer last; an example object in the reasoning must not be chosen.
    text = 'Example: {"incident_type": "benign"}\nFinal answer:\n{"incident_type": "botnet"}'
    assert extract_json_object(text) == '{"incident_type": "botnet"}'


def test_nested_objects_return_the_whole_outer_object() -> None:
    obj = '{"classification": {"incident_type": "benign"}, "confidence": 0.9}'
    assert extract_json_object(f"answer: {obj}") == obj


def test_truncated_final_object_is_skipped() -> None:
    # A complete object then a truncated one (ceiling cut-off): the complete one is returned.
    text = '{"a": 1}\nthen more\n{"b": 2'
    assert extract_json_object(text) == '{"a": 1}'


def test_no_object_returns_none_and_payload_falls_back_to_raw() -> None:
    assert extract_json_object("no json here at all") is None
    assert json_payload("no json here at all") == "no json here at all"  # validation still runs


def test_json_payload_returns_the_extracted_object() -> None:
    assert json_payload('prose {"x": 1} tail') == '{"x": 1}'
