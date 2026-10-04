# LLM SOC Agent Thesis — Complete Project Record

**Thesis:** LLM-Based Autonomous SOC Agent for IoT Cyberattack Detection and Response
**Author:** EL HAYEK Roy — MSc 2 Artificial Intelligence, ECE Paris
**Proposal date:** July 2026
**Record compiled:** September 2026

This file is the complete record of the planning conversation. It covers every decision made, every risk identified, every name considered, every document produced, and every question still open. It is written so that a fresh conversation — in any account — can pick up from here with no loss of context.

---

## 0. How to use this file

If you are starting a new conversation, upload:

1. The thesis proposal PDF
2. This file
3. `System_Architecture_Illustrated.docx`

Then say: _"Read the full record. Confirm what is locked and what is open, then continue from the next action in section 9."_

Everything below is either **CONFIRMED** (from the proposal), **DECIDED** (settled during planning), or **OPEN** (still undecided). These labels are used throughout.

---

## 1. What the project actually is

Stripped to its core:

> A pipeline that turns three streams of IoT security telemetry into one validated, machine-checkable incident verdict plus a recommended action, and a measurement rig that proves whether the agentic version of that pipeline beats two non-agentic versions.

**The software is the instrument. The experiment is the thesis.** This distinction drives every engineering decision in this document.

### 1.1 Confirmed by the proposal

- Three telemetry sources: MQTT anomalies, network flows, honeypot logs.
- Agent classifies incident type, severity, affected device; emits a structured response recommendation.
- **The agent recommends, never executes.** Non-negotiable; it is the differentiating claim.
- Safety layer = limited action space + structured output schema + validation rules + audit log.
- Two baselines: a conventional ML classifier, and a prompt-only LLM **on the same base model**.
- Four hypotheses, each with a designed ablation (H1 source fusion, H2 agentic vs prompt-only, H3 safety layer on/off, H4 end-to-end).
- Paired experimental design, same scenarios across all conditions, paired statistical tests.
- Ground truth from deliberately executed attacks in an isolated testbed.
- Metrics: precision/recall/F1 for detection; accuracy + macro-F1 for classification; unsafe/invalid rate for safety; agreement with a pre-fixed acceptable-action set for usefulness.
- Attack families drawn from Bot-IoT, TON_IoT, CICIoT2023, MQTTset: DoS, scanning, brute force, botnet.

### 1.2 Not in the proposal

- **Any user interface.** React is a personal requirement, not a thesis requirement.
- Which LLM, hosted or local. → now DECIDED, §4.2
- Whether the testbed is physical, emulated, or hybrid. → now DECIDED (emulated)
- How many scenarios, how many runs. → still OPEN
- What an "incident" is as a unit of data. → now DECIDED, §4.1

### 1.3 The research gap, restated

Existing work stops short in specific ways:

| Work               | What it does                                                                    | Where it stops                                 |
| ------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------- |
| IDS-Agent [16]     | First LLM agent for IoT intrusion detection; reasons over classifier outputs    | Stops at detection + explanation               |
| Ferrag et al. [17] | Lightweight BERT-based IoT threat detection                                     | Stops at detection                             |
| Chou et al. [18]   | Ensemble detection + ReAct RAG agent, evidence-grounded reports                 | Stops at report generation                     |
| CyberRAG [19]      | Agentic RAG, orchestrates classifiers, classification + explanation + reporting | Enterprise alerts, not IoT; stops at reporting |

**None of them** fuse multiple live telemetry sources, enforce explicit safety constraints on recommendations, or evaluate end to end against ground truth from a controlled testbed. That triple is the gap.

---

## 2. The seven subsystems

| #   | Subsystem                         | Responsibility                                                    | Nature                    |
| --- | --------------------------------- | ----------------------------------------------------------------- | ------------------------- |
| 1   | Testbed + scenario runner         | Produces labelled raw telemetry on demand, reproducibly           | Infrastructure            |
| 2   | Normalization + incident assembly | Raw telemetry → uniform alerts → incident bundles                 | Data engineering          |
| 3   | Detection layer                   | MQTT anomaly detector, flow classifier, honeypot parser           | Classical ML              |
| 4   | Knowledge + retrieval             | Device inventory, action catalog, ATT&CK mitigations              | Retrieval                 |
| 5   | Agent + safety layer              | Reasoning graph, schema-constrained output, validators, audit log | LLM engineering           |
| 6   | Evaluation harness                | Runs conditions, computes metrics, runs paired tests              | Research infrastructure   |
| 7   | SOC console                       | FastAPI + React                                                   | Outside the research path |

**Subsystems 5 and 6 carry the scientific contribution.** Subsystems 1–4 exist to feed them. Subsystem 7 demonstrates the result and produces no experimental data.

**Subsystems 1 and 7 will consume the most calendar time if not controlled.** Both are explicitly capped in §5.

---

## 3. Risks to the thesis

Eight issues identified. Four resolved, four live.

| #   | Risk                                                                         | Status       | Handling                                                                                |
| --- | ---------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------- |
| 1   | Incident unit undefined                                                      | **Resolved** | Fixed-window device-keyed tiling, §4.1                                                  |
| 2   | Statistical power — every hypothesis says "significantly" but no N is stated | **LIVE**     | Target 200–400 bundles, k = 3–5 repetitions (k = 3, decided 2026-10-04, METHODS.md v1.0 §2). Power calculation before corpus generation |
| 3   | H3 is circular — the validator eliminates violations by construction         | **LIVE**     | Split the safety metric three ways, §3.1                                                |
| 4   | H1 has a built-in confound                                                   | **LIVE**     | Stratify by attack family, §3.2                                                         |
| 5   | LLM reproducibility                                                          | **Resolved** | Open-weights model pinned by revision                                                   |
| 6   | ML baseline cannot produce a response, so part of H4 is ill-posed            | **Resolved** | Severity→action lookup table gives it a response                                        |
| 7   | Prompt injection via honeypot text                                           | **LIVE**     | Strict delimiting, validation as hard gate. Experiment is stretch-only                  |
| 8   | References [4] and [17] flagged incomplete in the proposal                   | **LIVE**     | Resolve before submission                                                               |

### 3.1 Risk 3 in detail — the H3 circularity

The safety layer validates output against the permitted action space. The safety metric counts recommendations outside that space. Turn the layer on and the count goes to zero **by construction**. That is a tautology, not a finding.

Split the safety metric three ways:

1. **Schema validity** — did it produce parseable, well-formed output? Layer-off will fail here sometimes. Real but shallow.
2. **Action-space membership** — did it name a permitted action? This is where circularity lives. Report it, but do not build the headline on it.
3. **Contextual appropriateness** — the action is permitted _and_ well-formed, but is it right for this incident? Recommending isolation of a critical device in response to a single port scan is a permitted action that is unsafe in context.

**Item 3 is the real H3 result.** It requires pre-fixed unsafe-action sets per scenario family.

**Still unresolved:** when the validator rejects output, what happens? Retry with feedback, fall back to escalate-to-human, or hard fail? Each policy produces a different measured unsafe rate. Fix it in advance and log it per attempt.

### 3.2 Risk 4 in detail — the H1 confound

Not every attack is visible in every source:

| Attack family                 | MQTT | Flows | Honeypot | Sources |
| ----------------------------- | ---- | ----- | -------- | ------- |
| MQTT message flood            | ✓    | ✓     | —        | 2       |
| MQTT broker password guessing | ✓    | ✓     | ✓        | 3       |
| Port scan                     | —    | ✓     | ✓        | 2       |
| SSH password guessing         | —    | ✓     | ✓        | 2       |
| Botnet traffic                | ✓    | ✓     | —        | 2       |
| Denial of service (DoS)       | —    | ✓     | —        | 1       |

