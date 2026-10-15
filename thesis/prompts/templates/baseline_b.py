"""Baseline B (one-call, prompt-only) template (E6-02 structure; wording finalised E8-03).

Baseline B answers "does the agentic architecture help, or is the model just good?" (§6.6). It is
the same model in a single call with the same output schema as the agent, but no retrieval, no
three-step reasoning and no safety layer. The prompt is written to the same standard as the agent's
so H2 is a fair test; `docs/baselines/baseline_b_prompt.md` records the rationale and what Baseline
B deliberately lacks.
"""

from __future__ import annotations

from thesis.prompts.render import TEMPLATE_VERSION, PromptTemplate
from thesis.prompts.templates._shared import (
    BASELINE_B_SCHEMA,
    REASONING,
    SYSTEM_ROLE,
    action_catalog_lines,
)

TASK = (
    "In a single step, analyse the bundle, classify the incident into one label, and recommend"
    " exactly one catalog action, citing the bundle alert ids that justify it. Weigh every source"
    " present together, and choose the most proportionate action for what the evidence supports."
    " The agent only recommends; it never executes.\n" + REASONING
)

TEMPLATE = PromptTemplate(
    name="baseline_b",
    version=TEMPLATE_VERSION,
    sections=(
        ("Role", SYSTEM_ROLE),
        ("Output schema", BASELINE_B_SCHEMA),
        ("Action catalog", action_catalog_lines()),
        ("Task", TASK),
    ),
)
