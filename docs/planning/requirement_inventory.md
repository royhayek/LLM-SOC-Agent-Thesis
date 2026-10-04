# Requirement inventory — Step A

**347 items**, numbered R-001 to R-347. Compiled 1 Oct 2026.

## Source key

| Code | Document |
|---|---|
| Proposal | Applied_Research_MSc_Thesis_Roy_EL-HAYEK_(M2_IA).pdf (July 2026) |
| Record §x | thesis_project_full_record.md (Sept 2026) |
| Arch §x | System_Architecture_MSc_Thesis_Roy_EL-HAYEK_(M2_IA).docx (Sept 2026) |
| Brief | Project brief .md in the Project (original topic description) — included because it holds requirements found nowhere else |

Items stated in several documents appear once, with every source listed. Parameter values are filed as `decision` (or `constraint` when they bound the work).

## Counts

| Category | Items |
|---|---|
| requirement | 89 |
| decision | 99 |
| constraint | 47 |
| risk | 9 |
| metric | 15 |
| test | 13 |
| deliverable | 15 |
| open question | 10 |
| prohibition | 22 |
| writing | 28 |

| Source | Items citing it |
|---|---|
| Proposal | 63 |
| Record | 301 |
| Arch | 68 |
| Brief | 12 |


## 1. Purpose, research questions and hypotheses

| ID | Item | Source | Category |
|---|---|---|---|
| R-001 | System turns three IoT telemetry streams into one validated, machine-checkable incident verdict plus a recommended action | Record §1 | requirement |
| R-002 | A measurement rig proves whether the agentic pipeline beats two non-agentic versions | Record §1 | requirement |
| R-003 | The software is the instrument, the experiment is the thesis: engineering choices serve the experiment | Record §1 | decision |
| R-004 | Subsystems 5 (agent + safety) and 6 (evaluation) carry the scientific contribution; 1–4 only feed them | Record §2; Arch §4.1 | decision |
| R-005 | Thesis title: "LLM-Based Autonomous SOC Agent for IoT Cyberattack Detection and Response" | Proposal: title | writing |
| R-006 | Central RQ: does the agent significantly improve detection, classification accuracy and response safety vs non-agentic approaches | Proposal: Central Research Question | requirement |
| R-007 | RQ1: does combining MQTT, flows and honeypot improve detection and classification vs a single source | Proposal: RQ1 | requirement |
| R-008 | RQ2: does the agentic workflow classify more accurately than a prompt-only LLM on the same base model | Proposal: RQ2 | requirement |
| R-009 | RQ3: do explicit safety constraints reduce unsafe/invalid recommendations without making them less useful | Proposal: RQ3 | requirement |
| R-010 | RQ4: does the complete agent beat both non-agentic baselines on detection, classification and response safety | Proposal: RQ4 | requirement |
| R-011 | H1: all three sources combined give significantly higher detection and classification than any single source | Proposal: H1; Record §1.1 | requirement |
| R-012 | H2: agentic workflow classifies incident type and severity significantly more accurately than prompt-only, same model | Proposal: H2; Record §1.1 | requirement |
| R-013 | H3: safety constraints significantly reduce unsafe or invalid recommendations with no significant loss in usefulness | Proposal: H3; Record §1.1 | requirement |
| R-014 | H4: complete agent significantly outperforms both baselines on detection and classification and gives significantly fewer unsafe recommendations | Proposal: H4; Record §1.1 | requirement |
| R-015 | Objective 1: build a small IoT testbed with normal and malicious activity and collect MQTT anomalies, flows and honeypot logs | Proposal: Objective 1 | deliverable |
| R-016 | Objective 2: agent reads alerts, correlates evidence across the three sources, classifies type, severity and affected device | Proposal: Objective 2 | requirement |
| R-017 | Objective 3: safety constraints (limited action space, schemas, validation) so recommendations are controlled, auditable and never executed | Proposal: Objective 3 | requirement |
| R-018 | Objective 4: define a ground-truth reference and a scoring protocol for classification accuracy, safety and usefulness | Proposal: Objective 4 | deliverable |
| R-019 | Objective 5: evaluate against ground truth and both baselines on detection, classification, response safety and reliability | Proposal: Objective 5 | requirement |
| R-020 | "Reliability" is promised as an evaluation dimension but no metric for it is defined anywhere | Proposal: Objective 5; Brief: Expected Work | open question |
| R-021 | Evaluate response quality, reliability and robustness | Brief: Expected Work | requirement |
| R-022 | "Robustness" is named in the brief but has no defined test or metric | Brief: Expected Work | open question |
| R-023 | Expected outcome: a working agent, the testbed, and labelled normal and malicious scenarios as ground truth | Proposal: Expected Outcomes | deliverable |
| R-024 | Report results honestly, including any case where the agent does not beat a baseline | Proposal: Expected Outcomes | writing |
| R-025 | Results must show where the agent is reliable and where it is not | Proposal: Expected Outcomes | writing |
| R-026 | Main-contribution statement: controlled, auditable assistant reaching safe structured response recommendation, evaluated end to end in IoT | Proposal: Expected Outcomes | writing |

## 2. Research gap and positioning