_(This selection is a proposal, not a decision — see §9.)_

Comparing MQTT-only against all-three would score near zero on half the attack families for reasons unrelated to correlation quality, and H1 would confirm itself trivially.

Fix it in **scenario design**, not analysis:

- Ensure a meaningful subset of attack families leave traces in at least two sources.
- Report H1 **stratified by attack family**, separating gain-from-fusion from gain-from-having-a-source-at-all.
- Consider pairwise conditions (MQTT+flows, flows+honeypot) rather than only single vs all three. _(Decision 2026-10-04, ticket E0-03: excluded; H1 reports the gain from fusion per family against the best single source instead. METHODS.md v1.0 §2.)_

### 3.3 Risk 7 in detail — prompt injection

Honeypot logs record commands typed by the attacker. Those strings enter the agent's context. That is a prompt injection channel.

- **Problem:** an unmitigated version undermines the safety claim.
- **Opportunity:** nobody in the related work ([16], [18], [19]) addresses it. A small dedicated experiment — inject adversarial strings into honeypot sessions, measure whether the agent's recommendation can be steered outside its permitted action set — would be a novel sub-contribution strengthening H3.
- **Decision:** keep the defensive design (strict delimiting, hard-truncation, never adjacent to schema instructions, validation as hard gate). Run the experiment only if ahead of schedule at month four.

### 3.4 Working solo — three substitutes

No supervisor guidance. The supervisor has stated no expectations and the student works alone. This removes three things, each needing a deliberate replacement:

**1. Nobody catches design flaws before the defense.**
Risks 2, 3 and 4 are exactly what a supervisor catches in a twenty-minute conversation in month two. Without one, they survive until the defense, where an examiner catches them in public.

_Substitute:_ write a **methods contract** (METHODS.md) before building and freeze it. Vagueness is where flaws hide. "The agent classifies incidents" survives any scrutiny; "an incident is a 60-second window keyed to one device, tiled contiguously" forces you to notice you hadn't decided. 4–6 pages: incident unit, condition matrix, metric definitions, action catalog derivation, statistical tests, target N. Date it. Append a changelog rather than editing once experiments start.

**2. Nobody says "that's too much."**
_Substitute:_ the explicit scope cuts in §5.

**3. No second rater for the action catalog.**
Cohen's κ is unavailable solo, and intra-rater test-retest is weak evidence.

_Substitute:_ derive the acceptable and unsafe action sets from **published sources** instead of personal judgment — French and EU official guidance first (ANSSI / CERT-FR for France, ENISA for the EU, and the French CERT Société Générale playbooks), then MITRE ATT&CK mitigations mapped to the attack families and NIST SP 800-61 as supporting references. Every entry carries a citation. _(Decision 2026-10-04, ticket E0-04: French and EU sources are cited first because the thesis is written and examined in France. ATT&CK stays because other tickets use its technique IDs; NIST SP 800-61 stays as a second citation; the US CISA playbooks are not cited. Not EU-only, so that every action keeps at least two independent sources. Details: docs/catalog_derivation.md §3.)_ This is stronger than a κ from one reluctant classmate and converts a subjective labelling problem into a documented mapping. If a classmate can double-rate 20% later, take it as a bonus; don't block on it.

---

## 4. Locked decisions

| Area          | Decision                                                                                                                                                   |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Incident unit | 60s window, device-keyed, contiguous tiling, assembled deterministically outside the agent. Identical bundle set for every condition                       |
| Ground truth  | Derived mechanically from the scenario schedule                                                                                                            |
| Testbed       | Fully emulated, Docker Compose. No physical hardware                                                                                                       |
| LLM serving   | Ollama local for development (8B class), hosted open-weights pinned by revision for the experiment matrix. One OpenAI-compatible client, base URL switches |
| Graph size    | 3 LLM calls per bundle, not 6. Deterministic nodes do the rest                                                                                             |
| Token budget  | ≤2,000 input / ≤200 output per call, asserted in code                                                                                                      |
| Baseline A    | The flow classifier doubles as the ML baseline, plus a severity→action lookup so H4's safety comparison is well-posed                                      |
| Auth          | None. Console binds to localhost. Out of scope, stated in one line in the thesis                                                                           |
| Name          | OPEN. Scaffold as `thesis`                                                                                                                                 |

### 4.1 The incident unit, fully specified

**An incident bundle is the set of all normalized alerts, from all sources in the current configuration, whose timestamp falls in window W and whose subject device is D. Bundles are assembled deterministically, outside the agent, before any condition runs.**

| Parameter           | Value                                                                           | Reasoning                                                                                              |
| ------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Window W            | 60 seconds                                                                      | Long enough for a scan or flood to register in flows; short enough to keep N large and context bounded |
| Device D            | The non-infrastructure endpoint. Honeypot events key to the honeypot            | Define the mapping once, in the normalizer, in code                                                    |
| Tiling              | Contiguous, non-overlapping, across the full capture, per device                | Benign and malicious bundles have identical structure                                                  |
| Empty windows       | Dropped                                                                         | Otherwise thousands of empty benign bundles make precision meaningless                                 |
| Label               | Family F if the window overlaps a scheduled episode of F against D, else benign | Ground truth derives mechanically from the schedule                                                    |
| Overlapping attacks | Schedule so they do not overlap on the same device                              | Cheapest fix, costs nothing scientifically                                                             |

**Why outside the agent:** if the agent decided where one incident ends and the next begins, each condition would produce a different number of items. Detection metrics would require matching agent-produced incidents to ground-truth incidents before anything could be counted, and the comparisons would no longer be paired.

**The trade-off, stated honestly:** you cannot claim the agent discovers incident boundaries. It classifies bundles it is handed. State this as a scoping decision in the methods chapter. The alternative costs the experimental design its validity.

**Two consequences to handle:**

- **Context budget.** A busy 60-second window can contain hundreds of flow records. The assembler needs a deterministic reduction, frozen before experiments and applied identically to every condition including baselines. _If the agent sees a reduced view and the ML baseline sees the full one, H4 is contaminated._
- **Clustering.** A four-minute brute-force episode produces four positively-labelled bundles that are not independent. Bundle-level paired tests slightly overstate significance. Report bundle-level metrics as primary and use the attack episode as the resampling unit for a block bootstrap. Mention it in the methods chapter — examiners respond well to seeing you noticed.

### 4.2 ADR-001 — LLM serving

**Hardware:** 16 GB Apple Silicon MacBook Pro (M2). **Budget:** under €100.

**Decision: an open-weights instruct model, served through a cheap hosted inference provider, pinned by model name and revision, as the primary system under test. Local Ollama on the Mac is the development environment, not the experiment runner.**

Reasoning:

- Apple Silicon is memory-bandwidth bound. An 8B model at Q4 gives roughly 20–40 tok/s, plus several seconds of prefill on a 3k-token bundle. Call it 25–30 s per LLM call. The full matrix locally would take roughly **three days of continuous inference** on the machine also needed for writing — before the first bug forces a re-run.
- Hosted open-weights inference does the same work in about **two hours** with modest concurrency, inside the €100 budget.
- **Write the LLM client against an OpenAI-compatible interface.** Ollama exposes one, as does essentially every hosted provider. Local and hosted become a base-URL change in config, not a code change.

```
LLM_BASE_URL=http://localhost:11434/v1     # dev
LLM_BASE_URL=https://<provider>/v1          # experiments
LLM_MODEL=<pinned model name + revision>
```

