"""The one OpenAI-compatible LLM client (E6-01, SCRUM-28).

Every LLM call in the project goes through this client, so reproducibility, cost control and the
token ceilings are enforced in one place (record §4.2, §4.4). Local Ollama and the hosted model
differ only by `LLM_BASE_URL` / `LLM_MODEL` (§4.2). The client sets `max_tokens` to the frozen
output ceiling, asserts the completion stays within it, retries transient failures with capped
exponential backoff (an uncapped loop is how a spending cap gets hit, §4.4.1), sets Ollama's
`num_ctx` to 8192 (§4.3), and logs every call through `log_llm_call()` (§6.10).

**No other module imports the OpenAI SDK** (DoD); everything goes through `LLMClient`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError, omit
from openai.types.chat import ChatCompletion

from thesis.obs.logging import LOG_PATH, log_llm_call
from thesis.reduce.check_tokens import (
    OUTPUT_CEILING,
    TokenCeilingError,
    assert_output_tokens,
    count_tokens,
)

BASE_URL_ENV = "LLM_BASE_URL"
MODEL_ENV = "LLM_MODEL"
API_KEY_ENV = "LLM_API_KEY"

OLLAMA_NUM_CTX = 8192  # Ollama truncates silently at its default context (§4.3); set it explicitly.
# Meta's Llama 3 reference defaults (ADR-0001); a run overrides these from its ExperimentConfig.
DEFAULT_TEMPERATURE = 0.6
DEFAULT_TOP_P = 0.9
MAX_ATTEMPTS = 4  # capped so a retry storm cannot exhaust the provider spending cap (§4.4.1).
BACKOFF_BASE_S = 1.0


class LLMError(RuntimeError):
    """A call failed after exhausting retries, or for a non-retryable reason."""


def _is_local(base_url: str) -> bool:
    return "localhost" in base_url or "127.0.0.1" in base_url


def _retryable(error: Exception) -> bool:
    if isinstance(error, RateLimitError | APIConnectionError | APITimeoutError):
        return True
    return isinstance(error, APIStatusError) and error.status_code >= 500


@dataclass
class LLMClient:
    """Wraps one OpenAI-compatible endpoint. Build it with `from_env()`."""

    model: str
    base_url: str
    model_revision: str = "unpinned"
    api_key: str = "ollama"
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    max_tokens: int = OUTPUT_CEILING
    max_attempts: int = MAX_ATTEMPTS
    backoff_base_s: float = BACKOFF_BASE_S
    sleep: Callable[[float], None] = time.sleep
    # Where this client's calls are logged (§6.10). The demo live run points this at a throwaway
    # file so it never writes the frozen experiment call log.
    log_path: Path = LOG_PATH
    _client: OpenAI = field(init=False)

    def __post_init__(self) -> None:
        # max_retries=0: this class owns retry, so it stays testable and capped (the SDK's own
        # retry would hide attempts and double the backoff).
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, max_retries=0)

    @classmethod
    def from_env(cls, *, model_revision: str = "unpinned", **overrides: object) -> LLMClient:
        base_url = os.environ.get(BASE_URL_ENV)
        model = os.environ.get(MODEL_ENV)
        if not base_url or not model:
            raise LLMError(f"set {BASE_URL_ENV} and {MODEL_ENV} in the environment")
        api_key = os.environ.get(API_KEY_ENV) or ("ollama" if _is_local(base_url) else "")
        if not api_key:
            raise LLMError(f"set {API_KEY_ENV} for the hosted endpoint {base_url}")
        return cls(
            model=model,
            base_url=base_url,
            model_revision=model_revision,
            api_key=api_key,
            **overrides,  # type: ignore[arg-type]
        )

    def _response_format(self, json_schema: dict[str, object] | None) -> dict[str, object] | None:
        # Structured output is json_object, not json_schema (ADR-0012, Option A): the pinned hosted
        # model rejects a json_schema response format, and json_object is used on every provider so
        # development and the experiment behave identically. json_object constrains output to valid
        # JSON; Verdict conformance is enforced by each node's parse and by the validator gate on E
        # (E7-02), not at decode time. The argument is the on/off signal; its contents are not sent.
        if json_schema is None:
            return None
        return {"type": "json_object"}

    def _create_once(
        self, prompt: str, response_format: dict[str, object] | None
    ) -> ChatCompletion:
        # Ollama truncates silently at its default context, so num_ctx goes in extra_body (§4.3).
        extra_body = {"options": {"num_ctx": OLLAMA_NUM_CTX}} if _is_local(self.base_url) else None
        rf: object = omit if response_format is None else response_format
        return self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            extra_body=extra_body,
            response_format=cast("Any", rf),
        )

    def _create_with_retry(
        self, prompt: str, response_format: dict[str, object] | None
    ) -> ChatCompletion:
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._create_once(prompt, response_format)
            except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as error:
                last = error
                if attempt == self.max_attempts or not _retryable(error):
                    break
                self.sleep(self.backoff_base_s * 2 ** (attempt - 1))
        raise LLMError(f"LLM call failed after {self.max_attempts} attempt(s): {last}") from last

    def complete(
        self,
        prompt: str,
        *,
        node: str,
        bundle_id: str,
        config_hash: str,
        repetition: int,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        """Send one prompt, enforce the output ceiling, log the call, and return the completion.

        Pass `json_schema` (e.g. `verdict_json_schema()`) to request json_object structured output
        (ADR-0012); its contents are the on/off signal, and conformance is checked after decoding.
        """
        started = time.monotonic()
        response = self._create_with_retry(prompt, self._response_format(json_schema))
        latency_ms = (time.monotonic() - started) * 1000.0

        completion = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else count_tokens(prompt)
        tokens_out = usage.completion_tokens if usage else count_tokens(completion)

        def _log(parse_outcome: str) -> None:
            log_llm_call(
                node=node,
                model=self.model,
                model_revision=self.model_revision,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                prompt=prompt,
                completion=completion,
                parse_outcome=parse_outcome,
                config_hash=config_hash,
                bundle_id=bundle_id,
                repetition=repetition,
                path=self.log_path,
            )

        try:
            assert_output_tokens(completion)
        except TokenCeilingError:
            _log("output_ceiling_exceeded")  # the attempt is logged before the error propagates
            raise
        _log("ok")
        return completion


__all__ = ["BACKOFF_BASE_S", "MAX_ATTEMPTS", "OLLAMA_NUM_CTX", "LLMClient", "LLMError"]
