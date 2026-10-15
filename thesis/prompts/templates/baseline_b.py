"""Baseline B (one-call, prompt-only) template structure (E6-02).

This fixes the section order, version and delimiting for Baseline B. The exact wording of the task
is finalised in E8-03 (`prompt_only`); only the structure is frozen here.
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
    "In one step, classify the incident and recommend one action from the catalog. The agent only"
    " recommends; it never executes.\n" + REASONING
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
