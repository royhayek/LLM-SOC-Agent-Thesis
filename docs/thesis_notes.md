# Thesis notes

Every decision, number or figure the thesis will cite is logged here when its ticket closes (Definition of Done). The EPIC-11 chapter tickets read this file.

| Date | Ticket | Chapter | What | Value | Source file |
|---|---|---|---|---|---|
| 2026-10-04 | SCRUM-31 [E0-04] | Methodology (safety layer, action catalog) | Action catalog v0.1: 8 recommendation-only actions from 14 candidates, each with at least one verbatim citation | no_action, monitor, escalate_to_analyst, block_source, rate_limit_source, isolate_device, reset_credentials, disable_service. French and EU sources cited first: ANSSI guides (2015–2026), CERT-FR, ENISA (2010 incident-management guide; 2025 NIS2 guidance), CERT SG IRM v2.0. Supporting: MITRE ATT&CK v19.2, NIST SP 800-61r3 (2025) and r2 (2012, withdrawn) | knowledge/action_catalog.yaml, docs/catalog_derivation.md |
| 2026-10-04 | SCRUM-31 [E0-04] | Methodology (action catalog derivation) | Source decision: French and EU official guidance first; ATT&CK and NIST SP 800-61 kept as supporting references; CISA read but not cited; not EU-only so each action keeps at least two independent sources | Every catalog action has 3–5 citations, the first from ANSSI, CERT-FR or ENISA | docs/catalog_derivation.md §3, record §3.4 |
| 2026-10-04 | SCRUM-6 [E0-01] | Methodology (model choice, token budget); Results (feasibility) | Walking-skeleton spike: 10 local + 10 hosted runs on one SSH password-guessing bundle, temperature 0 | Local Llama 3.1 8B Q4_K_M and hosted Llama 3.3 70B Turbo FP8 both 10/10 valid, 10/10 agreement, 10/10 correct; 2116 input tokens for 13 alerts (above the 2,000-token budget); hosted cost about USD 0.0024 | spikes/FINDINGS.md, spikes/results.csv |
