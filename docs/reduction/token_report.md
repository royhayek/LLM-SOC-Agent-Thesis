# Reduced-bundle token report (E3-08, SCRUM-99)

Prompt tokens over the pilot bundles, counted with the experiment model's own tokenizer (vendored Llama 3.1, ADR-0001 / ADR-0011). The frozen per-call ceilings (reduction-v1.0, METHODS.md Annex E §9): input target 2000, **ceiling 2500**; output target 200, ceiling 250.

These are **reduced-bundle** tokens: the static prompt prefix is frozen later (E6-02); the full-prompt assertion adds the prefix once it exists (`reduced_prompt(view, prefix)`).

- Pilot bundles measured: **160**
- Minimum: **279** tokens
- Median: **329.0** tokens
- 95th percentile: **772** tokens
- Maximum: **902** tokens
- Over the 2500-token input ceiling: **0**
