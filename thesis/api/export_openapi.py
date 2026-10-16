"""Write the console API's OpenAPI schema to a file (E10-03, SCRUM-65).

The frontend generates its TypeScript types from this schema, so a schema change (for example a
renamed `Verdict` field) breaks the frontend build instead of failing at runtime (record §6.2).

    python -m thesis.api.export_openapi frontend/src/api/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from thesis.api.app import create_app


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out = Path(args[0]) if args else Path("openapi.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app().openapi()
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
