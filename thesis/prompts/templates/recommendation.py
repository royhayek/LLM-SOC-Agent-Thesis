"""Node 3 (recommendation) prompt template (E6-02). Node logic is E6-05.

The action catalog sits between the schema and the bundle (§4.4), so it is also the non-honeypot
section that keeps the untrusted bundle away from the schema instructions (record §3.3).
"""

from __future__ import annotations

from thesis.prompts.render import TEMPLATE_VERSION, PromptTemplate
from thesis.prompts.templates._shared import (
    REASONING,
    RECOMMENDATION_SCHEMA,
    SYSTEM_ROLE,
    action_catalog_lines,
)

TASK = (
    "Recommend exactly one action from the catalog for the classified incident. The agent only"
    " recommends; it never executes. Choose the most proportionate action for the evidence.\n"
    + REASONING
)

TEMPLATE = PromptTemplate(
    name="recommendation",
    version=TEMPLATE_VERSION,
    sections=(
        ("Role", SYSTEM_ROLE),
        ("Output schema", RECOMMENDATION_SCHEMA),
        ("Action catalog", action_catalog_lines()),
        ("Task", TASK),
    ),
)