**Reproducibility:** open weights pinned by revision mean anyone can re-serve the exact model and re-run the experiments, independent of whether the provider still exists. A frontier API snapshot gives neither. Say this explicitly in the methods chapter — a reproducible artifact is a real contribution and most agent papers cannot make the claim.

**Record per run:** model name and revision, provider, sampling parameters, seed where supported, prompt template version, graph version. Serialize into every result row.

**Constraint:** develop against the same model family used for experiments. Two acceptable patterns — same model both places (cheapest, zero drift), or same family different size (develop on 8B, run on the larger sibling, with a sanity comparison first). **Never develop on one vendor's model and run on another's.**

**Off the table:** vLLM does not run meaningfully on Apple Silicon. Self-hosting at scale would need Linux and CUDA. Not needed here.

**Cost correction:** an earlier estimate of €100–350 used mid-to-frontier hosted pricing — the wrong reference class. Hosted inference for open-weights models costs roughly an **order of magnitude less**. The full matrix fits inside €100 with room for several complete re-runs. Verify current rates when writing ADR-001.

**Memory budget on 16 GB:**

| RAM    | Runs comfortably at Q4 |
| ------ | ---------------------- |
| 16 GB  | 7–8B; 14B is tight     |
| 32 GB  | up to 27–32B           |
| 64 GB+ | 70B, but slowly        |

Do not run Ollama and the full Docker testbed simultaneously on 16 GB. Generate the corpus, shut the testbed down, then develop the agent against frozen bundles.

### 4.3 The Ollama context trap

**Ollama's default context window is small (2048 tokens in most builds) and it truncates silently.** Bundles will be 2–3k tokens. The model receives a clipped prompt, produces degraded output, and gives no error. Days get lost debugging prompt quality that was never the problem.

Set it explicitly:

```
PARAMETER num_ctx 8192
```

Then **verify**: send a prompt with a known marker near the start and ask the model to repeat it. If it can't, the context isn't what you think.

An 8B model at Q4_K_M is roughly 4.5–5 GB of weights plus KV cache growing with `num_ctx`. At 8192 you're comfortable.

### 4.4 Token optimization

**Token optimization is not research-neutral.** The biggest lever is how aggressively the bundle is reduced before reaching the model — and that same reduction is what H1 measures. Compress too hard and fusion shows no benefit, not because correlating three sources doesn't help, but because the signal that made correlation possible was deleted.

Three rules:

1. Identical reduction for every condition, including both baselines.
2. Frozen in METHODS.md with a stated reduction ratio before the first experiment.
3. If it must change, rerun everything and say so in the changelog.

**The five levers, by impact:**

**1. Bundle reduction (largest by far).** Aggregates plus a fixed number of exemplars, never raw records:

| Source   | Aggregates                                                                                          | Exemplars                                 |
| -------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Flows    | count, unique dst IPs, unique dst ports, bytes in/out, protocol mix, SYN-only ratio, duration stats | top-5 by detector score                   |
| MQTT     | message count, unique topics, payload size stats, QoS mix, connect/disconnect count, auth failures  | top-3 anomalous messages                  |
| Honeypot | session count, unique source IPs, auth attempts, success/fail                                       | up to 3 command sequences, hard-truncated |

Plus each detector's score and label. Lands around 800–1,200 tokens instead of 10k+ for raw records.

**2. Node-scoped context.** Don't send everything to every call. The classification node doesn't need the action catalog. The recommendation node doesn't need raw exemplars, only the classification output and evidence IDs. Structural and free.

**3. Prompt caching.** Order every prompt static-prefix-first: system role, schema, action catalog, then variable bundle content last. Most hosted providers cache prefixes automatically; with 3 calls per bundle sharing a prefix that's a 3× saving within one analysis.

**4. Tight output schemas.** Constrained decoding against a Pydantic model, enums instead of free text, evidence as references to alert IDs rather than quoted text. 150–250 output tokens, not 500. Output tokens are also the slow part locally.

**5. No conversation accumulation.** Each graph node is a fresh call with explicitly constructed context. Never append a growing history.

**Budget to engineer against:**

|                            | Target               | Hard ceiling |
| -------------------------- | -------------------- | ------------ |
| Input tokens per call      | ≤ 2,000              | 2,500        |
| Output tokens per call     | ≤ 200                | 250          |
| Calls per bundle (agentic) | 3                    | 3            |
| Total per bundle           | ~6,600 in / ~600 out | —            |

Make the ceiling an **assertion in code**. If a bundle exceeds it, the reduction step failed and you want to know at build time, not after 4,000 calls.

**What NOT to optimize** — three things are worth their tokens, and cutting them damages the thesis:

- The reasoning instructions in the agentic prompts. Trimming these sabotages H2 by weakening the treatment condition.
- The evidence field in the output schema. Auditability is the differentiator.
- The explicit action catalog in the recommendation prompt. H3 depends on the model being told what is permitted.

Optimize the data going in. Leave the constraints and reasoning scaffolding alone.

**Instrument from call one.** Log per call: node name, model, input tokens, output tokens, latency, condition, bundle ID, repetition index. Write into the same result rows as metrics. **Cost per incident analyzed is a publishable result** — none of [16], [18] or [19] report it.

### 4.4.1 Experiment matrix size

- ~250 bundles
- 5 agentic conditions × 3 calls = 15 calls per bundle per repetition
- 1 prompt-only condition × 1 call = 1
- 250 × 16 × 3 repetitions ≈ **12,000 calls**
- At ~3k input / 250 output: ~36M input, ~3M output tokens

On hosted open-weights inference this fits inside €100 with room for three full re-runs. Budget: one exploratory partial run, three full matrix runs, and headroom. **Put a hard spending cap on the account** — a retry loop without backoff is the classic way to discover the rate limiter doesn't work.

---

## 5. Scope cuts

| Decision                                                            | Reasoning                                                                                                                                                                                  |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Six attack families**, not as many as possible                    | Two visible in all three sources, two in exactly two, two in one. Gives H1 its stratification and caps testbed work                                                                        |
| **Off-the-shelf detectors**, and the ML detector _is_ Baseline A    | One artifact, two purposes. Tune it properly: a weak baseline invalidates H4 faster than any flaw in the agent                                                                             |
| **Small curated knowledge base**, not a general RAG corpus          | 50–200 documents. A big corpus costs weeks and adds a confound                                                                                                                             |
| **React console: last three weeks, four screens, capped**           | Incident list, incident detail with evidence and trace, recommendation with accept/reject, audit log. Produces zero results for any hypothesis. Should not exceed ~10% of engineering time |
| **One base model**, no model comparison                             | H2 requires the same base model for agent and prompt-only. That is all the proposal promises                                                                                               |
| **Prompt-injection experiment: stretch only**                       | Keep the defensive design. Run the experiment only if ahead at month four                                                                                                                  |
| **Attack generation: replay published datasets + standard tooling** | No custom attack code. Better for reproducibility, better for the ethics section, keeps novelty in the agent and evaluation                                                                |

---

## 6. Architecture

### 6.1 The architectural driver

The experimental conditions **are** the architecture requirement. H1 swaps the telemetry source set, H2 swaps the reasoning strategy, H3 swaps the safety layer. None can be hardcoded anywhere. They are runtime-injected from a single config object:

```
ExperimentConfig
  sources:  {mqtt, flows, honeypot}   any subset
  strategy: agentic | prompt_only | ml_classifier
  safety:   enforcing | logging_only
```

Every result row carries the config and its hash. This is what makes comparisons paired and runs reproducible.

**Consequence:** a modular monolith with hard internal seams, rather than microservices or a single tangled application. No operational need for distributed services; strong research need for clean substitution points.

> Most students discover this requirement in month five, after hardcoding the three sources into the ingest layer. Build it in now; it costs nothing at the start.

