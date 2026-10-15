# Flow classifier search (E4-02, SCRUM-29)

**Library:** lightgbm 4.7.0 — the record fixes LightGBM or
XGBoost for flows (§6.2); LightGBM is light on 16 GB and fast on this small table. The
classifier doubles as Baseline A (§5), so it is tuned properly (§6.6).

- **Search space:** {"num_leaves": [15, 31, 63], "learning_rate": [0.05, 0.1], "min_child_samples": [5, 10, 20], "num_boost_round": [100, 200], "feature_fraction": [0.8, 1.0]}
- **Trials:** 15 random draws (seed 20261015).
- **Cross-validation:** 3-fold, **grouped by episode** so no episode spans train and validation folds (§4.1).
- **Class imbalance:** inverse-frequency sample weights.
- **Best parameters:** {"num_leaves": 63, "learning_rate": 0.1, "min_child_samples": 20, "num_boost_round": 200, "feature_fraction": 1.0}
- **Cross-validated macro-F1 of the best model:** 0.8517
- **Training flows:** 565 (training split only, E2-01).

The model is saved to `models/flow_classifier.txt` with its parameters in
`models/flow_classifier.json`. It is evaluated and frozen as Baseline A in E4-03.
