# ADR-0005: PyYAML for reading YAML files

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-31 [E0-04]

## Context

Ticket E0-04 delivers `knowledge/action_catalog.yaml` and a test, `tests/test_catalog.py`, that reads it (backlog, E0-04 acceptance criteria). Later tickets also plan YAML files: `config/conditions.yaml` (E0-03, E0-09). The Python standard library has no YAML parser. The locked stack (`docs/WORKING_RULES.md`) does not list one, and any new dependency needs an accepted ADR.

The catalog is a frozen, cited document (record §3.4, §6.4). It must be easy for a human to read and review, including the quoted citations.

## Decision

Use PyYAML, loading only with `yaml.safe_load`. Version 6.0.3 is installed on the development machine. The exact pin is set in the lock file when E0-02 creates `pyproject.toml`.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| PyYAML with `safe_load` | Widely used; one small dependency; `safe_load` builds only plain Python types | One new dependency. It cannot round-trip comments, which is not needed because the file is written by hand |
| ruamel.yaml | Preserves comments and ordering on write | Larger API. Writing YAML back is not needed |
| A `.yaml` file written in JSON syntax, read with the standard `json` module (YAML 1.2 is a superset of JSON) | No new dependency | Harder to read and review with long quoted citations. A later hand edit in normal YAML syntax would break the reader without warning |
| Store the catalog as JSON | No new dependency | Contradicts the deliverable paths named in the backlog (`.yaml`) |

## Consequences

- PyYAML becomes a development and runtime dependency, added to `pyproject.toml` by E0-02 or the first ticket after it.
- Only `yaml.safe_load` is allowed. `yaml.load` without a safe loader is never used.
- Until E0-02 exists, the catalog test runs with a locally installed `pytest` and `PyYAML`.
