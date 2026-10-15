"""Node 2 (classification) prompt template (E6-02). Node logic is E6-04."""

from __future__ import annotations

from thesis.prompts.render import TEMPLATE_VERSION, PromptTemplate
from thesis.prompts.templates._shared import CLASSIFICATION_SCHEMA, REASONING, SYSTEM_ROLE

TASK = (
    "Classify the incident into exactly one label, using the evidence in the bundle. Pick the label"
    " the evidence best supports, or `benign` if it supports no attack family.\n" + REASONING
)

TEMPLATE = PromptTemplate(
    name="classification",
    version=TEMPLATE_VERSION,
    sections=(
        ("Role", SYSTEM_ROLE),
        ("Output schema", CLASSIFICATION_SCHEMA),
        ("Task", TASK),
    ),
)
