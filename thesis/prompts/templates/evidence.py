"""Node 1 (evidence analysis) prompt template (E6-02). Node logic is E6-03."""

from __future__ import annotations

from thesis.prompts.render import TEMPLATE_VERSION, PromptTemplate
from thesis.prompts.templates._shared import EVIDENCE_SCHEMA, REASONING, SYSTEM_ROLE

TASK = (
    "Analyse the detector evidence in the bundle and summarise what is happening on the subject"
    " device. Do not classify the attack family or recommend an action yet.\n" + REASONING
)

TEMPLATE = PromptTemplate(
    name="evidence",
    version=TEMPLATE_VERSION,
    sections=(
        ("Role", SYSTEM_ROLE),
        ("Output schema", EVIDENCE_SCHEMA),
        ("Task", TASK),
    ),
)
