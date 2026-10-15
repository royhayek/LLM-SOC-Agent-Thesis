# Baseline A (flow classifier) evaluation (E4-03, SCRUM-37)

Evaluated once on held-out **training** episodes (never the evaluation split, E2-01): a
held-out grouped fold of 222 flows, with a model fit on the
remaining training episodes using the frozen best parameters (E4-02).

**Macro-F1 (held-out training episodes): 0.8652**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| benign | 0.969 | 0.596 | 0.738 | 52 |
| botnet | 0.948 | 0.986 | 0.967 | 74 |
| mqtt_brute_force | 0.981 | 0.981 | 0.981 | 53 |
| mqtt_publish_flood | 0.227 | 1.0 | 0.37 | 5 |
| port_scan | 1.0 | 1.0 | 1.0 | 18 |
| ssh_brute_force | 1.0 | 1.0 | 1.0 | 18 |
| syn_flood | 1.0 | 1.0 | 1.0 | 2 |

The frozen model is `models/flow_classifier.txt`, SHA-256 `1aa54a1636fc4c33874a958a44b42febb8cb05146a24523ed2b72341cb8a235d` (also in `models/flow_classifier.json`). Frozen at git tag `baseline-a-v1.0` before any
agent output exists; any later change needs a changelog entry and a full rerun.
