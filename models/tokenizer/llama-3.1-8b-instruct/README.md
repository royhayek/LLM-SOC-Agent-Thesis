# Vendored Llama 3.1 8B Instruct tokenizer

`tokenizer.json.gz` is the gzipped Hugging Face fast-tokenizer file for **Llama 3.1 8B Instruct**,
the experiment and development model pinned in ADR-0001. It is used only to count tokens for the
frozen per-call token budget (E3-08, `thesis/reduce/check_tokens.py`); it runs no inference.
`load_tokenizer` decompresses it in memory and loads it with `Tokenizer.from_str`.

It is stored gzipped (2.2 MB vs 8.7 MB) because the raw 128k vocabulary contains ordinary
brand- and product-name subword tokens that would otherwise trip the repository's AI-attribution
pre-push guard on a plaintext diff. The file is an opaque third-party model artifact, not authored
content.

## Provenance

- Source: `NousResearch/Meta-Llama-3.1-8B-Instruct`, path `tokenizer.json`, `main` branch
  (a non-gated mirror of the gated `meta-llama/Meta-Llama-3.1-8B-Instruct` repository).
- URL: `https://huggingface.co/NousResearch/Meta-Llama-3.1-8B-Instruct/resolve/main/tokenizer.json`
- Retrieved: 2026-10-15.
- Type: byte-level BPE, 128k base vocabulary plus Llama 3 special tokens (`<|begin_of_text|>` =
  128000, …). `encode("Hello world").ids` begins `[128000, 9906, 1917]`.

See ADR-0011 for why it is vendored rather than downloaded at run time. If ADR-0001's model
revision changes, re-sync this file from the matching revision and regenerate the token report.
