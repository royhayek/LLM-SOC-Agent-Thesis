# Jira key map

Site: `iot-soc-thesis.atlassian.net` · Project: Dev (`SCRUM`) · Created 2 Oct 2026.

Ticket references (`E0-01`) are used in every description and in `backlog_full.md`. Jira keys (`SCRUM-6`) are used in branch names and commits.

## EPIC-0 · Project Foundation & Engineering Baseline · `SCRUM-5`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E0-01 | SCRUM-6 | 5 | Run a walking-skeleton spike on one hand-written bundle |
| E0-02 | SCRUM-18 | 3 | Scaffold the monorepo with CI and an ADR log |
| E0-03 | SCRUM-24 | 5 | Write and freeze METHODS.md v1.0 |
| E0-04 | SCRUM-31 | 5 | Derive action catalog v0.1 with a citation per entry |
| E0-05 | SCRUM-44 | 5 | Define and freeze bundle reduction policy v1.0 |
| E0-06 | SCRUM-57 | 3 | Write ADR-001 on LLM serving, cost and time budget |
| E0-07 | SCRUM-70 | 5 | Build the benign-only Docker Compose testbed skeleton |
| E0-08 | SCRUM-82 | 3 | Draft alert schema v0.1 from the spike findings |
| E0-09 | SCRUM-91 | 3 | Implement ExperimentConfig with a reproducible config hash |
| E0-10 | SCRUM-100 | 2 | Add structured JSON logging for every LLM call |
| E0-11 | SCRUM-106 | 2 | Decide and freeze the validator rejection policy |
| E0-12 | SCRUM-111 | 3 | Define the three-way safety scoring protocol |
| E0-13 | SCRUM-114 | 2 | Define the reliability and robustness metrics |
| E0-14 | SCRUM-119 | 2 | Choose honeypot and flow-exporter software in ADR-002 |

## EPIC-1 · IoT Testbed & Scenario Generation · `SCRUM-7`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E1-01 | SCRUM-19 | 2 | Gate every scenario run on a passing isolation check |
| E1-02 | SCRUM-22 | 3 | Select and freeze the six attack families |
| E1-03 | SCRUM-30 | 3 | Build the per-family acceptable and unsafe action sets |
| E1-04 | SCRUM-39 | 2 | Write ADR-003 on the attack generation method per family |
| E1-05 | SCRUM-56 | 3 | Add benign traffic profiles to the MQTT emulators |
| E1-06 | SCRUM-67 | 3 | Define the scenario schedule format and its validator |
| E1-07 | SCRUM-78 | 5 | Build the scenario runner |
| E1-08 | SCRUM-87 | 2 | Implement attack family F1 (provisional: MQTT message flood) |
| E1-09 | SCRUM-96 | 2 | Implement attack family F2 (provisional: MQTT broker password guessing) |
| E1-10 | SCRUM-104 | 2 | Implement attack family F3 (provisional: port scan) |
| E1-11 | SCRUM-109 | 2 | Implement attack family F4 (provisional: SSH password guessing) |
| E1-12 | SCRUM-113 | 2 | Implement attack family F5 (provisional: botnet traffic) |
| E1-13 | SCRUM-117 | 2 | Implement attack family F6 (provisional: denial of service) |
| E1-14 | SCRUM-121 | 2 | Verify the source-visibility matrix against real captures |
| E1-15 | SCRUM-124 | 3 | Run a pilot schedule end to end and check repeatability |

## EPIC-2 · Ground Truth & Labelled Corpus · `SCRUM-8`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E2-01 | SCRUM-20 | 2 | Decide what Baseline A trains on |
| E2-02 | SCRUM-25 | 3 | Run the power calculation and fix target N |
| E2-03 | SCRUM-32 | 3 | Generate the corpus schedule for the target N |
| E2-04 | SCRUM-40 | 3 | Derive window labels mechanically from the execution log |
| E2-05 | SCRUM-52 | 3 | Execute the corpus generation run |
| E2-06 | SCRUM-62 | 2 | Build the corpus manifest with SHA-256 per file |
| E2-07 | SCRUM-74 | 3 | Validate corpus integrity before the freeze |
| E2-08 | SCRUM-83 | 2 | Write the dataset card |
| E2-09 | SCRUM-92 | 2 | Freeze corpus v1.0.0 (milestone) |