| ID | Item | Source | Category |
|---|---|---|---|
| R-027 | Gap claim: no work combines multi-source IoT telemetry, agentic classification and safety-constrained recommendation evaluated end to end against testbed ground truth | Proposal: Research Gap; Record §1.3 | writing |
| R-028 | Position IDS-Agent [16] as stopping at detection + explanation | Record §1.3; Proposal: Research Gap | writing |
| R-029 | Position Ferrag et al. [17] as stopping at detection | Record §1.3 | writing |
| R-030 | Position Chou et al. [18] as stopping at report generation | Record §1.3 | writing |
| R-031 | Position CyberRAG [19] as enterprise alerts, stopping at reporting | Record §1.3 | writing |
| R-032 | Frame the problem as the intersection of IoT IDS, LLM agents and AI risk management | Proposal: Research Problem | writing |
| R-033 | Motivate controlled autonomy with [13] (agents fail at measurable rates), [14] (risk awareness) and [15] (NIST AI RMF) | Proposal: Research Gap; Research Problem | writing |
| R-034 | Design draws on IDS-Agent [16] and CyberRAG [19]; cite them as the design lineage | Proposal: Methodology | writing |
| R-035 | Motivation example: a wrong automatic action (e.g. stopping a hospital machine) can harm as much as the attack | Arch §1.1; Proposal: Research Problem | writing |

## 3. Agent role and capabilities

| ID | Item | Source | Category |
|---|---|---|---|
| R-036 | The agent recommends and never executes any action | Proposal: Research Problem, Objective 3; Record §1.1; Arch §1; Brief | prohibition |
| R-037 | The system can read but never change anything on the network; a human always decides | Arch §1 | constraint |
| R-038 | Agent classifies incident type, severity and affected device | Record §1.1; Proposal: Methodology | requirement |
| R-039 | Agent emits a structured response recommendation | Record §1.1 | requirement |
| R-040 | Report fields: incident type, severity, affected device, evidence, recommended action | Brief: Expected Work; Proposal: Methodology | requirement |
| R-041 | The human receives one clear report with a suggestion instead of many separate alerts | Arch §2, §5 step 8 | requirement |
| R-042 | LLM generates hypotheses about attacks | Brief: Generative AI Dimension | requirement |
| R-043 | LLM asks for missing information | Brief: Generative AI Dimension | requirement |
| R-044 | LLM explains its reasoning in a structured format | Brief: Generative AI Dimension | requirement |
| R-045 | LLM produces incident reports | Brief: Generative AI Dimension | requirement |
| R-046 | Agent uses external tools: log parsers, detectors, an MQTT monitor and a retrieval component | Proposal: Methodology; Brief | requirement |
| R-047 | Agent may use vulnerability databases as a tool | Brief: Generative AI Dimension | requirement |
| R-048 | Agent follows a reason-and-act loop [10] | Proposal: Methodology | requirement |
| R-049 | Detectors (rule-based or ML) convert telemetry into the alerts the agent consumes | Proposal: Methodology; Brief | requirement |

## 4. Testbed and attack generation

| ID | Item | Source | Category |
|---|---|---|---|
| R-050 | Three telemetry sources: MQTT anomalies, network flows, honeypot logs | Record §1.1; Proposal: Methodology; Arch §3 | requirement |
| R-051 | Testbed contains IoT devices or emulators over MQTT, a captured network segment, and a decoy honeypot host | Proposal: Methodology | requirement |
| R-052 | Testbed is fully emulated with Docker Compose; no physical hardware | Record §4, §6.2; Arch §10 | decision |
| R-053 | Testbed produces labelled raw telemetry on demand, reproducibly | Record §2 | requirement |
| R-054 | Testbed resets with one command and is portable (corpus may be regenerated in month 5) | Record §6.2; Arch §10 | requirement |
| R-055 | Skeleton composition: Mosquitto broker, 3–4 MQTT emulators, one honeypot, a capture sidecar | Record §8 (ticket 7) | decision |
| R-056 | First testbed version runs benign traffic only | Record §8 (ticket 7) | decision |
| R-057 | Testbed runs under both normal and malicious activity | Proposal: Methodology | requirement |
| R-058 | Devices, protocols and attacks guided by Bot-IoT [6], TON_IoT [7], CICIoT2023 [8], MQTTset [9] | Proposal: Methodology; Record §1.1 | requirement |
| R-059 | Attack types include denial of service, scanning, brute-force login and botnet traffic | Proposal: Methodology; Record §1.1 | requirement |
| R-060 | Exactly six attack families | Record §5 | decision |
| R-061 | Family mix: two visible in all three sources, two in exactly two, two in one | Record §5 | decision |
| R-062 | Candidate families: MQTT flood, MQTT broker password guessing, port scan, SSH password guessing, botnet, DoS (proposal only) | Record §3.2 | decision |
| R-063 | Which six attack families? | Record §10; Arch §13 | open question |
| R-064 | A meaningful subset of families must leave traces in at least two sources | Record §3.2 | constraint |
| R-065 | Attack generation by replaying published datasets plus standard tooling | Record §5 | decision |
| R-066 | No custom attack code | Record §5 | prohibition |
| R-067 | Every attack is executed deliberately, so each event's label is known in advance | Proposal: Methodology | requirement |
| R-068 | Schedule attacks so they never overlap on the same device | Record §4.1 | constraint |
| R-069 | Testbed on an isolated Docker network with no route to the host LAN or the internet | Record §6.11 | requirement |
| R-070 | Verify network isolation before running any attack tooling, not after | Record §6.11 | test |
| R-071 | Attacks only on the isolated testbed, never on production or third-party networks | Proposal: Methodology | prohibition |
| R-072 | Never run Ollama and the full testbed at the same time on 16 GB | Record §4.2 | prohibition |
| R-073 | Workflow: generate corpus, shut testbed down, then develop the agent against frozen bundles | Record §4.2 | decision |

