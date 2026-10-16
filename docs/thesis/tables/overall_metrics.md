| Cond | Description | DET recall | DET F1 | CLS acc | CLS macroF1 | CU | SV | USE |
|---|---|---|---|---|---|---|---|---|
| C1 | all sources, agentic, enforcing | 0.901 | 0.617 | 0.192 | 0.355 | 0.049 | 0.918 | 0.28 |
| C2 | flows only, agentic, enforcing | 0.521 | 0.438 | 0.219 | 0.404 | 0.002 | 0.587 | 0.288 |
| C3 | mqtt only, agentic, enforcing | 0.765 | 0.55 | 0.135 | 0.157 | 0.042 | 0.8 | 0.245 |
| C4 | honeypot only, agentic, enforcing | 0.396 | 0.336 | 0.083 | 0.142 | 0.002 | 0.423 | 0.195 |
| C5 | all sources, agentic, logging_only | 0.913 | 0.623 | 0.195 | 0.357 | 0.134 | 0.918 | 0.339 |
| C6 | prompt-only (Baseline B) | 0.55 | 0.562 | 0.481 | 0.439 | 0.002 | 0.952 | 0.49 |
| C7 | ml-classifier (Baseline A) | 0.321 | 0.485 | 0.655 | 0.591 | 0.0 | 1.0 | 0.662 |