## EPIC-3 · Telemetry Normalization & Incident Assembly · `SCRUM-9`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E3-01 | SCRUM-21 | 3 | Finalize alert schema v1 from the pilot capture |
| E3-02 | SCRUM-27 | 3 | Normalize MQTT telemetry into alerts |
| E3-03 | SCRUM-38 | 3 | Normalize network flows into alerts |
| E3-04 | SCRUM-50 | 3 | Normalize honeypot logs into alerts |
| E3-05 | SCRUM-64 | 3 | Implement the device-keyed 60 s bundle assembler |
| E3-06 | SCRUM-77 | 5 | Implement the frozen reduction policy |
| E3-07 | SCRUM-86 | 2 | Add golden-file tests for the reduction step |
| E3-08 | SCRUM-99 | 2 | Assert the per-call token ceilings at build time |
| E3-09 | SCRUM-105 | 2 | Build the frozen bundle set and record its hash |
| E3-10 | SCRUM-128 | 2 | Decide the device mapping for traffic that §4.1 does not cover |

## EPIC-4 · Detection Layer · `SCRUM-10`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E4-01 | SCRUM-23 | 3 | Engineer flow features on the agreed training data |
| E4-02 | SCRUM-29 | 5 | Tune the flow classifier with class-imbalance handling |
| E4-03 | SCRUM-37 | 2 | Evaluate and freeze the flow classifier as Baseline A |
| E4-04 | SCRUM-48 | 3 | Implement the MQTT statistical-threshold detector |
| E4-05 | SCRUM-58 | 3 | Implement the honeypot parser and rules |
| E4-06 | SCRUM-68 | 2 | Write detector scores and labels into alerts |

## EPIC-5 · Knowledge Base & Retrieval · `SCRUM-11`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E5-01 | SCRUM-26 | 1 | Build the device inventory |
| E5-02 | SCRUM-34 | 3 | Curate the knowledge base of 50–200 cited documents |
| E5-03 | SCRUM-42 | 2 | Embed the knowledge base into a numpy index |
| E5-04 | SCRUM-51 | 2 | Implement the deterministic retrieval tool |

## EPIC-6 · LLM Agent Core · `SCRUM-12`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E6-01 | SCRUM-28 | 2 | Implement the OpenAI-compatible LLM client |
| E6-02 | SCRUM-36 | 2 | Version the prompt templates with a static prefix first |
| E6-03 | SCRUM-49 | 3 | Implement node 1: evidence analysis with retrieval |
| E6-04 | SCRUM-61 | 3 | Implement node 2: structured classification |
| E6-05 | SCRUM-72 | 3 | Implement node 3: constrained recommendation |
| E6-06 | SCRUM-81 | 3 | Wire the three-node graph runner with source injection |
| E6-07 | SCRUM-90 | 2 | Add a slow end-to-end test against local Ollama |
| E6-08 | SCRUM-98 | 2 | Sanity-compare the dev and experiment models |

## EPIC-7 · Safety & Constraint Layer · `SCRUM-13`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E7-01 | SCRUM-33 | 3 | Define the verdict schema with constrained decoding |
| E7-02 | SCRUM-43 | 3 | Implement the deterministic validator |
| E7-03 | SCRUM-54 | 2 | Add property tests for the validator |
| E7-04 | SCRUM-66 | 2 | Implement the frozen rejection policy |
| E7-05 | SCRUM-76 | 2 | Write the append-only JSONL audit log |
| E7-06 | SCRUM-85 | 2 | Implement the enforcing and logging_only switch |
| E7-07 | SCRUM-94 | 2 | Harden honeypot text handling against prompt injection |
| E7-08 | SCRUM-102 | 2 | Render a one-page incident report from each verdict |