### 6.2 Stack decisions

| Layer              | Choice                                                                                          | Reasoning                                                                                                                                                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend            | **FastAPI**                                                                                     | Async-native for streaming reasoning traces and concurrent inference calls. Pydantic is the native type system, so **the safety schema and the API schema are the same object**. Trade-off: no admin, no ORM, no auth scaffolding — none needed |
| Frontend           | **React**                                                                                       | Required stack. Kept deliberately thin                                                                                                                                                                                                          |
| Frontend ↔ backend | **REST for commands, Server-Sent Events for the reasoning trace**                               | Traffic is one-directional, SSE reconnects automatically, a fraction of WebSocket complexity                                                                                                                                                    |
| Type safety        | **`openapi-typescript`** generates TS types from the OpenAPI schema                             | A schema change breaks the build instead of failing silently at runtime                                                                                                                                                                         |
| Agent framework    | **None. Write the graph directly.** No LangChain, LlamaIndex or LangGraph                       | Three nodes with fixed topology ≈ 200 lines. Framework abstractions make it awkward to capture exactly what bytes went to the model, and exact prompt capture is the reproducibility claim                                                      |
| Retrieval          | **`sentence-transformers` embeddings in a numpy array, cosine similarity.** No vector database  | For 50–200 documents this is faster, simpler and fully deterministic. Chroma/Qdrant would introduce a component needing its own characterisation. BM25 also defensible                                                                          |
| Detectors          | **LightGBM or XGBoost** for flows, statistical thresholds for MQTT, parser + rules for honeypot | Conventional by design. The flow classifier is also Baseline A                                                                                                                                                                                  |
| Testbed            | **Docker Compose, fully emulated**                                                              | Reproducibility, one-command reset, portability — all critical when the corpus must be regenerated in month 5                                                                                                                                   |

### 6.3 The agent graph

**A bounded reasoning graph, not free-form ReAct.** The proposal cites ReAct [10], and free-form ReAct is more faithful to that citation. But free-form loops maximize variance, unbounded tool calls, and non-reproducibility — the three biggest research risks.

A fixed topology still provides step-by-step reasoning, tool use and knowledge retrieval, which is exactly what H2 tests, while keeping every run reproducible and every cost predictable. **State this trade-off explicitly in the methods chapter.**

| Node                              | LLM call?                            | Input                                             | Output                                                  |
| --------------------------------- | ------------------------------------ | ------------------------------------------------- | ------------------------------------------------------- |
| Bundle ingestion and reduction    | No — deterministic                   |                                                   |                                                         |
| Knowledge retrieval               | No — deterministic, called as a tool |                                                   |                                                         |
| **1. Evidence analysis**          | **Yes** (with tool access)           | The reduced bundle, plus retrieved device context | Findings per source and cross-source observations       |
| **2. Classification**             | **Yes** (structured output)          | Node 1 findings                                   | Incident type, severity, affected device, confidence    |
| **3. Recommendation**             | **Yes** (constrained to action enum) | Node 2 classification + permitted action catalog  | One action from a closed enum, with evidence references |
| Validation and rejection handling | No — deterministic                   |                                                   |                                                         |
| Audit log write                   | No — deterministic                   |                                                   |                                                         |

**Why three and not six:** retrieval, parsing, normalization, schema validation and audit logging are deterministic code. Only reasoning steps need the LLM. Three calls still satisfies what H2 tests. The prompt-only baseline remains one call with no tools, no retrieval, no safety layer.

### 6.4 The safety layer

Four mechanisms working together:

1. **A limited action space.** Recommendations constrained to a closed enumeration defined in advance, derived from published incident-handling sources with a citation per entry.
2. **A structured output schema.** A Pydantic model containing incident type, severity, affected device, evidence references and recommended action. Constrained decoding enforces it at generation time.
3. **Validation rules.** A deterministic validator rejects output that is malformed, names an action outside the enum, or references evidence not present in the bundle.
4. **An audit log.** Every attempt written to an append-only log — passed or not — with the full prompt, raw completion and parse outcome.

### 6.5 The output schema

| Field                | Type                                          |
| -------------------- | --------------------------------------------- |
| `incident_type`      | Enum — the six attack families plus `benign`  |
| `severity`           | Enum — low / medium / high / critical         |
| `affected_device`    | String, device ID                             |
| `evidence`           | List of alert IDs referenced from the input   |
| `recommended_action` | Enum — a closed list, 6–8 candidates to start |
| `confidence`         | Float 0–1                                     |

### 6.6 The two baselines

|                         | Baseline A                                                                                                                              | Baseline B                                                                      |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **What it is**          | A conventional ML classifier trained on the same data                                                                                   | The **same** language model, no agent: one request, send the alerts, it answers |
| **What it has**         | No generative AI. Statistical classification only                                                                                       | The language model                                                              |
| **What it lacks**       | No reasoning, no explanation, no recommendation — **a severity→action lookup table is added** so the H4 safety comparison is well-posed | No step-by-step reasoning, no tools, no knowledge retrieval, no safety layer    |
| **Question it answers** | _Do we actually need an LLM at all?_                                                                                                    | _Do we need the agentic architecture, or is the model just good?_               |

**Critical:** a weak baseline invalidates the whole result. If the classifier is tuned badly, the agent wins easily and that proves nothing — and an examiner will attack this first. Tune the ML classifier properly (feature engineering, hyperparameter search, class imbalance handling) and give the prompt-only LLM a well-written prompt with the same output schema. If the agent still wins, the claim is solid.

### 6.7 Storage

| Data                       | Store                                                | Reasoning                               |
| -------------------------- | ---------------------------------------------------- | --------------------------------------- |
| Raw telemetry              | Files on disk, corpus manifest with SHA-256 per file | Immutable, verifiable, citable          |
| Normalized alerts, bundles | Parquet                                              | Columnar, compact, fast to filter       |
| Experiment results         | Parquet, one row per (bundle, condition, repetition) | Carries full provenance per measurement |
| Console operational state  | SQLite                                               | Single user, no concurrency requirement |
| Audit log                  | Append-only JSONL                                    | One line per decision, never rewritten  |

**No Postgres, no message queue, no orchestration beyond Docker Compose.** None serves a research requirement.

### 6.8 Authentication

**None.** The console binds to localhost. Building auth consumes days with zero research value. Record as an explicit out-of-scope decision in one line in the thesis, not an oversight.

### 6.9 Testing strategy

The split matters more than the coverage number.

- **Test hard:** parsers, bundle assembly, reduction, validators. A bug in assembly silently invalidates every experiment run afterwards and you will not notice.
- **Golden-file tests on the reduction step.** Fixed input bundle, exact expected reduced output, committed. This is what stops an accidental change to a frozen METHODS.md parameter six weeks in.
- **Property tests on the validator.** No output outside the action enum ever passes, for any input.
- **Do not unit-test LLM outputs.** Test the code around them. Model quality is what the experiments measure; asserting it in pytest is a category error. One end-to-end integration test against local Ollama, marked slow, excluded from CI.

### 6.10 Observability

Structured JSON logging from the first commit (`structlog`). Every LLM call logs: node, model, revision, tokens in/out, latency, full prompt, raw completion, parse outcome, condition, bundle ID, repetition.

**That single mechanism is simultaneously the audit log, the cost instrumentation, and the debugging tool.** No OpenTelemetry, no Prometheus — there is no production to monitor.

### 6.11 Security and privacy

- Testbed runs on an **isolated Docker network** with no route to the host LAN or internet. **Verify before running any attack tooling, not after.**
- Honeypot text is attacker-controlled and enters prompts. Delimit strictly, hard-truncate, never place adjacent to schema instructions, treat validation as a hard gate rather than a filter.
- API key in `.env`, gitignored, never logged.
- No personal data, no human subjects, as the proposal states.

