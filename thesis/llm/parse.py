"""Extract the JSON object from a model completion (E9-08, ADR-0012, METHODS changelog 20).

The node prompts ask the model to reason step by step and then output one JSON object (`REASONING`,
record §6.3, the H2 treatment). Under `json_object` the model often wraps that object in prose or a
markdown code fence — `## Reasoning ... ```json {..} ```` — so a strict `model_validate_json` on the
whole completion fails even though the JSON object is present and complete.

This reads the model's answer out of its response; it does **not** repair content. It only locates
the JSON object (the prompts say the answer comes last — "output exactly one JSON object and nothing
after it"). It never edits a field, invents evidence or changes an action: a malformed, truncated or
absent object still fails validation, and the validator and rejection policy are untouched.
"""

from __future__ import annotations


def extract_json_object(text: str) -> str | None:
    """Return the last top-level ``{...}`` object in `text`, or None if there is none.

    Braces inside JSON strings are ignored, so reasoning prose and ``` fences around the object do
    not confuse it. The last balanced top-level object is the model's final answer (the prompts put
    it last); a truncated final object has no closing brace and is skipped, so an earlier complete
    object — or None — is returned and validation then fails as it should.
    """
    depth = 0
    start = -1
    last: str | None = None
    in_str = False
    escaped = False
    for i, ch in enumerate(text):
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                last = text[start : i + 1]
    return last


def json_payload(completion: str) -> str:
    """The JSON to validate: the extracted object, or the raw completion if none is found (so
    validation still runs and fails with a clear error on genuinely non-JSON output)."""
    return extract_json_object(completion) or completion


__all__ = ["extract_json_object", "json_payload"]
