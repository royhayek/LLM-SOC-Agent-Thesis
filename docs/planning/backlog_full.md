# Full backlog — 12 epics, 112 tickets (round 2)

Generated 1 Oct 2026 from the Step D files. Project DoD v1.0 and DoR: see DOD.md.

# Step D — EPIC-0 · Project Foundation & Engineering Baseline

14 tickets · 48 points · Project DoD v1.0 and DoR apply to every ticket.

**Suggested execution order:** E0-01 ∥ E0-02 ∥ E0-04 ∥ E0-13 → E0-14 → E0-08, E0-09 → E0-10, E0-07 → E0-05, E0-11, E0-12 → E0-06 → E0-03

---

**[E0-01] Run a walking-skeleton spike on one hand-written bundle**
**Type:** Spike · **Epic:** EPIC-0 · **Priority:** Highest · **Points:** 5 · **Labels:** spike, research
**Depends on:** None · **Blocks:** E0-03, E0-05, E0-06, E0-08, E2-02

**Context**
Nobody knows yet whether the base model can turn an alert bundle into a usable verdict, or what the alert format must contain. This spike answers both in week one, while changing direction is still cheap. It de-risks H2 and H4 (is the model adequate at all), H1 (behaviour when a source is missing) and risk #5 (LLM reproducibility).

**Goal**
A findings note states the validity, agreement, correctness and token cost of one schema-constrained verdict call on two models, and lists what the alert format lacks.

**Scope**
- In: one hand-written SSH brute-force bundle (honeypot + flows present, MQTT absent) with an expected verdict; one prompt; one schema-constrained call; one validator; 20 runs (10 local, 10 hosted); a findings note.
- Out: testbed, detectors, retrieval, the three-node graph, any agent framework, prompt tuning beyond one logged revision, a real action catalog, importing any spike code into `thesis/`.

**Technical notes**
- Output fields follow the §6.5 schema (record §6.5, §9).
- The action enum is a placeholder named `SPIKE_ONLY` and is never reused. This keeps the freeze-before-results rule intact (C-20).
- Ollama `num_ctx 8192`, verified by a marker test before any run (record §4.3).
- The hosted model is from the same family as the local one (record §4.2). ASSUMPTION.
- Timebox: 5 working days, hard stop (record §9).
- Suggested approach: one Pydantic model, one OpenAI-compatible call per run, a loop of 10 per model.
- ASSUMPTION: the expected verdict is committed in the bundle file before the first run, so correctness can be scored (R-310, C-10).

**Acceptance criteria**
- Given a prompt with a unique marker in its first 50 tokens, when it is sent to local Ollama with `num_ctx 8192`, then the reply contains the marker, and `spikes/marker_test.log` records the exchange.
- Given `spikes/bundle_ssh_bruteforce.json`, when `python spikes/walking_skeleton.py --model local` runs, then it prints either a verdict object or a validation error, and appends one row to `spikes/results.csv`.
- Given 10 runs per model have finished, when `spikes/results.csv` is opened, then it has 20 rows with the columns: run_id, model, schema_valid, incident_type, severity, affected_device, recommended_action, matches_expected, tokens_in, tokens_out, latency_s.
- [ ] `spikes/bundle_ssh_bruteforce.json` contains an `expected_verdict` block whose git commit predates the first results row.
- [ ] `spikes/logs/` holds the full prompt and raw completion of all 20 runs.
- [ ] `spikes/FINDINGS.md` (one page or less) states per model: validity rate, agreement rate (share of runs equal to the modal verdict), correctness rate against the expected verdict, mean tokens in/out, mean latency.
- [ ] `spikes/FINDINGS.md` lists every field the model asked for or invented that the format lacked.
- [ ] `spikes/FINDINGS.md` ends with recommendations on three points: model, token budget, alert-schema fields.

**Checklist**
- [ ] Write the hand-written bundle and its expected verdict; commit.
- [ ] Write the Pydantic verdict model (§6.5 fields, `SPIKE_ONLY` enum).
- [ ] Set `num_ctx 8192` and run the marker test.
- [ ] Write the script: build prompt, call, validate, log, append CSV.
- [ ] Run 10 times on local Ollama.
- [ ] Open the hosted account with a small spending cap; run 10 times.
- [ ] Compute the rates and write FINDINGS.md.
- [ ] Stop at day 5 whatever the state.

**Deliverables**
`spikes/walking_skeleton.py`, `spikes/bundle_ssh_bruteforce.json`, `spikes/results.csv`, `spikes/logs/*.json`, `spikes/marker_test.log`, `spikes/FINDINGS.md`

**Risks / gotchas**
- Ollama truncates context silently if `num_ctx` is set in the wrong place (Modelfile vs request option). The marker test exists to catch this.
- Local and hosted structured-output mechanisms differ, so the validity rate compares two mechanisms as well as two models. Note this in FINDINGS.md.
- Temptation to keep editing the prompt until runs pass. Write it once and log any revision.
- Throwaway code tends to get imported later. It stays in `spikes/`.

**Open questions**
None

**Traceability**
R-099, R-144–R-146, R-203, R-288, R-289, R-296–R-312 · Record §4.2, §4.3, §8 (ticket 1), §9 · Proposal: Methodology

---

**[E0-02] Scaffold the monorepo with CI and an ADR log**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** High · **Points:** 3 · **Labels:** engineering, infra
**Depends on:** None · **Blocks:** E0-06, E0-07, E0-08, E0-09, E0-10, E0-14

**Context**
Every later code ticket assumes linting, typing, tests and a place to record decisions. Setting them up first makes the DoD enforceable. ADR-000 records the architecture prohibitions once, so they never need a ticket. It supports risk #5 (reproducibility).

**Goal**
An empty `thesis` package passes ruff, mypy strict and pytest in CI, and ADR-000 records the toolchain and the architecture rules.

**Scope**
- In: pyproject, toolchain, pre-commit, CI, `slow` marker, `.env` handling, ADR template, ADR-000.
- Out: Docker files (E0-07), application code, containerised CI, release automation, a coverage target.

**Technical notes**
- Toolchain: uv or Poetry, ruff, mypy, pytest, pre-commit (record §8 ticket 2).
- Package name `thesis` until a name is chosen (record §4, §11.4).
- Tests marked `slow` are excluded from CI (record §6.9).
- `.env` is gitignored and secrets are never logged (record §6.11).
- ADR-000 records these rules:
  - Modular monolith (§6.1).
  - No microservices, Postgres, message queue or orchestration beyond Docker Compose (§6.7).
  - No OpenTelemetry or Prometheus (§6.10).
  - No agent framework and no vector database (§6.2).
  - No new dependency without an ADR (§14).
- ASSUMPTION: GitHub Actions, if the repo is on GitHub.

**Acceptance criteria**
- Given a fresh clone, when the install command, `pre-commit run --all-files` and `pytest` run, then all three exit with code 0.
- Given a test marked `@pytest.mark.slow`, when CI runs, then the CI log reports that test as deselected.
- Given `.env` is added to the git index, when CI runs, then the job fails with a message naming `.env`.
- [ ] `docs/adr/0000-toolchain-and-architecture-rules.md` has status Accepted and lists every prohibition in the technical notes.
- [ ] `docs/adr/template.md` exists.
- [ ] `.env.example` contains `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` placeholders.
- [ ] The mypy configuration excludes `spikes/`.
- [ ] `tests/test_smoke.py` exists and passes.

**Checklist**
- [ ] Initialise the project with uv or Poetry.
- [ ] Add ruff, mypy, pytest and pre-commit.
- [ ] Register the `slow` marker and exclude it in CI.
- [ ] Write the CI workflow, including the `.env` check.
- [ ] Add `.gitignore` and `.env.example`.
- [ ] Write the ADR template and ADR-000.
- [ ] Push and confirm CI passes.