---

## 7. Jira structure — 12 epics

```
EPIC-0  Project Foundation & Engineering Baseline
   ↓
EPIC-1  IoT Testbed & Scenario Generation
   ↓
EPIC-2  Ground Truth & Labelled Corpus  ←── CRITICAL PATH GATE
   ↓
EPIC-3  Telemetry Normalization & Incident Assembly
   ↓
EPIC-4  Detection Layer (also produces Baseline A)
   ↓
EPIC-5  Knowledge Base & Retrieval ──┐
                                      ├─→ EPIC-6  LLM Agent Core
                                      │        ↓
                                      │   EPIC-7  Safety & Constraint Layer
                                      │        ↓
EPIC-8  Baselines (A: ML+rules, B: prompt-only) ─┤
                                                  ↓
                                   EPIC-9  Evaluation Harness & Experiments H1–H4
                                                  ↓
EPIC-10 SOC Console (FastAPI + React)   [parallel, late]
EPIC-11 Thesis Writing & Research Artifacts  [continuous, all phases]
```

| Epic    | Name                                        | Depends on     | Note                              |
| ------- | ------------------------------------------- | -------------- | --------------------------------- |
| EPIC-0  | Project Foundation & Engineering Baseline   | —              | Sprint 0, §8                      |
| EPIC-1  | IoT Testbed & Scenario Generation           | EPIC-0         | Docker Compose, emulated          |
| EPIC-2  | Ground Truth & Labelled Corpus              | EPIC-1         | **CRITICAL PATH GATE**            |
| EPIC-3  | Telemetry Normalization & Incident Assembly | EPIC-2         | Blocked on the incident unit spec |
| EPIC-4  | Detection Layer                             | EPIC-3         | Also produces Baseline A          |
| EPIC-5  | Knowledge Base & Retrieval                  | EPIC-3         | Small curated corpus              |
| EPIC-6  | LLM Agent Core                              | EPIC-4, EPIC-5 | Three-node graph                  |
| EPIC-7  | Safety & Constraint Layer                   | EPIC-6         | The differentiator                |
| EPIC-8  | Baselines (A: ML+rules, B: prompt-only)     | EPIC-4         | —                                 |
| EPIC-9  | Evaluation Harness & Experiments H1–H4      | EPIC-7, EPIC-8 | —                                 |
| EPIC-10 | SOC Console (FastAPI + React)               | EPIC-9         | Parallel, late, capped            |
| EPIC-11 | Thesis Writing & Research Artifacts         | —              | Continuous                        |

### 7.1 Why EPIC-2 is the gate

Nothing downstream can be **measured** until the scenario corpus is frozen, and every schema change after the freeze forces a full regeneration. **This is where thesis timelines die.** Treat the corpus freeze as a formal milestone with a version number and a dataset card.

### 7.2 The four phases (simplified view for the supervisor)

| Phase                    | Epics     | Goal                                                                    |
| ------------------------ | --------- | ----------------------------------------------------------------------- |
| **A. Build the data**    | 0, 1, 2   | Build the test network. Run the attacks. Create the labelled data       |
| **B. Prepare**           | 3, 4, 5   | Clean the data, build the detectors, build the knowledge base           |
| **C. Build the agent**   | 6, 7, 8   | Build the agent, add the safety rules, build the two comparison methods |
| **D. Measure and write** | 9, 10, 11 | Run the experiments, build the interface, write the thesis              |

Phase A ends at the gate. After it, changing the format means starting again.

---

## 8. Sprint 0 backlog

| #   | Ticket                                               | Type     | Pts | Note                                                                    |
| --- | ---------------------------------------------------- | -------- | --- | ----------------------------------------------------------------------- |
| 1   | **SPIKE: vertical slice on one hand-written bundle** | Spike    | 5   | Unblocked. Start first. Full spec in §9                                 |
| 2   | Monorepo scaffold, CI, ADR log                       | Task     | 3   | `uv` or Poetry, ruff, mypy, pytest, pre-commit                          |
| 3   | **METHODS.md v1.0, the self-contract**               | Research | 5   | Incident unit is the first section. Blocks EPIC-3 and EPIC-9            |
| 4   | **Action catalog v0.1, citation per entry**          | Research | 5   | Published-source derivation replaces the second rater                   |
| 5   | **Bundle reduction policy v1.0**                     | Research | 5   | Aggregate fields and exemplar criteria per source. Freeze in METHODS.md |
| 6   | ADR-001: LLM serving, cost and time budget           | Task     | 3   | Decided in principle; the spike confirms the model                      |
| 7   | Docker Compose testbed skeleton, benign traffic only | Task     | 5   | Mosquitto broker, 3–4 MQTT emulators, one honeypot, capture sidecar     |
| 8   | Alert schema v0.1                                    | Task     | 3   | **After** the spike, informed by what it teaches                        |

Tickets 3, 4 and 5 are research-methodology work that people habitually postpone and then regret. **The action catalog especially:** if you define what counts as unsafe _after_ seeing your agent's outputs, the H3 result is worthless and a sharp examiner will say so.

---

## 9. NEXT ACTION — Ticket 1, the walking skeleton spike

**Start here.** Not the repo scaffold — this is the ticket that de-risks the thesis.

**Type:** Research Spike · **Priority:** Highest · **Points:** 5 · **Timebox:** 5 working days, hard stop · **Dependencies:** none

### Why this first

It answers the question that makes or breaks the thesis, in week one instead of month five. If the base model cannot produce useful verdicts from your alert format, you need to know while changing direction is still cheap. It also tells you what your alert schema actually needs to contain — information you cannot get by designing the schema in the abstract.

### What to build

One file, maybe 150 lines. Hand-write, in a JSON file, what you _think_ the normalized alerts from each source would look like. One prompt. One LLM call constrained to a Pydantic schema. One validator. Print the result.

No testbed. No detectors. No retrieval. No agent framework. **Keep the throwaway code throwaway** — do not let it become the foundation.

### Scenario

**SSH brute force against the honeypot**, which also leaves flow traces. Two sources present, one absent. That asymmetry is deliberate: you want to see how the model handles a missing source, because H1 depends on it.

### Output schema

See §6.5.

**The input format is what the spike is for.** Do not let anyone hand you an alert schema — you would be designing it blind. Write what you think it should be, feed it in, and let the model's failures tell you what is missing. _That information is the deliverable._

### Acceptance criteria

- [ ] A single script takes a hand-written alert bundle and produces a schema-valid verdict object
- [ ] `num_ctx` set explicitly and verified with a marker test before any runs
- [ ] **20 runs total: 10 against local Ollama, 10 against one hosted mid-size model**
- [ ] Per run recorded: schema-valid or not, the verdict, input tokens, output tokens, latency
- [ ] Findings note, half a page
- [ ] Log the full prompt and raw completion, not just the parsed object

### What to report back

1. Validity rate per model
2. Agreement rate across the 10 runs per model
3. Mean tokens in and out per call
4. Half a page: what the model got wrong, and what it asked for or hallucinated that the alert format did not provide

**Why two models:** the comparison tells you immediately whether the larger model is needed, which determines budget, serving choice, and whether H2/H4 test "does agentic structure help" or "does this small model fail at everything." The single most useful piece of information available this week, for about a cent.

Those numbers decide the model, confirm or break the 2,000-token budget, give you the alert schema, and settle ADR-001.

---

## 10. Open questions