## EPIC-8 · Baselines (A: ML+rules, B: prompt-only) · `SCRUM-14`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E8-01 | SCRUM-35 | 2 | Define the cited severity→action lookup for Baseline A |
| E8-02 | SCRUM-46 | 2 | Implement the Baseline A strategy behind ExperimentConfig |
| E8-03 | SCRUM-60 | 3 | Write the prompt-only prompt for Baseline B |
| E8-04 | SCRUM-71 | 2 | Implement the Baseline B strategy behind ExperimentConfig |

## EPIC-9 · Evaluation Harness & Experiments H1–H4 · `SCRUM-15`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E9-01 | SCRUM-41 | 5 | Build the condition-matrix runner with concurrency and resume |
| E9-02 | SCRUM-53 | 2 | Write results to Parquet with full provenance |
| E9-03 | SCRUM-63 | 3 | Compute detection and classification metrics |
| E9-04 | SCRUM-75 | 3 | Compute safety, usefulness and reliability metrics |
| E9-05 | SCRUM-84 | 3 | Run the paired McNemar and Wilcoxon tests |
| E9-06 | SCRUM-93 | 3 | Implement the episode-level block bootstrap |
| E9-07 | SCRUM-101 | 2 | Report cost and latency per incident |
| E9-08 | SCRUM-107 | 2 | Run the exploratory partial matrix |
| E9-09 | SCRUM-110 | 3 | Run the full matrix k times |
| E9-10 | SCRUM-115 | 3 | Analyze H1 stratified by attack family |
| E9-11 | SCRUM-118 | 3 | Produce the results tables and figures for H1–H4 |
| E9-12 | SCRUM-123 | 3 | Run the prompt-injection experiment (stretch) |

## EPIC-10 · SOC Console (FastAPI + React) · `SCRUM-16`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E10-01 | SCRUM-45 | 3 | Expose results and the audit log through FastAPI REST |
| E10-02 | SCRUM-55 | 2 | Stream the reasoning trace over SSE |
| E10-03 | SCRUM-65 | 1 | Generate TypeScript types with openapi-typescript |
| E10-04 | SCRUM-73 | 3 | Build the incident list screen |
| E10-05 | SCRUM-80 | 3 | Build the incident detail screen with evidence and trace |
| E10-06 | SCRUM-89 | 3 | Build the recommendation accept/reject screen |
| E10-07 | SCRUM-95 | 2 | Build the audit log screen |

## EPIC-11 · Thesis Writing & Research Artifacts · `SCRUM-17`

| Ref | Jira | Pts | Title |
|---|---|---|---|
| E11-01 | SCRUM-47 | 1 | Resolve references [4] and [17] |
| E11-02 | SCRUM-59 | 3 | Write the introduction and research-gap chapter |
| E11-03 | SCRUM-69 | 5 | Write the related work chapter |
| E11-04 | SCRUM-79 | 5 | Write the methods chapter from METHODS.md |
| E11-05 | SCRUM-88 | 3 | Write the system architecture chapter |
| E11-06 | SCRUM-97 | 3 | Write the testbed, corpus and ethics section |
| E11-07 | SCRUM-103 | 3 | Write the results chapter for H1 and H2 |
| E11-08 | SCRUM-108 | 3 | Write the results chapter for H3, H4 and cost |
| E11-09 | SCRUM-112 | 3 | Write the discussion, limitations and threats to validity |
| E11-10 | SCRUM-116 | 2 | Write the conclusion and abstract |
| E11-11 | SCRUM-120 | 3 | Prepare the thesis figures and tables |
| E11-12 | SCRUM-122 | 2 | Add the AI-use acknowledgement and proofread |
| E11-13 | SCRUM-125 | 2 | Package the reproducibility artifact |
| E11-14 | SCRUM-126 | 2 | Shortlist and conflict-check the system name |
| E11-15 | SCRUM-127 | 3 | Prepare the supervisor update pack |