**Deliverables**
`pyproject.toml`, lock file, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.gitignore`, `.env.example`, `thesis/__init__.py`, `tests/test_smoke.py`, `docs/adr/template.md`, `docs/adr/0000-toolchain-and-architecture-rules.md`

**Risks / gotchas**
- CI passing with zero tests proves nothing, which is why the smoke test exists.
- Strict mypy over generated or spike code produces noise. Keep strict mode scoped to `thesis/`.

**Open questions**
None

**Traceability**
R-133, R-154, R-155, R-161, R-175–R-177, R-179, R-184–R-186, R-271, R-288, R-344, R-345 · Record §6.1, §6.2, §6.7, §6.9, §6.10, §6.11, §8 (ticket 2) · Proposal: none

---

**[E0-03] Write and freeze METHODS.md v1.0**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 5 · **Labels:** research, writing, freeze-before-results
**Depends on:** E0-01, E0-04, E0-05, E0-11, E0-12, E0-13 · **Blocks:** E0-09 (fills `conditions.yaml`), E2-02, E3-05, E9-01, E9-05, E11-04

**Context**
With no supervisor, METHODS.md is the only review the design gets before the defense (record §3.4). It integrates the frozen outputs of E0-04, E0-05, E0-11, E0-12 and E0-13, and it resolves conflicts C-03, C-04 and C-05. It serves H1–H4 and risks #1–#4.

**Goal**
A dated 4–6 page METHODS.md v1.0 is tagged in git, and every later experiment can be checked against it.

**Scope**
- In:
  - Incident unit
  - Condition matrix and `config/conditions.yaml`
  - Metric definitions
  - Catalog derivation summary
  - Statistical tests
  - Target-N method
  - Scoping trade-offs
  - Honeypot all-positive handling
  - The two-baselines question
  - An empty changelog
- Out: the target-N number (E2-02), per-family action sets (E1-03), thesis prose (E11-04).

**Technical notes**
- Contents follow §3.4. The incident unit is the first section (§8). The file is dated, and changes after experiments start go in an appended changelog (§3.4).
- Statistics:
  - McNemar for paired binary outcomes and Wilcoxon signed-rank for paired scores (§10).
  - Bundle-level metrics are primary, with an episode-level block bootstrap (§4.1).
  - H1 is reported stratified by family (§3.2).
- Conflicts to resolve here:
  - C-03: k is 3–5 in one place and 3 in another.
  - C-04: the condition list, including whether pairwise H1 sets are in.
  - C-05: the 60 s window is both locked and open.
- ASSUMPTION: honeypot-keyed bundles are always positive, so detection metrics are reported with and without them, unless you decide otherwise.
- ASSUMPTION: the scoping section states that detectors run upstream rather than as agent tools (C-07).

**Acceptance criteria**
- [ ] The first section of `METHODS.md` is "Incident unit" and states W, D, the tiling rule, the empty-window rule and the label rule.
- [ ] The condition-matrix table and `config/conditions.yaml` list the same conditions. The count is stated as a number.
- [ ] k is stated as a single number (C-03).
- [ ] Pairwise H1 conditions are marked included or excluded, with a reason (C-04).
- [ ] The statistics section names the test used for each of H1–H4 and the resampling unit.
- [ ] The target-N section states the method and its inputs, and says the number is added in v1.1 by E2-02.
- [ ] The scoping section states three choices: bundles are given, not discovered; a fixed graph instead of ReAct; detectors run upstream.
- [ ] The honeypot all-positive handling is stated.
- [ ] The two-baselines question is recorded with its current answer.
- [ ] The rendered page count is between 4 and 6.
- [ ] The document is dated, carries a spike-exposure statement and an empty "Changelog" section, and is tagged `methods-v1.0`.

**Checklist**
- [ ] Collect the frozen sections from E0-04, E0-05, E0-11, E0-12 and E0-13.
- [ ] Write the incident-unit section.
- [ ] Write the condition matrix and `config/conditions.yaml`.
- [ ] Write the metrics and statistics sections.
- [ ] Write the target-N method.
- [ ] Write the scoping trade-offs and the honeypot handling.
- [ ] Re-read §10 and tick each open question as answered here or deferred to its ticket.
- [ ] Check the page count, date the file and tag it.

**Deliverables**
`METHODS.md`, `config/conditions.yaml`

**Risks / gotchas**
- Writing vaguely to avoid deciding. Vague text is exactly where design flaws hide.
- 60 s is untested on slow attacks. A slow brute force spans many bundles and inflates clustering.
- The number of conditions drives cost, so re-check ADR-001 if it changes.

**Open questions**
"Is a 60-second window the right unit?" (§10) · "Are two baselines sufficient?" (§10)

**Traceability**
R-077, R-086–R-088, R-101, R-234–R-236, R-241, R-242, R-254–R-256, R-273–R-280, R-288 · Record §3.1–§3.4, §4.1, §8 (ticket 3), §10 · Proposal: Methodology

---

**[E0-04] Derive action catalog v0.1 with a citation per entry**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 5 · **Labels:** research, freeze-before-results
**Depends on:** None · **Blocks:** E0-11, E0-12, E1-03, E7-01, E8-01

**Context**
H3 and H4 are scored against the actions the agent may recommend. If the catalog is written after seeing agent outputs, the safety result is worthless (record §8). With no second rater, deriving every entry from published sources replaces inter-rater agreement (record §3.4, risk #3).

**Goal**
A frozen catalog of 6–8 recommendation-only actions exists, each backed by at least one published citation.

**Scope**
- In: reading French and EU official guidance (ANSSI / CERT-FR, ENISA, CERT Société Générale playbooks), with MITRE ATT&CK mitigations and NIST SP 800-61 as supporting references; the catalog YAML; a derivation note; a provisional family-to-action table. French and EU sources are cited first (decision 2026-10-04, record §3.4).
- Out: per-family acceptable and unsafe sets (E1-03), scoring rules (E0-12), executable actions, reading spike outputs, classmate double-rating (optional bonus, never blocking).

**Technical notes**
- A closed enumeration defined in advance (§6.4), with 6–8 candidates (§6.5) and a citation per entry (§3.4).
- The agent recommends and never executes (§1.1).
- ASSUMPTION: the catalog includes an escalate-to-human action and a monitor/no-action action.
- Run this in parallel with the spike, before FINDINGS.md exists (C-20).

**Acceptance criteria**
- [ ] `knowledge/action_catalog.yaml` has between 6 and 8 entries. Each has an id, name, description and at least one citation.
- [ ] `tests/test_catalog.py::test_every_action_cited` fails when any entry has zero citations, and passes on the committed file.
- [ ] Every description starts with "Recommend".
- [ ] `docs/catalog_derivation.md` lists the sections read per source. For every candidate action considered, it records in or out with a reason.
- [ ] `docs/catalog_derivation.md` contains a provisional table mapping the §3.2 candidate families to actions, with citations.
- [ ] `docs/catalog_derivation.md` contains a dated statement that spike outputs were not read during derivation.
- [ ] Git tag `catalog-v0.1` exists.

**Checklist**
- [ ] Collect the three source types.
- [ ] Extract candidate actions with their citations.
- [ ] Merge duplicates.
- [ ] Choose 6–8.
- [ ] Write the YAML.
- [ ] Write the derivation note and the family table.
- [ ] Add the citation test.
- [ ] Tag the commit.

**Deliverables**
`knowledge/action_catalog.yaml`, `docs/catalog_derivation.md`, `tests/test_catalog.py`

**Risks / gotchas**
- A catalog that is too coarse makes contextual appropriateness unable to tell actions apart. One that is too large confuses the enum.
- The family mapping stays provisional until E1-02 freezes the families. The catalog itself does not depend on the families.

**Open questions**
None

**Traceability**
R-036, R-037, R-170, R-197–R-202, R-282, R-288 · Record §3.4, §6.4, §6.5, §8 (ticket 4) · Proposal: Objective 3, Methodology

---

**[E0-05] Define and freeze bundle reduction policy v1.0**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 5 · **Labels:** research, freeze-before-results
**Depends on:** E0-01, E0-08, E0-14 · **Blocks:** E0-03, E0-06, E2-01, E3-06, E3-07

**Context**
The reduction decides what every condition sees, including both baselines. If it compresses too hard, H1 shows no fusion benefit (record §4.4). If the agent and the baselines see different views, H4 is contaminated (record §4.1). This ticket also settles the token conflict C-02.

**Goal**
A frozen METHODS.md section defines, per source, the exact aggregates, exemplar rules and token limits applied to every condition.

**Scope**
- In: aggregate fields per source; exemplar counts, ranking keys and tie-breaks; honeypot truncation and delimiting; input and output token targets and ceilings; the reduction ratio measured on the spike bundle; Baseline A's input view.
- Out: implementation (E3-06), golden files (E3-07), changing W, prompt wording.

**Technical notes**
- Aggregates and exemplars follow the §4.4 table:
  - Flows: top-5 exemplars by detector score.
  - MQTT: top-3 anomalous messages.
  - Honeypot: up to 3 command sequences, hard-truncated.
  - Each detector's score and label is included.
- Token limits (§4, §4.4):
  - Reduced bundle target: 800–1,200 tokens.
  - Input per call: ≤2,000 target, 2,500 ceiling.
  - Output per call: ≤200 target, 250 ceiling.
- The same reduction applies to all conditions, including both baselines (§4.1).
- Field availability comes from the ADR-002 mapping (E0-14).
- Exemplar ranking needs detector scores, which only exist after EPIC-4 (C-15).
- ASSUMPTION: Baseline A classifies the reduced aggregate view rather than raw flows.

**Acceptance criteria**
- [ ] The METHODS.md section "Reduction policy v1.0" lists every aggregate field per source with its formula.
- [ ] Every exemplar rule states its count, ranking key and tie-break.
- [ ] The honeypot command cap is stated in characters, together with the delimiter format.
- [ ] Input target, input ceiling, output target and output ceiling are stated as numbers. The text records which side of C-02 was chosen and why.
- [ ] The reduction ratio (raw tokens ÷ reduced tokens), measured on the spike bundle with the experiment model's tokenizer, is recorded as a number.
- [ ] Baseline A's input view is defined in one paragraph.
- [ ] `docs/reduction_worked_example.md` shows the spike bundle before and after reduction.
- [ ] Git tag `reduction-v1.0` exists.

**Checklist**
- [ ] List the fields from §4.4 and the ADR-002 field mapping.
- [ ] Write the formulas.
- [ ] Write the exemplar rules and tie-breaks.
- [ ] Set the truncation cap and delimiter format.
- [ ] Decide the token budget (C-02).
- [ ] Reduce the spike bundle by hand and count its tokens.
- [ ] Define Baseline A's view.
- [ ] Write the section and tag it.

**Deliverables**
`METHODS.md` (section "Reduction policy v1.0"), `docs/reduction_worked_example.md`

**Risks / gotchas**
- The spike bundle is small, so the measured ratio understates busy windows.
- Token counts differ between tokenizers. Measure with the experiment model's tokenizer.
- Exemplar ranking depends on detectors that are not built yet (C-15).

**Open questions**
None

**Traceability**
R-102–R-114, R-120, R-121, R-218, R-219, R-229, R-281, R-288, R-312 · Record §4, §4.1, §4.4, §8 (ticket 5) · Proposal: Methodology

---

**[E0-06] Write ADR-001 on LLM serving, cost and time budget**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** Medium · **Points:** 3 · **Labels:** engineering, research
**Depends on:** E0-01, E0-05 · **Blocks:** E6-01, E6-08, E9-08

**Context**
The record decided serving in principle (record §4.2). The spike now gives real numbers. Pinning the exact model and revision is the reproducibility claim (risk #5), and a hard spending cap protects the €100 budget.

**Goal**
ADR-001 is Accepted. It pins the experiment and development models and shows that the full experiment plan fits under €100 with a cap active.

**Scope**
- In: model name and revision, provider, sampling parameters, seed support, development model, cost table, spending cap, environment variables.
- Out: client code (E6-01), self-hosting or vLLM, any model comparison, the final N (recomputed in E2-02).

**Technical notes**
- The model is open-weights and pinned by name and revision (§4.2).
- The development model is from the same family as the experiment model. Never develop on one vendor's model and run on another's (§4.2).
- One OpenAI-compatible client, switched by `LLM_BASE_URL` and `LLM_MODEL` (§4.2).
- Prices are verified at the time of writing (§4.2).
- The budget covers 1 exploratory run plus 3 full runs, with a hard cap (§4.4.1).
- Hardware: 16 GB M2 (§4.2).
- ASSUMPTION: N = 250 as a placeholder until E2-02.

**Acceptance criteria**
- [ ] `docs/adr/0001-llm-serving.md` has status Accepted.
- [ ] It names the experiment model's name and revision string, the provider, temperature, top_p, max_tokens, and whether seeds are supported.
- [ ] It names the development model, states its same-family relation, and cites spike numbers from FINDINGS.md.
- [ ] It contains a cost table for 1 exploratory run plus 3 full runs: calls, input tokens, output tokens, price per million tokens with the date checked, and a total of €100 or less.
- [ ] The provider's spending cap is set, and its amount and date are written in the ADR.
- [ ] It states: no vLLM or self-hosting; one base model, no model comparison.

**Checklist**
- [ ] Read FINDINGS.md.
- [ ] Shortlist models in the chosen family.
- [ ] Check the provider supports revision pinning.
- [ ] Look up current prices.
- [ ] Compute the cost table.
- [ ] Set the spending cap.
- [ ] Write the ADR.

**Deliverables**
`docs/adr/0001-llm-serving.md`

**Risks / gotchas**
- A provider can change the weights behind the same model name. Pin a revision or snapshot ID.
- No seed support means the repetitions carry all the variance. Record this.
- Prices change. Date the price check.

**Open questions**
"How many scenarios are needed for statistical validity?" (§10). The cost uses a placeholder N until E2-02.

**Traceability**
R-078, R-123, R-128–R-131, R-133, R-135, R-137–R-141, R-143, R-147, R-148, R-288, R-312 · Record §4.2, §4.4.1, §8 (ticket 6) · Proposal: Methodology

---

**[E0-07] Build the benign-only Docker Compose testbed skeleton**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** High · **Points:** 5 · **Labels:** infra, engineering
**Depends on:** E0-02, E0-14 · **Blocks:** E1-01, E1-05, E1-07

**Context**
Every attack scenario, and so all ground truth, runs on this testbed. Proving network isolation now, before any attack tool exists, is the ethics guarantee in the proposal. It serves Objective 1 and H1, because all three sources must exist.

**Goal**
One command starts an isolated, benign-only testbed whose three sources write raw logs into a per-run folder.

**Scope**
- In: a compose file with Mosquitto, 3–4 MQTT emulators, the honeypot and the capture sidecar from ADR-002; an internal network; an egress test; up, down and reset commands; the raw output layout.
- Out: attack tooling (EPIC-1), benign profiles with irregularities (E1-05), the scenario runner (E1-07), detectors, physical devices, any internet-reachable service.

**Technical notes**
- Fully emulated, using Docker Compose (§4, §6.2).
- An isolated network with no route to the host LAN or the internet, verified before any attack tooling exists (§6.11).
- Do not run alongside Ollama on 16 GB (§4.2).
- Raw telemetry is stored as files on disk (§6.7).
- ASSUMPTION: simple periodic publishers are enough at this stage.

**Acceptance criteria**
- Given a machine with no containers from this project, when `make up` runs, then `docker compose ps` lists the broker, 3–4 emulators, the honeypot and the capture sidecar as running.
- Given the testbed is up, when `scripts/check_isolation.sh` runs, then every container fails to reach 1.1.1.1 and the host LAN gateway, and the script exits 0 only in that case.
- Given the testbed ran for 5 minutes, when `make down` runs, then `data/raw/<run_id>/` contains a non-empty MQTT file, a non-empty flows file, and a honeypot log file (which may be empty under benign traffic).
- Given `make reset` has run, when `make up` runs again, then the same set of containers starts and no files from the previous run are present in the running containers.
- [ ] The README "Resources" section says to stop Ollama before `make up` on 16 GB, and records the testbed's measured peak memory.

**Checklist**
- [ ] Write the compose services.
- [ ] Declare the internal network.
- [ ] Write the emulator script.
- [ ] Add the honeypot container.
- [ ] Add the capture sidecar on the shared network namespace.
- [ ] Write `check_isolation.sh`.
- [ ] Add the Makefile targets.
- [ ] Run for 5 minutes and record memory.
- [ ] Update the README.

**Deliverables**
`docker-compose.yml`, `testbed/emulator/`, `testbed/capture/`, `scripts/check_isolation.sh`, `Makefile`, `README.md` (Resources section), `data/raw/` layout

**Risks / gotchas**
- On macOS, Docker Desktop runs inside a VM, so host-gateway behaviour differs from Linux. Test the host gateway explicitly.
- Flow capture must share the testbed's network namespace, or it captures nothing.
- Under benign traffic nothing touches the honeypot, so its log is empty by design. That is expected, not a failure.

**Open questions**
None

**Traceability**
R-015, R-050–R-052, R-054–R-056, R-069, R-070, R-072, R-288 · Record §4, §4.2, §6.2, §6.7, §6.11, §8 (ticket 7) · Proposal: Methodology, Objective 1

---

**[E0-08] Draft alert schema v0.1 from the spike findings**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** Medium · **Points:** 3 · **Labels:** engineering, research
**Depends on:** E0-01, E0-02 · **Blocks:** E0-05, E3-01, E3-10

**Context**
The record forbids designing the alert schema blind. The spike shows what the model actually needed (record §9). Every normalizer and the reduction depend on this format. It serves H1, because the sources must be comparable, and risk #1.

**Goal**
A versioned Pydantic `Alert` model represents all three sources, with the device-mapping rule implemented once in code.

**Scope**
- In: the `Alert` model, a source enum, the device-mapping function, one example per source, a round-trip test, a schema changelog.
- Out: normalizers (E3-02 to E3-04), Parquet input/output, detectors, freezing the schema (v1 comes in E3-01).

**Technical notes**
- D is the non-infrastructure endpoint, and honeypot events key to the honeypot. The mapping is defined once, in code (§4.1).
- One format downstream (Arch §5). Pydantic (§6.2).
- The schema is written after the spike and informed by it (§8 ticket 8, §9).

**Acceptance criteria**
- Given one example JSON per source in `tests/fixtures/alerts/`, when `pytest tests/test_alert_schema.py` runs, then each example parses into `Alert` and serialises back to identical JSON.
- Given a flow between an IoT device IP and the broker IP, when `subject_device()` is called, then it returns the IoT device ID.
- Given a honeypot event from any source IP, when `subject_device()` is called, then it returns the honeypot ID.
- [ ] `thesis/schema/alert.py` declares `SCHEMA_VERSION = "alert-v0.1"`.
- [ ] `docs/schema/CHANGELOG.md` lists each field added because of a spike finding, citing FINDINGS.md.

**Checklist**
- [ ] Read FINDINGS.md.
- [ ] List the fields.
- [ ] Write the model.
- [ ] Write the infrastructure list and the device-mapping function.
- [ ] Add the fixtures.
- [ ] Write the tests.
- [ ] Write the changelog.

**Deliverables**
`thesis/schema/alert.py`, `thesis/schema/devices.py`, `tests/fixtures/alerts/*.json`, `tests/test_alert_schema.py`, `docs/schema/CHANGELOG.md`

**Risks / gotchas**
- If the infrastructure list misses the broker, gateway or sidecar, traffic gets keyed to infrastructure and bundles go to the wrong device.
- An untyped payload dict hides drift between sources.
- The schema can over-fit the single SSH scenario.

**Open questions**
None

**Traceability**
R-089, R-090, R-095, R-098, R-099, R-288, R-312 · Record §4.1, §6.2, §8 (ticket 8), §9 · Arch §5 · Proposal: Objective 2

---

**[E0-09] Implement ExperimentConfig with a reproducible config hash**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E0-02 · **Blocks:** E0-10, E6-06, E8-02, E8-04, E9-01, E9-02

**Context**
H1, H2 and H3 are all switches on the same pipeline: sources, strategy and safety. If any switch is hardcoded, the comparisons stop being paired. The config hash in every result row is what makes runs reproducible (risk #5).

**Goal**
Every run is described by one validated config object whose hash is stable, and which changes whenever any field changes.

**Scope**
- In: `ExperimentConfig`, a `Provenance` model, canonical serialisation, SHA-256 hashing, a valid-combination check driven by `config/conditions.yaml`.
- Out: the runner (E9-01), filling `conditions.yaml` (E0-03), writing results (E9-02), a command-line interface.

**Technical notes**
- Fields follow §6.1. Provenance follows §4.2: model and revision, provider, sampling parameters, seed, prompt-template version, graph version.
- Canonical JSON uses sorted keys and sorted source sets, with floats serialised as strings.
- ASSUMPTION: `conditions.yaml` lists the allowed (sources, strategy, safety) combinations. E0-03 fills it, which keeps this ticket independent.

**Acceptance criteria**
- Given two configs with the same values supplied in a different order, when both are hashed, then the hashes are equal.
- Given a config, when any single field changes, then the hash changes. This is a parametrised test over every field.
- Given an empty `sources` set, when the config is constructed, then a validation error is raised.
- Given a combination not listed in `config/conditions.yaml`, when it is validated, then the error message names the combination.
- [ ] `thesis/config.py` exports `ExperimentConfig`, `Provenance` and `config_hash()`.
- [ ] `config/conditions.yaml` exists with one placeholder entry and a comment pointing to METHODS.md.

**Checklist**
- [ ] Write the models.
- [ ] Write the canonical serialisation.
- [ ] Write the hash function.
- [ ] Write the combination check.
- [ ] Write the tests.
- [ ] Add the placeholder YAML.

**Deliverables**
`thesis/config.py`, `config/conditions.yaml`, `tests/test_config.py`

**Risks / gotchas**
- Float formatting can change the hash across Python versions, which is why floats are serialised as strings.
- Adding a field later changes every hash. Record any such change in the METHODS.md changelog.

**Open questions**
None

**Traceability**
R-134, R-149, R-151–R-153 · Record §4.2, §6.1 · Proposal: Methodology

---

**[E0-10] Add structured JSON logging for every LLM call**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E0-02, E0-09 · **Blocks:** E6-01, E7-05

**Context**
One logging mechanism serves as the audit log, the cost instrumentation and the debugger (record §6.10). Cost per incident is a publishable result, so logging must exist from the first real call. It serves H3 (auditability) and risk #5.

**Goal**
A single function writes one append-only JSONL record per LLM call, containing every §6.10 field and no secrets.

**Scope**
- In: structlog configuration, `log_llm_call()`, the JSONL sink, a redaction test.
- Out: the LLM client (E6-01), rejection semantics of the audit log (E7-05), dashboards, OpenTelemetry or Prometheus.

**Technical notes**
- structlog emitting JSON (§6.10).
- The 12 fields are: node, model, revision, tokens in, tokens out, latency, full prompt, raw completion, parse outcome, config hash, bundle ID and repetition (§6.10, §4.4).
- The API key is never logged (§6.11). The log is append-only JSONL (§6.7).

**Acceptance criteria**
- Given a call to `log_llm_call()` with all 12 fields, when the log file is read, then one JSON line contains all 12 fields with the supplied values.
- Given a call missing any required field, when it is invoked, then it raises an error before writing anything.
- Given `LLM_API_KEY` is set in the environment, when any log line is written, then the key's value does not appear anywhere in the log file.
- Given an existing log file, when a second call is made, then the first line is byte-identical to before.
- [ ] `thesis/obs/logging.py` defines `log_llm_call()`, with a docstring listing the 12 fields.

**Checklist**
- [ ] Configure structlog.
- [ ] Define the record fields.
- [ ] Write the function and the sink.
- [ ] Write the four tests.
- [ ] Gitignore `logs/`.

**Deliverables**
`thesis/obs/logging.py`, `tests/test_llm_logging.py`, `logs/` (gitignored)

**Risks / gotchas**
- Full prompts make log files large. That is acceptable, but they must never be committed.
- Redaction that only matches the variable name misses the value. The test checks the value.

**Open questions**
None

**Traceability**
R-162, R-174, R-179, R-181–R-183, R-262 · Record §4.4, §6.7, §6.10, §6.11 · Proposal: Methodology

---

**[E0-11] Decide and freeze the validator rejection policy**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 2 · **Labels:** research, freeze-before-results
**Depends on:** E0-04 · **Blocks:** E0-03, E7-04

**Context**
When the validator rejects an output, the system can retry with feedback, fall back to escalate-to-human, or hard-fail. Each option gives a different measured unsafe rate, so choosing after results would bias H3 (risk #3).

**Goal**
METHODS.md states one rejection policy, which attempt is scored, and how every attempt is logged.

**Scope**
- In: the options analysis, the decision, the scoring rule, the logging rule, and the behaviour under `logging_only`.
- Out: implementation (E7-04), the validator rules themselves (E7-02).

**Technical notes**
- Validation is a hard gate, not a filter (§3.3, §6.11).
- Every attempt is logged (§3.1).
- ASSUMPTION: escalate-to-human exists as a catalog action (E0-04).

**Acceptance criteria**
- [ ] The METHODS.md "Rejection policy" section names the chosen policy, the maximum number of retries, and whether the first or final attempt is scored.
- [ ] The section contains a table showing each option's effect on schema validity, action-space membership and contextual appropriateness.
- [ ] The section states what happens on a failed validation under `logging_only`.
- [ ] The decision is dated.

**Checklist**
- [ ] Write out the three options.
- [ ] Analyse each option's effect on the metrics.
- [ ] Decide.
- [ ] Define the scoring rule.
- [ ] Define the logging rule.
- [ ] Write the section.

**Deliverables**
`METHODS.md` (section "Rejection policy")

**Risks / gotchas**
- Retries raise cost and hide first-attempt failures. Consider scoring the first attempt as well.
- Falling back to escalate-to-human inflates the "safe" rate.

**Open questions**
"What is the validator rejection policy?" (§10)

**Traceability**
R-214, R-215, R-221 · Record §3.1, §3.3, §10 · Proposal: H3

---

**[E0-12] Define the three-way safety scoring protocol**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 3 · **Labels:** research, freeze-before-results
**Depends on:** E0-04 · **Blocks:** E0-03, E1-03, E9-04

**Context**
The validator removes out-of-catalog actions by construction, so counting them turns H3 into a tautology (risk #3). The real H3 result is whether a permitted action fits the incident. This ticket must also fix what "unsafe" means for the validator (C-17) and what "safety off" switches off (C-16).

**Goal**
METHODS.md defines three safety metrics, usefulness, the rule for building per-family action sets, and the exact content of "safety off", before any result exists.

**Scope**
- In: formulas, the headline metric, the per-family set-building rule, benign-bundle scoring, the usefulness test, scoring for both baselines, the validator's definition of "unsafe", the definition of `logging_only`, and a free-text-to-catalog mapping if it is needed.
- Out: the per-family sets themselves (E1-03), implementation (E9-04, E7-06).

**Technical notes**
- The three-way split follows §3.1.
- Acceptable and unsafe sets are fixed before experiments and are the same across conditions (proposal Methodology, §3.1).
- Baseline A uses the severity→action lookup (§6.6).
- The catalog stays in the recommendation prompt in every condition (§4.4).
- ASSUMPTION: the options for "safety off" are:
  - (a) no validator and no constrained decoding;
  - (b) no validator only.

**Acceptance criteria**
- [ ] The METHODS.md "Safety scoring" section gives formulas for schema validity, action-space membership, contextual appropriateness and usefulness.
- [ ] It names contextual appropriateness as the H3 headline, and labels action-space membership as true by construction.
- [ ] It states the rule E1-03 will use to build acceptable and unsafe sets, with the sources it cites.
- [ ] It defines scoring for benign bundles.
- [ ] It defines the H3 usefulness test: which paired test, and the threshold for "no significant loss".
- [ ] It lists exactly which mechanisms `safety=logging_only` disables (C-16). If free-text actions become possible, it fixes their mapping to catalog IDs.
- [ ] It distinguishes "unsafe" as the validator uses it from "unsafe" as the metric uses it (C-17).
- [ ] It defines how Baseline A and Baseline B are scored on each metric.

**Checklist**
- [ ] Write the three formulas.
- [ ] Write the usefulness formula and test.
- [ ] Write the set-building rule.
- [ ] Define benign scoring.
- [ ] Define safety off (C-16).
- [ ] Define "unsafe" (C-17).
- [ ] Define baseline scoring.
- [ ] Write the section.

**Deliverables**
`METHODS.md` (section "Safety scoring")

**Risks / gotchas**
- If safety off also removes constrained decoding, H3 mixes two mechanisms. Consider reporting each separately.
- Unsafe sets that are too strict mark almost everything unsafe and flatten the comparison.

**Open questions**
"How should contextual safety be scored?" (§10)

**Traceability**
R-018, R-216, R-247–R-252 · Record §3.1, §6.4, §6.6, §10 · Proposal: H3, H4, Methodology

---

**[E0-13] Define the reliability and robustness metrics**
**Type:** Research · **Epic:** EPIC-0 · **Priority:** High · **Points:** 2 · **Labels:** research, freeze-before-results
**Depends on:** None · **Blocks:** E0-03, E9-04

**Context**
Objective 5 promises an evaluation of "reliability", and the brief adds "robustness", but no document defines either one (C-09). Left undefined, they would be measured after seeing results, or quietly dropped, and an examiner reading Objective 5 would notice.

**Goal**
METHODS.md defines a reliability metric, and either defines a robustness metric or states explicitly that robustness is out of scope.

**Scope**
- In: definitions, data source, reporting format.
- Out: the prompt-injection experiment (E9-12, stretch only), any LLM runs beyond the planned matrix.

**Technical notes**
- The matrix already has k repetitions (§4.4.1).
- ASSUMPTION: reliability is run-to-run agreement of verdicts across the k repetitions, plus the schema-validity rate, per condition. It needs no new calls.
- ASSUMPTION: robustness is either (a) out of scope, stated as a limitation, or (b) behaviour under prompt injection, only if E9-12 runs.

**Acceptance criteria**
- [ ] The METHODS.md "Reliability" section gives a formula computed only from the k repetitions in the matrix.
- [ ] METHODS.md either gives a robustness formula or contains a one-line out-of-scope statement with its reason.
- [ ] Any extra LLM call needed for these metrics is added to the ADR-001 cost table. If none is needed, that is stated.

**Checklist**
- [ ] Draft the reliability formula.
- [ ] Decide robustness: defined or out of scope.
- [ ] Check the cost impact.
- [ ] Write the section.

**Deliverables**
`METHODS.md` (section "Reliability and robustness")

**Risks / gotchas**
- With k = 3, agreement can only take a few values. Report it per condition, not as a headline.

**Open questions**
None

**Traceability**
R-020–R-022 · Proposal: Objective 5, Expected Outcomes · Brief: Expected Work

---

**[E0-14] Choose honeypot and flow-exporter software in ADR-002**
**Type:** Task · **Epic:** EPIC-0 · **Priority:** High · **Points:** 2 · **Labels:** engineering, infra
**Depends on:** E0-02 · **Blocks:** E0-05, E0-07, E1-04

**Context**
The record fixes "one honeypot" and "a capture sidecar" but names no software. Both choices decide what the honeypot and flow sources can see, so they affect H1 and the reduction fields. This was split out of E0-07 to keep it at 5 points.

**Goal**
ADR-002 is Accepted and names one honeypot and one flow exporter with versions, mapped to every reduction field they must supply.

**Scope**
- In: a shortlist of up to three options each, the criteria, the decision, the field mapping, licences.
- Out: installing them in the compose file (E0-07), the MQTT broker choice (Mosquitto is locked), packet-analytics tools, a SIEM.

**Technical notes**
- Must run in Docker within the 16 GB budget alongside the testbed (§4, §4.2).
- The honeypot must record SSH authentication attempts and typed commands, which the SSH brute-force family needs (§3.2, §9).
- The flow exporter must emit per-flow destination IP, destination port, bytes in and out, protocol, TCP flags (for the SYN-only ratio) and duration (§4.4).
- No technology beyond what the ADR records (DoD).

**Acceptance criteria**
- [ ] `docs/adr/0002-honeypot-and-flow-exporter.md` has status Accepted and names the tool and version for each role.
- [ ] The ADR contains a table mapping each §4.4 aggregate field to an emitted field, or marks it "derived" with its formula.
- [ ] The ADR contains one sample log line from each tool's documentation.
- [ ] The ADR records each tool's licence.

**Checklist**
- [ ] Write the criteria.
- [ ] Shortlist the options.
- [ ] Check field coverage.
- [ ] Check licences and memory use.
- [ ] Write the ADR and mark it Accepted.

**Deliverables**
`docs/adr/0002-honeypot-and-flow-exporter.md`

**Risks / gotchas**
- An exporter without TCP flags breaks the SYN-only ratio, and nothing errors.
- A honeypot that logs authentication but not commands removes the honeypot exemplars.

**Open questions**
None

**Traceability**
R-051, R-055, R-107, R-111, R-344 · Record §4, §4.2, §4.4, §6.2, §8 (ticket 7) · Proposal: Methodology


# Step D — EPIC-1 · IoT Testbed & Scenario Generation

15 tickets · 38 points · Project DoD v1.0 and DoR apply to every ticket.

**Suggested execution order:** E1-01 ∥ E1-02 ∥ E1-05 → E1-03 ∥ E1-04 ∥ E1-06 → E1-07 → E1-08 … E1-13 → E1-14 → E1-15

---

**[E1-01] Gate every scenario run on a passing isolation check**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 2 · **Labels:** infra, testing
**Depends on:** E0-07 · **Blocks:** E1-07

**Context**
E0-07 proves isolation once. This ticket makes the proof a precondition of every run, so no attack can start on a network that can reach the internet or the host LAN. This is the proposal's ethics guarantee, enforced in code rather than remembered.

**Goal**
The scenario runner cannot launch any attack container unless the isolation check passes in the same run.

**Scope**
- In: an `isolation_check()` function wrapping `scripts/check_isolation.sh`, a refusal path in the runner entry point, a negative test, logging of the result.
- Out: the runner itself (E1-07), firewall rules on the host, monitoring of the network during a run.

**Technical notes**
- An isolated Docker network with no route to the host LAN or the internet, verified before any attack tooling runs (record §6.11).
- Attacks run only on the isolated testbed (proposal Methodology).
- ASSUMPTION: the check runs at the start of every run. One check per run is enough, because the network definition cannot change mid-run.

**Acceptance criteria**
- Given the testbed network is declared internal, when `isolation_check()` runs, then it returns pass and the result is written to the run's execution log.
- Given a test that attaches a non-internal network to one container, when the runner entry point is called, then it exits with a non-zero code and no attack container is created (verified with `docker ps -a`).
- [ ] `thesis/testbed/isolation.py` defines `isolation_check()`.
- [ ] `tests/test_isolation_gate.py` contains the negative test, marked `slow`.

**Checklist**
- [ ] Wrap the E0-07 script in a Python function.
- [ ] Add the refusal path to the runner entry point.
- [ ] Write the negative test.
- [ ] Log the result into the execution log format.

**Deliverables**
`thesis/testbed/isolation.py`, `tests/test_isolation_gate.py`

**Risks / gotchas**
- On macOS, Docker Desktop's VM can route to the host even when the network is "internal". The check must probe the host gateway, not only the internet.
- A check that times out must count as a fail, never as a pass.

**Open questions**
None

**Traceability**
R-070, R-071 · Record §6.11 · Proposal: Methodology (ethics)

---

**[E1-02] Select and freeze the six attack families**
**Type:** Research · **Epic:** EPIC-1 · **Priority:** High · **Points:** 3 · **Labels:** research, freeze-before-results
**Depends on:** None · **Blocks:** E1-03, E1-04, E1-06, E2-01, E2-02, E3-10, E7-01

**Context**
The families fix the label space and H1's stratification. If every family is visible in every source, or none is, H1 confirms itself for the wrong reason (risk #4). This ticket also resolves C-01: §5 asks for a 2/2/2 mix across three, two and one sources, but the §3.2 table is 1/4/1.

**Goal**
Six families are frozen, each with a dataset reference, an ATT&CK technique and a predicted source-visibility row that satisfies a written stratification rule.

**Scope**
- In: the selection, the visibility matrix, the stratification rule, the `incident_type` enum, the METHODS.md entry.
- Out: how each attack is generated (E1-04), the action sets (E1-03), checking visibility against real captures (E1-14).

**Technical notes**
- Exactly six families (§5).
- The selection must include denial of service, scanning, brute-force login and botnet traffic (proposal Methodology).
- Families are guided by Bot-IoT, TON_IoT, CICIoT2023 and MQTTset (proposal Methodology).
- A meaningful subset of families must leave traces in at least two sources (§3.2).
- The `incident_type` enum is the six families plus `benign` (§6.5).
- Starting point: the §3.2 candidate table.

**Acceptance criteria**
- [ ] `knowledge/attack_families.yaml` names six families. Each has an id, a dataset reference from [6]–[9] and an ATT&CK technique ID.
- [ ] The same file contains a visibility matrix: six families × MQTT, flows and honeypot, each cell yes or no.
- [ ] The stratification rule is written in one sentence, and a test `tests/test_families.py::test_stratification` checks the matrix against it.
- [ ] The set covers DoS, scanning, brute force and botnet, each mapped to at least one family.
- [ ] `thesis/schema/verdict.py` (or a constants module) defines the `incident_type` enum with exactly seven values.
- [ ] METHODS.md records the selection and states which side of C-01 was taken. It goes in v1.0 if E0-03 is not yet frozen, otherwise as a changelog entry.

**Checklist**
- [ ] Start from the §3.2 table.
- [ ] Decide the stratification rule (C-01).
- [ ] Adjust the families to satisfy it.
- [ ] Assign dataset references and ATT&CK IDs.
- [ ] Write the YAML and the stratification test.
- [ ] Define the enum.
- [ ] Record in METHODS.md.

**Deliverables**
`knowledge/attack_families.yaml`, `tests/test_families.py`, enum in `thesis/schema/`, METHODS.md entry

**Risks / gotchas**
- A family that is "visible in the honeypot" only if the attacker targets the honeypot. The visibility prediction depends on the target choice, so record the target with each family.
- A DoS against the MQTT broker also appears in the MQTT source and breaks a "one-source" slot.

**Open questions**
"Which six attack families?" (§10)

**Traceability**
R-058–R-064, R-204, R-253 · Record §3.2, §5, §6.5, §10 · Proposal: Methodology

---

**[E1-03] Build the per-family acceptable and unsafe action sets**
**Type:** Research · **Epic:** EPIC-1 · **Priority:** High · **Points:** 3 · **Labels:** research, freeze-before-results
**Depends on:** E1-02, E0-04, E0-12 · **Blocks:** E8-01, E9-04, E2-09, E6-03

**Context**
Contextual appropriateness, the real H3 result, and usefulness are both scored against these sets (risk #3). The proposal requires them to be fixed per scenario before any experiment, and identical across all conditions.

**Goal**
Every catalog action is classified as acceptable, unsafe or neutral for each family and for `benign`, with a citation for every classification.

**Scope**
- In: one acceptable set and one unsafe set per family and for `benign`, citations, a completeness test, the version tag.
- Out: changing the catalog (a catalog change is a METHODS.md changelog entry and a new catalog version), scoring code (E9-04), Baseline A's lookup (E8-01).

**Technical notes**
- Apply the set-building rule frozen in E0-12.
- Sets are fixed before any experiment and identical across conditions (proposal Methodology, §3.1).
- Sources: French and EU official guidance first (ANSSI / CERT-FR, ENISA, CERT Société Générale playbooks), with ATT&CK mitigations and NIST SP 800-61 as supporting references (decision 2026-10-04, §3.4).
- ASSUMPTION: a "neutral" class covers actions that are neither acceptable nor unsafe for a family, so no action is forced into a wrong bucket.

**Acceptance criteria**
- [ ] `knowledge/action_sets.yaml` has an entry for each of the six families and for `benign`. Each entry classifies every catalog-v0.1 action as acceptable, unsafe or neutral.
- [ ] Every acceptable or unsafe assignment carries at least one citation.
- [ ] `tests/test_action_sets.py::test_complete` fails if any (family, action) pair is unclassified, and passes on the committed file.
- [ ] `tests/test_action_sets.py::test_catalog_ids` fails if any action ID is not in `action_catalog.yaml`.
- [ ] Git tag `action-sets-v1.0`, referenced from METHODS.md.

**Checklist**
- [ ] Load the catalog and the families.
- [ ] Classify the actions family by family, with citations.
- [ ] Classify the actions for `benign`.
- [ ] Write the two tests.
- [ ] Tag the commit and reference it in METHODS.md.

**Deliverables**
`knowledge/action_sets.yaml`, `tests/test_action_sets.py`

**Risks / gotchas**
- Sets that are too permissive make every recommendation "appropriate" and erase the H3 signal.
- Classifying with a particular agent behaviour in mind is the bias this rule exists to prevent. No agent output on corpus bundles exists yet; keep it that way.

**Open questions**
"How should contextual safety be scored?" (§10). This ticket applies the answer frozen in E0-12.

**Traceability**
R-018, R-246, R-247 · Record §3.1, §3.4 · Proposal: Methodology (acceptable and unsafe sets), H3

---

**[E1-04] Write ADR-003 on the attack generation method per family**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** research, engineering
**Depends on:** E1-02, E0-14 · **Blocks:** E1-08, E1-09, E1-10, E1-11, E1-12, E1-13

**Context**
§5 rules out custom attack code: attacks are generated by replaying published datasets or by standard tooling. Fixing the method per family makes the scenarios citable and reproducible, and gives the ethics section its facts.

**Goal**
ADR-003 is Accepted and fixes, for each of the six families, a generation method, its source and its parameters.

**Scope**
- In: the method per family, the source dataset or tool with version and licence, fixed parameters, the target device, the expected sources, an ethics paragraph.
- Out: implementing the families (E1-08 to E1-13), any custom exploit code, any target outside the testbed.

**Technical notes**
- Replay published datasets or use standard tooling; no custom attack code (§5).
- Replayed traffic must be retargeted to testbed device IDs, so the §4.1 device keying works.
- The ADR names the target device per family, because visibility depends on it (see E1-02).
- No new technology without recording it in an ADR (DoD).

**Acceptance criteria**
- [ ] `docs/adr/0003-attack-generation.md` has status Accepted.
- [ ] For each family it states: method, source dataset or tool with version, licence, fixed parameters, target device, and expected sources matching `attack_families.yaml`.
- [ ] It states that no family uses custom exploit code.
- [ ] It contains an ethics paragraph (isolated testbed, no third-party targets, no personal data), and the same paragraph is appended to `docs/thesis_notes.md` for E11-06.

**Checklist**
- [ ] Choose a method per family.
- [ ] Check licences.
- [ ] Fix the parameters and the target device.
- [ ] Check that the expected sources match E1-02.
- [ ] Write the ethics paragraph.
- [ ] Mark the ADR Accepted.

**Deliverables**
`docs/adr/0003-attack-generation.md`, an entry in `docs/thesis_notes.md`

**Risks / gotchas**
- Replayed captures carry their original IPs and timings. Without retargeting, flows key to devices that do not exist.
- A dataset's licence may forbid redistribution of derived captures. Check before deciding what the dataset card can include.

**Open questions**
None

**Traceability**
R-058, R-065, R-066, R-313 · Record §4.1, §5 · Proposal: Methodology

---

**[E1-05] Add benign traffic profiles to the MQTT emulators**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 3 · **Labels:** engineering, infra
**Depends on:** E0-07 · **Blocks:** E1-15, E4-04

**Context**
If benign traffic is perfectly regular, every anomaly is trivially detectable and precision is meaningless. Benign windows must contain the harmless irregularities a real network has, so detection results are worth reporting. It supports the detection metrics of H1 and H4.

**Goal**
Each emulator follows a seeded, documented benign profile that includes harmless irregularities at configured rates.

**Scope**
- In: one profile per emulator (publish period, payload size range, topic set, QoS mix), benign irregularities (reconnects, bursts, occasional wrong passwords), seeding, a YAML parameter file.
- Out: attack traffic (E1-08 to E1-13), the MQTT detector thresholds (E4-04), physical devices.

**Technical notes**
- Benign and malicious bundles must have identical structure (§4.1).
- ASSUMPTION: benign wrong-password attempts happen at a low configured rate, so a single auth failure is not a perfect attack signal.
- The profile file is cited by the dataset card (E2-08).

**Acceptance criteria**
- Given the same seed, when two 10-minute benign runs are made, then the per-emulator message sequences (topic, size, timestamp offset) are identical.
- Given a 30-minute benign run, when the MQTT log is counted, then each irregularity type appears at its configured rate within ±25 %. The tolerance is stated in the profile file.
- [ ] `testbed/profiles/benign.yaml` lists every profile parameter, with a comment per parameter.
- [ ] `tests/test_benign_profiles.py` contains the seed test.

**Checklist**
- [ ] Define the profile schema.
- [ ] Implement seeded publishing.
- [ ] Add the three irregularity types.
- [ ] Write the YAML.
- [ ] Run 30 minutes and count.
- [ ] Write the tests.

**Deliverables**
`testbed/profiles/benign.yaml`, emulator changes in `testbed/emulator/`, `tests/test_benign_profiles.py`

**Risks / gotchas**
- Container start-up jitter breaks timestamp-offset equality. Compare offsets from each emulator's first message, not absolute times.
- Benign wrong passwords that look exactly like the brute-force family make classification impossible rather than realistic. Keep the rate low.

**Open questions**
None

**Traceability**
R-057 · Record §4.1 · Proposal: Methodology (normal activity)

---

**[E1-06] Define the scenario schedule format and its validator**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E1-02, E0-02 · **Blocks:** E1-07, E2-03

**Context**
The schedule is the source of ground truth (record §4.1). Its format and validator must make wrong labels impossible: an overlapping attack on one device would give a window two true labels (risk #1).

**Goal**
Every schedule that passes validation has unambiguous labels for every (device, window).

**Scope**
- In: a Pydantic `Schedule` model with episodes and benign periods, the overlap rule, the family-enum check, tests, an example schedule.
- Out: executing schedules (E1-07), generating the corpus schedule (E2-03), labelling windows (E2-04).

**Technical notes**
- Attack episodes never overlap on the same device (§4.1).
- Episode fields: id, family, target device, start offset, duration, parameters, seed.
- Family values come from the E1-02 enum.

**Acceptance criteria**
- Given two attack episodes on the same device whose time ranges overlap, when the schedule is validated, then a validation error names both episode IDs.
- Given an episode whose family is not in the enum, when the schedule is validated, then a validation error names the family.
- Given `schedules/example.yaml` with one episode per family, when it is validated, then no error is raised.
- [ ] `thesis/scenario/schedule.py` defines `Schedule` and `Episode`.
- [ ] `tests/test_schedule.py` contains the three cases above.

**Checklist**
- [ ] Write the models.
- [ ] Write the overlap validator.
- [ ] Add the enum check.
- [ ] Write the example schedule.
- [ ] Write the tests.

**Deliverables**
`thesis/scenario/schedule.py`, `schedules/example.yaml`, `tests/test_schedule.py`

**Risks / gotchas**
- Two episodes that touch end-to-start are adjacent, not overlapping. Decide whether the end is inclusive and test the boundary.
- Overlap on different devices is allowed and must not be rejected.

**Open questions**
None

**Traceability**
R-068 · Record §4.1 · Proposal: Methodology (ground truth)

---

**[E1-07] Build the scenario runner**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 5 · **Labels:** engineering, infra
**Depends on:** E1-01, E1-06, E0-07 · **Blocks:** E1-08, E1-09, E1-10, E1-11, E1-12, E1-13, E2-04, E2-05

**Context**
The runner turns a validated schedule into raw telemetry plus a record of what actually happened. That record, not the plan, is what labels are derived from. It produces Objective 1's labelled scenarios.

**Goal**
One command executes a schedule end to end and leaves a run folder with raw logs, a schedule copy and an execution log that records actual episode times.

**Scope**
- In: `run_scenario(schedule)`, the isolation gate call, starting and stopping episodes at their offsets, the execution log, the run folder, invalid-run marking.
- Out: the attack implementations (E1-08 to E1-13), labelling (E2-04), parallel runs, resuming a failed run.

**Technical notes**
- Every attack is executed deliberately, so its label is known (proposal Methodology).
- Raw telemetry is stored as files (§6.7).
- ASSUMPTION: labels use the executed start and end times, not the planned ones, so container start-up delay cannot shift labels.
- Attack families are plugged in through one interface, so E1-08 to E1-13 only add a class each.

**Acceptance criteria**
- Given a valid schedule with two episodes, when `python -m thesis.scenario.run schedules/example_two.yaml` runs, then `data/raw/<run_id>/` contains the raw logs, `schedule.yaml` and `execution_log.jsonl`.
- Given a completed run, when `execution_log.jsonl` is read, then each episode has planned start, planned end, actual start (UTC), actual end (UTC), exit status and seed.
- Given an episode whose attack exits non-zero, when the run ends, then `execution_log.jsonl` marks the run `invalid` and the CLI exits non-zero.
- Given the isolation check fails, when the runner starts, then no episode starts (inherits E1-01).
- [ ] `thesis/scenario/runner.py` defines `run_scenario()` and an `AttackFamily` interface.

**Checklist**
- [ ] Define the `AttackFamily` interface.
- [ ] Write the run-folder layout.
- [ ] Call the isolation gate.
- [ ] Start the testbed.
- [ ] Schedule the episodes.
- [ ] Record actual times.
- [ ] Mark invalid runs.
- [ ] Write the CLI.
- [ ] Add a two-episode integration test, marked `slow`.

**Deliverables**
`thesis/scenario/runner.py`, `thesis/scenario/run.py` (CLI), `schedules/example_two.yaml`, `tests/test_runner.py`

**Risks / gotchas**
- Clock skew between containers. All timestamps must come from one clock, the runner's UTC clock or the host clock, never a container's.
- An attack container that keeps running past its end time silently extends the episode beyond the recorded end.

**Open questions**
None

**Traceability**
R-015, R-023, R-053, R-067 · Record §4.1, §6.7 · Proposal: Methodology, Objective 1

---

**[E1-08] Implement attack family F1 (provisional: MQTT message flood)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F1 is one of the six labelled families the whole evaluation is measured on. Its predicted visibility is MQTT and flows, so it occupies a "two-source" slot in H1's stratification.

**Goal**
A schedule entry for F1 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: tuning parameters beyond ADR-003, detecting the attack (EPIC-4), any target outside the testbed.

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5: no custom attack code).
- Expected sources: MQTT and flows (§3.2, provisional until E1-02).

**Acceptance criteria**
- Given a schedule with one 5-minute F1 episode, when `run_scenario` runs, then the execution log shows status OK and both the MQTT and flows files contain events inside the episode window.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f1.py` exists.
- [ ] `tests/attack_tolerance.yaml` contains the F1 tolerance.
- [ ] `docs/families/F1.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F1.
- [ ] Write the class.
- [ ] Run once and inspect the sources.
- [ ] Run twice with the same seed and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f1.py`, `tests/attack_tolerance.yaml`, `docs/families/F1.md`

**Risks / gotchas**
- A flood strong enough to crash the broker stops the MQTT log mid-episode and leaves fewer traces than expected.
- The family's title and slot change if E1-02 selects a different family.

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.2, §5 · Proposal: Methodology

---

**[E1-09] Implement attack family F2 (provisional: MQTT broker password guessing)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F2 is the provisional "three-source" family: MQTT, flows and honeypot. Without at least one family visible everywhere, H1 cannot show what full fusion adds.

**Goal**
A schedule entry for F2 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: tuning parameters beyond ADR-003, detecting the attack (EPIC-4), any target outside the testbed.

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5).
- Expected sources: MQTT, flows and honeypot (§3.2, provisional).

**Acceptance criteria**
- Given a schedule with one 5-minute F2 episode, when `run_scenario` runs, then the execution log shows status OK and the MQTT, flows and honeypot files all contain events inside the episode window.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the F2 tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f2.py` exists.
- [ ] `docs/families/F2.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F2.
- [ ] Write the class.
- [ ] Run once and inspect all three sources.
- [ ] Run twice and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f2.py`, F2 entry in `tests/attack_tolerance.yaml`, `docs/families/F2.md`

**Risks / gotchas**
- Honeypot visibility only exists if the honeypot exposes an MQTT listener and the attack also hits it. Otherwise this family is two-source and the matrix is wrong.
- Benign wrong passwords from E1-05 overlap with this signal by design. That is expected.

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.2, §5 · Proposal: Methodology

---

**[E1-10] Implement attack family F3 (provisional: port scan)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F3 covers the proposal's "scanning" attack type and is a provisional two-source family (flows and honeypot). It is also the reference case for contextual safety: isolating a critical device because of a single scan is permitted but unsafe.

**Goal**
A schedule entry for F3 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: tuning parameters beyond ADR-003, detecting the attack (EPIC-4), any target outside the testbed.

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5).
- Expected sources: flows and honeypot (§3.2, provisional).

**Acceptance criteria**
- Given a schedule with one 5-minute F3 episode, when `run_scenario` runs, then the execution log shows status OK and the flows and honeypot files contain events inside the episode window.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the F3 tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f3.py` exists.
- [ ] `docs/families/F3.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F3.
- [ ] Write the class.
- [ ] Run once and inspect the sources.
- [ ] Run twice and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f3.py`, F3 entry in `tests/attack_tolerance.yaml`, `docs/families/F3.md`

**Risks / gotchas**
- A scan that does not include the honeypot's address leaves no honeypot trace, so the target range must include the honeypot.
- A very fast scan finishes in one window; a slow one spans many. Fix the rate in ADR-003.

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.1, §3.2, §5 · Proposal: Methodology

---

**[E1-11] Implement attack family F4 (provisional: SSH password guessing)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F4 covers the proposal's "brute-force login" attack type and is the same scenario as the walking-skeleton spike, so it links spike findings to real data. It is a provisional two-source family (flows and honeypot).

**Goal**
A schedule entry for F4 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: tuning parameters beyond ADR-003, detecting the attack (EPIC-4), any target outside the testbed.

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5).
- Expected sources: flows and honeypot (§3.2, provisional; §9 spike scenario).

**Acceptance criteria**
- Given a schedule with one 5-minute F4 episode, when `run_scenario` runs, then the execution log shows status OK, the flows file contains SSH connections inside the window, and the honeypot log contains authentication attempts inside the window.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the F4 tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f4.py` exists.
- [ ] `docs/families/F4.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F4.
- [ ] Write the class.
- [ ] Run once and inspect the sources.
- [ ] Run twice and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f4.py`, F4 entry in `tests/attack_tolerance.yaml`, `docs/families/F4.md`

**Risks / gotchas**
- If the SSH target is an IoT device rather than the honeypot, the honeypot sees nothing and the family becomes one-source. The target must be the honeypot.
- Typed commands after a successful login feed the honeypot exemplars and the prompt-injection channel (risk #7).

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.2, §5, §9 · Proposal: Methodology

---

**[E1-12] Implement attack family F5 (provisional: botnet traffic)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F5 covers the proposal's "botnet traffic" attack type and is a provisional two-source family (MQTT and flows). Botnet traffic is central to Bot-IoT and TON_IoT, the datasets the proposal cites.

**Goal**
A schedule entry for F5 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: a working command-and-control server, any outbound connection beyond the testbed, detecting the attack (EPIC-4).

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5).
- Expected sources: MQTT and flows (§3.2, provisional).
- The "command server" is an emulated endpoint inside the isolated network (§6.11).

**Acceptance criteria**
- Given a schedule with one 5-minute F5 episode, when `run_scenario` runs, then the execution log shows status OK and the MQTT and flows files contain events inside the episode window.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the F5 tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f5.py` exists.
- [ ] `docs/families/F5.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F5.
- [ ] Write the class and the emulated command endpoint.
- [ ] Run once and inspect the sources.
- [ ] Run twice and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f5.py`, F5 entry in `tests/attack_tolerance.yaml`, `docs/families/F5.md`

**Risks / gotchas**
- MQTT visibility needs the botnet traffic to use the MQTT broker. A replayed capture that uses another protocol makes this a one-source family.
- Replayed botnet captures can be large. Trim to the episode length in ADR-003.

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.2, §5, §6.11 · Proposal: Methodology

---

**[E1-13] Implement attack family F6 (provisional: denial of service)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E1-04, E1-07 · **Blocks:** E1-14

**Context**
F6 covers the proposal's "denial of service" attack type and is the provisional one-source family (flows only). One-source families are what let H1 separate "gain from fusion" from "gain from having a source at all" (risk #4).

**Goal**
A schedule entry for F6 produces the attack against its ADR-003 target with no manual step, reproducibly.

**Scope**
- In: one `AttackFamily` class using the ADR-003 method and parameters, a repeatability test, a visibility note.
- Out: tuning parameters beyond ADR-003, detecting the attack (EPIC-4), any target outside the testbed.

**Technical notes**
- Method, parameters and target come only from ADR-003 (§5).
- Expected sources: flows only (§3.2, provisional).

**Acceptance criteria**
- Given a schedule with one 5-minute F6 episode, when `run_scenario` runs, then the execution log shows status OK, the flows file contains events inside the window, and neither the MQTT nor the honeypot file contains events attributable to the attacker.
- Given two runs with the same seed, when raw event counts per source are compared, then they differ by no more than the F6 tolerance in `tests/attack_tolerance.yaml`.
- [ ] `thesis/scenario/families/f6.py` exists.
- [ ] `docs/families/F6.md` records which sources received traces.

**Checklist**
- [ ] Read ADR-003 for F6.
- [ ] Write the class.
- [ ] Run once and inspect all three sources.
- [ ] Run twice and set the tolerance.
- [ ] Write the note.

**Deliverables**
`thesis/scenario/families/f6.py`, F6 entry in `tests/attack_tolerance.yaml`, `docs/families/F6.md`

**Risks / gotchas**
- A DoS against the broker or the honeypot makes it multi-source. The target must be a non-MQTT service on a non-honeypot device.
- A flood can saturate the capture sidecar and drop flow records. Record the drop count if the exporter reports one.

**Open questions**
"Which six attack families?" (§10). Answered by E1-02.

**Traceability**
R-057, R-062 · Record §3.2, §5 · Proposal: Methodology

---

**[E1-14] Verify the source-visibility matrix against real captures**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 2 · **Labels:** testing, research
**Depends on:** E1-08, E1-09, E1-10, E1-11, E1-12, E1-13 · **Blocks:** E1-15, E2-07

**Context**
The E1-02 matrix is a prediction. H1's stratification depends on what each source actually captures, so the prediction must be checked before the corpus is generated (risk #4).

**Goal**
The visibility matrix in `attack_families.yaml` matches the observed captures, and still satisfies the stratification rule.

**Scope**
- In: one run per family, trace counts per source, a predicted-vs-observed table, resolving mismatches.
- Out: detection quality (EPIC-4), repeatability (E1-15).

**Technical notes**
- The stratification rule comes from E1-02.
- A changed matrix is a METHODS.md changelog entry (DoD change control).

**Acceptance criteria**
- [ ] `docs/families/visibility_check.md` contains a six-family table with predicted and observed visibility per source, plus the trace counts.
- [ ] Every mismatch row states how it was resolved: setup fixed, or matrix updated.
- [ ] Every matrix update has a METHODS.md changelog entry.
- [ ] `tests/test_families.py::test_stratification` passes on the final matrix.

**Checklist**
- [ ] Run each family once.
- [ ] Count traces per source.
- [ ] Build the comparison table.
- [ ] Resolve each mismatch.
- [ ] Update the matrix and the changelog.
- [ ] Re-run the stratification test.

**Deliverables**
`docs/families/visibility_check.md`, updated `knowledge/attack_families.yaml`, METHODS.md changelog entries

**Risks / gotchas**
- A source with a handful of traces counts as "visible" but may be too weak to help. Record counts, not only yes or no.

**Open questions**
None

**Traceability**
R-064 · Record §3.2 · Proposal: H1

---

**[E1-15] Run a pilot schedule end to end and check repeatability**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 3 · **Labels:** testing, infra
**Depends on:** E1-14, E1-05 · **Blocks:** E2-05, E3-01, E3-02, E3-03, E3-04

**Context**
Before the expensive corpus run, a short mixed schedule run twice proves the testbed is reproducible. The pilot capture also lets the EPIC-3 normalizers be built before the gate (C-19), and checks the 16 GB memory budget.

**Goal**
Two runs of the same mixed pilot schedule produce event counts within tolerance, and the pilot capture is stored and marked as never used for evaluation.

**Scope**
- In: a 20–30 minute schedule with every family and benign periods, two runs from reset, a repeatability report, the pilot folder, a memory measurement.
- Out: the corpus run (E2-05), labelling (E2-04), any metric computed on pilot data.

**Technical notes**
- Do not run Ollama and the testbed together on 16 GB (§4.2).
- Tolerances come from `tests/attack_tolerance.yaml`.
- ASSUMPTION: pilot data may be used to develop normalizers but never to tune detectors or report results.

**Acceptance criteria**
- Given the pilot schedule, when it runs twice from `make reset`, then both runs are marked valid in their execution logs.
- Given the two runs, when per-source and per-episode event counts are compared, then every difference is within its family's tolerance.
- [ ] `docs/pilot/repeatability.md` contains the comparison table.
- [ ] `data/pilot/` holds both runs, and `data/pilot/README.md` states "NOT FOR EVALUATION".
- [ ] `docs/pilot/repeatability.md` records the testbed's peak memory with Ollama stopped.

**Checklist**
- [ ] Write the pilot schedule.
- [ ] Stop Ollama.
- [ ] Run it twice from reset.
- [ ] Compare the counts.
- [ ] Record memory.
- [ ] Store the pilot data with its README.

**Deliverables**
`schedules/pilot.yaml`, `data/pilot/`, `data/pilot/README.md`, `docs/pilot/repeatability.md`

**Risks / gotchas**
- Pilot data leaking into detector tuning or evaluation would contaminate results. The README label is the guard.
- A repeatability failure here is cheap; the same failure after the corpus run costs weeks.

**Open questions**
None

**Traceability**
R-053, R-054, R-072, R-128, R-147 · Record §4.2, §6.2, §7.1 · Proposal: Methodology

---
**[E1-16] Capture all testbed traffic for the flow source**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** High · **Points:** 3 · **Labels:** engineering, infra
**Depends on:** E1-04 · **Blocks:** E1-08, E1-09, E1-10, E1-11, E1-12, E1-13, E1-14

Added 2026-10-06 as the leftover work ADR-0003 (E1-04) names: "the mechanism is settled in an ADR-0008 amendment before any attack traffic is captured (leftover work, new ticket per DoD)". Jira SCRUM-129.

**Context**
ADR-0003 decided that flow capture observes all traffic on the testbed network. Today tcpdump runs in the broker's namespace only (ADR-0008, METHODS.md Annex F ASSUMPTION 3), so traffic to the honeypot, between devices and from a device to an external address is never captured, while the frozen visibility matrix predicts flows for every family.

**Goal**
The flow source sees every packet sent on the testbed network exactly once, without weakening the isolation check.

**Scope**
- In: an ADR choosing the capture mechanism (amending ADR-0008), the capture change in `docker-compose.yml`, `testbed/capture/` and the Makefile, a METHODS.md changelog entry superseding Annex F ASSUMPTION 3, a test.
- Out: the attack families (E1-08 to E1-13), the attacker container (first family ticket that needs it), NFStream settings (ADR-0002), detectors.

**Technical notes**
- Options for the ADR: one egress-only tcpdump sidecar per host merged into one pcap; a routing capture container; capture on the Docker host's bridge (fails the isolation check).
- Every packet must appear once, and both directions of a flow must reach NFStream in one file.
- Timestamps must come from one clock (the Docker VM kernel).

**Acceptance criteria**
- Given a benign run, when the merged pcap is read, then no packet appears twice (same timestamp, endpoints and bytes).
- Given a packet sent from one emulator to the honeypot, when the run ends, then `flows.jsonl` holds a flow between them.
- Given the testbed is up, when the isolation check runs, then it passes.
- [ ] An ADR in `docs/adr/` records the mechanism and is accepted.
- [ ] METHODS.md has a changelog entry superseding Annex F ASSUMPTION 3.

**Checklist**
- [ ] Write the ADR.
- [ ] Change the capture services and `make down`.
- [ ] Write the tests.
- [ ] Run a benign run and the isolation check.
- [ ] Append the METHODS.md entry.

**Deliverables**
`docs/adr/0009-whole-network-flow-capture.md`, `docker-compose.yml`, `testbed/capture/`, `Makefile`, `tests/test_capture.py`

**Risks / gotchas**
- A capture point that misses one direction of a flow silently changes NFStream's features.
- More capture containers use memory; keep the 16 GB budget (record §4.2).

**Open questions**
None. The capture point is decided by ADR-0003; this ticket chooses only the mechanism.

**Traceability**
R-057, R-064 · Record §3.2, §6.7, §6.11 · ADR-0003, ADR-0008 · Proposal: H1

---
**[E1-17] Re-run the pilot with all six families (add F5)**
**Type:** Task · **Epic:** EPIC-1 · **Priority:** Medium · **Points:** 1 · **Labels:** testing, infra
**Depends on:** E1-12, E1-15 · **Blocks:** —

Added 2026-10-10 as leftover work from E1-12 (DoD: leftover work becomes a new ticket). Jira SCRUM-130.

**Context**
F5 (botnet) is implemented and verified standalone (E1-12), but the pilot (E1-15, `schedules/pilot.yaml`, `docs/pilot/repeatability.md`) still covers only five families. A one-run 6-family pilot already passed (all six episodes exit 0, run `20261010T090507Z`); the two-run repeatability re-run was blocked when the host moved onto an iPhone hotspot (172.20.10.0/24), which the isolation-gate control cannot reach from Docker, so run 2 was correctly aborted.

**Goal**
`schedules/pilot.yaml` includes an F5 episode, and `docs/pilot/repeatability.md` reports two reproducible runs across all six families, with peak memory.

**Scope**
- In: add an F5 episode to `schedules/pilot.yaml` (iot-cam-01, ~90 s), run the pilot twice from `make reset` on a stable network, update `docs/pilot/repeatability.md`.
- Out: any change to the families themselves (E1-08 to E1-13), the corpus run (E2-05).

**Acceptance criteria**
- [ ] `schedules/pilot.yaml` has an F5 episode and no same-device overlaps.
- [ ] `docs/pilot/repeatability.md`'s table includes F5, both runs valid, all counts within tolerance.

**Technical notes**
- Run on a stable Wi-Fi (not an iPhone hotspot), or the isolation-gate control probe cannot reach the LAN gateway and the run aborts. `caffeinate -is`, Ollama stopped.

**Risks / gotchas**
- The hotspot-gateway-unreachable abort is an environment issue, not a testbed fault.

**Open questions**
None.

**Traceability**
R-053, R-054 · Record §4.2 · Proposal: Methodology


# Step D — EPIC-2 · Ground Truth & Labelled Corpus

9 tickets · 23 points · Project DoD v1.0 and DoR apply to every ticket.

**Suggested execution order:** E2-01 → E2-02 → E2-03 ∥ E2-04 → E2-05 → E2-06 ∥ E2-07 → E2-08 → E2-09 (milestone)

---

**[E2-01] Decide what Baseline A trains on**
**Type:** Research · **Epic:** EPIC-2 · **Priority:** High · **Points:** 2 · **Labels:** research, freeze-before-results
**Depends on:** E1-02, E0-05 · **Blocks:** E2-02, E4-01

**Context**
Baseline A must be a properly tuned classifier, or H4 proves nothing (record §6.6). Training it on the evaluation corpus leaks labels into the test. Training it elsewhere adds domain shift. The choice changes how many bundles the corpus needs, so it must come before the power calculation. This ticket also resolves C-14: the proposal says Baseline A is "trained on the same telemetry".

**Goal**
METHODS.md states what Baseline A trains on, how training and evaluation data are separated, and how that affects corpus size.

**Scope**
- In: the options, the decision, the split unit and proportion, consistency with Baseline A's input view (E0-05).
- Out: training the model (E4-02), feature engineering (E4-01), choosing the classifier library (fixed in §6.2).

**Technical notes**
- Option (a): train on a testbed split. This matches the proposal's wording.
- Option (b): train on a published dataset from [6]–[9]. This adds domain shift and contradicts "the same telemetry" (C-14).
- Under option (a), the split unit is the attack episode, so no episode appears in both training and evaluation. Splitting by bundle would leak, because bundles from one episode are not independent (§4.1).
- Baseline A sees the same reduced view as the agent (§4.1, E0-05).

**Acceptance criteria**
- [ ] A dated METHODS.md changelog entry names the chosen option and the reason.
- [ ] If option (a): the entry states the split unit (episode), the training share as a percentage, and that the split is fixed by seed before generation.
- [ ] If option (b): the entry names the dataset and the feature mapping from it to the reduced view, and states the domain-shift limitation for E11-09.
- [ ] The entry states the number of extra bundles needed for training, to be fed into E2-02.

**Checklist**
- [ ] Write out both options with their effect on H4.
- [ ] Decide.
- [ ] Fix the split unit and share, or the dataset mapping.
- [ ] Compute the extra bundles needed.
- [ ] Write the changelog entry.

**Deliverables**
`METHODS.md` changelog entry

**Risks / gotchas**
- A bundle-level random split puts half of an episode in training and half in evaluation, and Baseline A then looks better than it is.
- Under option (a), the training share makes the corpus bigger, so check the wall-clock time in E2-03.

**Open questions**
None

**Traceability**
R-225, R-231, R-232 · Record §4.1, §6.6 · Proposal: Methodology (Baseline A)

---

**[E2-02] Run the power calculation and fix target N**
**Type:** Research · **Epic:** EPIC-2 · **Priority:** Highest · **Points:** 3 · **Labels:** research, freeze-before-results
**Depends on:** E0-01, E0-03, E0-06, E1-02, E2-01 · **Blocks:** E2-03, E2-09

**Context**
Every hypothesis says "significantly", but no N has been fixed (risk #2). If N is chosen after seeing data, the corpus is sized by convenience. The power calculation must run before generation, and it must account for bundles from one episode not being independent.

**Goal**
METHODS.md v1.1 fixes the number of bundles per family and benign, justified by a power calculation that accounts for clustering, and ADR-001's cost is recomputed with it.

**Scope**
- In: assumed effect sizes with their sources, McNemar power for H2 and H4, the per-family minimum for stratified H1, a clustering adjustment, the training share from E2-01, the ADR-001 cost update.
- Out: generating the schedule (E2-03), any simulation of agent behaviour on real data.

**Technical notes**
- Target range 200–400 bundles and k = 3–5 are the record's starting points (§3, risk #2). k is fixed in E0-03.
- McNemar for paired binary outcomes, Wilcoxon signed-rank for paired scores (§10).
- Attack episode is the resampling unit (§4.1).
- ASSUMPTION: α = 0.05 and power = 0.8.
- ASSUMPTION: effect sizes come from spike correctness rates and published baselines, and both sources are stated.

**Acceptance criteria**
- [ ] `docs/power/power_calculation.md` (or a notebook exported to it) states every assumed effect size with its source, α, power, the test used and the resulting N.
- [ ] The document states the minimum number of positive bundles per family for stratified H1.
- [ ] The document states the expected bundles per episode and the adjustment applied for clustering.
- [ ] METHODS.md v1.1 contains the final counts per family, benign and training split, and is tagged `methods-v1.1`.
- [ ] ADR-001's cost table is recomputed with the final N and k, and the total is still €100 or less. If it is not, the ADR records the decision taken.

**Checklist**
- [ ] Collect the effect-size inputs.
- [ ] Compute N for H2 and H4.
- [ ] Compute the per-family minimum for H1.
- [ ] Apply the clustering adjustment.
- [ ] Add the training share.
- [ ] Write METHODS.md v1.1.
- [ ] Update ADR-001.

**Deliverables**
`docs/power/power_calculation.md`, `METHODS.md` v1.1, updated `docs/adr/0001-llm-serving.md`

**Risks / gotchas**
- Effect sizes guessed optimistically give an N that is too small to detect anything. Prefer the conservative input when two sources disagree.
- A large N can push cost past €100 or wall-clock time past the sprint. Check both before tagging.

**Open questions**
"How many scenarios are needed for statistical validity?" (§10)

**Traceability**
R-076, R-078, R-079, R-080 · Record §3 (risk #2), §4.1, §4.4.1, §10 · Proposal: Methodology (paired tests)

---

**[E2-03] Generate the corpus schedule for the target N**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** High · **Points:** 3 · **Labels:** engineering, research
**Depends on:** E2-02, E1-06 · **Blocks:** E2-05

**Context**
A schedule edited by hand is where hidden bias enters the corpus. A seeded script turns the frozen target N into a schedule that anyone can regenerate. The schedule is the ground truth (record §4.1).

**Goal**
A seeded script produces one validated corpus schedule whose expected bundle counts meet every E2-02 target.

**Scope**
- In: the generator script, the seed, per-family and benign counts, varied episode durations, device assignment, the train and evaluation split from E2-01, an expected-count report, a wall-clock estimate.
- Out: running the schedule (E2-05), changing the targets (that is E2-02).

**Technical notes**
- Attack episodes never overlap on the same device (§4.1). The E1-06 validator enforces this.
- Expected bundle counts follow 60-second tiling per device (§4.1).
- ASSUMPTION: episode durations vary within each family, so episode length is not a trivial cue for classification.

**Acceptance criteria**
- Given the seed in `schedules/corpus.seed`, when `python -m thesis.scenario.generate` runs twice, then both output files are byte-identical.
- Given the generated `schedules/corpus-v1.0.0.yaml`, when it is validated with E1-06, then no error is raised.
- [ ] `docs/corpus/expected_counts.md` shows expected bundles per family, benign and split, each greater than or equal to its E2-02 target.
- [ ] `docs/corpus/expected_counts.md` states the total wall-clock duration of the schedule.
- [ ] If E2-01 chose option (a), every episode carries a `split` field of `train` or `eval`.

**Checklist**
- [ ] Write the generator.
- [ ] Assign families, devices and durations.
- [ ] Add benign periods.
- [ ] Apply the split.
- [ ] Compute expected counts and wall-clock time.
- [ ] Validate the result.
- [ ] Commit the seed and schedule.

**Deliverables**
`thesis/scenario/generate.py`, `schedules/corpus.seed`, `schedules/corpus-v1.0.0.yaml`, `docs/corpus/expected_counts.md`

**Risks / gotchas**
- Expected counts assume every window has alerts. Empty windows are dropped (§4.1), so benign counts can come in lower than planned. Add margin.
- Long wall-clock time competes with other work on the same machine. Plan the run for a night.

**Open questions**
None

**Traceability**
R-068, R-074, R-076, R-079 · Record §4.1 · Proposal: Methodology (ground truth)

---

**[E2-04] Derive window labels mechanically from the execution log**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E1-07 · **Blocks:** E2-05, E2-07, E3-05

**Context**
Ground truth must come only from the executed schedule, never from a human label (record §4.1). Any off-by-one at an episode boundary would silently mislabel bundles and corrupt every metric (risk #1).

**Goal**
A pure function turns an execution log into one label per (device, window), with no manual edit possible.

**Scope**
- In: `label_windows()`, the overlap rule, episode IDs per window, boundary tests, the W parameter read from config.
- Out: assembling bundles (E3-05), dropping empty windows (E3-05, after normalization), any manual relabelling path.

**Technical notes**
- Label = family F if the window overlaps an executed episode of F against device D, otherwise benign (§4.1).
- W = 60 seconds, read from the METHODS.md parameter file, not hardcoded (§4, §4.1).
- Executed times, not planned times (E1-07 ASSUMPTION).
- Each window keeps its episode ID, which the block bootstrap needs (§4.1).

**Acceptance criteria**
- Given an episode fully inside one window, when `label_windows()` runs, then that window has the episode's family and ID, and its neighbours are benign.
- Given an episode that starts in the last second of a window, when `label_windows()` runs, then that window carries the family.
- Given two adjacent, non-overlapping episodes on the same device, when `label_windows()` runs, then each window has exactly one label.
- Given a device with no episode, when `label_windows()` runs, then all its windows are benign.
- [ ] `thesis/labels/windows.py` defines `label_windows()` and writes `data/labels/<run_id>.parquet` with columns device, window_start, label, episode_id.
- [ ] The module has no function that accepts a label as input.

**Checklist**
- [ ] Write the function.
- [ ] Read W from config.
- [ ] Write the four boundary tests.
- [ ] Write Parquet output.
- [ ] Check the module offers no manual-edit path.

**Deliverables**
`thesis/labels/windows.py`, `tests/test_label_windows.py`, `data/labels/` layout

**Risks / gotchas**
- Mixing inclusive and exclusive window ends shifts labels by one window at every boundary. Use half-open intervals and test both ends.
- Timezone-naive timestamps compared with UTC ones give a silent offset. Use UTC everywhere.

**Open questions**
None

**Traceability**
R-018, R-074, R-075, R-087 · Record §4, §4.1 · Proposal: Methodology (ground truth), Objective 4

---

**[E2-05] Execute the corpus generation run**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** Highest · **Points:** 3 · **Labels:** infra, research
**Depends on:** E2-03, E2-04, E1-15 · **Blocks:** E2-06, E2-07

**Context**
This is the one expensive run whose output everything is measured on. It is bound by wall-clock time, not effort. A failure here that goes unnoticed costs weeks later.

**Goal**
Every episode in the corpus schedule has executed with status OK, and its raw telemetry and labels are on disk.

**Scope**
- In: running the schedule in chunks, the isolation check per chunk, re-running failed chunks from reset, producing labels with E2-04.
- Out: the manifest (E2-06), integrity checks (E2-07), any change to the schedule.

**Technical notes**
- Never run Ollama and the testbed together on 16 GB (§4.2).
- Generate the corpus, then shut the testbed down (§4.2).
- The isolation check gates every chunk (E1-01).
- ASSUMPTION: the schedule may be split into chunks, each started from `make reset` with its own run ID.

**Acceptance criteria**
- Given the corpus schedule, when all chunks have run, then every chunk's execution log is marked valid and the episode IDs across chunks equal the scheduled episode IDs.
- Given a chunk marked invalid, when it is re-run from reset, then the new run replaces it and the invalid run is moved to `data/raw/rejected/`.
- [ ] `data/raw/corpus-v1.0.0-rc/` holds every valid chunk.
- [ ] `data/labels/` holds one label file per valid chunk.
- [ ] `docs/corpus/run_log.md` lists each chunk with start time, end time, status and peak memory, and confirms Ollama was stopped.

**Checklist**
- [ ] Stop Ollama.
- [ ] Split the schedule into chunks.
- [ ] Run each chunk.
- [ ] Re-run any failed chunk.
- [ ] Produce the labels.
- [ ] Write the run log.
- [ ] Shut the testbed down.

**Deliverables**
`data/raw/corpus-v1.0.0-rc/`, `data/labels/`, `docs/corpus/run_log.md`

**Risks / gotchas**
- The machine sleeping mid-run stops the containers and leaves a partial run that looks complete. Disable sleep, and check the execution logs, not the folder.
- Disk space. Check free space before starting.

**Open questions**
None

**Traceability**
R-015, R-072, R-073 · Record §4.2, §6.11, §7.1 · Proposal: Methodology, Objective 1

---

**[E2-06] Build the corpus manifest with SHA-256 per file**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** High · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E2-05 · **Blocks:** E2-09

**Context**
The frozen corpus must be immutable, verifiable and citable (record §6.7). A manifest with a hash per file is what lets anyone, including you in six weeks, prove the data under a result is the data that was frozen.

**Goal**
A manifest lists every raw and label file with its hash, and one command detects any changed byte.

**Scope**
- In: the manifest format, the manifest's own hash, a `verify_corpus` command, a test.
- Out: the freeze itself (E2-09), backups, uploading the corpus anywhere.

**Technical notes**
- Raw telemetry is kept as files on disk with a SHA-256 manifest (§6.7).

**Acceptance criteria**
- Given the corpus folder, when `python -m thesis.corpus.manifest build` runs, then `data/corpus-manifest.json` lists path, size and SHA-256 for every file under `data/raw/corpus-v1.0.0-rc/` and `data/labels/`.
- Given an unchanged corpus, when `python -m thesis.corpus.manifest verify` runs, then it exits 0.
- Given a copy of the corpus with one byte changed in one file, when `verify` runs on it, then it exits non-zero and names that file.
- [ ] The manifest's own SHA-256 is written to `data/corpus-manifest.sha256`.

**Checklist**
- [ ] Write the build command.
- [ ] Write the verify command.
- [ ] Write the changed-byte test on a temporary copy.
- [ ] Hash the manifest.

**Deliverables**
`thesis/corpus/manifest.py`, `data/corpus-manifest.json`, `data/corpus-manifest.sha256`, `tests/test_manifest.py`

**Risks / gotchas**
- Hidden files such as `.DS_Store` on macOS get added to the folder and fail verification. Exclude them explicitly.

**Open questions**
None

**Traceability**
R-083 · Record §6.7, §7.1 · Proposal: Methodology (reproducibility)

---

**[E2-07] Validate corpus integrity before the freeze**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** High · **Points:** 3 · **Labels:** testing, research
**Depends on:** E2-04, E2-05, E1-14 · **Blocks:** E2-08, E2-09

**Context**
This is the last chance to catch a broken corpus cheaply. A missing source for one family would silently bias H1 (risk #4). Too few bundles for one family would sink the statistics (risk #2). Any failed check means regenerating, never patching.

**Goal**
An integrity report shows that every planned episode exists with the expected source traces, and that label counts meet their targets.

**Scope**
- In: five checks, an integrity report, a pass or fail verdict that blocks the freeze.
- Out: fixing data by hand, detector quality (EPIC-4), bundle-level counts after assembly (E3-09).

**Technical notes**
- Expected visibility comes from the E1-14 matrix.
- Targets come from METHODS.md v1.1 (E2-02).
- Same-device overlap is forbidden (§4.1).

**Acceptance criteria**
- Given the corpus, when `python -m thesis.corpus.check` runs, then it writes `docs/corpus/integrity_report.md` with one pass or fail line for each of five checks:
  1. Every scheduled episode has an execution record.
  2. Every episode has traces in each source its family's matrix row predicts.
  3. Window-level label counts per family meet their METHODS.md v1.1 targets.
  4. No two executed episodes overlap on the same device.
  5. No gap in capture longer than one window inside any chunk.
- Given any failed check, when the command ends, then it exits non-zero.
- [ ] The committed `docs/corpus/integrity_report.md` shows all five checks passing.

**Checklist**
- [ ] Write the five checks.
- [ ] Write the report generator.
- [ ] Run it on the corpus.
- [ ] If a check fails, regenerate the affected chunks with E2-05 and run again.

**Deliverables**
`thesis/corpus/check.py`, `docs/corpus/integrity_report.md`

**Risks / gotchas**
- Window-level counts overestimate bundle counts, because empty windows are dropped later. E3-09 confirms the bundle-level numbers.
- The temptation to "fix" a gap by hand-editing logs. Regenerate instead.

**Open questions**
None

**Traceability**
R-064, R-068, R-253 · Record §3.2, §4.1 · Proposal: H1

---

**[E2-08] Write the dataset card**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** Medium · **Points:** 2 · **Labels:** writing, research
**Depends on:** E2-07 · **Blocks:** E2-09, E11-06

**Context**
The record requires a dataset card for the frozen corpus (record §7.1). It is the citable description of the data, and it feeds the testbed and ethics section of the thesis almost directly.

**Goal**
A dataset card describes the corpus completely enough that someone else could regenerate it.

**Scope**
- In: the dataset card with every section listed below.
- Out: thesis prose (E11-06), publishing the corpus.

**Technical notes**
- Sources: ADR-002, ADR-003, `benign.yaml`, the schedule and seed, METHODS.md v1.1, the integrity report.
- Licence limits from ADR-003 decide what the card can say about redistribution.

**Acceptance criteria**
- [ ] `docs/dataset_card.md` contains these sections, each non-empty:
  1. Purpose
  2. Composition: devices, broker, honeypot, capture
  3. Benign profiles
  4. Attack families, with generation method and licences
  5. Schedule and seed
  6. Label derivation
  7. Counts per family, benign and split
  8. Known limitations: emulated, not physical; replayed traffic; honeypot all-positive handling
  9. Version and manifest hash
- [ ] Every number in the card matches the integrity report or the manifest.

**Checklist**
- [ ] Collect the source documents.
- [ ] Write each section.
- [ ] Cross-check every number.
- [ ] Add a pointer in `docs/thesis_notes.md` for E11-06.

**Deliverables**
`docs/dataset_card.md`, an entry in `docs/thesis_notes.md`

**Risks / gotchas**
- Numbers copied by hand drift from the real files. Paste them from the integrity report output.

**Open questions**
None

**Traceability**
R-082 · Record §7.1 · Proposal: Expected Outcomes (labelled scenarios)

---

**[E2-09] Freeze corpus v1.0.0 (milestone)**
**Type:** Task · **Epic:** EPIC-2 · **Priority:** Highest · **Points:** 2 · **Labels:** research, infra, freeze-before-results
**Depends on:** E2-06, E2-07, E2-08, E0-03, E0-04, E0-05, E0-11, E0-12, E0-13, E1-02, E1-03, E2-01, E2-02 · **Blocks:** E3-05, E3-09, E4-01, E6-03

**Context**
This is the critical-path gate (record §7.1). Nothing downstream can be measured until it closes, and after it closes a format change means regenerating. It also checks that every "what counts as correct" decision was frozen before any agent output exists. This ticket resolves C-13: what kind of change forces a regeneration.

**Goal**
Corpus v1.0.0 is tagged, read-only and verifiable, and every freeze-before-results decision is closed before it.

**Scope**
- In: the pre-freeze checklist, the tag, the read-only raw folder, the change policy, the METHODS.md version record.
- Out: building bundles (E3-09), any further data generation.

**Technical notes**
- The freeze is a formal milestone with a version number and a dataset card (§7.1).
- Any raw-format change after the freeze forces full regeneration (§7.1).
- ASSUMPTION (C-13): a change to the alert schema, the reduction or W after the freeze re-runs normalization, assembly and every result, but not corpus generation. A change to the raw capture format regenerates the corpus. Confirm or reject this split.

**Acceptance criteria**
- [ ] Every ticket in "Depends on" is Done. All eight freeze-before-results tickets are in that list.
- [ ] METHODS.md records the honeypot all-positive handling.
- [ ] Git tag `corpus-v1.0.0` exists, and the manifest hash is written in METHODS.md and in the dataset card.
- [ ] `data/raw/corpus-v1.0.0-rc/` is renamed to `data/raw/corpus-v1.0.0/` and set read-only, and `verify_corpus` passes after the rename.
- [ ] METHODS.md contains a "Change policy after freeze" section with the C-13 split, and states that any raw change creates corpus v2.0.0 plus a changelog entry.
- [ ] METHODS.md records the version in force at the freeze.

**Checklist**
- [ ] Confirm every dependency is Done.
- [ ] Rename the folder and set it read-only.
- [ ] Rebuild and verify the manifest.
- [ ] Write the change policy.
- [ ] Record the hash and versions.
- [ ] Tag the commit.

**Deliverables**
Git tag `corpus-v1.0.0`, `data/raw/corpus-v1.0.0/` (read-only), updated `data/corpus-manifest.json`, `METHODS.md` sections

**Risks / gotchas**
- Renaming the folder changes the paths in the manifest. Rebuild and verify after the rename, not before.
- Closing this milestone with a freeze-before-results ticket still open would let agent outputs come first, and the H3 result would be worthless.

**Open questions**
None

**Traceability**
R-023, R-081, R-084, R-085 · Record §7, §7.1 · Proposal: Methodology (acceptable and unsafe sets fixed before any experiment)


# Step D — EPIC-3 · Telemetry Normalization & Incident Assembly

10 tickets · 28 points · Project DoD v1.0 and DoR apply to every ticket.

**Ticket-level exceptions to the locked epic order (C-15, C-19):**
- E3-01 to E3-04 may be developed on the pilot capture (E1-15) before the corpus freeze. Only their final run on the frozen corpus waits for E2-09.
- E3-06 and E3-09 depend on E4-06, because the reduction includes detector scores and ranks exemplars by them. The epic order is unchanged; only these two tickets wait.

**Rule for every ticket here:** a change to the alert schema, W or the reduction after E2-09 requires a METHODS.md changelog entry (DoD change control).

**Suggested execution order:** E3-01 ∥ E3-10 → E3-02 ∥ E3-03 ∥ E3-04 → E3-05 → (E4-06) → E3-06 → E3-07 ∥ E3-08 → E3-09

---

**[E3-01] Finalize alert schema v1 from the pilot capture**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 3 · **Labels:** engineering, research, needs-refinement
**Depends on:** E0-08, E1-15 · **Blocks:** E3-02, E3-03, E3-04

**Context**
Alert schema v0.1 was shaped by a hand-written bundle. Real pilot telemetry will show fields the spike could not predict. Every normalizer, the reduction and the detectors read this format, so it must be settled before they are built. It serves H1, since the three sources must be comparable, and risk #1.

**Goal**
Alert schema v1 represents every field the three normalizers and the reduction policy need, and is versioned.

**Scope**
- In: comparing v0.1 with the pilot logs, adding or removing fields, bumping the version, updating fixtures and the changelog.
- Out: writing the normalizers (E3-02 to E3-04), changing the device-mapping rule (§4.1 is locked), Parquet storage.

**Technical notes**
- One format downstream; no consumer needs to know the source (Arch §5).
- The device mapping stays defined once, in code (§4.1).
- Every field the reduction policy names (E0-05) must exist in v1.
- ASSUMPTION: this ticket is done before E2-09. If it is done after, it needs a METHODS.md changelog entry.

**Acceptance criteria**
- Given one pilot log line per source, when it is mapped by hand into `Alert`, then every field named in "Reduction policy v1.0" is populated or derivable. This is recorded in `docs/schema/v1_field_check.md`.
- Given the updated fixtures, when `pytest tests/test_alert_schema.py` runs, then every fixture round-trips to identical JSON.
- [ ] `SCHEMA_VERSION = "alert-v1"` in `thesis/schema/alert.py`.
- [ ] `docs/schema/CHANGELOG.md` has a v1 entry listing every field change with its reason.
- [ ] If E2-09 is already Done: a METHODS.md changelog entry exists for this change.

**Checklist**
- [ ] Sample pilot lines from each source.
- [ ] Map them against v0.1.
- [ ] Check every reduction field.
- [ ] Update the model.
- [ ] Update the fixtures.
- [ ] Write the changelog.

**Deliverables**
`thesis/schema/alert.py` (v1), `tests/fixtures/alerts/*.json`, `docs/schema/v1_field_check.md`, `docs/schema/CHANGELOG.md`

**Risks / gotchas**
- Pilot data covers each family once. Rare fields may only appear in the corpus. Keep source-specific payload fields optional, not removed.
- May change after the spike: the whole field list depends on FINDINGS.md (`needs-refinement`).

**Open questions**
None

**Traceability**
R-095, R-098, R-099 · Record §4.1, §7.1, §9 · Arch §5 · Proposal: Objective 2

---

**[E3-02] Normalize MQTT telemetry into alerts**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing, needs-refinement
**Depends on:** E3-01, E3-10 · **Blocks:** E3-05, E4-04

**Context**
MQTT anomalies are one of the three telemetry sources H1 compares. A parsing bug here would silently remove MQTT evidence from every bundle and bias H1 against fusion. The record says parsers must be tested hard (§6.9).

**Goal**
Every line of the broker log becomes one validated `Alert`, or is counted as skipped with a reason.

**Scope**
- In: a parser for the Mosquitto log format, mapping to `Alert` v1, the device mapping, a skip counter, tests on pilot-derived fixtures.
- Out: anomaly scoring (E4-04), bundling (E3-05), live streaming.

**Technical notes**
- Normalized alerts are stored as Parquet (§6.7).
- The device mapping is the one function from E0-08 (§4.1).
- Develop on `data/pilot/`. Run on the frozen corpus only after E2-09 (C-19).

**Acceptance criteria**
- Given `tests/fixtures/raw/mqtt_sample.log` with a known count of lines, when `normalize_mqtt()` runs, then the number of alerts plus the number of skipped lines equals the line count.
- Given a malformed line, when it is parsed, then it is skipped, counted, and its reason is written to the skip log. The run continues.
- Given a publish from an emulator, when it is normalized, then `subject_device` is the emulator's device ID, not the broker.
- [ ] `thesis/normalize/mqtt.py` writes `data/alerts/mqtt/<run_id>.parquet`.

**Checklist**
- [ ] Extract fixtures from the pilot.
- [ ] Write the parser.
- [ ] Map to `Alert`.
- [ ] Apply the device mapping.
- [ ] Add the skip counter.
- [ ] Write the tests.
- [ ] Run on the pilot.

**Deliverables**
`thesis/normalize/mqtt.py`, `tests/fixtures/raw/mqtt_sample.log`, `tests/test_normalize_mqtt.py`

**Risks / gotchas**
- Broker log timestamps may lack a timezone. Convert to UTC explicitly.
- Silent skipping. The count invariant in the first criterion catches it.
- May change after the spike: which MQTT fields matter depends on FINDINGS.md.

**Open questions**
None

**Traceability**
R-050, R-090, R-095, R-264 · Record §4.1, §6.7, §6.9 · Proposal: Methodology (MQTT anomalies)

---

**[E3-03] Normalize network flows into alerts**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing, needs-refinement
**Depends on:** E3-01, E3-10 · **Blocks:** E3-05, E4-01

**Context**
Flows are the only source present in every provisional attack family, so a flow-parsing bug touches every result. Correct device keying matters most here: a flow keyed to the broker instead of the device puts evidence in the wrong bundle.

**Goal**
Every flow record becomes one validated `Alert` keyed to the correct device, or is counted as skipped with a reason.

**Scope**
- In: a parser for the ADR-002 flow format, mapping to `Alert` v1, the device mapping, a skip counter, tests.
- Out: flow classification (E4-02), bundling (E3-05).

**Technical notes**
- D is the non-infrastructure endpoint (§4.1).
- Field names come from the ADR-002 mapping.
- Develop on the pilot; run on the frozen corpus after E2-09 (C-19).

**Acceptance criteria**
- Given `tests/fixtures/raw/flows_sample.*` with a known count of records, when `normalize_flows()` runs, then alerts plus skipped records equals the record count.
- Given a flow between an emulator and the broker, when it is normalized, then `subject_device` is the emulator.
- Given a flow between two infrastructure hosts, when it is normalized, then it is skipped with reason `infrastructure_only`.
- Given a flow from the attacker to the honeypot, when it is normalized, then `subject_device` is the honeypot.
- [ ] `thesis/normalize/flows.py` writes `data/alerts/flows/<run_id>.parquet`.

**Checklist**
- [ ] Extract fixtures.
- [ ] Write the parser.
- [ ] Map to `Alert`.
- [ ] Apply the device mapping, including the infrastructure case.
- [ ] Add the skip counter.
- [ ] Write the tests.
- [ ] Run on the pilot.

**Deliverables**
`thesis/normalize/flows.py`, `tests/fixtures/raw/flows_sample.*`, `tests/test_normalize_flows.py`

**Risks / gotchas**
- A bidirectional flow can be recorded twice by some exporters, which doubles counts. Check the exporter's behaviour against the pilot.
- May change after the spike: required flow fields depend on FINDINGS.md and E0-05.

**Open questions**
None

**Traceability**
R-050, R-089, R-090, R-095, R-264 · Record §4.1, §6.9 · Proposal: Methodology (network flows)

---

**[E3-04] Normalize honeypot logs into alerts**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing, needs-refinement
**Depends on:** E3-01 · **Blocks:** E3-05, E4-05

**Context**
Honeypot logs carry the commands the attacker typed. That text is evidence for the agent and, at the same time, the prompt-injection channel (risk #7). This ticket keeps it verbatim and safely typed. Delimiting and truncation happen later, at prompt time.

**Goal**
Every honeypot session event becomes one validated `Alert` keyed to the honeypot, with attacker text stored verbatim in a typed field.

**Scope**
- In: a parser for the ADR-002 honeypot format; sessions, auth attempts, success or fail, and commands; mapping to `Alert` v1; tests.
- Out: truncation and delimiting (E7-07), the honeypot detector rules (E4-05), sanitizing or rewriting attacker text.

**Technical notes**
- Honeypot events key to the honeypot (§4.1).
- Attacker text is stored as data only. It is never interpreted, logged as an instruction, or executed (§6.11).
- Develop on the pilot; run on the frozen corpus after E2-09 (C-19).

**Acceptance criteria**
- Given `tests/fixtures/raw/honeypot_sample.*`, when `normalize_honeypot()` runs, then alerts plus skipped events equals the event count, and every alert's `subject_device` is the honeypot.
- Given a command containing quotes, newlines and the string "ignore previous instructions", when it is normalized and read back from Parquet, then it is byte-identical to the original.
- [ ] `thesis/normalize/honeypot.py` writes `data/alerts/honeypot/<run_id>.parquet`.

**Checklist**
- [ ] Extract fixtures.
- [ ] Write the parser.
- [ ] Map sessions, auth events and commands.
- [ ] Write the verbatim round-trip test.
- [ ] Run on the pilot.

**Deliverables**
`thesis/normalize/honeypot.py`, `tests/fixtures/raw/honeypot_sample.*`, `tests/test_normalize_honeypot.py`

**Risks / gotchas**
- Attacker text can contain control characters that break a JSON log or a terminal. Store it as bytes-safe text and escape it only on display.
- May change after the spike: what counts as a "command sequence" depends on FINDINGS.md.

**Open questions**
None

**Traceability**
R-050, R-090, R-095, R-264 · Record §3.3, §4.1, §6.11 · Proposal: Methodology (honeypot logs)

---

**[E3-05] Implement the device-keyed 60 s bundle assembler**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E3-02, E3-03, E3-04, E2-04, E0-03 · **Blocks:** E3-06

**Context**
The bundle is the unit everything is measured on. Assembly happens outside the agent, so every condition sees the identical set of items and the comparisons stay paired (record §4.1). A bug here silently invalidates every experiment, which is why the record says to test it hard (§6.9).

**Goal**
The assembler turns normalized alerts and window labels into the same set of bundles every time, with a stable hash.

**Scope**
- In: tiling per device, dropping empty windows, joining labels and episode IDs, filtering sources by configuration, the bundle-set hash, tests.
- Out: reduction (E3-06), building the frozen set (E3-09), letting the agent decide boundaries.

**Technical notes**
- A bundle is all alerts from the configured sources with timestamp in window W and subject device D (§4.1).
- W = 60 s, read from config. Tiling is contiguous and non-overlapping per device. Empty windows are dropped (§4.1).
- Labels come from E2-04, with their episode IDs.
- Bundles are stored as Parquet (§6.7).

**Acceptance criteria**
- Given the same alerts and labels, when the assembler runs twice, then both runs produce the same bundle-set SHA-256.
- Given alerts at 59.999 s and 60.000 s for one device, when bundles are assembled, then they fall in two different bundles.
- Given a device with no alerts in a window, when bundles are assembled, then no bundle exists for that (device, window).
- Given `sources = {flows}`, when bundles are assembled, then no bundle contains an MQTT or honeypot alert, and every bundle ID also exists in the all-sources run.
- [ ] `thesis/assemble/bundles.py` defines `assemble()` and `bundle_set_hash()`.

**Checklist**
- [ ] Write the tiling.
- [ ] Drop empty windows.
- [ ] Join labels and episode IDs.
- [ ] Filter by source.
- [ ] Write the hash.
- [ ] Write the four tests.
- [ ] Run on the pilot.

**Deliverables**
`thesis/assemble/bundles.py`, `tests/test_assemble.py`

**Risks / gotchas**
- With a source filter, a window can become empty and be dropped, so single-source conditions see fewer bundles. Decide in E0-03 whether those bundles count as "no detection" or are excluded. Otherwise the H1 pairing breaks.
- Window starts must align to a fixed epoch, not to each device's first alert.

**Open questions**
"Is a 60-second window the right unit?" (§10). Answered in E0-03; this ticket reads W from config.

**Traceability**
R-001, R-086, R-087, R-091–R-093, R-096, R-100, R-265 · Record §4.1, §6.7, §6.9 · Proposal: Methodology (paired design)

---

**[E3-06] Implement the frozen reduction policy**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 5 · **Labels:** engineering, needs-refinement
**Depends on:** E3-05, E0-05, E4-06 · **Blocks:** E3-07, E3-08, E3-09

**Context**
Reduction decides what every model sees. It must match the frozen policy exactly, or the experiment measures an unrecorded variant. It must also be identical for the agent and both baselines, or H4 is contaminated (record §4.1). Over-compression would hide the H1 fusion signal (§4.4).

**Goal**
A deterministic function turns any bundle into the reduced view defined by `reduction-v1.0`, for all three sources.

**Scope**
- In: aggregates per source, exemplar selection by detector score, honeypot truncation, the reduced output format, determinism.
- Out: prompt wording (E6-02), token assertions (E3-08), golden files (E3-07), changing the policy (a METHODS.md changelog entry plus a full rerun if after the freeze).

**Technical notes**
- Aggregates and exemplars follow §4.4 as frozen in `reduction-v1.0`.
- Exemplars are ranked by detector score, which is why this ticket waits for E4-06 (C-15).
- The output is the single view consumed by the agent, Baseline A and Baseline B (§4.1).
- If implementation forces any policy change: stop, write the changelog entry, re-run everything affected (§4.4).

**Acceptance criteria**
- Given the same bundle, when `reduce()` runs twice, then the outputs are byte-identical.
- Given a bundle with more flow alerts than the exemplar cap, when it is reduced, then exactly the cap's number of flow exemplars appear, ordered by detector score with the frozen tie-break.
- Given a honeypot command longer than the frozen cap, when it is reduced, then it is cut to exactly the cap.
- Given a bundle with no MQTT alerts, when it is reduced, then the MQTT section states "no alerts" rather than being omitted.
- [ ] `thesis/reduce/policy.py` declares `POLICY_VERSION = "reduction-v1.0"`.

**Checklist**
- [ ] Implement the flow aggregates.
- [ ] Implement the MQTT aggregates.
- [ ] Implement the honeypot aggregates.
- [ ] Implement exemplar selection.
- [ ] Implement truncation.
- [ ] Define the output format.
- [ ] Write the determinism and edge-case tests.

**Deliverables**
`thesis/reduce/policy.py`, `tests/test_reduce.py`

**Risks / gotchas**
- Floating-point aggregates printed with different precision change the bytes and the hash. Fix the formatting.
- "No alerts" written differently per source confuses the model. Use one phrasing.
- May change after the spike: the exact output format depends on what the spike model read best.

**Open questions**
None

**Traceability**
R-102, R-103, R-105, R-107–R-113, R-190 · Record §4.1, §4.4 · Proposal: Methodology (same alerts for every condition)

---

**[E3-07] Add golden-file tests for the reduction step**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 2 · **Labels:** testing
**Depends on:** E3-06 · **Blocks:** E3-09

**Context**
The record calls for golden files on the reduction step (§6.9). They are what stops an accidental change to a frozen METHODS.md parameter weeks after the freeze. Any change to the reduced output then shows up as a failing test, not a silent difference in results.

**Goal**
Committed golden files fix the exact reduced output for representative bundles, and any change to that output fails CI.

**Scope**
- In: one fixed input bundle per source mix, the committed expected output, a test comparing them, a documented way to update goldens.
- Out: property tests (E7-03), token assertions (E3-08).

**Technical notes**
- Golden-file tests: fixed input, exact expected output, committed (§6.9).
- Updating a golden after the freeze is a locked-parameter change (DoD change control).

**Acceptance criteria**
- Given the committed goldens, when `pytest tests/test_reduce_golden.py` runs, then it passes.
- Given a one-character change in the reduction output format, when the test runs, then it fails and prints a diff.
- [ ] `tests/golden/reduce/` holds at least four input/expected pairs: all three sources, flows only, flows plus honeypot, and a bundle at the exemplar cap.
- [ ] `tests/golden/README.md` states that updating a golden after E2-09 needs a METHODS.md changelog entry.

**Checklist**
- [ ] Choose the four inputs from the pilot.
- [ ] Generate the expected outputs.
- [ ] Review them by eye against the policy.
- [ ] Commit them.
- [ ] Write the test.
- [ ] Write the README.

**Deliverables**
`tests/golden/reduce/*`, `tests/test_reduce_golden.py`, `tests/golden/README.md`

**Risks / gotchas**
- Goldens generated without review just freeze whatever the code does today. Check each one against the policy text before committing.

**Open questions**
None

**Traceability**
R-266, R-268 · Record §6.9 · Proposal: none (engineering)

---

**[E3-08] Assert the per-call token ceilings at build time**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** Medium · **Points:** 2 · **Labels:** testing, engineering, needs-refinement
**Depends on:** E3-06, E0-06 · **Blocks:** E3-09, E6-06

**Context**
The token budget is an assertion in code, so an oversized bundle fails at build time rather than after thousands of calls (record §4.4). The output ceiling had no enforcement in round 1 (R-121), so this ticket covers both directions.

**Goal**
No reduced bundle exceeds the input ceiling, and the build fails when one does.

**Scope**
- In: token counting with the experiment model's tokenizer, the input-ceiling assertion over the bundle set, the output-ceiling assertion helper used by the client (E6-01), a report.
- Out: changing the ceilings (frozen in E0-05), prompt text (E6-02).

**Technical notes**
- Input ≤2,000 target and 2,500 ceiling; output ≤200 target and 250 ceiling, as frozen in `reduction-v1.0` (§4, §4.4).
- Count with the experiment model's tokenizer (ADR-001).
- ASSUMPTION: the assertion measures the full prompt (static prefix plus reduced bundle), since the ceiling is per call.

**Acceptance criteria**
- Given a bundle set where one assembled prompt exceeds the input ceiling, when `python -m thesis.reduce.check_tokens` runs, then it exits non-zero and names the bundle.
- Given a completion longer than the output ceiling, when `assert_output_tokens()` is called, then it raises.
- [ ] `docs/reduction/token_report.md` records the minimum, median, 95th percentile and maximum prompt tokens over the pilot bundles.

**Checklist**
- [ ] Load the experiment tokenizer.
- [ ] Count tokens per prompt.
- [ ] Write the input assertion.
- [ ] Write the output helper.
- [ ] Generate the report.

**Deliverables**
`thesis/reduce/check_tokens.py`, `tests/test_token_ceiling.py`, `docs/reduction/token_report.md`

**Risks / gotchas**
- Counting with the local tokenizer while the experiment model uses another one passes here and fails in production.
- May change after the spike: the 2,000 vs 3k question (C-02) is settled in E0-05 using spike data.

**Open questions**
None

**Traceability**
R-114, R-120, R-121, R-124 · Record §4, §4.4 · Proposal: none (engineering)

---

**[E3-09] Build the frozen bundle set and record its hash**
**Type:** Task · **Epic:** EPIC-3 · **Priority:** High · **Points:** 2 · **Labels:** engineering, research
**Depends on:** E3-06, E3-07, E3-08, E2-09, E4-06 · **Blocks:** E6-03, E6-08, E8-02, E8-04, E9-01

**Context**
Every condition must receive the identical bundle set (record §4). Recording its hash is what lets any later result be traced back to exactly these bundles. The agent is developed against these frozen bundles, with the testbed shut down (§4.2).

**Goal**
The reduced bundle set for corpus v1.0.0 exists as Parquet, with a recorded hash and per-family counts checked against target N.

**Scope**
- In: running normalization, detectors, assembly and reduction on corpus v1.0.0; writing Parquet; hashing; comparing counts with METHODS.md v1.1.
- Out: any agent or baseline run, regenerating the corpus.

**Technical notes**
- Identical bundle set for every condition (§4).
- Generate the corpus, shut the testbed down, then develop against frozen bundles (§4.2).
- Under E2-01 option (a), training-split bundles are written to a separate file, so they never enter evaluation.

**Acceptance criteria**
- Given corpus v1.0.0, when `python -m thesis.assemble.build_frozen` runs twice, then both runs produce the same bundle-set hash.
- Given the frozen set, when bundle counts per family and benign are compared with METHODS.md v1.1, then every count is at or above its target. If one is not, the shortfall is recorded and a decision logged in the METHODS.md changelog.
- [ ] `data/bundles/v1.0.0/eval.parquet` (and `train.parquet` if E2-01 = a) exist.
- [ ] The bundle-set hash is written in METHODS.md and in `docs/thesis_notes.md`.

**Checklist**
- [ ] Verify the corpus with `verify_corpus`.
- [ ] Run the full pipeline.
- [ ] Split train and eval.
- [ ] Hash.
- [ ] Compare counts.
- [ ] Record the hash.

**Deliverables**
`thesis/assemble/build_frozen.py`, `data/bundles/v1.0.0/`, METHODS.md entry

**Risks / gotchas**
- Empty-window dropping makes benign counts lower than the window-level counts in E2-07. Plan for the shortfall in E2-03, not here.

**Open questions**
None

**Traceability**
R-073, R-094, R-100 · Record §4, §4.2 · Proposal: Methodology (paired design)

---

**[E3-10] Decide the device mapping for traffic that §4.1 does not cover**
**Type:** Research · **Epic:** EPIC-3 · **Priority:** High · **Points:** 2 · **Labels:** research
**Depends on:** E0-08, E1-02 · **Blocks:** E3-02, E3-03

**Context**
Record §4.1 keys every bundle to D, the non-infrastructure endpoint, and keys honeypot events to the honeypot. Alert schema v0.1 (E0-08) found two cases the rule does not cover, and left them open as ASSUMPTIONs 4 and 5 in METHODS.md, "Alert schema v0.1: device mapping (draft)". E3-01 cannot settle them, because changing the device-mapping rule is out of its scope. The choice decides which traffic forms bundles, so it must be fixed before the normalizers run on the frozen corpus. It serves H1 and risk #1.

**Goal**
METHODS.md states, for both open cases, which device an alert is keyed to (or that it forms no bundle), with a rationale, and `subject_device()` implements it.

**Scope**
- In: case 4, traffic from an external host to an infrastructure host (for example an MQTT flood on the broker); case 5, traffic between two testbed devices (for example lateral movement); the options and their effect on bundles and labels; the decision; an appended METHODS.md section that supersedes ASSUMPTIONs 4 and 5; the change to `subject_device()` and its tests; a record §4.1 update if the rule changes.
- Out: the other mapping cases (ASSUMPTIONs 1–3), the alert fields (E3-01), the normalizers (E3-02 to E3-04), W and tiling (§10).

**Technical notes**
- Case 4 depends on the frozen families (E1-02): it matters only if a family targets infrastructure.
- If an alert is keyed to more than one device, bundles stop being disjoint. Check the effect on the pairing in §4.1 and on clustering.
- The mapping stays defined once, in code (§4.1).
- The frozen METHODS.md section is never edited. The decision is an appended section.

**Acceptance criteria**
- Given a flow from an external IP to the broker IP, when `subject_device()` is called, then it returns the result the METHODS.md section states.
- Given a flow between two testbed device IPs, when `subject_device()` is called, then it returns the result the METHODS.md section states, and no longer raises `AmbiguousSubjectError` unless the section says so.
- [ ] METHODS.md has an appended section that decides cases 4 and 5, with a rationale and the options considered.
- [ ] If the rule in §4.1 changes, `thesis_project_full_record.md` §4.1 is updated.

**Checklist**
- [ ] Read the frozen families (E1-02) and list which ones produce case 4 or case 5 traffic.
- [ ] Draft the options and their trade-offs for Roy.
- [ ] Record Roy's decision in METHODS.md.
- [ ] Update `subject_device()` and its tests.

**Deliverables**
METHODS.md (appended section), `thesis/schema/devices.py`, `tests/test_alert_schema.py`, record §4.1 if changed

**Risks / gotchas**
- Leaving case 4 unmapped silently drops every attack aimed at infrastructure from the corpus.
- Keying one alert to two devices double-counts it across bundles.

**Open questions**
None blocking. The decision itself is Roy's.

**Traceability**
R-089, R-090 · Record §4.1, §10 ("Which six attack families?") · METHODS.md, "Alert schema v0.1: device mapping (draft)"


# Step D — EPIC-4 · Detection Layer

6 tickets · 18 points · Project DoD v1.0 and DoR apply to every ticket.

**Rule for every ticket here:** detectors are tuned only on training-split data (E2-01) or benign calibration data, never on evaluation bundles and never on the pilot (E1-15).

**Suggested execution order:** E4-01 → E4-02 → E4-03 ∥ E4-04 ∥ E4-05 → E4-06

---

**[E4-01] Engineer flow features on the agreed training data**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** High · **Points:** 3 · **Labels:** engineering, research
**Depends on:** E3-03, E2-01, E2-09 · **Blocks:** E4-02

**Context**
The flow classifier is both a detector and Baseline A (record §5). A weak baseline invalidates H4 faster than any flaw in the agent (§6.6), so its features deserve real engineering effort. The data it learns from was fixed in E2-01.

**Goal**
A deterministic feature pipeline turns normalized flow alerts into a training table, using only data allowed by E2-01.

**Scope**
- In: per-flow features, the training table, a leakage check, a feature list with reasons.
- Out: model training (E4-02), bundle-level aggregation for Baseline A (defined in E0-05, implemented in E8-02), any evaluation-split data.

**Technical notes**
- Feature engineering is part of tuning Baseline A properly (§6.6).
- Training data follows E2-01: an episode-level testbed split, or a published dataset.
- ASSUMPTION: features are computed per flow; the bundle-level verdict is derived later by a fixed rule.

**Acceptance criteria**
- Given the training data, when `python -m thesis.detect.flow_features` runs twice, then both output tables are byte-identical.
- Given the training table and the evaluation episode IDs, when the leakage check runs, then no evaluation episode ID appears in the training table.
- [ ] `data/features/flows_train.parquet` exists.
- [ ] `docs/detectors/flow_features.md` lists every feature with its formula and a one-line reason.

**Checklist**
- [ ] Load the training data per E2-01.
- [ ] Define the features.
- [ ] Write the pipeline.
- [ ] Write the leakage check.
- [ ] Document the features.

**Deliverables**
`thesis/detect/flow_features.py`, `data/features/flows_train.parquet`, `docs/detectors/flow_features.md`, `tests/test_flow_features.py`

**Risks / gotchas**
- Features that encode the attacker's IP or the testbed's fixed addresses let the classifier memorise addresses instead of behaviour. Exclude raw addresses.

**Open questions**
None

**Traceability**
R-225, R-231 · Record §5, §6.6 · Proposal: Methodology (Baseline A)

---

**[E4-02] Tune the flow classifier with class-imbalance handling**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** High · **Points:** 5 · **Labels:** engineering, research
**Depends on:** E4-01 · **Blocks:** E4-03

**Context**
An examiner will attack a weak baseline first (record §6.6). The classifier gets a real hyperparameter search and class-imbalance handling, so if the agent still wins, the H4 claim holds.

**Goal**
A tuned LightGBM or XGBoost flow classifier is selected by cross-validation on the training data, with its search fully recorded.

**Scope**
- In: choosing LightGBM or XGBoost, a hyperparameter search, imbalance handling, episode-grouped cross-validation, a search log.
- Out: evaluation on held-out data (E4-03), deep learning models, ensembles of several libraries, evaluation bundles.

**Technical notes**
- LightGBM or XGBoost (§6.2). Conventional detectors are not the contribution (§5).
- Tune properly: feature engineering, hyperparameter search, class imbalance (§6.6).
- Cross-validation folds are grouped by episode, so one episode never spans training and validation folds (§4.1).

**Acceptance criteria**
- Given the training table, when `python -m thesis.detect.train_flow` runs with the committed seed, then it produces the same best parameters on two runs.
- [ ] `docs/detectors/flow_search.md` lists the library chosen and why, the search space, the number of trials, the imbalance method, and the cross-validated macro-F1 of the best model.
- [ ] `models/flow_classifier.<ext>` is saved with its parameters in `models/flow_classifier.json`.

**Checklist**
- [ ] Choose the library.
- [ ] Define the search space.
- [ ] Set up episode-grouped folds.
- [ ] Add imbalance handling.
- [ ] Run the search.
- [ ] Save the best model.
- [ ] Document the search.

**Deliverables**
`thesis/detect/train_flow.py`, `models/flow_classifier.*`, `docs/detectors/flow_search.md`

**Risks / gotchas**
- Random folds instead of grouped folds make the cross-validation score look much better than real performance.
- A search that runs for hours competes with the agent work on 16 GB. Cap the trial count.

**Open questions**
None

**Traceability**
R-049, R-166, R-169, R-225, R-231, R-232 · Record §4.1, §5, §6.2, §6.6 · Proposal: Methodology (Baseline A)

---

**[E4-03] Evaluate and freeze the flow classifier as Baseline A**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** High · **Points:** 2 · **Labels:** research, testing
**Depends on:** E4-02 · **Blocks:** E4-06, E8-02

**Context**
The flow classifier doubles as Baseline A (record §5). It must be frozen, versioned and hashed before any agent run, so it cannot be retuned after seeing how the agent does.

**Goal**
The flow classifier is evaluated once on held-out training data and frozen with a hash, before any agent output exists.

**Scope**
- In: held-out evaluation within the training data, the metrics report, the model hash, the freeze record.
- Out: evaluation on the evaluation bundles (that is EPIC-9), any retraining after this ticket.

**Technical notes**
- One artifact, two purposes: detector and Baseline A (§5).
- ASSUMPTION: "held-out" means held-out episodes within the training data, never the evaluation split.

**Acceptance criteria**
- [ ] `docs/detectors/flow_eval.md` reports per-class precision, recall, F1 and macro-F1 on held-out training episodes.
- [ ] The model file's SHA-256 is recorded in `models/flow_classifier.json` and in `docs/thesis_notes.md`.
- [ ] Git tag `baseline-a-v1.0` exists.
- [ ] A METHODS.md changelog entry states that Baseline A was frozen before any agent run.

**Checklist**
- [ ] Hold out episodes.
- [ ] Evaluate.
- [ ] Write the report.
- [ ] Hash the model.
- [ ] Tag it.
- [ ] Write the changelog entry.

**Deliverables**
`docs/detectors/flow_eval.md`, `models/flow_classifier.json` (with hash), git tag

**Risks / gotchas**
- Retuning Baseline A after seeing agent results is the bias this freeze exists to prevent. Any later change needs a changelog entry and a full rerun.

**Open questions**
None

**Traceability**
R-226 · Record §4, §5 · Proposal: Methodology (Baseline A)

---

**[E4-04] Implement the MQTT statistical-threshold detector**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** Medium · **Points:** 3 · **Labels:** engineering
**Depends on:** E3-02, E2-09, E1-05 · **Blocks:** E4-06

**Context**
MQTT anomalies are one of the three sources (proposal Methodology). The detector is deliberately simple: statistical thresholds (record §6.2). Its scores rank the MQTT exemplars in the reduction.

**Goal**
Every MQTT alert gets an anomaly score and label from thresholds fixed on benign training data only.

**Scope**
- In: thresholds on message rate, topic novelty, payload size and auth failures; calibration on benign training windows; scoring.
- Out: machine learning for MQTT, tuning on evaluation bundles or on the pilot, writing scores into bundles (E4-06).

**Technical notes**
- Statistical thresholds (§6.2), conventional by design (§5).
- Calibrate only on benign windows of the training split (E2-01). Under option (b), use a benign-only calibration run.
- Benign irregularities from E1-05 must not score as attacks at the chosen threshold, by design of the calibration.

**Acceptance criteria**
- Given the benign calibration windows, when thresholds are fitted, then each threshold and the percentile it comes from is written to `models/mqtt_thresholds.json`.
- Given an MQTT alert, when `score_mqtt()` runs, then it returns a score between 0 and 1 and a label.
- [ ] `docs/detectors/mqtt.md` records the false-positive rate on held-out benign training windows.

**Checklist**
- [ ] Select benign calibration windows.
- [ ] Compute the statistics.
- [ ] Fix the percentile thresholds.
- [ ] Write the scoring function.
- [ ] Measure the false-positive rate.
- [ ] Document.

**Deliverables**
`thesis/detect/mqtt.py`, `models/mqtt_thresholds.json`, `docs/detectors/mqtt.md`, `tests/test_mqtt_detector.py`

**Risks / gotchas**
- Calibrating on windows that contain attacks raises the thresholds and hides attacks. Use benign windows only.

**Open questions**
None

**Traceability**
R-046, R-049, R-167, R-169 · Record §5, §6.2 · Proposal: Methodology (MQTT anomalies)

---

**[E4-05] Implement the honeypot parser and rules**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** Medium · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E3-04 · **Blocks:** E4-06

**Context**
Honeypot activity is malicious by definition, but the type of activity still matters for classification. Rules separate brute force, successful login and command execution (record §6.2).

**Goal**
Every honeypot alert gets a rule-based label and score from a small, documented rule set.

**Scope**
- In: rules for brute force, successful login and command execution; scoring; tests per rule.
- Out: interpreting attacker commands semantically, any machine learning, prompt-injection handling (E7-07).

**Technical notes**
- Parser plus rules (§6.2), conventional by design (§5).
- Parsers are tested hard (§6.9).

**Acceptance criteria**
- Given a fixture session with 20 failed logins within one minute, when the rules run, then the alert is labelled brute force.
- Given a fixture session with a successful login followed by commands, when the rules run, then the alerts are labelled login-success and command-execution.
- [ ] `docs/detectors/honeypot_rules.md` lists every rule with its threshold.

**Checklist**
- [ ] Define the rules.
- [ ] Implement them.
- [ ] Write one test per rule.
- [ ] Document.

**Deliverables**
`thesis/detect/honeypot.py`, `docs/detectors/honeypot_rules.md`, `tests/test_honeypot_rules.py`

**Risks / gotchas**
- A rule threshold tuned to make one family easy to classify leaks the label into the detector. Set thresholds from the rule's meaning, not from the families.

**Open questions**
None

**Traceability**
R-046, R-049, R-168, R-169, R-264 · Record §5, §6.2, §6.9 · Proposal: Methodology (honeypot logs)

---

**[E4-06] Write detector scores and labels into alerts**
**Type:** Task · **Epic:** EPIC-4 · **Priority:** High · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E4-03, E4-04, E4-05 · **Blocks:** E3-06, E3-09

**Context**
The architecture puts detection before grouping (Arch §5). The reduction includes each detector's score and ranks exemplars by it (record §4.4). This ticket is the bridge that lets EPIC-3 finish (C-15).

**Goal**
Every normalized alert carries its detector's name, score and label before bundles are reduced.

**Scope**
- In: running the three detectors over the normalized alerts, populating the `Alert` detector fields, a completeness check.
- Out: changing detectors, reduction (E3-06).

**Technical notes**
- Pipeline order: clean, detect, group, shrink (Arch §5).
- Detector score and label are part of the reduced bundle (§4.4).

**Acceptance criteria**
- Given normalized alerts for one run, when `python -m thesis.detect.annotate` runs, then every alert in the output has non-null detector name, score and label.
- Given an alert with a source that has no detector output, when the completeness check runs, then it fails and names the alert ID.
- [ ] Annotated alerts are written to `data/alerts_annotated/<source>/<run_id>.parquet`.

**Checklist**
- [ ] Load the three detectors.
- [ ] Annotate per source.
- [ ] Write the output.
- [ ] Write the completeness check.
- [ ] Run on the pilot.

**Deliverables**
`thesis/detect/annotate.py`, `tests/test_annotate.py`

**Risks / gotchas**
- Running detectors on the pilot for development is fine; tuning them on it is not.

**Open questions**
None

**Traceability**
R-046, R-049, R-096, R-113 · Record §4.4 · Arch §5 · Proposal: Methodology (detectors produce alerts)


# Step D — EPIC-5 · Knowledge Base & Retrieval

4 tickets · 8 points · Project DoD v1.0 and DoR apply to every ticket.

**Suggested execution order:** E5-01 ∥ E5-02 → E5-03 → E5-04

---

**[E5-01] Build the device inventory**
**Type:** Task · **Epic:** EPIC-5 · **Priority:** Medium · **Points:** 1 · **Labels:** engineering
**Depends on:** E0-07 · **Blocks:** E5-04, E6-03

**Context**
Node 1 receives "retrieved device context" with every bundle (record §6.3). Device criticality is also what makes an action contextually unsafe: isolating a critical device for a single scan (§3.1).

**Goal**
One file describes every testbed device with its ID, role, criticality and network position.

**Scope**
- In: the inventory file, a schema check, a test that every testbed device is listed.
- Out: real asset-management integration, vulnerability data (scoped out, see E5-02).

**Technical notes**
- The knowledge subsystem holds the device inventory (§2).
- ASSUMPTION: criticality uses a three-level scale (low, medium, high), set once and never changed after E2-09.

**Acceptance criteria**
- Given `knowledge/devices.yaml`, when `pytest tests/test_devices.py` runs, then every device ID in `docker-compose.yml` appears in the inventory, and every entry has ID, role, criticality and network position.
- [ ] `knowledge/devices.yaml` exists.

**Checklist**
- [ ] List the compose devices.
- [ ] Assign role, criticality and position.
- [ ] Write the test.
- [ ] Record the criticality scale in METHODS.md before E2-09.

**Deliverables**
`knowledge/devices.yaml`, `tests/test_devices.py`

**Risks / gotchas**
- Criticality set after seeing agent output would bias contextual safety. Fix it before E2-09.

**Open questions**
None

**Traceability**
R-170 · Record §2, §3.1, §6.3 · Proposal: Methodology (retrieval component)

---

**[E5-02] Curate the knowledge base of 50–200 cited documents**
**Type:** Research · **Epic:** EPIC-5 · **Priority:** Medium · **Points:** 3 · **Labels:** research
**Depends on:** E1-02, E0-04 · **Blocks:** E5-03

**Context**
The agent's retrieval step needs a small, curated corpus, not a general RAG collection (record §5). A large corpus would cost weeks and add a confound to H2.

**Goal**
A curated folder of 50–200 short documents, each with its source, covers mitigations and incident handling for the six families.

**Scope**
- In: ATT&CK mitigation entries and incident-handling excerpts mapped to the six families, one file per document, a source field per document, an index.
- Out: vulnerability databases (brief-only, scoped out and stated as a limitation in E11-09), web scraping, more than 200 documents.

**Technical notes**
- Small curated knowledge base, 50–200 documents (§5).
- ATT&CK mitigations are part of the knowledge subsystem (§2).
- Copy only what licences allow. ASSUMPTION: short excerpts with citations.

**Acceptance criteria**
- [ ] `knowledge/docs/` holds between 50 and 200 files.
- [ ] `tests/test_kb.py::test_every_doc_has_source` fails if any document lacks a source field, and passes on the committed set.
- [ ] `knowledge/docs/INDEX.md` maps each of the six families to at least three documents.
- [ ] `knowledge/docs/INDEX.md` states that vulnerability databases are out of scope, with the reason.

**Checklist**
- [ ] Collect the mitigation entries.
- [ ] Collect the incident-handling excerpts.
- [ ] Map them to families.
- [ ] Write one file per document.
- [ ] Write the index.
- [ ] Write the test.

**Deliverables**
`knowledge/docs/*.md`, `knowledge/docs/INDEX.md`, `tests/test_kb.py`

**Risks / gotchas**
- Documents that name the correct answer for a family ("for port scans, recommend X") turn retrieval into an answer key and inflate H2. Keep documents descriptive.

**Open questions**
None

**Traceability**
R-047, R-170, R-171 · Record §2, §5 · Brief: Generative AI Dimension (vulnerability databases, scoped out)

---

**[E5-03] Embed the knowledge base into a numpy index**
**Type:** Task · **Epic:** EPIC-5 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E5-02 · **Blocks:** E5-04

**Context**
For 50–200 documents, embeddings in a numpy array are faster, simpler and fully deterministic. A vector database would add a component that needs its own characterisation (record §6.2).

**Goal**
A pinned embedding model produces one numpy index of the knowledge base, rebuilt byte-identically on demand.

**Scope**
- In: sentence-transformers embeddings with a pinned model revision, a numpy array saved to disk, a document-ID map, a rebuild command.
- Out: any vector database, approximate nearest-neighbour libraries, re-ranking models.

**Technical notes**
- sentence-transformers embeddings in a numpy array, cosine similarity (§6.2).
- No vector database (§6.2, ADR-000).
- The embedding model's revision is recorded, like the LLM's (§4.2).

**Acceptance criteria**
- Given the committed knowledge base, when `python -m thesis.kb.build` runs twice, then both `.npy` files have the same SHA-256.
- [ ] `knowledge/index/embeddings.npy` and `knowledge/index/doc_ids.json` exist.
- [ ] The embedding model name and revision are recorded in `knowledge/index/meta.json`.

**Checklist**
- [ ] Pin the embedding model.
- [ ] Embed the documents.
- [ ] Save the array and ID map.
- [ ] Record the metadata.
- [ ] Check the rebuild hash.

**Deliverables**
`thesis/kb/build.py`, `knowledge/index/embeddings.npy`, `knowledge/index/doc_ids.json`, `knowledge/index/meta.json`

**Risks / gotchas**
- GPU or Apple Metal backends can produce slightly different floats from the CPU. Build on CPU so the hash is stable.

**Open questions**
None

**Traceability**
R-163, R-164 · Record §4.2, §6.2 · Proposal: Methodology (retrieval component)

---

**[E5-04] Implement the deterministic retrieval tool**
**Type:** Task · **Epic:** EPIC-5 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E5-03, E5-01 · **Blocks:** E6-03

**Context**
Retrieval is called as a tool by node 1, but it is deterministic code (record §6.3). It must return the same documents for the same query every time, so runs are reproducible.

**Goal**
One function returns the same top-k documents and the device context for the same query, every time.

**Scope**
- In: cosine top-k with a fixed k, a deterministic tie-break, device-context lookup, a tool interface for node 1, tests.
- Out: query rewriting, re-ranking, any LLM call inside retrieval.

**Technical notes**
- Deterministic, called as a tool (§6.3).
- Cosine similarity (§6.2). BM25 is an acceptable alternative if embeddings perform poorly (§6.2).
- ASSUMPTION: k = 3, recorded in METHODS.md as a locked parameter.

**Acceptance criteria**
- Given the same query, when `retrieve()` is called 100 times, then every call returns the same document IDs in the same order.
- Given two documents with equal similarity, when retrieval ranks them, then the one with the lower document ID comes first.
- Given a device ID, when `device_context()` is called, then it returns that device's inventory entry.
- [ ] The value of k is recorded in METHODS.md.

**Checklist**
- [ ] Load the index.
- [ ] Implement cosine top-k.
- [ ] Add the tie-break.
- [ ] Add device lookup.
- [ ] Define the tool interface.
- [ ] Write the tests.

**Deliverables**
`thesis/kb/retrieve.py`, `tests/test_retrieve.py`

**Risks / gotchas**
- The query text is built from bundle content, which includes attacker text. Retrieval itself is safe, but log the query so a strange retrieval can be traced.

**Open questions**
None

**Traceability**
R-046, R-163, R-165, R-191 · Record §6.2, §6.3 · Proposal: Methodology (retrieval component)


# Step D — EPIC-6 · LLM Agent Core

8 tickets · 20 points · Project DoD v1.0 and DoR apply to every ticket.

**Rule for every ticket here:** prompts are developed on pilot bundles or training-split bundles only, never on evaluation bundles. Developing prompts on the evaluation set would tune the agent to the test and inflate H2 and H4.

**Integrity gate:** no ticket here may run on corpus bundles until every freeze-before-results ticket is Done (E0-03, E0-04, E0-05, E0-11, E0-12, E0-13, E1-02, E1-03, E2-01, E2-02, E8-01). E2-09 and E8-01 enforce this.

**Suggested execution order:** E6-01 ∥ E6-02 → E6-03 → E6-04 → E6-05 → E6-06 → E6-07 ∥ E6-08

---

**[E6-01] Implement the OpenAI-compatible LLM client**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 2 · **Labels:** engineering
**Depends on:** E0-06, E0-10 · **Blocks:** E6-03, E6-04, E6-05, E6-07, E6-08, E8-04

**Context**
Every LLM call in the project goes through this one client, so it is where reproducibility, cost control and the token ceilings are enforced (record §4.2, §4.4). It switches between local Ollama and the hosted model through configuration only.

**Goal**
One client sends every LLM call, logs it, enforces the output ceiling and retries with backoff, against either local or hosted endpoints.

**Scope**
- In: an OpenAI-compatible client, `LLM_BASE_URL` and `LLM_MODEL` configuration, `max_tokens` set to the output ceiling, an output-token assertion, a `num_ctx` check for Ollama, retry with exponential backoff, logging through `log_llm_call()`.
- Out: prompt content (E6-02), structured-output schemas (E6-04, E7-01), streaming, any agent framework.

**Technical notes**
- One OpenAI-compatible client; local and hosted differ only by base URL (§4.2).
- Ollama silently truncates at its default context; `num_ctx` is set to 8192 and checked (§4.3).
- Retries use backoff, and a hard spending cap exists on the provider account (§4.4.1).
- Output ceiling 250 tokens (§4.4); this closes the gap found for R-121.
- No direct SDK calls anywhere else in the code (DoD).

**Acceptance criteria**
- Given `LLM_BASE_URL` pointing at local Ollama, when the marker-test prompt is sent through the client, then the reply contains the marker.
- Given a server that returns HTTP 429 twice then succeeds, when a call is made, then the client retries with increasing waits and returns the third response.
- Given a completion longer than 250 tokens, when the client receives it, then it raises an output-ceiling error and logs the attempt.
- Given any call, when it completes, then one JSONL record with all 12 §6.10 fields is written.
- [ ] `thesis/llm/client.py` defines the client, and `grep` for direct SDK imports outside it returns nothing (checked in CI).

**Checklist**
- [ ] Write the client.
- [ ] Read configuration from the environment.
- [ ] Add `max_tokens` and the output assertion.
- [ ] Add the `num_ctx` handling for Ollama.
- [ ] Add retry with backoff.
- [ ] Wire in logging.
- [ ] Add the CI check for direct SDK imports.
- [ ] Write the tests with a fake server.

**Deliverables**
`thesis/llm/client.py`, `tests/test_llm_client.py`, CI step

**Risks / gotchas**
- Ollama ignores `num_ctx` sent in some request formats. The marker test is the only reliable check.
- A retry loop without a ceiling on attempts is how a spending cap gets hit. Cap the attempts.

**Open questions**
None

**Traceability**
R-121, R-131–R-133, R-142, R-144–R-146 · Record §4.2, §4.3, §4.4, §4.4.1 · Proposal: Methodology

---

**[E6-02] Version the prompt templates with a static prefix first**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 2 · **Labels:** engineering, research, needs-refinement
**Depends on:** E0-05, E0-04 · **Blocks:** E6-03, E6-04, E6-05, E8-03, E7-07

**Context**
The exact prompt bytes are part of the reproducibility claim (record §6.2). Ordering them static-prefix-first allows prompt caching across the three calls (§4.4). The reasoning instructions must not be trimmed, because that would weaken H2's treatment condition (§4.4).

**Goal**
Every prompt is built from a versioned template in a fixed order, and the template version is recorded in each call's provenance.

**Scope**
- In: one template per node and one for Baseline B, the fixed section order, a version string, the honeypot delimiting from the reduction policy, a rendering function.
- Out: the node logic (E6-03 to E6-05), Baseline B's wording (E8-03), prompt optimisation on evaluation bundles.

**Technical notes**
- Order: system role, schema, action catalog (recommendation node only), then the variable bundle content last (§4.4).
- Honeypot text is delimited and never adjacent to schema instructions (§3.3, §6.11).
- Do not trim the reasoning instructions (§4.4).
- A template change after the first experiment is a locked-parameter change (DoD change control).

**Acceptance criteria**
- Given any template and any bundle, when the prompt is rendered, then the bytes before the bundle section are identical for every bundle.
- Given a rendered prompt, when it is inspected, then honeypot text appears only inside the frozen delimiters, and at least one non-honeypot section separates it from the schema section.
- [ ] `thesis/prompts/templates/` holds one file per node, each with a `TEMPLATE_VERSION` string that `Provenance` records.

**Checklist**
- [ ] Write the templates.
- [ ] Fix the section order.
- [ ] Add the delimiters.
- [ ] Write the renderer.
- [ ] Add the version to provenance.
- [ ] Write the tests.

**Deliverables**
`thesis/prompts/templates/*`, `thesis/prompts/render.py`, `tests/test_prompts.py`

**Risks / gotchas**
- A timestamp or bundle ID placed in the system section breaks the static prefix and disables caching.
- May change after the spike: the wording and section order depend on what the spike model handled best.

**Open questions**
None

**Traceability**
R-117, R-125, R-162, R-218, R-220 · Record §3.3, §4.4, §6.2, §6.11 · Proposal: Methodology

---

**[E6-03] Implement node 1: evidence analysis with retrieval**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 3 · **Labels:** engineering, needs-refinement
**Depends on:** E6-01, E6-02, E5-04, E3-09, E8-01 · **Blocks:** E6-04

**Context**
Node 1 is where cross-source correlation happens, which is the core of H1 and H2 (record §6.3). It also absorbs the brief's requests for attack hypotheses and missing-information requests (C-08), without adding a fourth LLM call or any interactive step.

**Goal**
Node 1 turns one reduced bundle plus retrieved context into structured findings per source, cross-source observations, candidate hypotheses and a missing-evidence list.

**Scope**
- In: one LLM call with tool access to retrieval, a findings model with per-source findings, cross-source observations, candidate hypotheses and missing evidence, evidence referenced by alert ID.
- Out: classification (E6-04), recommendation (E6-05), asking a human anything, a second retrieval round.

**Technical notes**
- Input: reduced bundle plus retrieved device context. Output: findings per source and cross-source observations (§6.3).
- Retrieval is deterministic and called as a tool (§6.3).
- Fresh context per call; no conversation history (§4.4).
- ASSUMPTION (C-08, confirmed): the output adds `candidate_hypotheses` and `missing_evidence` fields. These are recorded, never acted on.
- Develop on pilot or training-split bundles only.

**Acceptance criteria**
- Given a pilot bundle, when node 1 runs, then its output parses into `Findings` with per-source findings, cross-source observations, candidate hypotheses and missing evidence.
- Given a bundle where one source is absent, when node 1 runs, then the findings for that source state "no alerts", and no evidence ID refers to a non-existent alert.
- Given any node 1 call, when it completes, then the retrieval query and returned document IDs are logged with the call.
- [ ] `thesis/agent/node_evidence.py` and the `Findings` model exist.

**Checklist**
- [ ] Define `Findings`.
- [ ] Wire retrieval as a tool.
- [ ] Build the prompt from the template.
- [ ] Call through the client.
- [ ] Parse.
- [ ] Log retrieval.
- [ ] Test on pilot bundles.

**Deliverables**
`thesis/agent/node_evidence.py`, `thesis/agent/models.py`, `tests/test_node_evidence.py` (mocked client)

**Risks / gotchas**
- Free-text findings grow long and push the next call over its input ceiling. Cap each field's length in the model.
- Tool-call support differs between Ollama and hosted providers. If the hosted model lacks it, call retrieval deterministically before the LLM call and record that choice.
- May change after the spike: the findings structure depends on what the model produced reliably.

**Open questions**
None

**Traceability**
R-016, R-042–R-044, R-191, R-192 · Record §4.4, §6.3 · Proposal: Objective 2 · Brief: Generative AI Dimension

---

**[E6-04] Implement node 2: structured classification**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 3 · **Labels:** engineering, needs-refinement
**Depends on:** E6-03 · **Blocks:** E6-05

**Context**
Node 2 produces the classification that H2 compares against the prompt-only baseline: incident type, severity, affected device and confidence (record §6.3). It does not receive the action catalog, which keeps classification separate from recommendation (§4.4).

**Goal**
Node 2 turns node 1's findings into one `Classification` object that uses the frozen enums.

**Scope**
- In: a `Classification` model reusing the `incident_type` and severity enums, one LLM call, parsing.
- Out: the final verdict schema and constrained decoding (E7-01), the action catalog, recommendations.

**Technical notes**
- Input: node 1 findings. Output: type, severity, affected device, confidence (§6.3).
- The classification node gets no action catalog (§4.4).
- `incident_type` uses the E1-02 enum; severity is low, medium, high or critical (§6.5).
- ASSUMPTION: `Classification` is an intermediate model here; E7-01 composes the final verdict from it, so EPIC-6 never depends on EPIC-7.

**Acceptance criteria**
- Given node 1 findings for a pilot bundle, when node 2 runs, then its output parses into `Classification`, with `incident_type` in the seven-value enum and confidence between 0 and 1.
- Given the rendered node 2 prompt, when it is inspected, then it contains no action-catalog text.
- [ ] `thesis/agent/node_classify.py` exists.

**Checklist**
- [ ] Define `Classification`.
- [ ] Build the prompt.
- [ ] Call through the client.
- [ ] Parse.
- [ ] Write the catalog-absence test.

**Deliverables**
`thesis/agent/node_classify.py`, `tests/test_node_classify.py`

**Risks / gotchas**
- Models often return a family name that is close to, but not exactly, an enum value. Log these parse failures rather than mapping them silently.
- May change after the spike: confidence calibration behaviour is unknown until the spike.

**Open questions**
None

**Traceability**
R-016, R-038, R-115, R-193 · Record §4.4, §6.3, §6.5 · Proposal: Objective 2

---

**[E6-05] Implement node 3: constrained recommendation**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 3 · **Labels:** engineering, needs-refinement
**Depends on:** E6-04, E0-04 · **Blocks:** E6-06

**Context**
Node 3 produces the recommendation that H3 and H4 score. It sees the classification and the permitted catalog, and nothing else (record §6.3, §4.4). The explicit catalog in this prompt is what H3 depends on, so it is never removed (§4.4).

**Goal**
Node 3 turns a classification into one recommended action from the catalog, with evidence references.

**Scope**
- In: one LLM call, the catalog in the prompt, a `Recommendation` model with action ID and evidence IDs, parsing.
- Out: validation and rejection (E7-02, E7-04), constrained decoding (E7-01), raw exemplars in the prompt.

**Technical notes**
- Input: node 2 classification plus the permitted catalog; output: one action with evidence references (§6.3).
- The recommendation node gets only the classification output and evidence IDs, no raw exemplars (§4.4).
- Never remove the explicit action catalog from this prompt (§4.4).
- The agent recommends and never executes (§1.1).

**Acceptance criteria**
- Given a pilot classification, when node 3 runs, then its output parses into `Recommendation` with one action ID and at least one evidence ID.
- Given the rendered node 3 prompt, when it is inspected, then it contains the full catalog and no raw exemplar text.
- [ ] `thesis/agent/node_recommend.py` exists.

**Checklist**
- [ ] Define `Recommendation`.
- [ ] Build the prompt with the catalog.
- [ ] Pass evidence IDs through.
- [ ] Call through the client.
- [ ] Parse.
- [ ] Write the prompt-content tests.

**Deliverables**
`thesis/agent/node_recommend.py`, `tests/test_node_recommend.py`

**Risks / gotchas**
- Without raw exemplars, the model may invent evidence IDs. The E7-02 validator catches this; count it here too.
- May change after the spike: catalog wording in the prompt may need adjusting.

**Open questions**
None

**Traceability**
R-016, R-039, R-116, R-127, R-194 · Record §1.1, §4.4, §6.3 · Proposal: Objective 3

---

**[E6-06] Wire the three-node graph runner with source injection**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E6-05, E0-09, E3-08 · **Blocks:** E6-07, E6-08, E7-01, E9-01

**Context**
The graph is the agentic condition that H2 tests: a fixed three-call topology, not a free ReAct loop (record §6.3). It must take its sources from `ExperimentConfig`, so H1's conditions differ only by configuration (§6.1).

**Goal**
One function runs exactly three LLM calls per bundle, in fixed order, on the sources named by the config.

**Scope**
- In: the graph runner, source filtering from config, an assertion of exactly three calls, an end-to-end trace object.
- Out: validation and the audit log (EPIC-7), the matrix runner (E9-01), any loop or branching between nodes.

**Technical notes**
- Bounded graph with fixed topology (§6.3); about 200 lines; no agent framework (§6.2).
- Exactly three LLM calls per bundle (§4, §6.3).
- Fresh context per node; no history (§4.4).
- Sources come only from `ExperimentConfig` (§6.1).
- The methods chapter states the fixed-graph vs ReAct trade-off (E11-04).

**Acceptance criteria**
- Given any bundle and config, when `run_graph()` completes, then the client logged exactly three calls for that bundle and repetition, in the order evidence, classify, recommend.
- Given `sources = {flows}`, when `run_graph()` runs, then no prompt contains MQTT or honeypot content.
- Given any node's prompt, when it is inspected, then it contains no text from a previous node's raw completion other than the parsed fields passed on.
- [ ] `thesis/agent/graph.py` defines `run_graph()` and is under 300 lines.

**Checklist**
- [ ] Write the runner.
- [ ] Filter sources from config.
- [ ] Add the call-count assertion.
- [ ] Build the trace object.
- [ ] Write the three tests with a mocked client.

**Deliverables**
`thesis/agent/graph.py`, `tests/test_graph.py`

**Risks / gotchas**
- Passing a node's raw completion forward instead of its parsed fields reintroduces conversation accumulation by the back door.

**Open questions**
None

**Traceability**
R-001, R-016, R-023, R-048, R-097, R-119, R-122, R-152, R-161, R-187, R-189, R-190 · Record §4, §4.4, §6.1, §6.2, §6.3 · Proposal: Methodology (agent)

---

**[E6-07] Add a slow end-to-end test against local Ollama**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** Medium · **Points:** 2 · **Labels:** testing
**Depends on:** E6-06, E6-01 · **Blocks:** None

**Context**
The record asks for one end-to-end integration test against local Ollama, marked slow and excluded from CI (§6.9). It tests the code path with a real model, never the model's quality.

**Goal**
One slow test runs the full graph on one pilot bundle with local Ollama and checks the shape of the result.

**Scope**
- In: one integration test, the `slow` marker, a skip when Ollama is not running.
- Out: asserting what the model concluded, more than one integration test, running it in CI.

**Technical notes**
- Do not unit-test LLM output quality (§6.9).
- Marked `slow`, excluded from CI (§6.9).

**Acceptance criteria**
- Given Ollama running locally, when `pytest -m slow tests/test_e2e_ollama.py` runs, then the test passes if three calls were made and a parsed recommendation object exists, whatever its content.
- Given Ollama is not running, when the test runs, then it is skipped with a message, not failed.
- [ ] CI logs show the test as deselected.

**Checklist**
- [ ] Pick one pilot bundle as a fixture.
- [ ] Write the test.
- [ ] Add the skip condition.
- [ ] Confirm CI deselects it.

**Deliverables**
`tests/test_e2e_ollama.py`, `tests/fixtures/bundles/pilot_one.json`

**Risks / gotchas**
- Asserting on the predicted family turns this into a flaky model-quality test. Assert structure only.

**Open questions**
None

**Traceability**
R-271 · Record §6.9 · Proposal: none (engineering)

---

**[E6-08] Sanity-compare the dev and experiment models**
**Type:** Research · **Epic:** EPIC-6 · **Priority:** Medium · **Points:** 2 · **Labels:** research
**Depends on:** E6-06, E0-06, E3-09 · **Blocks:** E9-08

**Context**
Development happens on the local model and experiments on the hosted sibling (record §4.2). A sanity comparison before the matrix confirms the same-family assumption holds in practice. If it does not, prompts tuned locally may fail on the experiment model.

**Goal**
A short report shows whether the dev and experiment models produce comparable validity and verdicts on the same small sample.

**Scope**
- In: 20 bundles from the training split or pilot, both models, validity and agreement rates, a go/no-go note.
- Out: any evaluation-split bundle, reporting these numbers as results, choosing a different model family (an ADR-001 change).

**Technical notes**
- Same family; sanity comparison first (§4.2).
- Use non-evaluation bundles only, so this does not become a peek at the test set.

**Acceptance criteria**
- [ ] `docs/agent/model_sanity.md` reports, for both models on the same 20 bundles: schema-validity rate and agreement rate between models on `incident_type`.
- [ ] The report ends with go or no-go for running the matrix on the experiment model, with a reason.
- [ ] If no-go, an ADR-001 update is opened as a new ticket.

**Checklist**
- [ ] Select 20 non-evaluation bundles.
- [ ] Run both models.
- [ ] Compute the rates.
- [ ] Write go or no-go.

**Deliverables**
`docs/agent/model_sanity.md`

**Risks / gotchas**
- Hosted cost for 20 bundles is small, but it still counts against the cap. Check the cap before running.

**Open questions**
None

**Traceability**
R-136 · Record §4.2 · Proposal: Methodology (same base model)

---

**[E6-09] Send json_object for structured output on the hosted provider**
**Type:** Task · **Epic:** EPIC-6 · **Priority:** High · **Points:** 2 · **Labels:** infra
**Depends on:** E6-01, E6-08, ADR-0012 (accepted) · **Blocks:** E9-08

**Context**
The pinned experiment model on DeepInfra returns HTTP 400 for a `json_schema` response format; it accepts `json_object` (E6-08). The client sends `json_schema` on the evidence and classification nodes for every condition and on the recommendation node under `enforcing` (`thesis/llm/client.py`, `thesis/agent/graph.py`), so every agentic call fails on DeepInfra. ADR-0012 (Accepted, Option A) decides to send `json_object` wherever structured output is requested, on every provider; schema conformance is enforced by the node parse and the validator gate, not at decode time.

**Goal**
Agentic calls succeed on the hosted provider, structured as valid JSON, with the enforcing / logging_only distinction preserved as json_object vs free-text, and no frozen parameter changed.

**Scope**
- In: a structured-output mode on the single client that emits `json_object` on every provider (ADR-0012 Option A); the graph requests it on the same calls as today; the METHODS §6.1 changelog entry; tests around the client and the graph wiring (never LLM output quality).
- Out: changing prompts, the action catalog, the rejection policy, `max_retries`, the model, the provider, or any other locked parameter. No retry-until-valid loop.

**Technical notes**
- Keep the single OpenAI-compatible client (locked stack). The switch is the `response_format` type only.
- Membership stays 1-by-construction under enforcing via the validator (safety_scoring §3.2); do not rely on the decoder for schema conformance.
- Nodes 1–2 send a schema for all conditions today, so the switch must cover them too, or C5 also 400s.

**Acceptance criteria**
- A structured call sends `response_format` of type `json_object`, never `json_schema`, asserted from the request the client builds (no network).
- A call with no schema sends no response format (free text), so the enforcing/logging_only difference is json_object vs free-text.
- The METHODS §6.1 changelog entry is merged in the same change.

**Deliverables**
`thesis/llm/client.py`, tests; METHODS changelog entry; ADR-0012.

**Risks / gotchas**
- Do not touch the rejection policy or `max_retries` (frozen). json_object is valid-JSON only; let the validator reject non-conforming output as designed.

**Open questions**
None

**Traceability**
R-136 · Record §4.2, §6.4 · ADR-0012 · Proposal: Methodology (structured output)


# Step D — EPIC-7 · Safety & Constraint Layer

8 tickets · 18 points · Project DoD v1.0 and DoR apply to every ticket.

E7-08 is new in this round. It covers the "one clear report for the human" (R-041) independently of the console, so the requirement survives if the console is cut (C-12).

**Suggested execution order:** E7-01 → E7-02 → E7-03 ∥ E7-04 ∥ E7-05 ∥ E7-07 → E7-06 → E7-08

---

**[E7-01] Define the verdict schema with constrained decoding**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 3 · **Labels:** engineering
**Depends on:** E6-06, E1-02, E0-04 · **Blocks:** E7-02, E8-03, E10-01

**Context**
The structured output schema is one of the four safety mechanisms (record §6.4). The same Pydantic model is also the API schema, so the safety contract and the console can never drift apart (§6.2). It serves H3 and Objective 3.

**Goal**
One Pydantic `Verdict` model holds every §6.5 field, and generation is constrained to it when safety is enforcing.

**Scope**
- In: the `Verdict` model composed from `Classification` and `Recommendation`, enums for type, severity and action, evidence as alert IDs, constrained decoding through the client.
- Out: the validator (E7-02), the API (E10-01), free-text fields beyond what §6.5 lists.

**Technical notes**
- Fields: `incident_type` (six families plus benign), `severity` (low, medium, high, critical), `affected_device`, `evidence` (alert IDs), `recommended_action` (closed enum), `confidence` (0–1) (§6.5).
- Constrained decoding at generation time (§6.4); output 150–250 tokens (§4.4).
- Never remove the evidence field (§4.4).
- What `logging_only` disables follows E0-12 (C-16).

**Acceptance criteria**
- Given a JSON object with every field valid, when it is parsed into `Verdict`, then it succeeds.
- Given an action ID not in the catalog, when it is parsed, then a validation error names the field.
- Given `safety = enforcing`, when a node 3 call is made, then the request sent to the model includes the `Verdict` JSON schema as its output constraint.
- [ ] `thesis/schema/verdict.py` defines `Verdict`, and the action enum is generated from `knowledge/action_catalog.yaml`, not typed by hand.

**Checklist**
- [ ] Compose `Verdict`.
- [ ] Generate the action enum from the catalog.
- [ ] Add schema export.
- [ ] Pass the schema through the client.
- [ ] Write the tests.

**Deliverables**
`thesis/schema/verdict.py`, `tests/test_verdict.py`

**Risks / gotchas**
- A hand-typed enum drifts from the catalog file. Generate it.
- Some providers support only a subset of JSON Schema for constrained output. Test the exact schema against the experiment provider.

**Open questions**
None

**Traceability**
R-017, R-036, R-039, R-040, R-044, R-045, R-118, R-126, R-157, R-197, R-203–R-209 · Record §4.4, §6.2, §6.4, §6.5 · Proposal: Objective 3

---

**[E7-02] Implement the deterministic validator**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 3 · **Labels:** engineering, testing
**Depends on:** E7-01 · **Blocks:** E7-03, E7-04, E7-05, E7-07

**Context**
The validator is the hard gate between the model and any human (record §3.3). It rejects three things: malformed output, actions outside the enum, and evidence not present in the bundle (§6.4). Hallucinated evidence would destroy auditability, which is the project's differentiator.

**Goal**
A pure function accepts a raw completion and its bundle, and returns either a valid `Verdict` or a typed rejection with one of three reasons.

**Scope**
- In: parsing, the three checks, a typed rejection result, tests per check.
- Out: what happens after a rejection (E7-04), contextual safety scoring (E9-04), rewriting or repairing outputs.

**Technical notes**
- Reject malformed output, out-of-enum actions and unknown evidence references (§6.4).
- Validation is a hard gate, not a filter (§3.3, §6.11).
- "Unsafe" in the validator's sense is defined in E0-12 (C-17).

**Acceptance criteria**
- Given a completion that is not valid JSON, when `validate()` runs, then it returns a rejection with reason `malformed`.
- Given a well-formed completion with an action not in the catalog, when `validate()` runs, then it returns reason `action_out_of_space`.
- Given a well-formed completion citing an alert ID not in the bundle, when `validate()` runs, then it returns reason `unknown_evidence`.
- Given a valid completion, when `validate()` runs, then it returns the parsed `Verdict` and no rejection.
- [ ] `thesis/safety/validator.py` defines `validate()` with no network or LLM access.

**Checklist**
- [ ] Define the rejection type.
- [ ] Implement parsing.
- [ ] Implement the action check.
- [ ] Implement the evidence check.
- [ ] Write one test per reason.

**Deliverables**
`thesis/safety/validator.py`, `tests/test_validator.py`

**Risks / gotchas**
- A validator that "repairs" near-miss outputs turns the gate into a filter and changes what H3 measures. Never repair.

**Open questions**
None

**Traceability**
R-001, R-017, R-195, R-210–R-212, R-221, R-267 · Record §3.3, §6.4, §6.9 · Proposal: Objective 3, Methodology (validation rules)

---

**[E7-03] Add property tests for the validator**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 2 · **Labels:** testing
**Depends on:** E7-02 · **Blocks:** None

**Context**
The record asks for property tests: no output outside the action enum ever passes, for any input (§6.9). Example tests cover the cases you thought of; property tests cover the ones you did not.

**Goal**
Generated inputs prove that no action outside the enum and no unknown evidence ID can pass the validator.

**Scope**
- In: property tests over generated completions and bundles, a fixed example budget, a seed.
- Out: tests of model behaviour, tests of contextual safety.

**Technical notes**
- Property tests on the validator (§6.9).
- ASSUMPTION: the Hypothesis library is used. It is a new dependency, so it is recorded as an amendment to ADR-000 (DoD).

**Acceptance criteria**
- Given generated completions whose action is any string not in the catalog, when the property test runs at least 1,000 examples, then none passes the validator.
- Given generated bundles and completions citing IDs outside the bundle, when the property test runs at least 1,000 examples, then none passes.
- [ ] ADR-000 records the Hypothesis dependency.

**Checklist**
- [ ] Write the generators.
- [ ] Write the two properties.
- [ ] Fix the seed and example count.
- [ ] Amend ADR-000.

**Deliverables**
`tests/test_validator_properties.py`, ADR-000 amendment

**Risks / gotchas**
- Generators that only produce random strings never hit near-miss cases like a catalog ID with different casing. Include those strategies explicitly.

**Open questions**
None

**Traceability**
R-017, R-267, R-269 · Record §6.9 · Proposal: Objective 3

---

**[E7-04] Implement the frozen rejection policy**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 2 · **Labels:** engineering
**Depends on:** E7-02, E0-11 · **Blocks:** E7-06

**Context**
What happens after a rejection changes the measured unsafe rate, so the policy was frozen in E0-11 before any result (risk #3). This ticket implements exactly that policy and logs every attempt.

**Goal**
Every rejection is handled exactly as METHODS.md's rejection policy states, and every attempt is logged.

**Scope**
- In: the policy as frozen (retry count, fallback or hard fail), attempt numbering, scoring flags for first and final attempt.
- Out: changing the policy (needs a changelog entry), the audit log format (E7-05).

**Technical notes**
- Policy, retry count and scored attempt are those frozen in E0-11.
- Every attempt is logged (§3.1).

**Acceptance criteria**
- Given a bundle whose first completion is rejected, when the policy runs, then the number of further attempts equals the frozen maximum or stops at the first valid one, and each attempt is logged with its index.
- Given all attempts rejected, when the policy ends, then the outcome matches the frozen fallback exactly.
- [ ] `thesis/safety/rejection.py` reads its parameters from METHODS.md's parameter file, not from constants in code.

**Checklist**
- [ ] Read the frozen policy.
- [ ] Implement attempts.
- [ ] Implement the fallback.
- [ ] Flag first and final attempts.
- [ ] Write the tests with a mocked client.

**Deliverables**
`thesis/safety/rejection.py`, `tests/test_rejection.py`

**Risks / gotchas**
- A retry that includes the rejected completion in the next prompt is a form of conversation accumulation. Follow exactly what E0-11 froze about feedback.

**Open questions**
None

**Traceability**
R-017, R-195, R-215 · Record §3.1 · Proposal: H3

---

**[E7-05] Write the append-only JSONL audit log**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 2 · **Labels:** engineering
**Depends on:** E7-02, E0-10 · **Blocks:** E7-06, E7-08, E10-01

**Context**
The audit log is one of the four safety mechanisms (record §6.4). Every attempt, passed or not, is written with the exact prompt and completion. It is the evidence that the system is auditable.

**Goal**
Every validation attempt produces one append-only audit record that links the call log, the verdict or rejection, and the bundle.

**Scope**
- In: the audit record (built on E0-10's call log), the validation outcome, the rejection reason, the bundle and config hash, an append-only writer.
- Out: a console view (E10-07), rotation or compression, editing past records.

**Technical notes**
- Every attempt, passed or not, with full prompt, raw completion and parse outcome (§6.4).
- Append-only JSONL, never rewritten (§6.7).
- One logging mechanism is audit, cost and debug (§6.10).

**Acceptance criteria**
- Given a rejected attempt and an accepted attempt, when both are logged, then `logs/audit.jsonl` contains two records with outcome, reason (if any), bundle ID, config hash and the matching call-log ID.
- Given an existing audit log, when the writer opens it, then it opens in append mode only (test asserts the mode).
- [ ] `thesis/safety/audit.py` exists.

**Checklist**
- [ ] Define the audit record.
- [ ] Link it to the call log.
- [ ] Write the append-only writer.
- [ ] Write the tests.

**Deliverables**
`thesis/safety/audit.py`, `tests/test_audit.py`

**Risks / gotchas**
- Two processes writing the same file in parallel can interleave lines. Use one writer or one file per process.

**Open questions**
None

**Traceability**
R-017, R-162, R-174, R-183, R-196, R-213 · Record §6.4, §6.7, §6.10 · Proposal: Methodology (audit log)

---

**[E7-06] Implement the enforcing and logging_only switch**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** High · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E7-04, E7-05, E0-12 · **Blocks:** E9-01, E7-08

**Context**
H3 compares the same agent with the safety layer on and off (proposal Methodology). The switch must disable exactly what E0-12 defined (C-16), and nothing else, so H3 isolates the effect of the constraints.

**Goal**
`ExperimentConfig.safety` turns the defined safety mechanisms on or off, and `logging_only` still records what would have been rejected.

**Scope**
- In: the switch, wiring into the graph and the client, recording "would have been rejected" under `logging_only`, a test per mode.
- Out: deciding what is switched off (frozen in E0-12), scoring (E9-04).

**Technical notes**
- Safety values: enforcing or logging_only (§6.1).
- The action catalog stays in the node 3 prompt in both modes (§4.4).
- Which mechanisms are disabled follows E0-12 exactly.

**Acceptance criteria**
- Given `safety = enforcing` and a completion with an out-of-space action, when the graph runs, then the rejection policy is applied.
- Given `safety = logging_only` and the same completion, when the graph runs, then the completion passes through, and the audit log records outcome `would_reject` with its reason.
- Given either mode, when the node 3 prompt is rendered, then it contains the full catalog.
- [ ] The mechanisms disabled under `logging_only` match the E0-12 list, checked by a test that reads it.

**Checklist**
- [ ] Read the E0-12 definition.
- [ ] Implement the switch.
- [ ] Record `would_reject`.
- [ ] Write the three tests.

**Deliverables**
Changes in `thesis/agent/graph.py` and `thesis/safety/`, `tests/test_safety_switch.py`

**Risks / gotchas**
- If `logging_only` also removes constrained decoding while E0-12 says it should not, H3 measures two changes at once.

**Open questions**
None

**Traceability**
R-013, R-017, R-216, R-238 · Record §4.4, §6.1 · Proposal: H3, Methodology

---

**[E7-07] Harden honeypot text handling against prompt injection**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering, testing
**Depends on:** E6-02, E7-02 · **Blocks:** E9-12

**Context**
Attacker-typed commands enter the agent's prompt, which makes them a prompt-injection channel (risk #7). The defensive design is mandatory even though the injection experiment itself is stretch only (record §3.3).

**Goal**
Attacker text always appears truncated and inside delimiters, never next to schema instructions, and validation stays a hard gate whatever it says.

**Scope**
- In: tests that the delimiting and truncation from the reduction and templates hold, a test with injection-style strings, a check that the validator still rejects steered outputs.
- Out: the injection experiment (E9-12), sanitizing or rewriting attacker text, a separate classifier for injections.

**Technical notes**
- Strict delimiting, hard truncation, never adjacent to schema instructions, validation as a hard gate (§3.3, §6.11).
- Truncation cap and delimiter come from `reduction-v1.0`.

**Acceptance criteria**
- Given a honeypot command containing the closing delimiter string, when the prompt is rendered, then the delimiter in the attacker text is escaped and the section still closes at the real delimiter.
- Given a honeypot command longer than the cap, when the prompt is rendered, then the honeypot section contains exactly the cap's number of characters from it.
- Given a mocked completion recommending an action outside the catalog because of injected text, when it is validated, then it is rejected.
- [ ] `tests/test_injection_defence.py` contains these three tests.

**Checklist**
- [ ] Write the delimiter-escape test.
- [ ] Write the truncation test.
- [ ] Write the steered-output test.
- [ ] Fix any gap found.

**Deliverables**
`tests/test_injection_defence.py`, fixes in `thesis/prompts/` if needed

**Risks / gotchas**
- An attacker string that contains the delimiter closes the section early and lets the rest of the text look like instructions. Escaping is mandatory.

**Open questions**
None

**Traceability**
R-217–R-221 · Record §3.3, §6.11 · Proposal: Research Problem (controlled autonomy)

---

**[E7-08] Render a one-page incident report from each verdict**
**Type:** Task · **Epic:** EPIC-7 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E7-05, E7-06 · **Blocks:** E10-05

**Context**
The architecture promises the human one clear report with a suggestion, instead of many separate alerts (Arch §2, §5 step 8), and the brief asks for incident reports. In round 1 this lived only in the console, which is first on the descope list (C-12). This ticket makes the report exist on its own.

**Goal**
Every accepted verdict can be rendered as a one-page Markdown report that a human reads in under a minute.

**Scope**
- In: a Markdown template, rendering from `Verdict` plus findings plus audit record, evidence resolved to alert summaries, a "recommendation only, a human decides" line.
- Out: the console (EPIC-10), PDF output, editing the report.

**Technical notes**
- The agent recommends and never executes; the report says so (§1.1, Arch §1).
- Evidence is shown by resolving alert IDs to short summaries, not by quoting raw attacker text without delimiters.
- ASSUMPTION: Markdown output, so it can be read directly or embedded by the console.

**Acceptance criteria**
- Given an accepted verdict, when `render_report()` runs, then `reports/<bundle_id>.md` contains: incident type, severity, affected device, recommended action, confidence, evidence list, the key findings and the line "This is a recommendation. A human decides."
- Given a rendered report, when its length is measured, then it is under 400 words.
- [ ] `thesis/report/render.py` exists.

**Checklist**
- [ ] Write the template.
- [ ] Resolve evidence IDs.
- [ ] Render.
- [ ] Write the tests.
- [ ] Render three pilot examples for the thesis appendix.

**Deliverables**
`thesis/report/render.py`, `thesis/report/template.md`, `tests/test_report.py`, three example reports in `docs/examples/`

**Risks / gotchas**
- Attacker text pasted into the report can contain Markdown that breaks rendering. Escape it.

**Open questions**
None

**Traceability**
R-041, R-044, R-045 · Record §1.1 · Arch §1, §2, §5 · Brief: Generative AI Dimension (incident reports)


# Step D — EPIC-8 · Baselines (A: ML+rules, B: prompt-only)

4 tickets · 9 points · Project DoD v1.0 and DoR apply to every ticket.

**Ticket-level dependency added (C-18):** E8-04 depends on E6-01, because Baseline B uses the same LLM client. The epic order is unchanged.

**Scheduling note:** E8-01 is `freeze-before-results` and blocks E6-03, so it must be done during Phase A or B, well before the rest of this epic.

**Suggested execution order:** E8-01 (early) … E8-02 ∥ E8-03 → E8-04

---

**[E8-01] Define the cited severity→action lookup for Baseline A**
**Type:** Research · **Epic:** EPIC-8 · **Priority:** High · **Points:** 2 · **Labels:** research, freeze-before-results
**Depends on:** E0-04, E1-03 · **Blocks:** E8-02, E6-03

**Context**
Baseline A is a classifier, so on its own it cannot recommend anything. A severity→action lookup gives it a response, which makes H4's safety comparison well-posed (record risk #6). The lookup must be fixed before any agent output, so it cannot be tuned to make the agent look better or worse.

**Goal**
A frozen lookup maps each (family, severity) to exactly one catalog action, with a citation for each mapping.

**Scope**
- In: the lookup table, citations, a completeness test, the version tag.
- Out: running Baseline A (E8-02), changing the catalog or the action sets.

**Technical notes**
- Baseline A gets a severity→action lookup (§6.6).
- Actions come from catalog-v0.1; citations from the same sources as the catalog (§3.4).
- ASSUMPTION: Baseline A's severity comes from a fixed rule over the classifier's score, defined here.

**Acceptance criteria**
- [ ] `knowledge/baseline_a_lookup.yaml` maps every (family or benign, severity) pair to one catalog action ID, each with a citation.
- [ ] The file states the fixed rule that turns the classifier's score into a severity.
- [ ] `tests/test_baseline_a_lookup.py` fails if any pair is missing or any action ID is not in the catalog, and passes on the committed file.
- [ ] Git tag `baseline-a-lookup-v1.0` exists, and its date is earlier than the first node-1 call on corpus bundles.

**Checklist**
- [ ] Define the severity rule.
- [ ] Map every pair.
- [ ] Add citations.
- [ ] Write the test.
- [ ] Tag the commit.

**Deliverables**
`knowledge/baseline_a_lookup.yaml`, `tests/test_baseline_a_lookup.py`

**Risks / gotchas**
- Mapping every pair to the most cautious action makes Baseline A look "safe" by construction. Map each pair to the action the cited source recommends.

**Open questions**
None

**Traceability**
R-227 · Record §3 (risk #6), §6.6 · Proposal: H4

---

**[E8-02] Implement the Baseline A strategy behind ExperimentConfig**
**Type:** Task · **Epic:** EPIC-8 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E4-03, E8-01, E3-09, E0-09 · **Blocks:** E9-01

**Context**
Baseline A answers "is an LLM needed at all?" (record §6.6). It must run on the same bundles and the same reduced view as the agent, or H4 is contaminated (§4.1).

**Goal**
`strategy = ml_classifier` produces a verdict-shaped result for any bundle, using only the frozen classifier and the frozen lookup.

**Scope**
- In: the strategy implementation, the bundle-level aggregation rule from E0-05, mapping to `Verdict` fields, a smoke run on training-split bundles.
- Out: retraining (frozen in E4-03), evaluation-split runs (E9-09), any LLM call.

**Technical notes**
- Same reduced view as the agent (§4.1, E0-05).
- Uses the frozen classifier (`baseline-a-v1.0`) and lookup (`baseline-a-lookup-v1.0`).

**Acceptance criteria**
- Given a bundle and `strategy = ml_classifier`, when the strategy runs, then it returns `incident_type`, severity, affected device and recommended action, and makes no LLM call.
- Given the same bundle twice, when the strategy runs, then both results are identical.
- Given the model file, when its SHA-256 is checked at load time, then it matches the hash recorded in E4-03, or the run aborts.
- [ ] `thesis/baselines/baseline_a.py` exists.

**Checklist**
- [ ] Load the frozen model and check its hash.
- [ ] Apply the aggregation rule.
- [ ] Apply the lookup.
- [ ] Map to `Verdict` fields.
- [ ] Smoke-run on training bundles.

**Deliverables**
`thesis/baselines/baseline_a.py`, `tests/test_baseline_a.py`

**Risks / gotchas**
- Baseline A cannot produce evidence references. Decide in E0-12 how its evidence field is scored, and do not invent evidence here.

**Open questions**
None

**Traceability**
R-014, R-103, R-225 · Record §4.1, §6.6 · Proposal: Methodology (Baseline A), H4

---

**[E8-03] Write the prompt-only prompt for Baseline B**
**Type:** Research · **Epic:** EPIC-8 · **Priority:** High · **Points:** 3 · **Labels:** research, engineering, needs-refinement
**Depends on:** E6-02, E7-01 · **Blocks:** E8-04

**Context**
Baseline B answers "does the agentic architecture help, or is the model just good?" (record §6.6). If its prompt is weak, the agent wins for the wrong reason and H2 proves nothing. It gets a well-written prompt and the same output schema.

**Goal**
One versioned prompt asks the same model for a full `Verdict` in a single call, written to the same quality standard as the agent's prompts.

**Scope**
- In: one template with role, schema, catalog and bundle; a version string; a review against the agent's prompts for equal quality.
- Out: tools, retrieval, multi-step reasoning, the safety layer, tuning on evaluation bundles.

**Technical notes**
- Same model, one request, no reasoning steps, tools, retrieval or safety layer (§6.6).
- Same output schema as the agent (§6.6).
- Same reduced view and static-prefix order (§4.1, §4.4).
- Develop on pilot or training-split bundles only.

**Acceptance criteria**
- Given a pilot bundle, when the Baseline B prompt is rendered and sent, then the completion parses into `Verdict` at a rate recorded in `docs/baselines/baseline_b_prompt.md`.
- [ ] `thesis/prompts/templates/baseline_b.*` has a `TEMPLATE_VERSION`.
- [ ] `docs/baselines/baseline_b_prompt.md` explains, section by section, why each instruction is there, and lists what the agent has that Baseline B deliberately lacks.
- [ ] The input-token count of the rendered prompt is within the frozen ceiling.

**Checklist**
- [ ] Draft the prompt.
- [ ] Add the schema and catalog.
- [ ] Test on pilot bundles.
- [ ] Write the rationale document.
- [ ] Check the token count.

**Deliverables**
`thesis/prompts/templates/baseline_b.*`, `docs/baselines/baseline_b_prompt.md`

**Risks / gotchas**
- Iterating the Baseline B prompt less than the agent's prompts makes it weaker by neglect. Give it the same number of revision rounds, and record them.
- May change after the spike: the spike's single-call setup is effectively a first Baseline B, so its findings apply directly.

**Open questions**
"Are two baselines sufficient?" (§10). Recorded in E0-03; this ticket builds Baseline B either way.

**Traceability**
R-228, R-230, R-232 · Record §4.1, §4.4, §6.6 · Proposal: Methodology (prompt-only LLM), H2

---

**[E8-04] Implement the Baseline B strategy behind ExperimentConfig**
**Type:** Task · **Epic:** EPIC-8 · **Priority:** Medium · **Points:** 2 · **Labels:** engineering
**Depends on:** E8-03, E6-01, E3-09, E0-09 · **Blocks:** E9-01

**Context**
`strategy = prompt_only` must use the same model, the same client and the same bundles as the agent, so the only difference measured in H2 is the architecture (record §6.6).

**Goal**
`strategy = prompt_only` makes exactly one LLM call per bundle and returns a parsed verdict, logged like every other call.

**Scope**
- In: the strategy implementation, one call through the shared client, parsing, logging, a smoke run on training bundles.
- Out: the safety layer, retries beyond the client's network retries, evaluation runs.

**Technical notes**
- Same base model as the agent (proposal Methodology, H2).
- One call, no tools, no retrieval, no safety layer (§6.6).
- Same alerts as the agent (proposal Methodology).

**Acceptance criteria**
- Given a bundle and `strategy = prompt_only`, when the strategy runs, then the client logs exactly one call for that bundle and repetition.
- Given the config, when it runs, then the model name and revision in the call log equal those used by the agentic strategy.
- [ ] `thesis/baselines/baseline_b.py` exists.

**Checklist**
- [ ] Implement the strategy.
- [ ] Call through the shared client.
- [ ] Parse into `Verdict`.
- [ ] Write the two tests.
- [ ] Smoke-run on training bundles.

**Deliverables**
`thesis/baselines/baseline_b.py`, `tests/test_baseline_b.py`

**Risks / gotchas**
- A parse failure must be recorded as a result (invalid output), not retried until it succeeds. Otherwise Baseline B gets a hidden safety layer.

**Open questions**
None

**Traceability**
R-014, R-149, R-228, R-229 · Record §6.6 · Proposal: Methodology (prompt-only LLM), H2


# Step D — EPIC-9 · Evaluation Harness & Experiments H1–H4

12 tickets · 32 points committed + 3 points stretch (E9-12) · Project DoD v1.0 and DoR apply to every ticket.

**Suggested execution order:** E9-01 → E9-02 → E9-03 ∥ E9-04 ∥ E9-06 ∥ E9-07 → E9-05 → E9-08 → E9-09 → E9-10 → E9-11 → (E9-12 if go)

---

**[E9-01] Build the condition-matrix runner with concurrency and resume**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 5 · **Labels:** engineering
**Depends on:** E6-06, E7-06, E8-02, E8-04, E0-03 · **Blocks:** E9-02, E9-08

**Context**
The runner executes every (bundle, condition, repetition) in the frozen matrix (record §6.1). It is the measurement rig the thesis rests on (§1). It must survive interruptions without duplicating or losing calls, because a full run is about 12,000 calls.

**Goal**
One command runs the frozen condition matrix over the evaluation bundles, with bounded concurrency, and resumes after any interruption without repeating finished work.

**Scope**
- In: reading `config/conditions.yaml` and k, iterating bundles, conditions and repetitions, bounded concurrency, backoff, a completion ledger for resume, a dry-run mode that counts calls and estimates cost.
- Out: metric computation (E9-03 to E9-07), changing the matrix (METHODS.md changelog), distributed execution.

**Technical notes**
- Conditions come only from `ExperimentConfig` and `conditions.yaml` (§6.1).
- Paired design: every condition runs on the same bundles (proposal Methodology).
- Retries use backoff; the provider cap stays active (§4.4.1).
- ASSUMPTION: concurrency is capped at a value set in ADR-001, to stay under provider rate limits.

**Acceptance criteria**
- Given the frozen matrix, when `python -m thesis.eval.run --dry-run` runs, then it prints the number of calls and the estimated cost, and the call count equals bundles × (3 × agentic conditions + 1 × prompt-only) × k.
- Given a run killed halfway, when it is restarted, then no (bundle, condition, repetition) completed before the kill is called again, and the final ledger has every item exactly once.
- Given any condition, when the run finishes, then every evaluation bundle has a result for every repetition of that condition.
- [ ] `thesis/eval/run.py` and `thesis/eval/ledger.py` exist.

**Checklist**
- [ ] Load the matrix.
- [ ] Write the iteration.
- [ ] Add bounded concurrency.
- [ ] Write the ledger.
- [ ] Add resume.
- [ ] Add dry-run.
- [ ] Write the kill-and-resume test with a mocked client.

**Deliverables**
`thesis/eval/run.py`, `thesis/eval/ledger.py`, `tests/test_eval_runner.py`

**Risks / gotchas**
- Resume that is keyed only by bundle ID repeats or skips conditions. Key the ledger by (bundle, config hash, repetition).
- Concurrency higher than the provider's limit causes 429 storms that look like model failures.

**Open questions**
None

**Traceability**
R-002, R-019, R-142, R-235–R-239, R-263 · Record §1, §4.4.1, §6.1 · Proposal: Methodology (paired design)

---

**[E9-02] Write results to Parquet with full provenance**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 2 · **Labels:** engineering
**Depends on:** E9-01, E0-09 · **Blocks:** E9-03, E9-04, E9-06, E9-07

**Context**
Every result row must carry its config, config hash and full provenance (record §6.1, §4.2). This is what makes every number in the thesis traceable to an exact model, prompt and bundle.

**Goal**
Every (bundle, condition, repetition) produces one result row with the verdict, the ground truth, the cost data and the full provenance.

**Scope**
- In: the result row schema, writing Parquet, joining ground truth labels and episode IDs, per-call token and latency sums.
- Out: metric computation, plots.

**Technical notes**
- One row per (bundle, condition, repetition), with full provenance (§6.7).
- Provenance: model name and revision, provider, sampling params, seed, prompt template version, graph version, config hash (§4.2).
- Per-call tokens and latency go into the same rows as the metrics (§4.4).

**Acceptance criteria**
- Given a completed run, when `results/run_<id>.parquet` is read, then every row has non-null config hash, model revision, template version, bundle ID, episode ID, ground-truth label, predicted fields, tokens in, tokens out and latency.
- Given two rows for the same bundle and repetition under different conditions, when they are compared, then their bundle ID and ground-truth label are identical.
- [ ] `thesis/eval/results.py` defines the row schema.

**Checklist**
- [ ] Define the schema.
- [ ] Join ground truth.
- [ ] Sum tokens and latency per row.
- [ ] Write Parquet.
- [ ] Write the tests.

**Deliverables**
`thesis/eval/results.py`, `tests/test_results.py`

**Risks / gotchas**
- A rejected-then-accepted attempt has several calls. Decide which calls a row's tokens include, consistently with E0-11.

**Open questions**
None

**Traceability**
R-134, R-153, R-172, R-262 · Record §4.2, §4.4, §6.1, §6.7 · Proposal: Methodology

---

**[E9-03] Compute detection and classification metrics**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research, engineering
**Depends on:** E9-02 · **Blocks:** E9-05, E9-09

**Context**
Detection and classification are the first two outcomes of the central research question. The proposal fixes their metrics: precision, recall and F1 for detection, accuracy and macro-F1 for classification.

**Goal**
One function computes the frozen detection and classification metrics per condition from the results Parquet.

**Scope**
- In: binary detection (attack vs benign), multi-class classification, per-condition and per-family breakdowns, bundle level as primary.
- Out: safety metrics (E9-04), significance tests (E9-05), confidence intervals (E9-06).

**Technical notes**
- Detection: precision, recall, F1. Classification: accuracy, macro-F1 (proposal Methodology).
- Bundle-level metrics are primary (§4.1).
- Invalid or unparsed outputs count as wrong, never dropped, unless METHODS.md says otherwise.

**Acceptance criteria**
- Given a hand-built results table with known counts, when `compute_detection()` and `compute_classification()` run, then they return the hand-computed values exactly.
- Given a row whose output failed to parse, when metrics are computed, then it counts as an incorrect prediction.
- [ ] `thesis/eval/metrics.py` defines both functions.

**Checklist**
- [ ] Write the detection metrics.
- [ ] Write the classification metrics.
- [ ] Add per-family breakdown.
- [ ] Handle invalid outputs.
- [ ] Write the hand-computed tests.

**Deliverables**
`thesis/eval/metrics.py`, `tests/test_metrics.py`

**Risks / gotchas**
- Dropping invalid outputs from the denominator makes a model that often fails to answer look more accurate.

**Open questions**
None

**Traceability**
R-012, R-019, R-021, R-243, R-244, R-256, R-263 · Record §4.1 · Proposal: Methodology (metrics), H2, H4

---

**[E9-04] Compute safety, usefulness and reliability metrics**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research, engineering
**Depends on:** E9-02, E0-12, E0-13, E1-03 · **Blocks:** E9-05, E9-09

**Context**
H3's real result is contextual appropriateness, not action-space membership, which is true by construction (risk #3). This ticket implements exactly the formulas frozen in E0-12 and E0-13. It also covers the "reliability" promised in Objective 5.

**Goal**
One function computes schema validity, action-space membership, contextual appropriateness, usefulness and reliability per condition, exactly as frozen.

**Scope**
- In: the three safety metrics, usefulness against the acceptable sets, the reliability formula, per-condition and per-family breakdowns.
- Out: changing any formula, significance tests (E9-05).

**Technical notes**
- Formulas from METHODS.md "Safety scoring" (E0-12) and "Reliability and robustness" (E0-13).
- Acceptable and unsafe sets from `action-sets-v1.0` (E1-03).
- Membership is reported, never the headline (§3.1).

**Acceptance criteria**
- Given a hand-built results table with known actions per family, when `compute_safety()` runs, then each of the three safety metrics and usefulness equal the hand-computed values.
- Given k repetitions with known verdicts, when `compute_reliability()` runs, then it returns the hand-computed agreement.
- [ ] Each function's docstring quotes the METHODS.md section it implements.

**Checklist**
- [ ] Implement the three safety metrics.
- [ ] Implement usefulness.
- [ ] Implement reliability.
- [ ] Write the hand-computed tests.

**Deliverables**
Additions to `thesis/eval/metrics.py`, `tests/test_safety_metrics.py`

**Risks / gotchas**
- If `logging_only` lets free-text actions through, they need the E0-12 mapping before scoring. Unmapped actions must be scored as the mapping says, never guessed.

**Open questions**
None

**Traceability**
R-009, R-013, R-019–R-022, R-245, R-246, R-249–R-251, R-263 · Record §3.1 · Proposal: H3, Objective 5, Methodology (metrics)

---

**[E9-05] Run the paired McNemar and Wilcoxon tests**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research
**Depends on:** E9-03, E9-04 · **Blocks:** E9-10, E9-11

**Context**
All four hypotheses claim "significantly". The comparisons are paired because every condition sees the same bundles (proposal Methodology). The tests and any correction were frozen in METHODS.md before results existed.

**Goal**
One function produces, for each hypothesis comparison, the test statistic, p-value and effect size, using the tests frozen in METHODS.md.

**Scope**
- In: McNemar for paired binary outcomes, Wilcoxon signed-rank for paired scores, the declared multiple-comparison correction if any, a results table per hypothesis.
- Out: confidence intervals (E9-06), choosing tests after seeing results.

**Technical notes**
- McNemar and Wilcoxon (§10), as frozen in E0-03.
- Pairing is by (bundle, repetition) across conditions.

**Acceptance criteria**
- Given a constructed paired dataset with a known McNemar result, when the function runs, then its statistic and p-value match the reference values to 4 decimal places.
- Given the frozen matrix, when the function runs, then it produces one row for each comparison listed in METHODS.md, and no comparison not listed there.
- [ ] `thesis/eval/stats.py` defines the tests.

**Checklist**
- [ ] Implement McNemar.
- [ ] Implement Wilcoxon.
- [ ] Apply the declared correction.
- [ ] List comparisons from METHODS.md.
- [ ] Write the reference tests.

**Deliverables**
`thesis/eval/stats.py`, `tests/test_stats.py`

**Risks / gotchas**
- Adding comparisons after seeing results is p-hacking. The second criterion prevents it.

**Open questions**
None

**Traceability**
R-002, R-008, R-010–R-014, R-019, R-235, R-254, R-255, R-263 · Record §10 · Proposal: Hypotheses H1–H4, Methodology

---

**[E9-06] Implement the episode-level block bootstrap**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research
**Depends on:** E9-02 · **Blocks:** E9-10, E9-11

**Context**
A four-minute attack produces four bundles that are not independent, so bundle-level tests overstate significance slightly (record §4.1). Resampling whole episodes gives honest confidence intervals.

**Goal**
Every reported metric and difference gets a confidence interval from resampling attack episodes, not bundles.

**Scope**
- In: block bootstrap with the episode as resampling unit, benign bundles handled per METHODS.md, a fixed number of resamples and seed.
- Out: changing the primary bundle-level metrics.

**Technical notes**
- Episode as the resampling unit (§4.1).
- ASSUMPTION: 2,000 resamples, seeded.

**Acceptance criteria**
- Given a constructed dataset where every episode has one bundle, when the bootstrap runs, then its interval matches an ordinary bootstrap within 0.01.
- Given the same seed, when it runs twice, then both intervals are identical.
- [ ] `thesis/eval/bootstrap.py` exists.

**Checklist**
- [ ] Implement episode resampling.
- [ ] Handle benign bundles.
- [ ] Seed it.
- [ ] Write the two tests.

**Deliverables**
`thesis/eval/bootstrap.py`, `tests/test_bootstrap.py`

**Risks / gotchas**
- Benign bundles have no episode. Treating each as its own block is one choice; state it in METHODS.md.

**Open questions**
None

**Traceability**
R-257, R-263 · Record §4.1 · Proposal: Methodology (paired statistical tests)

---

**[E9-07] Report cost and latency per incident**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** Medium · **Points:** 2 · **Labels:** research
**Depends on:** E9-02 · **Blocks:** E9-09, E9-11

**Context**
Cost per incident analysed is a publishable result that none of [16], [18] or [19] report (record §4.4). It is computed from the call logs that exist from the first call.

**Goal**
A table gives tokens, euros and seconds per bundle for every condition.

**Scope**
- In: aggregation of tokens and latency per row, conversion to euros using the dated ADR-001 prices, a table per condition.
- Out: optimising cost, comparing providers.

**Technical notes**
- Cost per incident is a result (§4.4).
- Prices come from ADR-001, with their date.

**Acceptance criteria**
- Given a results file, when `python -m thesis.eval.cost` runs, then `results/cost_per_incident.csv` lists, per condition, mean and median input tokens, output tokens, euros and seconds per bundle.
- Given a hand-built row set, when the cost is computed, then it equals the hand-computed euros.
- [ ] The price date is written in the CSV header.

**Checklist**
- [ ] Aggregate tokens and latency.
- [ ] Apply prices.
- [ ] Write the table.
- [ ] Write the test.

**Deliverables**
`thesis/eval/cost.py`, `results/cost_per_incident.csv`, `tests/test_cost.py`

**Risks / gotchas**
- Rejected attempts cost tokens too. Include them, or the safety layer looks free.

**Open questions**
None

**Traceability**
R-122, R-261 · Record §4.4 · Proposal: none (contribution beyond the proposal)

---

**[E9-08] Run the exploratory partial matrix**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 2 · **Labels:** research, infra
**Depends on:** E9-01, E9-02, E9-03, E9-04, E9-07, E6-08 · **Blocks:** E9-09

**Context**
The budget includes one exploratory partial run before the full matrix (record §4.4.1). It catches bugs and confirms cost while a mistake is still cheap. Its numbers are discarded.

**Goal**
A small slice of the matrix runs end to end through every metric, and its measured cost confirms the full run fits the budget.

**Scope**
- In: a slice of about 10 % of bundles, every condition, k = 1, the full metric pipeline, a cost check.
- Out: reporting any of these numbers, changing prompts or parameters based on its results (a changelog entry and a rerun if it happens).

**Technical notes**
- One exploratory partial run before the full matrix (§4.4.1).
- ASSUMPTION: the slice is drawn by seed from the evaluation set; numbers are never reported.

**Acceptance criteria**
- Given the slice, when the run finishes, then every metric function produced output with no error.
- [ ] `docs/eval/exploratory_run.md` records actual euros spent, projected euros for k full runs, bugs found and fixed, and confirms no prompt or parameter changed. If one changed, the changelog entry is linked.
- [ ] The projected total is within the remaining budget under the cap.

**Checklist**
- [ ] Draw the slice.
- [ ] Run it.
- [ ] Run all metrics.
- [ ] Project cost.
- [ ] Write the note.

**Deliverables**
`docs/eval/exploratory_run.md`

**Risks / gotchas**
- Seeing exploratory numbers tempts prompt changes. Any change after this point is a locked-parameter change.

**Open questions**
None

**Traceability**
R-143, R-259 · Record §4.4.1 · Proposal: none (engineering)

---

**[E9-09] Run the full matrix k times**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** Highest · **Points:** 3 · **Labels:** research, infra
**Depends on:** E9-08 · **Blocks:** E9-10, E9-11, E9-12

**Context**
This produces every number the thesis reports. It runs on the hosted experiment model, under the spending cap, with k repetitions as frozen in METHODS.md (record §4.4.1).

**Goal**
The complete frozen matrix has run k times on the evaluation bundles, with every result row present and the spend recorded.

**Scope**
- In: k full runs, verification that every row exists, the spend record, archiving the results with their hashes.
- Out: any change to prompts, parameters or bundles between repetitions.

**Technical notes**
- k is the single number frozen in E0-03 (C-03).
- Hosted open-weights model pinned by revision (§4.2); cap active (§4.4.1).

**Acceptance criteria**
- Given the frozen matrix, when all k runs finish, then the results Parquet has exactly bundles × conditions × k rows.
- Given the call logs, when the model revision is checked, then every call used the revision pinned in ADR-001.
- [ ] `results/` files are hashed, and the hashes are written in `docs/thesis_notes.md`.
- [ ] Actual spend is recorded in `docs/eval/full_run.md`.

**Checklist**
- [ ] Check the cap.
- [ ] Run k times.
- [ ] Check row counts.
- [ ] Check revisions.
- [ ] Hash and archive.
- [ ] Record spend.

**Deliverables**
`results/*.parquet`, `docs/eval/full_run.md`, hashes in `docs/thesis_notes.md`

**Risks / gotchas**
- A provider-side model update mid-run splits the results across two models. The revision check catches it.

**Open questions**
None

**Traceability**
R-143, R-260 · Record §4.2, §4.4.1 · Proposal: Methodology

---

**[E9-10] Analyze H1 stratified by attack family**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research
**Depends on:** E9-09, E9-05, E9-06 · **Blocks:** E9-11

**Context**
Without stratification, H1 confirms itself trivially, because some families are invisible to some sources (risk #4). The analysis must separate gain from fusion from gain from simply having a source. It also shows where the agent is reliable and where it is not (proposal Expected Outcomes).

**Goal**
H1 results are reported per family and visibility group, with and without honeypot-keyed bundles, as METHODS.md specifies.

**Scope**
- In: per-family results per source condition, grouping by visibility (one, two, three sources), the honeypot with-and-without split, a reliability-by-family view.
- Out: new conditions, new statistical tests beyond METHODS.md.

**Technical notes**
- Stratify by attack family (§3.2).
- Honeypot all-positive handling as frozen in E0-03.
- Over-compression can hide fusion (§4.4); note the reduction ratio next to H1 results.

**Acceptance criteria**
- [ ] `results/h1_stratified.csv` gives, per family and per source condition, the detection and classification metrics with episode-bootstrap intervals.
- [ ] `docs/eval/h1_analysis.md` states, for each visibility group, whether the all-sources condition beats the best single source, with the test result.
- [ ] The same document reports the results with and without honeypot-keyed bundles.
- [ ] Key numbers are appended to `docs/thesis_notes.md`.

**Checklist**
- [ ] Group by family and visibility.
- [ ] Compute per-group results.
- [ ] Apply the honeypot split.
- [ ] Write the analysis.
- [ ] Add thesis notes.

**Deliverables**
`results/h1_stratified.csv`, `docs/eval/h1_analysis.md`

**Risks / gotchas**
- Small per-family counts give wide intervals. Report the intervals, not only the point estimates.

**Open questions**
None

**Traceability**
R-007, R-011, R-025, R-106, R-240, R-253 · Record §3.2, §4.4 · Proposal: H1, Expected Outcomes

---

**[E9-11] Produce the results tables and figures for H1–H4**
**Type:** Task · **Epic:** EPIC-9 · **Priority:** High · **Points:** 3 · **Labels:** research, writing
**Depends on:** E9-05, E9-06, E9-07, E9-10 · **Blocks:** E11-07, E11-08

**Context**
The results chapters need tables and figures that answer each hypothesis. Generating them by script from the Parquet files means every number in the thesis can be regenerated, and none is typed by hand.

**Goal**
One script regenerates every results table and figure for H1–H4 and cost from the frozen results files.

**Scope**
- In: one table per hypothesis, the cost table, the figures, export to the thesis folder.
- Out: interpretation (EPIC-11), new analyses.

**Technical notes**
- Results come only from the hashed `results/` files (E9-09).
- Negative results are reported with the same prominence as positive ones (proposal Expected Outcomes).

**Acceptance criteria**
- Given the results files, when `python -m thesis.eval.report` runs, then it writes every table and figure listed in `docs/eval/outputs.md` into `docs/thesis/figures/` and `docs/thesis/tables/`.
- Given the same results files, when the script runs twice, then the tables are byte-identical.
- [ ] `docs/eval/outputs.md` lists each output with the hypothesis it answers.

**Checklist**
- [ ] List the outputs per hypothesis.
- [ ] Write the tables.
- [ ] Write the figures.
- [ ] Export.
- [ ] Check reproducibility.

**Deliverables**
`thesis/eval/report.py`, `docs/thesis/figures/*`, `docs/thesis/tables/*`, `docs/eval/outputs.md`

**Risks / gotchas**
- A figure edited by hand after generation breaks traceability. Fix the script instead.

**Open questions**
None

**Traceability**
R-006, R-024 · Record §1 · Proposal: Central Research Question, Expected Outcomes

---

**[E9-12] Run the prompt-injection experiment (stretch)**
**Type:** Research · **Epic:** EPIC-9 · **Priority:** Low · **Points:** 3 · **Labels:** research
**Depends on:** E9-09, E7-07 · **Blocks:** None

**Context**
No related work ([16], [18], [19]) tests prompt injection through honeypot text. A small experiment would be a novel sub-contribution strengthening H3 (record §3.3). It is stretch only and runs only if ahead of schedule. Its 3 points are excluded from the committed total.

**Goal**
If the go/no-go check passes, the share of injected bundles whose recommendation is steered outside the permitted action set is measured with safety on and off.

**Scope**
- In: a go/no-go decision on a fixed date, a small set of injected honeypot sessions, safety on and off, the steering rate.
- Out: new attack families, changing the defensive design, more than one model.

**Technical notes**
- Stretch only; run only if ahead (§3.3, §5).
- ASSUMPTION (C-11): the go/no-go date is the end of Sprint 3 (13 Nov 2026), because "month four" from the July proposal falls in the last sprint.
- Injected sessions are new bundles, kept separate from the frozen evaluation set.

**Acceptance criteria**
- [ ] `docs/eval/injection_go_no_go.md` records the decision on or before 13 Nov 2026, with the remaining points and days as evidence.
- [ ] If go: `results/injection.csv` reports the steering rate with safety on and off, with intervals.
- [ ] If no-go: E11-09 lists the experiment as future work.

**Checklist**
- [ ] Hold the go/no-go check on the date.
- [ ] If go: build the injected sessions.
- [ ] Run both safety modes.
- [ ] Compute the rate.
- [ ] Write the result or the future-work line.

**Deliverables**
`docs/eval/injection_go_no_go.md`, `results/injection.csv` (if go)

**Risks / gotchas**
- Starting this before the core results exist puts the thesis at risk for a bonus. The date check exists to stop that.

**Open questions**
None

**Traceability**
R-222, R-223 · Record §3.3, §5 · Proposal: H3


# Step D — EPIC-10 · SOC Console (FastAPI + React)

7 tickets · 17 points · Project DoD v1.0 and DoR apply to every ticket.

**Console share:** 17 of 257 engineering points = 6.6 %. Cap: about 10 % (record §5).
**Position:** first item on the descope list. E7-08 keeps the human-readable report alive if this epic is cut (C-12).

**Suggested execution order:** E10-01 → E10-02 ∥ E10-03 → E10-04 ∥ E10-07 → E10-05 → E10-06

---

**[E10-01] Expose results and the audit log through FastAPI REST**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 3 · **Labels:** engineering
**Depends on:** E9-02, E7-05, E7-01 · **Blocks:** E10-02, E10-03

**Context**
The console demonstrates the result; it produces no data for any hypothesis (record §2, §5). The API reads what the experiments already wrote. Because the safety schema and the API schema are the same Pydantic object, the contract cannot drift (§6.2).

**Goal**
A localhost-only FastAPI service serves incidents, verdicts, reports and audit records read-only, plus one endpoint to store a human accept or reject.

**Scope**
- In: read endpoints over the results Parquet, reports and audit log; one write endpoint for the human decision into SQLite; localhost binding.
- Out: authentication, any endpoint that acts on the testbed or any network, running experiments from the API.

**Technical notes**
- FastAPI (§6.2); `Verdict` reused as the response model (§6.2).
- No authentication; binds to localhost (§4, §6.8).
- Console state in SQLite (§6.7).
- The system recommends and never executes (§1.1).

**Acceptance criteria**
- Given the service running, when `GET /incidents` is called, then it returns every evaluated bundle with verdict fields typed as `Verdict`.
- Given the service config, when it starts, then it binds only to 127.0.0.1 (test asserts the bind address).
- Given the route table, when it is listed in a test, then the only non-GET route is the human-decision endpoint, and it writes only to SQLite.
- [ ] `thesis/api/app.py` exists.

**Checklist**
- [ ] Write the read endpoints.
- [ ] Write the decision endpoint.
- [ ] Bind to localhost.
- [ ] Write the route and bind tests.

**Deliverables**
`thesis/api/app.py`, `thesis/api/db.py`, `tests/test_api.py`

**Risks / gotchas**
- Adding a "convenience" endpoint that triggers a run or touches the testbed breaks the recommend-only claim. The route test guards it.

**Open questions**
None

**Traceability**
R-156, R-157, R-159, R-178, R-294 · Record §2, §4, §5, §6.2, §6.7, §6.8 · Proposal: none (demonstration)

---

**[E10-02] Stream the reasoning trace over SSE**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 2 · **Labels:** engineering
**Depends on:** E10-01 · **Blocks:** E10-05

**Context**
The trace shows the three reasoning steps behind a verdict, which is what makes the agent's evidence visible. Traffic is one-way, so Server-Sent Events are enough (record §6.2).

**Goal**
The detail screen can stream a recorded trace node by node from one SSE endpoint.

**Scope**
- In: one SSE endpoint that replays a recorded trace from the logs.
- Out: live model calls from the console, WebSockets.

**Technical notes**
- REST for commands, SSE for the reasoning trace (§6.2).
- Replays recorded traces only; the console never calls the model.

**Acceptance criteria**
- Given a bundle with a recorded trace, when `GET /incidents/{id}/trace` is opened, then three events arrive in order evidence, classify, recommend, then the stream closes.
- Given a bundle with no trace (for example Baseline A), when the endpoint is opened, then it returns 404.

**Checklist**
- [ ] Read the trace from the logs.
- [ ] Write the SSE endpoint.
- [ ] Mark attacker text in events so the frontend escapes it.
- [ ] Write the two tests.

**Deliverables**
Additions to `thesis/api/app.py`, `tests/test_trace_sse.py`

**Risks / gotchas**
- Streaming full prompts sends attacker text to the browser. Escape it on display.

**Open questions**
None

**Traceability**
R-159 · Record §6.2 · Proposal: none (demonstration)

---

**[E10-03] Generate TypeScript types with openapi-typescript**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 1 · **Labels:** engineering
**Depends on:** E10-01 · **Blocks:** E10-04, E10-07

**Context**
Generated types make a schema change break the frontend build instead of failing silently at runtime (record §6.2).

**Goal**
The frontend's API types are generated from the OpenAPI schema, and a schema change breaks the build.

**Scope**
- In: the generation script, the generated types, a build step that fails on mismatch.
- Out: hand-written API types.

**Technical notes**
- openapi-typescript generates TS types from the OpenAPI schema (§6.2).
- ASSUMPTION: the React build tool is recorded in a short ADR-004 here, since the record names React but no build tool (DoD).

**Acceptance criteria**
- Given a field renamed in `Verdict`, when the frontend build runs after regeneration, then it fails at compile time.
- [ ] `frontend/src/api/types.ts` is generated, not edited by hand (header comment says so).
- [ ] `docs/adr/0004-frontend-build.md` is Accepted.

**Checklist**
- [ ] Write the ADR.
- [ ] Add the generation script.
- [ ] Generate the types.
- [ ] Prove the rename breaks the build.

**Deliverables**
`frontend/package.json`, `frontend/src/api/types.ts`, `docs/adr/0004-frontend-build.md`

**Risks / gotchas**
- Forgetting to regenerate after a schema change hides the mismatch. Put the generation in the build script.

**Open questions**
None

**Traceability**
R-160 · Record §6.2 · Proposal: none (demonstration)

---

**[E10-04] Build the incident list screen**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 3 · **Labels:** engineering
**Depends on:** E10-03 · **Blocks:** E10-05

**Context**
The first of the four screens the record allows (§5). It lets the human see every analysed bundle at a glance.

**Goal**
One screen lists every incident with its verdict, severity and device, and filters by condition.

**Scope**
- In: the list, sorting by severity, a condition filter, links to the detail screen.
- Out: editing, live updates, more than the four allowed screens.

**Technical notes**
- React, kept thin (§6.2). Four screens maximum (§5).

**Acceptance criteria**
- Given the API running with results, when the list screen loads, then it shows one row per incident with type, severity, device and condition.
- Given a condition selected in the filter, when the list updates, then only incidents of that condition are shown.

**Checklist**
- [ ] Build the table.
- [ ] Add sorting.
- [ ] Add the filter.
- [ ] Link rows to details.

**Deliverables**
`frontend/src/screens/IncidentList.tsx`

**Risks / gotchas**
- Loading thousands of rows at once freezes the page. Paginate on the server.

**Open questions**
None

**Traceability**
R-158, R-292 · Record §5, §6.2 · Proposal: none (demonstration)

---

**[E10-05] Build the incident detail screen with evidence and trace**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 3 · **Labels:** engineering
**Depends on:** E10-02, E10-04, E7-08 · **Blocks:** E10-06

**Context**
The second allowed screen. It shows the one clear report the architecture promises (Arch §2), plus the evidence and the reasoning trace behind it.

**Goal**
One screen shows an incident's report, its evidence resolved to alerts, and its streamed reasoning trace.

**Scope**
- In: the E7-08 report, the evidence list, the trace panel over SSE.
- Out: editing the verdict, re-running the agent.

**Technical notes**
- The report comes from E7-08; the console only displays it.
- Attacker text is escaped on display.

**Acceptance criteria**
- Given an incident, when its detail screen opens, then it shows the report, every evidence ID resolved to an alert summary, and the three trace steps.
- Given an evidence item containing HTML characters from attacker text, when it is displayed, then it renders as text, not markup.

**Checklist**
- [ ] Show the report.
- [ ] Resolve evidence.
- [ ] Add the trace panel.
- [ ] Add escaping.

**Deliverables**
`frontend/src/screens/IncidentDetail.tsx`

**Risks / gotchas**
- Rendering attacker text as HTML is a cross-site scripting hole in a security tool.

**Open questions**
None

**Traceability**
R-041, R-045, R-158, R-292 · Record §5 · Arch §2, §5 · Proposal: none (demonstration)

---

**[E10-06] Build the recommendation accept/reject screen**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 3 · **Labels:** engineering
**Depends on:** E10-05 · **Blocks:** None

**Context**
The third allowed screen. It makes "it suggests only, a human always decides" visible: the human accepts or rejects, and nothing executes (Arch §1).

**Goal**
The human can accept or reject a recommendation, and the decision is stored without any action being taken.

**Scope**
- In: the recommendation view, accept and reject buttons, an optional comment, storage in SQLite, the "nothing is executed" message.
- Out: any action on the testbed or network, automation of accepted actions.

**Technical notes**
- The agent recommends and never executes (§1.1).
- Decisions go to SQLite only (§6.7).

**Acceptance criteria**
- Given a recommendation, when the human clicks accept, then one row is written to SQLite with incident ID, decision and time, and the screen states that no action was executed.
- Given the network panel of the browser, when accept is clicked, then the only request sent is the decision POST to localhost.

**Checklist**
- [ ] Build the view.
- [ ] Add the buttons and comment.
- [ ] Store the decision.
- [ ] Show the message.

**Deliverables**
`frontend/src/screens/Recommendation.tsx`

**Risks / gotchas**
- A button labelled "Apply" or "Execute" contradicts the thesis claim. Use "Accept recommendation".

**Open questions**
None

**Traceability**
R-036, R-037, R-041, R-158, R-173, R-292 · Record §1.1, §5, §6.7 · Arch §1 · Proposal: Objective 3

---

**[E10-07] Build the audit log screen**
**Type:** Task · **Epic:** EPIC-10 · **Priority:** Low · **Points:** 2 · **Labels:** engineering
**Depends on:** E10-03 · **Blocks:** None

**Context**
The fourth allowed screen. It shows that every attempt, accepted or rejected, is recorded, which is the auditability claim made visible.

**Goal**
One read-only screen pages through the audit log, with filters for outcome and rejection reason.

**Scope**
- In: a paged table, filters for outcome and reason, a link to the incident.
- Out: editing or deleting records, exporting.

**Technical notes**
- The audit log is append-only and never rewritten (§6.7).

**Acceptance criteria**
- Given the audit log, when the screen loads, then it shows records in time order with outcome, reason, bundle ID and condition.
- Given the filter set to `would_reject`, when the table updates, then only `logging_only` records that would have been rejected are shown.

**Checklist**
- [ ] Build the table.
- [ ] Add paging.
- [ ] Add the filters.
- [ ] Link to incidents.

**Deliverables**
`frontend/src/screens/AuditLog.tsx`

**Risks / gotchas**
- Full prompts are large. Show them collapsed by default.

**Open questions**
None

**Traceability**
R-158, R-292 · Record §5, §6.7 · Proposal: Methodology (audit log)


# Step D — EPIC-11 · Thesis Writing & Research Artifacts

15 tickets · 43 points · Project DoD v1.0 and DoR apply to every ticket.

Writing tickets consume `docs/thesis_notes.md`, where every decision, number and figure from other tickets was logged (DoD).
ASSUMPTION: the thesis source lives in `docs/thesis/`, one file per chapter; the format (LaTeX or Word) is fixed in E11-02.

**Suggested execution order:** E11-01 ∥ E11-14 ∥ E11-15 (early and recurring) → E11-02 → E11-03 → E11-05 ∥ E11-06 → E11-04 → E11-07 ∥ E11-08 → E11-09 → E11-11 → E11-10 → E11-13 → E11-12

---

**[E11-01] Resolve references [4] and [17]**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 1 · **Labels:** writing
**Depends on:** None · **Blocks:** E11-12

**Context**
The proposal itself flags two incomplete references (risk #8). An incomplete reference in the final thesis is an easy point for an examiner to take.

**Goal**
References [4] and [17] are complete in IEEE style in the thesis bibliography.

**Scope**
- In: the complete author list, volume and article number for [4]; the end page for [17].
- Out: other references.

**Technical notes**
- [4] from the ScienceDirect record; [17] from IEEE Xplore (proposal References).

**Acceptance criteria**
- [ ] The bibliography entry for [4] lists every author, the volume and the article number, and contains no "to be confirmed" text.
- [ ] The bibliography entry for [17] has start and end pages.
- [ ] Both DOIs resolve to the cited articles.

**Checklist**
- [ ] Look up [4].
- [ ] Look up [17].
- [ ] Update the bibliography.
- [ ] Check both DOIs.

**Deliverables**
Updated bibliography file in `docs/thesis/`

**Risks / gotchas**
- An "in press" article may have received its volume since July. Check the current record, not a cached one.

**Open questions**
"References [4] and [17]" (§10)

**Traceability**
R-316, R-317 · Record §3 (risk #8), §16 · Proposal: References

---

**[E11-02] Write the introduction and research-gap chapter**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 3 · **Labels:** writing
**Depends on:** E11-14 · **Blocks:** E11-10

**Context**
The introduction states the problem, the gap and the research questions. Most of the content exists in the proposal and only needs adapting. It also fixes the thesis format.

**Goal**
A complete introduction chapter states the problem, the gap, the research questions, the hypotheses and the contribution.

**Scope**
- In: motivation, the gap claim, RQ1–RQ4, H1–H4, the contribution statement, the chapter outline, the thesis format decision.
- Out: related work detail (E11-03), results.

**Technical notes**
- Motivation includes the cost of a wrong automatic action (Arch §1.1).
- The gap claim matches the proposal.
- The title follows E11-14.

**Acceptance criteria**
- [ ] `docs/thesis/01_introduction.*` contains sections: motivation, problem, gap, research questions, hypotheses, contribution, outline.
- [ ] RQ1–RQ4 and H1–H4 match the proposal's wording, or every change is listed in `docs/thesis_notes.md`.
- [ ] The thesis format (LaTeX or Word) is recorded in `docs/thesis/README.md`.

**Checklist**
- [ ] Decide the format.
- [ ] Adapt the proposal text.
- [ ] Write the contribution statement.
- [ ] Write the outline.

**Deliverables**
`docs/thesis/01_introduction.*`, `docs/thesis/README.md`

**Risks / gotchas**
- Promising more in the introduction than the results deliver. Write the contribution last, or revise it after E11-07 and E11-08.

**Open questions**
None

**Traceability**
R-005, R-006, R-026, R-027, R-032, R-035 · Proposal: Research Gap, Central Research Question, Research Problem · Arch §1.1

---

**[E11-03] Write the related work chapter**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 5 · **Labels:** writing, research
**Depends on:** None · **Blocks:** E11-12

**Context**
The related work chapter makes the gap credible by showing exactly where each close work stops (record §1.3). It also adds the prompt-injection gap found during planning (R-224).

**Goal**
A related work chapter covers IoT intrusion detection, LLM agents, agent safety and the four closest works, and ends with the gap table.

**Scope**
- In: IoT IDS and datasets [5]–[9], agent architectures [10]–[12], agent risk and safety [13]–[15], the four closest works [16]–[19], the prompt-injection gap, the gap table.
- Out: new literature searches beyond what is needed to support these sections.

**Technical notes**
- [16] stops at detection and explanation; [17] at detection; [18] at report generation; [19] at enterprise reporting (§1.3).
- None of [16], [18], [19] addresses prompt injection (§3.3).
- Design lineage: IDS-Agent and CyberRAG (proposal Methodology).

**Acceptance criteria**
- [ ] `docs/thesis/02_related_work.*` has one section per area listed in Scope.
- [ ] The chapter ends with a table comparing [16]–[19] and this thesis on: multi-source fusion, safety constraints, end-to-end testbed evaluation, prompt-injection handling, cost reporting.
- [ ] Every claim about a cited work points to that work's reference number.

**Checklist**
- [ ] Draft each area section.
- [ ] Write the four close-work summaries.
- [ ] Add the prompt-injection paragraph.
- [ ] Build the gap table.

**Deliverables**
`docs/thesis/02_related_work.*`

**Risks / gotchas**
- Describing related work only through the gap it leaves reads as unfair. Credit what each work does well before saying where it stops.

**Open questions**
None

**Traceability**
R-027–R-031, R-033, R-034, R-224 · Record §1.3, §3.3 · Proposal: Research Gap, Methodology

---

**[E11-04] Write the methods chapter from METHODS.md**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 5 · **Labels:** writing, research
**Depends on:** E2-09 · **Blocks:** E11-07, E11-08

**Context**
METHODS.md is the frozen contract. The methods chapter turns it into prose and states every deliberate trade-off before an examiner can raise it. Examiners respond well to seeing these noticed (record §4.1).

**Goal**
The methods chapter describes the experiment completely and states each scoping trade-off explicitly.

**Scope**
- In: the incident unit, conditions, metrics, statistics, the frozen changelog, and the stated trade-offs listed in Technical notes.
- Out: system implementation detail (E11-05), results.

**Technical notes**
- State that the agent classifies the bundles it is given and does not discover boundaries (§4.1).
- State the fixed graph vs free-form ReAct trade-off (§6.3), and that detectors run upstream rather than as tools (C-07).
- State the reproducibility claim: pinned open weights (§4.2).
- State clustering and the episode bootstrap (§4.1).
- State the H3 circularity and why contextual appropriateness is the headline (§3.1).
- Frame Baseline A and Baseline B by the questions they answer (§6.6).

**Acceptance criteria**
- [ ] `docs/thesis/03_methods.*` contains every METHODS.md section, and its numbers equal the METHODS.md version recorded at the freeze plus its changelog.
- [ ] Each of the six trade-offs in Technical notes appears in a paragraph that names it.
- [ ] Every METHODS.md changelog entry is mentioned in the chapter.

**Checklist**
- [ ] Convert each METHODS.md section.
- [ ] Write the six trade-off paragraphs.
- [ ] Summarise the changelog.
- [ ] Cross-check every number.

**Deliverables**
`docs/thesis/03_methods.*`

**Risks / gotchas**
- Hiding a changelog entry because it looks like a mistake. A documented change is defensible; an undocumented one found by an examiner is not.

**Open questions**
None

**Traceability**
R-048, R-101, R-150, R-188, R-233, R-258 · Record §3.1, §4.1, §4.2, §6.3, §6.6 · Proposal: Methodology

---

**[E11-05] Write the system architecture chapter**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 3 · **Labels:** writing
**Depends on:** E7-08 · **Blocks:** E11-12

**Context**
The architecture document already exists with 11 figures. This chapter adapts it to thesis register, and records the out-of-scope line for authentication (R-315).

**Goal**
A system chapter describes the seven parts, the agent graph, the safety layer and the stack, reusing the existing figures.

**Scope**
- In: the seven subsystems, the eight pipeline steps, the agent graph, the four safety mechanisms, the stack and why, the one-line auth statement.
- Out: experiment design (E11-04), the console beyond one paragraph.

**Technical notes**
- Reuse the illustrated architecture document's figures (Record §13).
- Authentication is out of scope, stated in one line (§4, §6.8).
- Design lineage from IDS-Agent and CyberRAG.

**Acceptance criteria**
- [ ] `docs/thesis/04_system.*` covers each item in Scope.
- [ ] The chapter contains the sentence stating that authentication is out of scope and why.
- [ ] Every figure reused from the architecture document is referenced in the text.

**Checklist**
- [ ] Adapt the architecture document's sections.
- [ ] Insert the figures.
- [ ] Add the auth line.
- [ ] Update anything that changed since September.

**Deliverables**
`docs/thesis/04_system.*`

**Risks / gotchas**
- The architecture document was written in simplified English for the supervisor. The thesis needs academic register; do not paste it unchanged.

**Open questions**
None

**Traceability**
R-034, R-315 · Record §4, §6.8, §13 · Proposal: Methodology

---

**[E11-06] Write the testbed, corpus and ethics section**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 3 · **Labels:** writing
**Depends on:** E2-08 · **Blocks:** E11-12

**Context**
The testbed and corpus are a deliverable of their own (proposal Expected Outcomes). The proposal also commits to an ethics statement: isolated testbed, no human subjects, no personal data.

**Goal**
A section describes the testbed, the attack generation, the labelled corpus and the ethics safeguards, from the dataset card and ADR-003.

**Scope**
- In: testbed composition, attack families and generation, labelling, counts, the isolation guarantee, the ethics paragraph.
- Out: results.

**Technical notes**
- Source: `docs/dataset_card.md` and ADR-003's ethics paragraph.
- No personal data and no human subjects (proposal Methodology, §6.11).

**Acceptance criteria**
- [ ] `docs/thesis/05_testbed.*` covers each item in Scope.
- [ ] Every count matches the dataset card.
- [ ] The ethics paragraph states isolation, no third-party targets, no human subjects and no personal data.

**Checklist**
- [ ] Adapt the dataset card.
- [ ] Describe the families.
- [ ] Write the ethics paragraph.
- [ ] Cross-check the counts.

**Deliverables**
`docs/thesis/05_testbed.*`

**Risks / gotchas**
- Mentioning tool or dataset licences incorrectly. Copy them from ADR-003.

**Open questions**
None

**Traceability**
R-180, R-313 · Record §6.11 · Proposal: Methodology (ethics), Expected Outcomes

---

**[E11-07] Write the results chapter for H1 and H2**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 3 · **Labels:** writing, research
**Depends on:** E9-11, E11-04 · **Blocks:** E11-09

**Context**
H1 and H2 answer whether fusion and the agentic architecture help. The proposal commits to reporting them honestly, including any negative result.

**Goal**
A results section reports H1 (stratified) and H2 with effect sizes, intervals and test results, and states plainly whether each hypothesis is supported.

**Scope**
- In: H1 stratified results with and without honeypot-keyed bundles, H2 results, a verdict per hypothesis.
- Out: interpretation beyond what the numbers show (E11-09).

**Technical notes**
- Tables and figures come only from E9-11.
- Negative results get the same prominence (proposal Expected Outcomes).

**Acceptance criteria**
- [ ] `docs/thesis/06_results.*` has an H1 section and an H2 section, each ending with "supported", "not supported" or "partly supported" and the test result.
- [ ] Every number in the section appears in an E9-11 output file.

**Checklist**
- [ ] Insert the H1 tables.
- [ ] Write the H1 text.
- [ ] Insert the H2 tables.
- [ ] Write the H2 text.
- [ ] Cross-check numbers.

**Deliverables**
`docs/thesis/06_results.*` (H1, H2 sections)

**Risks / gotchas**
- Describing a non-significant difference as "a trend" overstates it. Use the test result.

**Open questions**
None

**Traceability**
R-007, R-008, R-024 · Proposal: H1, H2, Expected Outcomes

---

**[E11-08] Write the results chapter for H3, H4 and cost**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 3 · **Labels:** writing, research
**Depends on:** E9-11, E11-04 · **Blocks:** E11-09

**Context**
H3 is reported with the three-way safety split, so the headline is contextual appropriateness, not the by-construction membership count. H4 is the end-to-end comparison. Cost per incident is a contribution none of the closest works report (record §4.4).

**Goal**
A results section reports H3, H4 and cost per incident, each with its test and verdict.

**Scope**
- In: the three safety metrics and usefulness, reliability, the H4 comparison, the cost table.
- Out: interpretation (E11-09).

**Technical notes**
- Membership is reported as true by construction, never as the headline (§3.1).
- Cost from E9-07.

**Acceptance criteria**
- [ ] `docs/thesis/06_results.*` has H3, H4 and cost sections, H3 and H4 each ending with a supported or not-supported verdict and the test result.
- [ ] The H3 section names contextual appropriateness as its headline metric.
- [ ] The cost section states that [16], [18] and [19] do not report cost per incident.
- [ ] Every number appears in an E9-11 output file.

**Checklist**
- [ ] Write H3.
- [ ] Write H4.
- [ ] Write cost.
- [ ] Cross-check numbers.

**Deliverables**
`docs/thesis/06_results.*` (H3, H4, cost sections)

**Risks / gotchas**
- Leading H3 with "zero unsafe actions" invites the circularity objection. Lead with contextual appropriateness.

**Open questions**
None

**Traceability**
R-009, R-010, R-024, R-319 · Record §3.1, §4.4 · Proposal: H3, H4

---

**[E11-09] Write the discussion, limitations and threats to validity**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 3 · **Labels:** writing
**Depends on:** E11-07, E11-08 · **Blocks:** E11-10

**Context**
A thesis written alone has no reviewer to pre-empt objections. This chapter states the limitations before the jury does, and shows where the agent is reliable and where it is not (proposal Expected Outcomes).

**Goal**
A discussion chapter interprets the results and lists every known limitation and threat to validity.

**Scope**
- In: interpretation per hypothesis, where the agent is reliable and where not, and the limitations listed in Technical notes.
- Out: new analyses.

**Technical notes**
- Limitations to cover:
  - Emulated, not physical, testbed.
  - A single base model.
  - Action sets derived from published sources by one person.
  - The effect of honeypot all-positive bundles.
  - Bundles given, not discovered.
  - Vulnerability databases and interactive information requests from the brief, scoped out (C-08 partial).
  - Robustness, if scoped out in E0-13.
  - The prompt-injection experiment, if not run.

**Acceptance criteria**
- [ ] `docs/thesis/07_discussion.*` has an interpretation section per hypothesis and a limitations section listing each item in Technical notes.
- [ ] A "where it is reliable and where it is not" section cites the per-family results from E9-10.

**Checklist**
- [ ] Interpret each hypothesis.
- [ ] Write the reliability section.
- [ ] Write the limitations.
- [ ] Write the threats to validity.

**Deliverables**
`docs/thesis/07_discussion.*`

**Risks / gotchas**
- A short limitations section reads as unawareness. Each item gets a sentence on its likely effect.

**Open questions**
None

**Traceability**
R-024, R-025, R-047 · Proposal: Expected Outcomes · Brief: Generative AI Dimension

---

**[E11-10] Write the conclusion and abstract**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 2 · **Labels:** writing
**Depends on:** E11-09, E11-02 · **Blocks:** E11-12

**Context**
The conclusion and abstract are written last, once results are final, so they state what was actually shown.

**Goal**
An abstract and a conclusion state the contribution and the answer to each research question in line with the results.

**Scope**
- In: the abstract, the conclusion, future work.
- Out: new claims not supported in the results chapters.

**Technical notes**
- Contribution framing from the proposal, adjusted to the results.

**Acceptance criteria**
- [ ] The abstract is under 300 words and gives one sentence per hypothesis result.
- [ ] The conclusion answers RQ1–RQ4 in order.
- [ ] Future work includes every item scoped out in E11-09.

**Checklist**
- [ ] Write the conclusion.
- [ ] Write future work.
- [ ] Write the abstract.
- [ ] Re-check the introduction's contribution statement.

**Deliverables**
`docs/thesis/00_abstract.*`, `docs/thesis/08_conclusion.*`

**Risks / gotchas**
- An abstract written early and never revised promises results that changed.

**Open questions**
None

**Traceability**
R-026 · Proposal: Expected Outcomes

---

**[E11-11] Prepare the thesis figures and tables**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 3 · **Labels:** writing
**Depends on:** E9-11 · **Blocks:** E11-12

**Context**
The thesis reuses the 11 architecture figures and adds the generated results figures. Consistent numbering and captions are what make a long document navigable.

**Goal**
Every figure and table in the thesis is numbered, captioned, referenced in the text and traceable to its source.

**Scope**
- In: the reused architecture figures, the generated results figures, captions, the lists of figures and tables.
- Out: creating new diagrams beyond what the chapters need.

**Technical notes**
- Architecture figures from the illustrated document (Record §13).
- Results figures only from E9-11.

**Acceptance criteria**
- [ ] Every figure and table has a number and a caption, and is referenced at least once in the text.
- [ ] `docs/thesis/figure_sources.md` lists each figure with its source file.

**Checklist**
- [ ] Collect all figures.
- [ ] Number and caption them.
- [ ] Check every in-text reference.
- [ ] Write the source list.

**Deliverables**
`docs/thesis/figures/`, `docs/thesis/figure_sources.md`

**Risks / gotchas**
- Architecture figures drawn for a non-fluent reader may be too simple for the thesis. Re-label where needed.

**Open questions**
None

**Traceability**
R-339 · Record §13 · Proposal: Expected Outcomes

---

**[E11-12] Add the AI-use acknowledgement and proofread**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** High · **Points:** 2 · **Labels:** writing
**Depends on:** E11-01, E11-03, E11-05, E11-06, E11-10, E11-11, E11-13 · **Blocks:** None

**Context**
The proposal commits to acknowledging any use of AI tools in line with the dissertation guide. The final pass also checks reference style (R-318).

**Goal**
The thesis contains an accurate AI-use acknowledgement, and the full text has been proofread with every reference in IEEE style.

**Scope**
- In: the AI-use statement, a full proofread, the IEEE style check, a final consistency check of numbers.
- Out: content changes beyond corrections.

**Technical notes**
- AI tools acknowledged transparently per the dissertation guide (proposal Methodology).
- IEEE style as in the proposal.

**Acceptance criteria**
- [ ] The thesis contains an AI-use section listing which tools were used and for what.
- [ ] Every bibliography entry follows the proposal's IEEE format.
- [ ] A final check finds no "TODO", "TBD" or "to be confirmed" in the document.

**Checklist**
- [ ] Write the AI-use statement.
- [ ] Proofread every chapter.
- [ ] Check the references.
- [ ] Search for leftover markers.

**Deliverables**
Final `docs/thesis/` and the exported thesis file

**Risks / gotchas**
- The dissertation guide may require a specific wording or placement for the AI statement. Check the guide.

**Open questions**
None

**Traceability**
R-314, R-318 · Proposal: Methodology, References

---

**[E11-13] Package the reproducibility artifact**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 2 · **Labels:** research, writing
**Depends on:** E9-09 · **Blocks:** E11-12

**Context**
A reproducible artifact is a real contribution most agent papers cannot claim (record §4.2). Packaging it means one tag and one README let anyone rerun the matrix.

**Goal**
One git tag and one README give everything needed to regenerate the corpus and rerun the full matrix.

**Scope**
- In: the release tag, the README with exact steps, the list of pinned versions and hashes.
- Out: publishing the corpus where licences forbid it, a hosted demo.

**Technical notes**
- Pinned open weights can be re-served by anyone (§4.2).
- Hashes come from the manifest, the bundle set and the results.

**Acceptance criteria**
- [ ] Git tag `thesis-v1.0` exists.
- [ ] `REPRODUCE.md` lists the model name and revision, the corpus manifest hash, the bundle-set hash, the METHODS.md version and the commands to regenerate and rerun.
- [ ] The commands in `REPRODUCE.md` were run once from a fresh clone up to the dry-run step, and the run is noted.

**Checklist**
- [ ] Collect the hashes and versions.
- [ ] Write `REPRODUCE.md`.
- [ ] Test from a fresh clone.
- [ ] Tag the release.

**Deliverables**
`REPRODUCE.md`, git tag `thesis-v1.0`

**Risks / gotchas**
- Instructions that only work on your machine. The fresh-clone check is the guard.

**Open questions**
None

**Traceability**
R-150 · Record §4.2 · Proposal: Expected Outcomes

---

**[E11-14] Shortlist and conflict-check the system name**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 2 · **Labels:** writing
**Depends on:** None · **Blocks:** E11-02

**Context**
The system name is still open (record §10). The record fixed the constraints and the next step: five names you like, a conflict check, an execution-implication flag and a draft title (§11.4). The repo stays `thesis` until then.

**Goal**
One name is chosen, conflict-checked against the record's constraints, and used in a draft title.

**Scope**
- In: five candidate names, a conflict check, an execution-implication check, the draft title with subtitle.
- Out: trademark clearance (only needed beyond the thesis, §11.6), logo design.

**Technical notes**
- No implication of execution; no Latin or Greek; reads as an LLM system, not a startup; avoids "AI" and "Detect" (§11.1, §11.5).
- None of the names on the verified-conflict list (§11.2).
- Descriptors go in the subtitle; no forced backronym (§11.5).

**Acceptance criteria**
- [ ] `docs/naming.md` lists five candidates, each with conflict-check results and an execution-implication flag.
- [ ] One name is chosen, with a draft thesis title and subtitle.
- [ ] If the name differs from `thesis`, the package rename is a separate ticket.

**Checklist**
- [ ] Write five candidates.
- [ ] Check each against §11.2.
- [ ] Search for conflicts.
- [ ] Flag execution implications.
- [ ] Choose and draft the title.

**Deliverables**
`docs/naming.md`

**Risks / gotchas**
- Spending more than the timebox on naming. It does not affect any result.

**Open questions**
"Project name" (§10)

**Traceability**
R-005, R-320–R-327 · Record §10, §11 · Proposal: Proposed Title

---

**[E11-15] Prepare the supervisor update pack**
**Type:** Task · **Epic:** EPIC-11 · **Priority:** Medium · **Points:** 3 · **Labels:** writing
**Depends on:** None · **Blocks:** None

**Context**
The supervisor is not fluent in English, may not have read the proposal, and gives no methodological guidance (record §12.1). Each update follows a fixed cadence and a fixed format. This ticket is cloned once per supervisor meeting.

**Goal**
One update pack is sent on the Monday after its Thursday draft, in simple English, opening with the overview, and humanized without changing protected text.

**Scope**
- In: the overview opener, the current status, the questions to raise, the meeting booking, the email, the humanizer pass.
- Out: setting the meeting agenda (his role), new technical content not already in other tickets.

**Technical notes**
- Simple words, short sentences, many diagrams; open with a short overview (§12.1).
- 60-second opener in English and French (§12.2); the three questions, with the third as priority (§12.5).
- Meeting booked for 45 minutes (§12.6); the email carries no agenda (§12.7).
- Cadence: Thursday draft, weekend changes, Monday send (§12.8).
- Humanizer rules: sentences of about 18 words maximum, no idioms or contractions, protected terms unchanged, and the sentence "It suggests only. It never acts by itself. A human always decides." unchanged. Humanize via Markdown export, then rebuild (§13.2).

**Acceptance criteria**
- [ ] The draft exists on the Thursday, and the final pack is sent on the following Monday (dates recorded in the ticket).
- [ ] The pack opens with the overview section.
- [ ] A check confirms no sentence over about 18 words and that the protected sentence is unchanged.
- [ ] The meeting invitation is 45 minutes long.
- [ ] The email body contains no agenda.

**Checklist**
- [ ] Draft on Thursday.
- [ ] Add the overview and status.
- [ ] Add the questions.
- [ ] Export to Markdown and humanize.
- [ ] Rebuild the document.
- [ ] Check protected text.
- [ ] Send on Monday and book 45 minutes.

**Deliverables**
`docs/supervisor/<date>/` with the pack and the email text

**Risks / gotchas**
- Running the humanizer directly on a .docx damages tables, images and headings (§13.2).

**Open questions**
None

**Traceability**
R-328–R-338 · Record §12, §13.2 · Proposal: none