| Question                                     | Why it matters                                                                                                                                                                     | Status                         |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Is a 60-second window the right unit?        | A slow brute-force episode spans several bundles. The choice propagates into every metric                                                                                          | Decided 2026-10-04: kept at 60 s, limitation stated. METHODS.md v1.0 §1 (E0-03) |
| How many scenarios for statistical validity? | All four hypotheses claim significance. Target must be fixed before the corpus is generated and frozen. McNemar for paired binary outcomes, Wilcoxon signed-rank for paired scores | Undecided                      |
| How should contextual safety be scored?      | The validator makes the naive metric circular. §3.1 proposes a split, needs review                                                                                                 | Decided 2026-10-04: METHODS.md "Safety scoring" (E0-12) |
| What is the validator rejection policy?      | Retry with feedback, escalate to a human, or hard fail. Each yields a different measured unsafe rate                                                                               | Decided 2026-10-04: hard fail, no retries. METHODS.md "Rejection policy" (E0-11) |
| Are two baselines sufficient?                | A and B isolate the model and the architecture respectively. A third may be expected                                                                                               | Decided 2026-10-04: two, no third. METHODS.md v1.0 §9 (E0-03) |
| Which six attack families?                   | Must be chosen so some appear in several sources and some in only one, or H1 confirms itself trivially                                                                             | Criteria fixed, selection open |
| Project name                                 | See §11                                                                                                                                                                            | Open                           |
| References [4] and [17]                      | Flagged incomplete in the proposal itself                                                                                                                                          | To resolve before submission   |

---

## 11. Naming — complete record

### 11.1 Constraints established

- Must not imply execution (the agent recommends, never executes). **This rules out the entire default security vocabulary:** Guardian, Shield, Sentinel, Warden, Defender, Enforcer, Interceptor, Response, Containment.
- No Latin or Greek (stated preference).
- Should read as an **LLM system, not a startup**.
- Should feel **serious and institutional**.
- Not generic combinations of "Cyber," "AI," "Guard".
- Easy to pronounce and spell.
- Balanced: academic fit and product potential both matter.

### 11.2 Verified conflicts — do not use

| Name                       | Conflict                                                                                                                                                       |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auspex**                 | Auspex Labs Inc., cybersecurity company; flagship product Auspex Observatory, an automated threat hunting platform. Separate Auspex LLC acquired by Edgesource |
| **Interlock**              | **Active ransomware group** since Sept 2024, joint FBI/CISA/HHS/MS-ISAC advisory                                                                               |
| **Quorum**                 | Quorum Cyber, Edinburgh-based MDR and incident response provider — exact domain                                                                                |
| **Sightline**              | NETSCOUT Arbor Sightline, NetFlow/IPFIX flow analytics — literally one of the three telemetry sources                                                          |
| **Tracepoint**             | DFIR company acquired by Booz Allen Hamilton                                                                                                                   |
| **Vestige / Vestigia**     | Vestige Ltd, digital forensics; Vestigit, Polish cybersecurity                                                                                                 |
| **Consilium**              | Consilium Software and related registered marks, enterprise software                                                                                           |
| **Colligo**                | Active Microsoft 365 / SharePoint software company                                                                                                             |
| **Quaestor**               | Phonetic collision with Quest Software, a major IT/cybersecurity vendor; also CyberQuest SIEM                                                                  |
| **Anything with "Detect"** | Vectra Detect (NDR, covers IoT), plus "Detection and Response" is the generic category name — EDR/NDR/XDR/MDR                                                  |
| **Cortex**                 | Palo Alto XSOAR platform                                                                                                                                       |
| **Keystone**               | OpenStack identity service                                                                                                                                     |
| **Arctic**                 | Arctic Wolf                                                                                                                                                    |
| **AlphaSOC**               | Already exists                                                                                                                                                 |
| **FuseSOC**                | Existing open-source FPGA package manager                                                                                                                      |
| **Cilium**                 | Major eBPF networking/security project                                                                                                                         |
| **Invariant**              | Invariant Labs, AI agent security, acquired by Snyk                                                                                                            |
| **Talos**                  | Cisco Talos                                                                                                                                                    |
| **Helix**                  | FireEye Helix                                                                                                                                                  |
| **Waypoint**               | HashiCorp                                                                                                                                                      |
| **Nous**                   | Nous Research, well-known AI lab                                                                                                                               |
| **Aporia**                 | ML observability company                                                                                                                                       |
| **Crossfeed**              | CISA tool                                                                                                                                                      |
| **Kestrel**                | ASP.NET Kestrel server; OASIS Kestrel threat hunting language                                                                                                  |
| **Prism**                  | NSA surveillance program — toxic association                                                                                                                   |
| **Beacon**                 | "C2 beaconing" is malware behaviour — bad connotation                                                                                                          |

**Checked and no direct conflict found** (preliminary scan only, not a clearance search): Corrobora, Confero, Attesta, Weft, Nomos, Parallax. **Lockstep** came back essentially clear — only a small open-source personal security checklist with 19 GitHub stars.

### 11.3 All names proposed, by round

**Round 1 — Latin/Greek scholarly (rejected: no Latin/Greek wanted)**

Corrobora, Confero, Indicium, Collatio, Elenchus, Triangulum, Sensorium, Cognita, Inferra, Noema, Cairn, Lodestar, Tessera, Vigil, Syllogos, Explanans, Deliberant, Weft, Apiary, Nexilis, Nomos, Limen, Attesta, Assay, Adjutant, Fiducia

_Top 5 that round:_ Corrobora, Confero, Attesta, Nomos, Weft

**Round 2 — technical/engineering register (rejected)**

Parallax, Lockstep, Crossfix, Manifold, Aperture, Coherence, Throughline, Envelope, Deadband, Passband, Governor, Detent, Backstop, Failsafe, Readback, Interposer, Span, Bearing, Provenance, Attest, Assertion, Lineage

_Top 5 that round:_ Parallax, Lockstep, Readback, Deadband, Crossfix

**Round 3 — short concrete English (rejected)**

Splice, Braid, Truss, Loom, Gauge, Caliper, Plumb, Scout, Sift, Winnow, Keel, Vantage

**Round 4 — compound descriptive, matching the bibliography's own convention**

SafeSOC, FusionSOC, TriSense-Agent, SOC-Advisor, IoT-SOCA, ConstrainedSOC, TriDetect
Single grave words: Discern, Warrant _(flaw: also means legal authorization to act)_, Deliberate, Circumspect

### 11.4 Where the naming landed

The brief that finally emerged: **it should read as an LLM system rather than a startup, and feel serious and institutional.** That points at the convention the bibliography itself uses — **IDS-Agent [16]** and **CyberRAG [19]** are exactly that.

The trade is explicit:

|                            | Academic-descriptive       | Product-abstract         |
| -------------------------- | -------------------------- | ------------------------ |
| Examples                   | IDS-Agent, CyberRAG, ReAct | Parallax, Zeek, Suricata |
| Reader knows what it is    | Immediately                | After you tell them      |
| Ownable                    | No                         | Yes                      |
| Survives beyond the thesis | No                         | Yes                      |

**Next step on naming:** write down five names you actually like, then conflict-check each, flag any implying execution, and draft the thesis title for whichever survive. Taste is yours; verification can be delegated.

**Meanwhile scaffold the repo as `thesis`.** Renaming is one line in `pyproject.toml`.

### 11.5 On putting "AI" or "detect" in the name

Advised against both, for four reasons:

1. **A date stamp, not a descriptor.** "AI" does what ".com" did in 1999 and "Cloud" did in 2012 — tells people when the thing was named.
2. **No information.** Every security product claims AI now, including [16], [18] and [19], which are all LLM-based.
3. **Legally inert.** Generic and descriptive terms get disclaimed in trademark registration.
4. **Reads as insecure in a thesis.** The degree is in AI Engineering, the department is AI, the title says LLM-based, the abstract says agentic. The jury already knows.

