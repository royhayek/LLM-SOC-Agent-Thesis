# Action catalog v0.1: derivation

Ticket: SCRUM-31 [E0-04]. Version 0.1, 2026-10-04.

The catalog is a closed list of recommendation-only actions (record §6.4). Each action rests on a published source (record §3.4), which replaces a second rater. The agent recommends and never executes (record §1.1).

## 1. Sources and sections read

US and international sources were retrieved on 2026-10-03, European sources on 2026-10-04. French and EU official guidance (ANSSI / CERT-FR, ENISA) is cited first, then CERT Société Générale, MITRE ATT&CK and NIST SP 800-61 as supporting references. CISA was read but is not cited (source decision, §3; record §3.4). All 35 quotes in the catalog were matched against the text of the downloaded documents: 34 by an automated text match, and 1 (N3 RS.MI-01 C2, which crosses a page break) by hand. French quotes are kept verbatim; the author checked the English translations on 2026-10-04.

| ID | Source | Edition | Sections read |
|---|---|---|---|
| E1 | ENISA, *Good Practice Guide for Incident Management*. https://www.enisa.europa.eu/sites/default/files/publications/Incident_Management_guide.pdf | December 2010 | §5.4.2, §5.5.1.1 (escalation), §8.3 and §8.3.1 (triage, verification), §8.4.3–8.4.4 (actions proposed) |
| E2 | ENISA, *Baseline Security Recommendations for IoT in the context of Critical Information Infrastructures*. doi 10.2824/03228 | November 2017 | §4.3.11–4.3.15, Annex A (GP-TM-25, -45, -46, -47, -50, -56). Preventive baselines; read, not cited |
| E3 | ENISA, *Technical Implementation Guidance on Commission Implementing Regulation (EU) 2024/2690* (NIS2 security measures) | Version 1.0, June 2025 | §3.2.2, §3.4.1, §3.5.2, §11.6.2 |
| A1 | ANSSI, *Comprendre et anticiper les attaques DDoS* | March 2015 | §3.1, §3.2 (réaction face à une attaque), §4.1.1 |
| A2 | ANSSI, *Les Essentiels – Dénis de service distribués (DDoS)*, and its English version *Back to Basics – DDoS* | V2.0, April 2024 | §1–§3. Read, not cited |
| A3 | ANSSI, *Cyberattaques et remédiation – Piloter la remédiation* | Version 1.0, December 2023 | Endiguement (containment) objectives and phase, pp. 34–35; remediation strategy, p. 62 |
| A4 | ANSSI, *Cyberattaques et remédiation – Préparer la remédiation* | Version 1.0, January 2026 | "En réaction", p. 17. Read, not cited |
| A5 | ANSSI, *Attaques par rançongiciels, tous concernés*, ANSSI-GP-077 | Version 1.0, August 2020 | "Adopter les bons réflexes", pp. 24–25; "Restaurer les systèmes depuis des sources saines", p. 32 |
| A6 | ANSSI, *Crise d'origine cyber, les clés d'une gestion opérationnelle et stratégique*, ANSSI-PA-089 | Version 1.0, December 2021 | Fiche 8 (activer son dispositif de crise), Fiche 9 (endiguer l'attaque) |
| A7 | ANSSI, *L'investigation et la qualification d'incidents : les clés de décision* | Version 1.0, September 2026 | p. 2 |
| A8 | ANSSI, *Recommandations relatives à la sécurité des (systèmes d') objets connectés*, ANSSI-PA-087 | August 2021 | Searched for response actions; none cited |
| C1 | CERT-FR, *Les bons réflexes en cas d'intrusion sur un système d'information*. https://www.cert.ssi.gouv.fr/les-bons-reflexes-en-cas-dintrusion-sur-un-systeme-dinformation/ | Web page, undated; accessed 2026-10-04 | §2 (qualifier), §3 (réagir: décider, agir) |
| N3 | NIST SP 800-61r3, *Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile*. Nelson, Rekhi, Souppaya, Scarfone. https://doi.org/10.6028/NIST.SP.800-61r3 | Rev. 3, April 2025 (current) | §3.2, Table 3 (CSF 2.0 Community Profile part 2): DE.AE-08, RS.MA, RS.MA-02, RS.MA-03, RS.MA-04, RS.AN-06, RS.AN-07, RS.CO-02, RS.MI, RS.MI-01, RS.MI-02, RC, RC.RP-04 |
| N2 | NIST SP 800-61r2, *Computer Security Incident Handling Guide*. Cichonski, Millar, Grance, Scarfone. https://doi.org/10.6028/NIST.SP.800-61r2 | Rev. 2, August 2012. **Withdrawn 2025-04-03**, superseded by Rev. 3 | §2.3.4.4, §3.2.2, §3.2.4, §3.2.6, §3.2.7, §3.3.1, §3.3.2, §3.3.4, Table 3-5, Appendix G |
| AT | MITRE ATT&CK Enterprise. https://attack.mitre.org | v19.2 (website version from 2026-04-28) | Techniques T1110, T1110.001, T1046, T1595, T1595.001, T1498, T1498.001, T1498.002, T1499, T1499.002, T1499.003, T1583.005, T1584.005, T1071, T1071.005. Mitigations M1018, M1027, M1030, M1031, M1032, M1035, M1036, M1037, M1042, M1051, M1056 |
| CI | CISA, *Federal Government Cybersecurity Incident and Vulnerability Response Playbooks*. https://www.cisa.gov/resources-tools/resources/federal-government-cybersecurity-incident-and-vulnerability-response-playbooks | November 2021 (PDF re-issued August 2024) | Incident Response Playbook: Containment, Eradication, Recovery, Coordination (pp. 10–18); Appendix B checklist (pp. 27–33). **Read, not cited** (source decision, §3) |
| IR | CERT Société Générale, *Incident Response Methodologies* (IRM). https://github.com/certsocietegenerale/IRM | IRM v2.0. No printed date; repository commits 2022-12 and 2023-01 | IRM #1 Worm Infection, IRM #4 DDoS, IRM #5 Malicious Network Behaviour |
| SA | P. Kral, *The Incident Handlers Handbook*, SANS Institute. https://www.sans.org/white-papers/33901 | 2012 | Containment (p. 7), Eradication and Recovery (pp. 7–8), Identification (p. 5) |

## 2. Candidate actions

Each candidate was found in at least one source. Duplicates are grouped under one candidate. This table records what was read, so it still shows CISA (CI) quotes; the catalog does not cite CISA (source decision, §3).

| # | Candidate | Citations (source, locator: quote) | Decision | Reason |
|---|---|---|---|---|
| C1 | Monitor: continue observing the source and device | N3 RS.MA-03 R3: "balancing the need to quickly recover from an incident with the need to observe the attacker". CI App. B 7k, p. 31: "Monitor for signs of threat actor response to containment activities." N2 §3.2.2, p. 26: "At a minimum, the organization could monitor activity involving the target more closely." | IN as `monitor` | Lets the agent recommend watching without acting. The catalog cites A3, A7, N3. |
| C2 | No action: the activity is not an incident | N3 DE.AE-08: "consider known false positives to determine whether an incident should be declared." N2 §3.2.4, p. 28: "Even if an indicator is accurate, it does not necessarily mean that an incident has occurred." Neither NIST revision says "take no action" outright (ENISA E1 does; see the European citations below). | IN as `no_action` | Benign bundles need their own answer, distinct from watching a live threat. The US sources do not say "take no action" outright. ENISA E1 §8.3 does ("skip handling completely"), and is cited first. |
| C3 | Escalate to a human analyst | N3 RS.MA-04 N1: "Escalation generally refers to increasing resources or time frames, while elevation usually indicates involving a higher level of management in the response efforts." N2 §3.2.6, p. 33: "the caller should escalate the incident to a higher level". CI p. 10: "alerting agency IT leadership to the need for investigation and response." | IN as `escalate_to_analyst` | The human-in-the-loop action. The catalog cites E1, C1, N3, N2. |
| C4 | Block the source address at the network boundary | AT M1037 on T1498.001 and T1499: "blocking source addresses sourcing the attack". CI App. B 7g, p. 31: "Perform blocking (and logging) of unauthorized accesses, malware sources, and egress traffic to known attacker Internet Protocol (IP) addresses." IR #5 p. 7: "block them on all your network boundaries." N2 App. G step 6, p. 68: "firewall and router configurations may need to be modified to stop network traffic that is part of an incident". N3 gives no direct support. | IN as `block_source` | Cheap containment aimed at the attacker. The catalog cites A1, A5, AT. N3 gives no support. |
| C5 | Rate-limit or throttle the source's traffic | IR #4 p. 7: "Attempt to throttle or block DDoS traffic as close to the network's "cloud" as possible". AT M1037 on T1498: "intercept the incoming traffic upstream to filter out the attack traffic from the legitimate traffic." Overlaps with C4. | IN as `rate_limit_source`, absorbing C14 | A lighter option than blocking, for floods where legitimate traffic must continue. Kept apart from C4 so the two can be scored differently. |
| C6 | Isolate the affected device from the network | N3 RS.MI-01 C1: "transferring a compromised endpoint to an isolated remediation network". N2 §3.3.1, p. 35: "shut down a system, disconnect it from a network, disable certain functions". CI p. 14: "Isolating impacted systems and network segments from each other and/or from non-impacted systems and networks." IR #5 p. 6: "Isolate the source of the attack." | IN as `isolate_device` | Costly containment aimed at the device. The catalog cites A3, A5, A6, N3. |
| C7 | Reset credentials or disable breached accounts on the device | N3 RS.MI-02 N1: "disabling breached user accounts". N3 RC N2: "changing passwords". CI p. 15: "Resetting passwords on compromised accounts." AT M1018 on T1110: "Proactively reset accounts that are known to be part of breached credentials either immediately, or after detecting bruteforce attempts." | IN as `reset_credentials`, absorbing C8 | The credential response to password guessing. The catalog cites A3, A5, E3, AT, N3. |
| C8 | Enforce account lockout after failed logins | AT M1036 on T1110 and T1110.001: "Set account lockout policies after a certain number of failed login attempts to prevent passwords from being guessed." Not in N2 or N3. Overlaps with C7. | OUT, merged into C7 | Lockout is a variant of the credential response. Its citation (AT M1036) is kept on `reset_credentials`. |
| C9 | Disable or close an exposed service or port | AT M1042 on T1046: "Ensure that unnecessary ports and services are closed to prevent risk of discovery and potential exploitation." CI p. 14: "Closing specific ports and mail servers or other relevant servers and services." N2 §3.3.1, p. 35: "disable certain functions". IR #4 p. 7: "temporarily disable that feature." | IN as `disable_service` | Removes the exposed service. The catalog cites E1, A1, AT. |
| C10 | Patch or update the device's software | AT M1051 on T1110.001: "Upgrade management services to the latest supported and compatible version." N3 RC N2: "installing patches". CI p. 15: "Installing patches." SA p. 8: "installing patches and disabling unused services". | OUT | Patching is a later clean-up or hardening step, not a response to one 60-second bundle. The bundles carry no vulnerability data, so the agent could not justify it. |
| C11 | Preserve evidence: capture traffic and logs | N3 RS.AN-07 R1: "Collect and retain evidence from an incident". N2 §3.3.2, p. 36: "It is generally desirable to acquire evidence from a system of interest as soon as one suspects that an incident may have occurred." CI p. 14: "Capturing forensic images to preserve evidence". IR #5 p. 5: "Use network capture tools". | OUT | Fits almost every incident, so it cannot tell a fitting recommendation from an unfitting one. Recording evidence is the audit log's job (record §6.4). |
| C12 | Segment the network | AT M1030 on T1046: "Ensure proper network segmentation is followed to protect critical servers and devices." | OUT | An architecture change, not an incident response. |
| C13 | Strengthen authentication policy (MFA, password policy) | AT M1032 on T1110: "Use multi-factor authentication." AT M1027 on T1110: "Refer to NIST guidelines when creating password policies." | OUT | A policy change, not an incident response. |
| C14 | Request upstream (ISP or provider) filtering | N3 RS.MI-01 C2: "Consider authorizing third parties (e.g., the organization's internet service providers and cloud service providers) to automatically act to contain certain types of incidents (e.g., large-scale DDoS attacks)". N2 §2.3.4.4, p. 12: "assistance from its ISP in blocking a major network-based attack". | OUT, merged into C5 | Upstream filtering is the rate-limit response carried out by a provider. Its citation (N3 RS.MI-01 C2) is kept on `rate_limit_source`. |

### European citations per catalog action

The catalog cites these first. Full quotes and translations are in `knowledge/action_catalog.yaml`.

| Catalog action | European citations | Note |
|---|---|---|
| `no_action` | E1 §8.3, p. 46: "Eventually you may skip handling completely if your triage process tells you the issue is not important at all." E3 §3.4.1 | E1 gives the explicit support that the US sources lacked (C2) |
| `monitor` | A3 p. 35 ("mettre sous surveillance un moyen de l'attaquant identifié, plutôt que de le désactiver hâtivement"); A7 p. 2 | |
| `escalate_to_analyst` | E1 §5.5.1.1, p. 21; C1 §3 ("Notifier les décideurs métiers et direction") | |
| `block_source` | A1 §3.2, p. 28 ("le blocage des adresses IP sources identifiées comme étant à l'origine de l'attaque"); A5 p. 25 | |
| `rate_limit_source` | A1 §3.2, pp. 28–29 (limiting concurrent connections per source IP; asking operators to filter) | |
| `isolate_device` | A3 p. 34; A5 p. 24; A6 Fiche 9, p. 39 | A6 says containment that affects continuity is approved by the decision-makers, which matches "recommend, never execute". No ENISA passage on isolation during response was found |
| `reset_credentials` | A3 p. 62 ("désactiver les comptes compromis"); A5 p. 32 ("changer les mots de passe"); E3 §11.6.2(d) | E3 §11.6.2 is regulation text on access control, cited for the lockout part |
| `disable_service` | E1 §8.4.3, p. 52 ("turn off a service"); A1 §3.2, p. 29 | |

## 3. Selection

### Source decision (2026-10-04)

Decision by the author: the catalog rests on French and EU official guidance first (ANSSI, CERT-FR, ENISA), because the thesis is written and examined in France. Three non-EU sources stay as supporting references, and one is dropped:

- **CERT Société Générale IRM**: kept. It is a French CERT's published playbook.
- **MITRE ATT&CK**: kept. It is run by a non-profit and used worldwide. Other tickets depend on it: E1-02 gives each attack family an ATT&CK technique ID, and the knowledge subsystem stores ATT&CK mitigations (R-170).
- **NIST SP 800-61**: kept as a second citation behind the European ones. It is the most widely cited incident-response reference, so an examiner will expect it.
- **CISA playbooks**: dropped. They are US federal procedure, and every point they supported is already covered by ANSSI or ENISA.

Not going EU-only: `rate_limit_source` would then rest on a single 2015 ANSSI document. A second, independent source per action is what replaces the missing second rater (record §3.4).

### Action selection


The catalog keeps 8 actions, the top of the 6–8 range (record §6.5). It was chosen against four criteria:

1. **Response, not hardening.** Every action answers the incident in front of the agent. Patching (C10), segmentation (C12) and policy changes (C13) are left out.
2. **Each action can be told apart.** An action that fits almost every incident (C11) cannot be scored for contextual fit, so it is left out.
3. **Different costs stay separate.** Blocking an attacker's address (C4) is cheap; isolating a device (C6) can be costly for a critical IoT device. Rate-limiting (C5) sits between them. Keeping these separate lets later safety scoring (E0-12, E1-03) judge contextual appropriateness.
4. **Benign and uncertain cases have their own answers:** `no_action`, `monitor` and `escalate_to_analyst`. This follows the ticket's ASSUMPTION that the catalog includes an escalate-to-human action and a monitor/no-action action.

Close variants are merged rather than dropped: lockout (C8) into `reset_credentials`, and upstream filtering (C14) into `rate_limit_source`. Their citations move with them.

## 4. Provisional family-to-action table

PROVISIONAL. The families are the §3.2 candidates; E1-02 freezes the real list. This table shows which catalog actions a source ties to each family's technique. It is not an acceptable-action set or an unsafe-action set; those belong to E1-03. `no_action`, `monitor` and `escalate_to_analyst` apply to every family and are not repeated.

| Family (§3.2) | ATT&CK technique | Catalog actions tied by a source |
|---|---|---|
| MQTT message flood | T1498.001 Direct Network Flood, or T1499.002 Service Exhaustion Flood | `block_source`, `rate_limit_source` (AT M1037 on T1498.001 and T1499.002: "blocking source addresses sourcing the attack") |
| MQTT broker password guessing | T1110.001 Password Guessing. **Inference:** ATT&CK lists SSH but not MQTT among targeted services | `reset_credentials` (AT M1018 and M1036 on T1110) |
| Port scan | T1046 Network Service Discovery | `disable_service` (AT M1042 on T1046), `block_source` (AT M1031 on T1046: "Use network intrusion detection/prevention systems to detect and prevent remote service scans.") |
| SSH password guessing | T1110.001 Password Guessing ("SSH (22/TCP)" is listed among targeted services) | `reset_credentials` (AT M1018 and M1036 on T1110) |
| Botnet traffic | T1071 / T1071.005 C2 over an application or pub/sub protocol. T1583.005 and T1584.005 offer only M1056 Pre-compromise | `isolate_device` (A5 p. 24; IR #1 p. 6: "Isolate the infected area. Disconnect it from any network."), `block_source` (AT M1037 on T1071.005) |
| Denial of service | T1498 Network Denial of Service, T1499 Endpoint Denial of Service | `block_source`, `rate_limit_source` (AT M1037 on T1498 and T1499; N3 RS.MI-01 C2) |

## 5. Statement on spike outputs

Confirmed by Roy El Hayek, 2026-10-04.

From 2026-10-03 to 2026-10-04, while this derivation was made, no spike verdict run had taken place. `spikes/results.csv` and `spikes/logs/` did not exist, and `spikes/FINDINGS.md` was removed in commit cc5c65d before it held any results. Spike outputs were therefore not read during derivation.

Disclosure: `spikes/walking_skeleton.py` (branch SCRUM-6) contains a placeholder action enum marked SPIKE_ONLY, written before this derivation. Its names were invented for the spike from generic incident-response wording, and were not used as an input here. Several catalog actions resemble those names (for example `monitor`, `isolate_device`), because both use the common vocabulary of the sources above. Every catalog entry stands on its own citations in section 2. The spike enum is never reused.
