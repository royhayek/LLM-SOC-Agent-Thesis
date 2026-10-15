"""The OpenAI SDK is imported only by the one client (E6-01 DoD, SCRUM-28).

Every LLM call must go through `thesis/llm/client.py`, so no other module may import `openai`.
This is the grep the ticket asks CI to run.
"""

from __future__ import annotations

import re
from pathlib import Path

THESIS = Path(__file__).resolve().parent.parent / "thesis"
ALLOWED = THESIS / "llm" / "client.py"
_IMPORT = re.compile(r"^\s*(import openai|from openai\b)", re.MULTILINE)


def test_openai_sdk_is_imported_only_by_the_client() -> None:
    offenders = [
        str(path.relative_to(THESIS.parent))
        for path in THESIS.rglob("*.py")
        if path != ALLOWED and _IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"openai imported outside the client: {offenders}"