For "detect" specifically: **the proposed title already contains "Detection."** Putting it in the system name repeats it on the same cover page, and it names the crowded part of the field rather than the contribution.

**Where descriptors belong — the subtitle:**

> _Name: An LLM-Based Autonomous SOC Agent for Multi-Source IoT Telemetry Correlation, Incident Detection and Safety-Constrained Response Recommendation_

**Avoid a forced backronym.** Examiners notice reverse-engineered acronyms. A real word with a clean subtitle reads as confidence.

### 11.6 Verification caveat

Everything above was a **preliminary conflict scan, not a trademark clearance search**. Before any use beyond the thesis, check INPI (France), EUIPO, USPTO, plus `.com`/`.io`/`.ai` domains and the GitHub, PyPI and npm namespaces. For thesis purposes none of this blocks anything — a project name in a dissertation is nominative use.

---

## 12. Supervisor communication

### 12.1 Situation

- The supervisor stated no expectations and gives no methodological guidance. The student works alone.
- He is **not fluent in English** — all material for him must use simple words, short sentences, and many diagrams.
- He may not have read the proposal. Always open with a short overview.
- A checkpoint meeting was scheduled for 19:00 the following day.

### 12.2 The 60-second opener (if he hasn't read the proposal)

> "Today, security tools detect anomalies and send alerts. But they stop there. They don't say what is happening, and they don't say what to do. A human analyst has to interpret everything, and analysts are already overloaded.
>
> My project is an LLM-based agent that reads those alerts, combines them, identifies the attack type and its severity, and suggests an action. It only suggests, it never executes. That's deliberate, because an LLM sometimes makes mistakes, and a wrong automatic action can cause as much damage as the attack.
>
> The context is IoT, because that's where classical tools work least well.
>
> And most importantly: I don't only build a system, I measure it. I compare it against two simpler methods, on the same data, to prove with numbers that the agentic approach actually helps."

**French version:**

> « Aujourd'hui, dans un centre de sécurité, les outils détectent des anomalies et envoient des alertes. Mais ils s'arrêtent là. Ils ne disent pas ce qui se passe, et ils ne disent pas quoi faire. C'est l'analyste humain qui doit tout interpréter, et il est déjà surchargé.
>
> Mon projet : un agent basé sur un LLM qui lit ces alertes, les croise, identifie le type d'attaque et sa gravité, et propose une action. Il propose seulement, il n'exécute jamais. C'est volontaire, parce qu'un LLM se trompe parfois, et une mauvaise action automatique peut faire autant de dégâts que l'attaque elle-même.
>
> Le contexte est l'IoT, les objets connectés, parce que c'est là que les outils classiques marchent le moins bien.
>
> Et surtout : je ne construis pas seulement un système, je le mesure. Je le compare à deux méthodes plus simples, sur les mêmes données, pour prouver avec des chiffres que l'approche agentique apporte vraiment quelque chose. »

**If he asks "why is this research and not just engineering?":**

> « Parce que la question n'est pas _est-ce que ça marche_, mais _est-ce que c'est significativement meilleur qu'une méthode simple_. Je teste quatre hypothèses avec des tests statistiques, sur des données dont je connais la vérité terrain, parce que c'est moi qui lance les attaques. »

### 12.3 The three sources, explained simply

| Source             | What it is                                                                                                                | What it catches                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **MQTT anomalies** | MQTT is the messaging protocol IoT devices use, through a central broker. This source watches that traffic                | Strange messages, floods, failed logins to the broker, unusual topics |
| **Network flows**  | A summary of each connection: who talked to whom, which port, how many bytes, how long. Not the content, just metadata    | Port scans, DoS floods, botnet traffic to a command server            |
| **Honeypot logs**  | A decoy machine that looks like a real vulnerable device. No real job, so anyone touching it is an attacker by definition | Brute-force login attempts, and the commands the attacker types       |

**French:** « Les trois sources sont : les anomalies MQTT, c'est-à-dire le protocole de messagerie des objets connectés ; les flux réseau, un résumé de chaque connexion ; et les logs du honeypot, une machine-leurre où toute activité est forcément une attaque. »

**One line to say:** "Each source sees only part of the attack. My hypothesis H1 is that combining the three gives a better classification than one alone. That's what I will measure."

### 12.4 The two baselines, explained simply

**English:** "Two comparison points. The first is a conventional machine learning classifier: it answers the question _is an LLM necessary?_ The second is the same language model but with no agentic architecture, just a simple request: it answers the question _does the architecture add something, or is it just that the model is good?_"

**French:** « Deux points de comparaison. Le premier, un classifieur machine learning classique : il répond à la question _est-ce qu'un LLM est nécessaire ?_ Le deuxième, le même modèle de langage mais sans architecture agentique, juste une requête simple : il répond à la question _est-ce que l'architecture apporte quelque chose, ou c'est juste le modèle qui est bon ?_ »

### 12.5 Three questions to ask him

If he answers only one, make it the third.

1. **"I group alerts into packets of 60 seconds. Does this seem reasonable to you?"**
   _(A slow attack will cover several packets. This choice affects everything downstream.)_
2. **"How many test scenarios do I need for the statistics to be valid?"**
   _(All hypotheses say "significantly better". A number is needed before generating the data.)_
3. **"How should I measure an unsafe recommendation in a fair way? My safety filter blocks forbidden actions automatically, so the score is perfect by construction. I think this is a problem."**
   _(The strongest question available — it shows a weakness found in your own method before he found it.)_

French versions:

1. « Je groupe les alertes en paquets de 60 secondes. Est-ce que ça vous paraît raisonnable ? »
2. « Combien de scénarios de test il me faut pour que les statistiques soient valides ? »
3. « Comment mesurer une recommandation dangereuse de façon honnête ? Mon filtre de sécurité bloque automatiquement les actions interdites, donc le score est parfait par construction. Je pense que c'est un problème. »

### 12.6 Meeting title for Teams

**Recommended:** `Thesis checkpoint — architecture review (R. EL HAYEK)`

Alternatives:

| Title                                                   | When it fits                                  |
| ------------------------------------------------------- | --------------------------------------------- |
| Thesis checkpoint — architecture review (R. EL HAYEK)   | Default. Clear and professional               |
| MSc thesis — architecture review and open questions     | Signals decisions to discuss, not just status |
| Point d'avancement mémoire — architecture (R. EL HAYEK) | If he prefers French for admin                |
| Thesis checkpoint #1 — architecture                     | For a numbered series                         |

**Set the duration to 45 minutes, not 30.** Eleven diagrams plus six questions will not fit in 30.

### 12.7 Email sending the two documents

**Subject:** Thesis documents before tomorrow's meeting

> Dear Professor,
>
> As agreed, please find attached the two documents ahead of tomorrow's meeting:
>
> 1. The thesis proposal (the version I sent you earlier).
> 2. A document on the system architecture, explaining how I plan to build it. It is written in simple language and includes 11 diagrams, with a short glossary at the end.
>
> Please let me know if you need anything else.
>
> Best regards,
> Roy EL HAYEK
> MSc 2 Artificial Intelligence

_(Agenda and questions deliberately omitted — setting the agenda is the supervisor's role, not the student's. The questions live in section 13 of the architecture document and can be raised in the meeting itself.)_

### 12.8 Working cadence

- **Thursday night:** internal draft version shared for review.
- **Thursday night → weekend:** window for modifications.
- **Monday:** final version sent to the supervisor.

---

## 13. Deliverables produced

