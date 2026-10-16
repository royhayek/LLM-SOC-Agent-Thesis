# ADR-0004: Frontend build tool (Vite + React + TypeScript)

- Status: Accepted (2026-10-16)
- Date: 2026-10-16
- Ticket: SCRUM-65 [E10-03]

## Context

The SOC console is React, served on localhost only, with its API types generated from the OpenAPI
schema so a schema change breaks the build rather than failing at runtime (`docs/WORKING_RULES.md`,
record §6.2). It needs a build tool for the dev server, the type-check and the production bundle, and
a test runner for the component tests (E10-04..E10-07). The console is first on the descope list
(C-12), so the setup should be small and standard, not elaborate.

## Decision

Accepted: **Vite** (dev server + build) with the **React + TypeScript** template, **vitest** with
Testing Library for component tests, and **openapi-typescript** to generate `frontend/src/api/types.ts`
from the FastAPI OpenAPI schema. The generation runs in an npm script (`gen:types`) that the build
depends on, and `types.ts` carries a "generated, do not edit" header. TypeScript is strict. The
frontend lives under `frontend/`; it talks only to the localhost API (§6.8) and never to the testbed.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| Vite + React + TS (+ vitest) | The current standard; fast; first-class TS; vitest integrates with no extra config; tiny setup | Another toolchain (Node) beside the Python one — unavoidable for any React UI |
| Create React App | Familiar | Deprecated/unmaintained; slow; Webpack heavy |
| Next.js | Batteries included | A server framework for a static localhost demo; far more than needed |
| No build tool (plain JS + import maps) | Zero tooling | No TypeScript, so the generated-types-break-the-build requirement (§6.2) cannot be met |

## Consequences

- A `frontend/` Node project is added (package.json, vite, tsconfig, vitest). It is independent of
  the Python package and not part of `uv`/pytest; it has its own `npm run build` and `npm test`.
- `openapi-typescript` turns the `Verdict` (and other) Pydantic schemas into TS types; renaming a
  field and regenerating makes `tsc` fail where the old field is used (E10-03 AC).
- The console remains descope-able: nothing in `thesis/` depends on the frontend.