## 5. Ground truth and corpus

| ID | Item | Source | Category |
|---|---|---|---|
| R-074 | Ground truth derived mechanically from the scenario schedule | Record §4, §4.1; Proposal: Methodology | decision |
| R-075 | Label rule: family F if the window overlaps a scheduled episode of F against device D, else benign | Record §4.1 | decision |
| R-076 | Target corpus size 200–400 bundles | Record §3 (risk #2) | decision |
| R-077 | Repetitions k = 3–5 per condition | Record §3 (risk #2) | decision |
| R-078 | Matrix sizing uses ~250 bundles and k = 3 | Record §4.4.1 | decision |
| R-079 | Run a power calculation before generating the corpus | Record §3 (risk #2) | requirement |
| R-080 | How many scenarios are needed for statistical validity? | Record §10; Arch §13 | open question |
| R-081 | Corpus freeze is a formal milestone with a version number | Record §7.1 | deliverable |
| R-082 | Corpus has a dataset card | Record §7.1 | deliverable |
| R-083 | Raw telemetry kept as files on disk with a corpus manifest holding SHA-256 per file | Record §6.7 | requirement |
| R-084 | Any format change after the freeze forces full regeneration of the corpus | Record §7.1; Arch §12 | constraint |
| R-085 | EPIC-2 (corpus) is the critical-path gate; nothing downstream can be measured before it | Record §7, §7.1; Arch §12 | decision |

## 6. Incident unit and assembly

| ID | Item | Source | Category |
|---|---|---|---|
| R-086 | Bundle = all normalized alerts, from sources in the current config, with timestamp in window W and subject device D | Record §4.1; Arch §6 | decision |
| R-087 | Window W = 60 seconds | Record §4, §4.1; Arch §6 | decision |
| R-088 | Is a 60-second window the right unit? | Record §10; Arch §13 | open question |
| R-089 | Device D = the non-infrastructure endpoint; honeypot events key to the honeypot | Record §4.1 | decision |
| R-090 | Device mapping is defined once, in the normalizer, in code | Record §4.1 | constraint |
| R-091 | Tiling is contiguous and non-overlapping, per device, across the full capture | Record §4, §4.1 | decision |
| R-092 | Empty windows are dropped | Record §4.1 | decision |
| R-093 | Bundles are assembled deterministically, outside the agent, before any condition runs | Record §4, §4.1; Arch §6.1 | decision |
| R-094 | Every condition receives the identical bundle set | Record §4; Arch §6.1 | constraint |
| R-095 | Normalization rewrites all telemetry into one format; downstream code never needs to know the source | Arch §5; Record §2 | requirement |
| R-096 | Pipeline order: raw logs → clean → detect → group → shrink → agent → safety check → report | Arch §5 | decision |
| R-097 | Only the agent step uses AI; every other step is deterministic code | Arch §5; Record §6.3 | constraint |
| R-098 | Alert schema v0.1 is written after the spike and informed by it | Record §8 (ticket 8), §9 | decision |
| R-099 | Do not let anyone hand you an alert schema: derive it from the spike's failures | Record §9 | constraint |
| R-100 | Normalized alerts and bundles stored as Parquet | Record §6.7 | decision |
| R-101 | Methods chapter states the scoping choice: the agent classifies bundles it is given, it does not discover incident boundaries | Record §4.1; Arch §6.1 | writing |

## 7. Bundle reduction and token budget

| ID | Item | Source | Category |
|---|---|---|---|
| R-102 | A deterministic reduction bounds the bundle size before it reaches any model | Record §4.1; Arch §6.2 | requirement |
| R-103 | Identical reduction for every condition, including both baselines | Record §4.1, §4.4; Arch §6.2 | constraint |
| R-104 | Reduction frozen in METHODS.md with a stated reduction ratio before the first experiment | Record §4.4 | requirement |
| R-105 | If the reduction must change: rerun everything and record it in the changelog | Record §4.4 | constraint |
| R-106 | Over-compression can hide the H1 fusion benefit (token optimisation is not research-neutral) | Record §4.4 | risk |
| R-107 | Flows reduction: count, unique dst IPs, unique dst ports, bytes in/out, protocol mix, SYN-only ratio, duration stats | Record §4.4 | decision |
| R-108 | Flows exemplars: top-5 by detector score | Record §4.4 | decision |
| R-109 | MQTT reduction: message count, unique topics, payload size stats, QoS mix, connect/disconnect count, auth failures | Record §4.4 | decision |
| R-110 | MQTT exemplars: top-3 anomalous messages | Record §4.4 | decision |
| R-111 | Honeypot reduction: session count, unique source IPs, auth attempts, success/fail | Record §4.4 | decision |
| R-112 | Honeypot exemplars: up to 3 command sequences, hard-truncated | Record §4.4 | decision |
| R-113 | Reduced bundle includes each detector's score and label | Record §4.4 | decision |
| R-114 | Reduced bundle target size ~800–1,200 tokens | Record §4.4 | decision |
| R-115 | Node-scoped context: the classification node gets no action catalog | Record §4.4 | decision |
| R-116 | Node-scoped context: the recommendation node gets only the classification output and evidence IDs, no raw exemplars | Record §4.4 | decision |
| R-117 | Prompt order static prefix first: system role, schema, action catalog, then variable bundle content last (caching) | Record §4.4 | decision |
| R-118 | Output target 150–250 tokens via enums and evidence-by-ID | Record §4.4 | decision |
| R-119 | No conversation accumulation: each graph node is a fresh call with explicitly built context | Record §4.4 | prohibition |
| R-120 | Input tokens per call: target ≤2,000, hard ceiling 2,500 | Record §4, §4.4 | decision |
| R-121 | Output tokens per call: target ≤200, hard ceiling 250 | Record §4, §4.4 | decision |
| R-122 | Total per bundle ~6,600 input / ~600 output tokens | Record §4.4 | decision |
| R-123 | Cost estimate assumes ~3k input and ~250 output tokens per call (~36M in / 3M out) | Record §4.4.1 | decision |
| R-124 | Token ceiling enforced as a code assertion that fails at build time | Record §4, §4.4 | test |
| R-125 | Do not trim the reasoning instructions in the agentic prompts (would weaken H2's treatment) | Record §4.4 | prohibition |
| R-126 | Do not cut the evidence field from the output schema | Record §4.4 | prohibition |
| R-127 | Do not remove the explicit action catalog from the recommendation prompt (H3 depends on it) | Record §4.4 | prohibition |

## 8. LLM serving and cost

| ID | Item | Source | Category |
|---|---|---|---|
| R-128 | Hardware: 16 GB Apple Silicon M2 MacBook Pro | Record §4.2 | constraint |
| R-129 | Total experiment budget under €100 | Record §4.2; Arch §10 | constraint |
| R-130 | System under test: open-weights instruct model on a hosted provider, pinned by model name and revision | Record §4, §4.2; Arch §10 | decision |
| R-131 | Local Ollama (8B class) is the development environment, not the experiment runner | Record §4, §4.2; Arch §11 | decision |
| R-132 | One LLM client against an OpenAI-compatible interface; local vs hosted is a base-URL change | Record §4, §4.2; Arch §11 | decision |
| R-133 | Configuration via LLM_BASE_URL and LLM_MODEL | Record §4.2 | decision |
| R-134 | Record per run: model name + revision, provider, sampling params, seed, prompt template version, graph version, in every result row | Record §4.2 | requirement |
| R-135 | Develop on the same model family as the experiments (same model, or smaller sibling) | Record §4.2 | constraint |
| R-136 | Sanity comparison between development and experiment model before the matrix | Record §4.2 | test |
| R-137 | Never develop on one vendor's model and run experiments on another's | Record §4.2 | prohibition |
| R-138 | No vLLM or self-hosted serving at scale | Record §4.2 | prohibition |
| R-139 | ADR-001: LLM serving, cost and time budget | Record §4.2, §8 (ticket 6) | deliverable |
| R-140 | Verify current hosted rates when writing ADR-001 | Record §4.2 | requirement |
| R-141 | Hard spending cap on the provider account | Record §4.4.1 | requirement |
| R-142 | Retries use backoff (a tight retry loop is how the cap gets tested) | Record §4.4.1 | requirement |
| R-143 | Budget covers one exploratory partial run, three full matrix runs and headroom | Record §4.4.1 | decision |
| R-144 | Ollama default context (2048) truncates silently | Record §4.3 | risk |
| R-145 | Set Ollama num_ctx to 8192 explicitly | Record §4.3, §9 | decision |
| R-146 | Verify context with a marker test before any run | Record §4.3, §9 | test |
| R-147 | Memory: 8B at Q4 fits comfortably; 14B is tight on 16 GB; 8B Q4_K_M ≈ 4.5–5 GB | Record §4.2, §4.3 | constraint |
| R-148 | One base model only; no model comparison | Record §5 | decision |
| R-149 | Prompt-only baseline uses the same base model as the agent | Proposal: Methodology, H2; Record §1.1 | constraint |
| R-150 | Methods chapter states the reproducibility claim: pinned open weights can be re-served by anyone | Record §4.2; Arch §10 | writing |

## 9. Architecture and stack

| ID | Item | Source | Category |
|---|---|---|---|
| R-151 | ExperimentConfig with sources (any subset of mqtt/flows/honeypot), strategy (agentic/prompt_only/ml_classifier), safety (enforcing/logging_only) | Record §6.1 | decision |
| R-152 | No condition is hardcoded; all are runtime-injected from one config object | Record §6.1 | constraint |
| R-153 | Every result row carries the config and its hash | Record §6.1 | requirement |
| R-154 | Modular monolith with hard internal seams | Record §6.1 | decision |
| R-155 | No microservices | Record §6.1 | prohibition |
| R-156 | Backend: FastAPI | Record §6.2; Arch §10 | decision |
| R-157 | The safety schema and the API schema are the same Pydantic object | Record §6.2 | decision |
| R-158 | Frontend: React, kept thin | Record §6.2; Arch §10 | decision |
| R-159 | REST for commands, Server-Sent Events for the reasoning trace (no WebSockets) | Record §6.2 | decision |
| R-160 | openapi-typescript generates TS types from the OpenAPI schema so a schema change breaks the build | Record §6.2 | decision |
| R-161 | No agent framework (no LangChain, LlamaIndex, LangGraph); graph written directly, ~200 lines | Record §6.2; Arch §10 | prohibition |
| R-162 | Exact prompt bytes sent to the model must be capturable (reproducibility claim) | Record §6.2 | requirement |
| R-163 | Retrieval: sentence-transformers embeddings in a numpy array, cosine similarity | Record §6.2; Arch §10 | decision |
| R-164 | No vector database (no Chroma, no Qdrant) | Record §6.2 | prohibition |
| R-165 | BM25 is an acceptable alternative retrieval method | Record §6.2 | decision |
| R-166 | Flow detector: LightGBM or XGBoost | Record §6.2 | decision |
| R-167 | MQTT detector: statistical thresholds | Record §6.2 | decision |
| R-168 | Honeypot detector: parser plus rules | Record §6.2 | decision |
| R-169 | Detectors are conventional/off-the-shelf; they are not the contribution | Record §5; Arch §10 | decision |
| R-170 | Knowledge subsystem holds device inventory, action catalog and ATT&CK mitigations | Record §2; Arch §4.1 | requirement |
| R-171 | Small curated knowledge base of 50–200 documents, not a general RAG corpus | Record §5; Arch §10 | decision |
| R-172 | Results stored as Parquet, one row per (bundle, condition, repetition), with full provenance | Record §6.7 | decision |
| R-173 | Console operational state in SQLite | Record §6.7 | decision |
| R-174 | Audit log is append-only JSONL, never rewritten | Record §6.7 | decision |
| R-175 | No Postgres | Record §6.7 | prohibition |
| R-176 | No message queue | Record §6.7 | prohibition |
| R-177 | No orchestration beyond Docker Compose | Record §6.7 | prohibition |
| R-178 | No authentication; console binds to localhost | Record §4, §6.8 | decision |
| R-179 | API key in .env, gitignored, never logged | Record §6.11 | requirement |
| R-180 | No personal data and no human subjects | Record §6.11; Proposal: Methodology | constraint |
| R-181 | Structured JSON logging with structlog from the first commit | Record §6.10 | requirement |
| R-182 | Every LLM call logs node, model, revision, tokens in/out, latency, full prompt, raw completion, parse outcome, condition, bundle ID, repetition | Record §6.10, §4.4 | requirement |
| R-183 | One logging mechanism serves as audit log, cost instrumentation and debugger | Record §6.10 | decision |
| R-184 | No OpenTelemetry, no Prometheus | Record §6.10 | prohibition |
| R-185 | Monorepo scaffold with uv or Poetry, ruff, mypy, pytest, pre-commit, CI and an ADR log | Record §8 (ticket 2) | deliverable |
| R-186 | Repository and package scaffolded as `thesis` until a name is chosen | Record §4, §11.4 | decision |

## 10. Agent graph

| ID | Item | Source | Category |
|---|---|---|---|
| R-187 | Bounded reasoning graph with fixed topology, not free-form ReAct | Record §6.3; Arch §7 | decision |
| R-188 | Methods chapter states the fixed-graph vs free-form ReAct trade-off | Record §6.3; Arch §7.1 | writing |
| R-189 | Exactly 3 LLM calls per bundle; deterministic code does everything else | Record §4, §6.3 | decision |
| R-190 | Bundle ingestion and reduction is a deterministic (non-LLM) node | Record §6.3 | decision |
| R-191 | Knowledge retrieval is deterministic and called as a tool | Record §6.3 | decision |
| R-192 | Node 1 evidence analysis (LLM, tool access): reduced bundle + device context in; per-source findings + cross-source observations out | Record §6.3; Arch §7 | requirement |
| R-193 | Node 2 classification (LLM, structured output): node 1 findings in; type, severity, affected device, confidence out | Record §6.3; Arch §7 | requirement |
| R-194 | Node 3 recommendation (LLM, enum-constrained): classification + permitted catalog in; one action with evidence refs out | Record §6.3; Arch §7 | requirement |
| R-195 | Validation and rejection handling is a deterministic node | Record §6.3 | requirement |
| R-196 | Audit log write is a deterministic node | Record §6.3 | requirement |

## 11. Safety layer

| ID | Item | Source | Category |
|---|---|---|---|
| R-197 | Limited action space: a closed enumeration defined in advance | Record §6.4; Proposal: Methodology | requirement |
| R-198 | Action catalog derived from European official guidance (ENISA, ANSSI / CERT-FR), NIST SP 800-61, MITRE ATT&CK mitigations and published IR playbooks, with a citation per entry | Record §3.4, §6.4; Arch §8 | requirement |
| R-199 | Action catalog has 6–8 candidate actions to start | Record §6.5 | decision |
| R-200 | Action catalog defined before seeing any agent output | Record §8 | constraint |
| R-201 | Optional: a classmate double-rates 20% of the catalog as a bonus; never block on it | Record §3.4 | decision |
| R-202 | Solo work means no second rater (Cohen's κ unavailable; intra-rater test-retest is weak) | Record §3.4 | risk |
| R-203 | Output schema (Pydantic): incident_type, severity, affected_device, evidence, recommended_action, confidence | Record §6.4, §6.5 | requirement |
| R-204 | incident_type enum: the six attack families plus benign | Record §6.5 | decision |
| R-205 | severity enum: low / medium / high / critical | Record §6.5 | decision |
| R-206 | affected_device: string device ID | Record §6.5 | decision |
| R-207 | evidence: list of alert IDs referenced from the input, not quoted text | Record §6.5, §4.4 | decision |
| R-208 | confidence: float 0–1 | Record §6.5 | decision |
| R-209 | Constrained decoding enforces the schema at generation time | Record §6.4, §4.4 | decision |
| R-210 | Validator rejects malformed output | Record §6.4; Arch §8 | requirement |
| R-211 | Validator rejects any action outside the enum | Record §6.4; Arch §8 | requirement |
| R-212 | Validator rejects evidence references not present in the bundle | Record §6.4; Arch §8 | requirement |
| R-213 | Audit log records every attempt, passed or not, with full prompt, raw completion and parse outcome | Record §6.4; Proposal: Methodology; Arch §8 | requirement |
| R-214 | What happens when the validator rejects: retry with feedback, escalate to human, or hard fail? | Record §3.1, §10; Arch §13 | open question |
| R-215 | Fix the rejection policy in advance and log it per attempt | Record §3.1 | requirement |
| R-216 | Safety layer can be switched on and off (enforcing vs logging_only) for the H3 ablation | Record §6.1; Proposal: Methodology | requirement |
| R-217 | Honeypot attacker text enters prompts and is a prompt-injection channel | Record §3 (risk #7), §3.3 | risk |
| R-218 | Honeypot text is strictly delimited | Record §3.3, §6.11; Arch §8 | requirement |
| R-219 | Honeypot text is hard-truncated | Record §3.3, §6.11; Arch §8 | requirement |
| R-220 | Honeypot text is never placed adjacent to schema instructions | Record §3.3, §6.11 | constraint |
| R-221 | Validation is a hard gate, not a filter | Record §3.3, §6.11 | constraint |
| R-222 | Prompt-injection experiment (inject adversarial strings, measure steering outside the action set) is stretch only | Record §3.3, §5 | decision |
| R-223 | Decide at month four whether to run the prompt-injection experiment (only if ahead) | Record §3.3 | decision |
| R-224 | Note in the thesis that [16], [18], [19] do not address prompt injection | Record §3.3 | writing |

## 12. Baselines

| ID | Item | Source | Category |
|---|---|---|---|
| R-225 | Baseline A: conventional ML classifier trained on the same telemetry | Proposal: Methodology; Record §6.6 | requirement |
| R-226 | The flow classifier doubles as Baseline A | Record §4, §5 | decision |
| R-227 | Baseline A gets a severity→action lookup so the H4 safety comparison is well-posed | Record §3 (risk #6), §4, §6.6 | decision |
| R-228 | Baseline B: same LLM, one request, no reasoning steps, tools, retrieval or safety layer | Proposal: Methodology; Record §6.3, §6.6 | requirement |
| R-229 | Baseline B receives the same alerts as the agent | Proposal: Methodology | constraint |
| R-230 | Baseline B gets a well-written prompt with the same output schema | Record §6.6 | requirement |
| R-231 | Tune Baseline A properly: feature engineering, hyperparameter search, class-imbalance handling | Record §5, §6.6; Arch §9 | requirement |
| R-232 | A weak baseline invalidates the result; an examiner will attack this first | Record §6.6; Arch §9 | risk |
| R-233 | Thesis frames Baseline A as 'is an LLM needed?' and Baseline B as 'does the architecture help?' | Record §6.6, §12.4; Arch §9 | writing |
| R-234 | Are two baselines sufficient? | Record §10; Arch §13 | open question |

## 13. Evaluation design, metrics and statistics

| ID | Item | Source | Category |
|---|---|---|---|
| R-235 | Paired design: same scenarios for every condition, analysed with paired tests | Proposal: Methodology; Record §1.1 | requirement |
| R-236 | H1 ablation: agent on each single source and on all three combined | Proposal: Methodology; Arch §9.1 | requirement |
| R-237 | H2 ablation: agent vs prompt-only LLM | Proposal: Methodology | requirement |
| R-238 | H3 ablation: same agent with safety layer on and off | Proposal: Methodology | requirement |
| R-239 | H4 comparison: complete agent vs both baselines | Proposal: Methodology | requirement |
| R-240 | Report H1 stratified by attack family, separating gain-from-fusion from gain-from-having-a-source | Record §3.2 | requirement |
| R-241 | Consider pairwise source conditions (MQTT+flows, flows+honeypot) | Record §3.2 | open question |
| R-242 | Matrix: 5 agentic conditions × 3 calls + 1 prompt-only condition × 1 call per bundle per repetition | Record §4.4.1 | decision |
| R-243 | Detection metrics: precision, recall, F1 | Proposal: Methodology; Record §1.1 | metric |
| R-244 | Classification metrics: accuracy and macro-F1 | Proposal: Methodology; Record §1.1 | metric |
| R-245 | Safety metric: proportion of unsafe or invalid recommendations | Proposal: Methodology; Record §1.1 | metric |
| R-246 | Usefulness metric: agreement with a predefined acceptable-action set | Proposal: Methodology; Record §1.1 | metric |
| R-247 | Acceptable and unsafe action sets fixed per scenario family before any experiment, identical across conditions | Proposal: Methodology; Record §3.1 | constraint |
| R-248 | H3 is circular: the validator drives the out-of-catalog count to zero by construction | Record §3 (risk #3), §3.1; Arch §8.1 | risk |
| R-249 | Safety metric part 1: schema validity | Record §3.1; Arch §8.1 | metric |
| R-250 | Safety metric part 2: action-space membership — reported, never the headline | Record §3.1; Arch §8.1 | metric |
| R-251 | Safety metric part 3: contextual appropriateness — the real H3 result (e.g. isolating a critical device for one port scan is unsafe) | Record §3.1; Arch §8.1 | metric |
| R-252 | How should contextual safety be scored? | Record §10; Arch §13 | open question |
| R-253 | H1 has a built-in confound: not every family is visible in every source | Record §3 (risk #4), §3.2 | risk |
| R-254 | McNemar test for paired binary outcomes | Record §10 | metric |
| R-255 | Wilcoxon signed-rank test for paired scores | Record §10 | metric |
| R-256 | Bundle-level metrics are primary | Record §4.1 | decision |
| R-257 | Block bootstrap with the attack episode as the resampling unit (bundles in one episode are not independent) | Record §4.1 | metric |
| R-258 | Methods chapter mentions the clustering issue and the block bootstrap | Record §4.1; Arch §6.2 | writing |
| R-259 | Run an exploratory partial run before the full matrix | Record §4.4.1 | requirement |
| R-260 | Run the full matrix three times | Record §4.4.1 | requirement |
| R-261 | Cost per incident analysed is reported as a result | Record §4.4; Arch §10 | metric |
| R-262 | Per-call token and latency data written into the same result rows as the metrics | Record §4.4 | requirement |
| R-263 | Evaluation harness runs conditions, computes metrics and runs the paired tests | Record §2 | requirement |

## 14. Testing

| ID | Item | Source | Category |
|---|---|---|---|
| R-264 | Test parsers hard | Record §6.9 | test |
| R-265 | Test bundle assembly hard (a bug here silently invalidates every experiment) | Record §6.9 | test |
| R-266 | Test the reduction step hard | Record §6.9 | test |
| R-267 | Test validators hard | Record §6.9 | test |
| R-268 | Golden-file tests on reduction: fixed input bundle, exact expected output, committed | Record §6.9 | test |
| R-269 | Property tests on the validator: no output outside the action enum ever passes | Record §6.9 | test |
| R-270 | Do not unit-test LLM output quality | Record §6.9 | prohibition |
| R-271 | One end-to-end integration test against local Ollama, marked slow, excluded from CI | Record §6.9 | test |
| R-272 | The test split matters more than the coverage number (no coverage target) | Record §6.9 | decision |

## 15. Methods contract and solo-work substitutes

| ID | Item | Source | Category |
|---|---|---|---|
| R-273 | No supervisor guidance: design flaws would otherwise surface only at the defense | Record §3.4; Arch §13 | risk |
| R-274 | Write METHODS.md before building and freeze it | Record §3.4, §8 (ticket 3) | deliverable |
| R-275 | METHODS.md is 4–6 pages | Record §3.4 | constraint |
| R-276 | METHODS.md contains: incident unit, condition matrix, metric definitions, action catalog derivation, statistical tests, target N | Record §3.4 | requirement |
| R-277 | The incident unit is the first section of METHODS.md | Record §8 (ticket 3) | decision |
| R-278 | METHODS.md is dated | Record §3.4 | requirement |
| R-279 | Once experiments start, METHODS.md gets an appended changelog instead of edits | Record §3.4, §4.4 | constraint |
| R-280 | METHODS.md blocks EPIC-3 and EPIC-9 | Record §8 (ticket 3) | constraint |
| R-281 | Bundle reduction policy v1.0: aggregate fields and exemplar criteria per source, frozen in METHODS.md | Record §8 (ticket 5) | deliverable |
| R-282 | Action catalog v0.1 with a citation per entry | Record §8 (ticket 4) | deliverable |
| R-283 | Research tickets (METHODS.md, catalog, reduction policy) are not postponed | Record §8 | constraint |
| R-284 | Explicit scope cuts stand in for a supervisor saying 'that's too much' | Record §3.4, §5 | decision |

## 16. Plan, epics and scope caps

| ID | Item | Source | Category |
|---|---|---|---|
| R-285 | 12 epics with the dependency graph in §7 | Record §7 | decision |
| R-286 | Four phases: A build the data, B prepare, C build the agent, D measure and write | Record §7.2; Arch §12 | decision |
| R-287 | EPIC-10 (console) runs in parallel and late; EPIC-11 (writing) is continuous | Record §7 | decision |
| R-288 | Sprint 0 has 8 tickets (spike 5, scaffold 3, METHODS 5, catalog 5, reduction 5, ADR-001 3, testbed 5, alert schema 3) | Record §8 | decision |
| R-289 | The spike is the first ticket, before the repo scaffold | Record §8, §9 | decision |
| R-290 | Subsystems 1 (testbed) and 7 (console) are the biggest calendar risks and are explicitly capped | Record §2 | risk |
| R-291 | Console is built in the last three weeks | Record §5 | constraint |
| R-292 | Console has exactly four screens: incident list, incident detail with evidence and trace, recommendation with accept/reject, audit log | Record §5 | decision |
| R-293 | Console stays at or below ~10% of engineering time | Record §5 | constraint |
| R-294 | Console produces zero results for any hypothesis; it is for demonstration only | Record §2, §5; Arch §4.1 | constraint |
| R-295 | A user interface is a personal requirement, not a thesis requirement | Record §1.2 | constraint |

## 17. Walking-skeleton spike (Ticket 1)

| ID | Item | Source | Category |
|---|---|---|---|
| R-296 | Spike timebox: 5 working days, hard stop | Record §9; Arch §12.1 | constraint |
| R-297 | Spike is one file, ~150 lines, kept throwaway and never used as the foundation | Record §9; Arch §12.1 | constraint |
| R-298 | Spike input: hand-written JSON of what the normalized alerts from each source would look like | Record §9 | requirement |
| R-299 | Spike: one prompt, one LLM call constrained to a Pydantic schema, one validator, print the result | Record §9 | requirement |
| R-300 | No testbed, detectors, retrieval or agent framework in the spike | Record §9 | prohibition |
| R-301 | Spike scenario: SSH brute force against the honeypot with flow traces; MQTT deliberately absent | Record §9 | decision |
| R-302 | Spike output uses the §6.5 schema | Record §9 | requirement |
| R-303 | Spike: num_ctx set explicitly and verified with the marker test before any run | Record §9 | test |
| R-304 | Spike: 20 runs, 10 on local Ollama and 10 on one hosted mid-size model | Record §9; Arch §12.1 | test |
| R-305 | Spike records per run: schema-valid or not, verdict, input tokens, output tokens, latency | Record §9 | requirement |
| R-306 | Spike logs the full prompt and raw completion, not only the parsed object | Record §9 | requirement |
| R-307 | Spike reports validity rate per model | Record §9 | metric |
| R-308 | Spike reports agreement rate across the 10 runs per model | Record §9 | metric |
| R-309 | Spike reports mean input and output tokens per call | Record §9 | metric |
| R-310 | Spike counts how many answers are correct (needs an expected verdict for the hand-written bundle) | Arch §12.1 | metric |
| R-311 | Spike findings note, half a page: what the model got wrong, asked for or hallucinated | Record §9 | deliverable |
| R-312 | Spike results decide the model, confirm or break the 2,000-token budget, give the alert schema, settle ADR-001 | Record §9 | decision |

## 18. Thesis writing, ethics and references

| ID | Item | Source | Category |
|---|---|---|---|
| R-313 | Ethics section: attacks only on the isolated testbed, no human subjects, no personal data | Proposal: Methodology; Record §6.11 | writing |
| R-314 | Acknowledge any use of AI tools transparently, per the dissertation guide | Proposal: Methodology | writing |
| R-315 | Thesis states in one line that authentication is out of scope | Record §4, §6.8 | writing |
| R-316 | Resolve reference [4]: complete author list, volume and article number | Proposal: References; Record §3 (risk #8), §16 | writing |
| R-317 | Resolve reference [17]: end page | Proposal: References; Record §3 (risk #8), §16 | writing |
| R-318 | References follow the IEEE style used in the proposal | Proposal: References | writing |
| R-319 | Report cost per incident as a contribution none of [16], [18], [19] report | Record §4.4 | writing |
| R-320 | System name is still open | Record §4, §10, §11 | open question |
| R-321 | Name must not imply execution (rules out Guardian, Shield, Sentinel, Warden, Defender, Enforcer…) | Record §11.1 | constraint |
| R-322 | Name: no Latin or Greek; reads as an LLM system, not a startup; serious; easy to say and spell | Record §11.1 | constraint |
| R-323 | Name avoids 'AI', 'Detect', and generic Cyber/Guard combinations | Record §11.1, §11.5 | constraint |
| R-324 | Do not use any name on the verified-conflict list (Auspex, Interlock, Quorum, Sightline, …) | Record §11.2 | prohibition |
| R-325 | Naming next step: write five names, conflict-check each, flag execution implication, draft the title | Record §11.4 | requirement |
| R-326 | Put descriptors in the subtitle; avoid a forced backronym | Record §11.5 | writing |
| R-327 | Trademark clearance (INPI, EUIPO, USPTO, domains, GitHub/PyPI/npm) only before use beyond the thesis | Record §11.6 | decision |

## 19. Supervisor communication and documents

| ID | Item | Source | Category |
|---|---|---|---|
| R-328 | Material for the supervisor uses simple words, short sentences and many diagrams | Record §12.1 | constraint |
| R-329 | Always open supervisor material with a short overview (he may not have read the proposal) | Record §12.1 | constraint |
| R-330 | 60-second project opener prepared in English and French | Record §12.2 | deliverable |
| R-331 | Three questions to raise: window size, number of scenarios, fair unsafe-recommendation measure (third has priority) | Record §12.5 | writing |
| R-332 | Supervisor meetings are booked for 45 minutes | Record §12.6 | constraint |
| R-333 | Emails to the supervisor carry no agenda; setting the agenda is his role | Record §12.7 | constraint |
| R-334 | Cadence: Thursday internal draft → weekend modifications → Monday final version to the supervisor | Record §12.8 | constraint |
| R-335 | Humanizer pass: sentences ≤~18 words, common words, no idioms, phrasal verbs, metaphors or contractions; never merge sentences | Record §13.2 | constraint |
| R-336 | Humanizer must not change technical names, project vocabulary, labels, numbers, tables, captions, glossary or title page | Record §13.2 | constraint |
| R-337 | Humanizer must not change the meaning of: "It suggests only. It never acts by itself. A human always decides." | Record §13.2 | constraint |
| R-338 | Humanize via Markdown export and rebuild the .docx; never humanize the .docx directly | Record §13.2 | decision |
| R-339 | Illustrated architecture document (14 pages, 11 figures, glossary) is the current version to send | Record §13 | deliverable |
| R-340 | Project Reference document (8 sections, 13 pages) exists | Record §13 | deliverable |
| R-341 | The full project record is kept current as the continuation file | Record §0, §13 | deliverable |

## 20. Working rules

| ID | Item | Source | Category |
|---|---|---|---|
| R-342 | Distinguish academic research requirements from production engineering requirements | Record §14 | constraint |
| R-343 | Avoid unnecessary complexity and over-engineering | Record §14 | constraint |
| R-344 | Do not introduce technologies because they are popular | Record §14; Arch §10 | prohibition |
| R-345 | Do not force AI components, experiments or metrics irrelevant to the proposal | Record §14 | prohibition |
| R-346 | Separate confirmed information from assumptions and recommendations | Record §14 | constraint |
| R-347 | Work incrementally: next step, review, then move on | Record §14 | constraint |