| File                                           | Contents                                                                                                                                  | Status                                |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Project Reference** (.docx)                  | 8 sections: project summary, risk register, locked decisions, architecture, Jira epics, Sprint 0, Ticket 1 spec, open questions. 13 pages | Complete                              |
| **System_Architecture_LLM_SOC_Agent_IoT.docx** | 10 sections, 2 diagrams, English, technical register. 12 pages                                                                            | Superseded by the illustrated version |
| **System_Architecture_Illustrated.docx**       | 13 sections + glossary, **11 figures**, beginner-level English, humanized. 14 pages                                                       | **Current — send this one**           |
| **thesis_project_full_record.md**              | This file                                                                                                                                 | Current                               |

### 13.1 The 11 figures in the illustrated architecture document

| #   | Shows                             | Purpose                                            |
| --- | --------------------------------- | -------------------------------------------------- |
| 1   | Context: network → system → human | Makes "never acts by itself" visible in one glance |
| 2   | Today vs with the system          | The problem, before any technical words            |
| 3   | Which source sees which attack    | This _is_ H1, as a picture                         |
| 4   | The whole system, full page       | The main architecture diagram                      |
| 5   | The eight pipeline steps          | A simple chain when the big diagram is too much    |
| 6   | Timeline cut into bundles         | Explains the 60-second rule visually               |
| 7   | Inside the agent                  | Green = AI, blue = normal code                     |
| 8   | Three safety checks               | Shows accepted vs refused                          |
| 9   | Three methods compared            | Makes the baselines concrete                       |
| 10  | Mac vs online                     | Answers "where does it run"                        |
| 11  | Four phases + the freeze gate     | The plan, with the risky moment marked             |

### 13.2 Humanizer instructions used

The documents were run through a humanizer with these constraints — reuse them for future passes:

```
HARD CONSTRAINT — READING LEVEL
The reader is a native French speaker who is not fluent in English.
Keep sentences short, max ~18 words. Common words only. No idioms,
no phrasal verbs, no metaphors. No contractions. Do not merge short
sentences into longer ones. Do not add transition words for flow.
If a change makes the text sound better but harder to read, do not
make it.

DO NOT CHANGE:
Technical names: MQTT, IoT, SOC, LLM, FastAPI, Python, React, Docker,
Ollama, Pydantic, Parquet, SQLite, JSONL, LightGBM, XGBoost, Bot-IoT,
TON_IoT, CICIoT2023, MQTTset, ATT&CK, NIST SP 800-61
Project vocabulary: bundle, ground truth, baseline, Baseline A,
Baseline B, honeypot, network flow, audit log, open model, detector, epic
Labels: H1-H4, all figure references, all section numbers, [16] [18] [19]
All numbers and units
Tables, figure captions, Appendix A glossary, title page

MUST NOT CHANGE MEANING:
"It suggests only. It never acts by itself. A human always decides."
```

**Workflow note:** running a humanizer directly on a `.docx` risks damaging tables, images, heading styles and the TOC field. Better: export the body as Markdown, humanize that, then rebuild the `.docx`.

**The 8 edits applied in the last pass:**

| #   | Section | Change                                          |
| --- | ------- | ----------------------------------------------- |
| 1   | 2       | "Each tool sends" → "Each one sends"            |
| 2   | 2       | dropped "together"                              |
| 3   | 4       | "main road: they show" → "main flow. They show" |
| 4   | 4.1     | "feed them" → "prepare data for them"           |
| 5   | 6       | "measure is measured" → "measure is based on"   |
| 6   | 6.1     | "The price I pay." → "There is a cost."         |
| 7   | 6.2     | "take this into account" → "consider this"      |
| 8   | 12.1    | one long sentence split into two                |

---

## 14. Working agreement

How this collaboration has been operating:

- Act as a senior full-stack engineer, senior AI engineer, and technical lead / software architect.
- Distinguish **academic research requirements** from **production engineering requirements**.
- **Challenge technical decisions** when there is a better alternative, and explain why.
- Avoid unnecessary complexity and overengineering.
- **Clearly separate confirmed information from assumptions and recommendations.**
- Guide **incrementally** — next actionable step, review it, then move on. Not the whole implementation at once.
- Track decisions, completed tasks, and outstanding work throughout.
- Do not force AI components, experiments, or metrics that are irrelevant to the actual proposal.
- Do not introduce technologies because they are popular.

---

## 15. Continuation primer

Paste this as the first message in a new conversation, with the three files attached:

> I am implementing my MSc thesis: an LLM-based autonomous SOC agent for IoT cyberattack detection and response. I am working alone — my supervisor gives no methodological guidance.
>
> Attached: my thesis proposal, the full project record of our planning so far, and the architecture document I sent my supervisor.
>
> Read the full record. The decisions in sections 4, 5 and 6 are locked. The questions in section 10 are open. My next action is Ticket 1 in section 9 — the walking skeleton spike.
>
> Work as a senior engineer and technical lead. Challenge my decisions when there is a better option. Separate confirmed facts from assumptions. Guide me one step at a time, not all at once. Keep track of what is decided and what is outstanding.
>
> Start by confirming your understanding of where the project stands, then help me with Ticket 1.

---

## 16. Reference list (from the proposal)

| #    | Reference                                                                                                                                     |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [1]  | Srinivas et al., "AI-augmented SOC: A survey of LLMs and agents for security automation," _J. Cybersecur. Privacy_, 2025                      |
| [2]  | Loevenich et al., "Design and evaluation of an autonomous cyber defence agent using DRL and an augmented LLM," _Comput. Netw._, 2025          |
| [3]  | Radah et al., "ReAct-driven SOC agent with integrated detection engineering," _J. Inf. Syst. Eng. Manage._, 2025                              |
| [4]  | Alqahtani et al., "Secure autonomous cyber defense with LLM agents," _Comput. Electr. Eng._, 2026 — **incomplete, resolve before submission** |
| [5]  | Zarpelão et al., "A survey of intrusion detection in Internet of Things," _J. Netw. Comput. Appl._, 2017                                      |
| [6]  | Koroniotis et al., **Bot-IoT dataset**, _Future Gener. Comput. Syst._, 2019                                                                   |
| [7]  | Alsaedi et al., **TON_IoT telemetry dataset**, _IEEE Access_, 2020                                                                            |
| [8]  | Neto et al., **CICIoT2023**, _Sensors_, 2023                                                                                                  |
| [9]  | Vaccari et al., **MQTTset**, _Sensors_, 2020                                                                                                  |
| [10] | Yao et al., **ReAct**, ICLR 2023                                                                                                              |
| [11] | Schick et al., **Toolformer**, NeurIPS 2023                                                                                                   |
| [12] | Wang et al., "A survey on large language model based autonomous agents," 2024                                                                 |
| [13] | Ruan et al., "Identifying the risks of LM agents with an LM-emulated sandbox," ICLR 2024                                                      |
| [14] | Yuan et al., **R-Judge**, EMNLP Findings 2024                                                                                                 |
| [15] | Tabassi, **NIST AI RMF 1.0**, NIST AI 100-1, 2023                                                                                             |
| [16] | Li et al., **IDS-Agent**, NeurIPS 2024 Workshop on Open-World Agents                                                                          |
| [17] | Ferrag et al., BERT-based lightweight model for IoT/IIoT, _IEEE Access_, 2024 — **incomplete, resolve before submission**                     |
| [18] | Chou, Sudheer, Park, "An LLM-based agentic network traffic incident-report approach," _J. Sens. Actuator Netw._, 2026                         |
| [19] | Blefari et al., **CyberRAG**, _Future Gener. Comput. Syst._, 2026                                                                             |

---

_End of record._
