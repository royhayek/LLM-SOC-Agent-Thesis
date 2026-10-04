"""E0-01 walking-skeleton spike. Throwaway: nothing outside spikes/ may import this file.

Usage:
    python spikes/walking_skeleton.py --marker-test     # context check, local Ollama only
    python spikes/walking_skeleton.py --model local     # one verdict run
    python spikes/walking_skeleton.py --model hosted    # one verdict run

The endpoint and model come from .env (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY).
--model is a label and must agree with LLM_BASE_URL (local means localhost).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SPIKE_DIR = Path(__file__).resolve().parent
ROOT = SPIKE_DIR.parent
BUNDLE_PATH = SPIKE_DIR / "bundle_ssh_bruteforce.json"
RESULTS_PATH = SPIKE_DIR / "results.csv"
LOG_DIR = SPIKE_DIR / "logs"
MARKER_LOG = SPIKE_DIR / "marker_test.log"

PROMPT_VERSION = "v1"
# Greedy decoding, no seed: any run-to-run disagreement is serving nondeterminism (risk #5).
# The experiment temperature is decided later (E0-06, ADR-001).
TEMPERATURE: float | None = 0.0
CSV_COLUMNS = [
    "run_id", "model", "schema_valid", "incident_type", "severity", "affected_device",
    "recommended_action", "matches_expected", "tokens_in", "tokens_out", "latency_s",
]


# SPIKE_ONLY: candidate families from record §3.2 plus benign. Never reused. E1-02 decides the real list.
class SpikeOnlyIncidentType(str, Enum):
    MQTT_MESSAGE_FLOOD = "mqtt_message_flood"
    MQTT_PASSWORD_GUESSING = "mqtt_password_guessing"
    PORT_SCAN = "port_scan"
    SSH_PASSWORD_GUESSING = "ssh_password_guessing"
    BOTNET_TRAFFIC = "botnet_traffic"
    DENIAL_OF_SERVICE = "denial_of_service"
    BENIGN = "benign"


# SPIKE_ONLY: placeholder actions in generic SOC wording, invented for the spike and derived
# from no source. Never reused. The real catalog is E0-04.
class SpikeOnlyAction(str, Enum):
    NO_ACTION = "no_action"
    MONITOR = "monitor"
    BLOCK_SOURCE_IP = "block_source_ip"
    RATE_LIMIT_SOURCE = "rate_limit_source"
    ISOLATE_DEVICE = "isolate_device"
    RESET_CREDENTIALS = "reset_credentials"
    ESCALATE_TO_ANALYST = "escalate_to_analyst"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(BaseModel):
    """Record §6.5 fields."""

    model_config = ConfigDict(extra="forbid")

    incident_type: SpikeOnlyIncidentType
    severity: Severity
    affected_device: str
    evidence: list[str]
    recommended_action: SpikeOnlyAction
    confidence: float = Field(ge=0.0, le=1.0)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("LLM_")})
    for key in ("LLM_BASE_URL", "LLM_MODEL"):
        if not env.get(key):
            sys.exit(f"{key} is not set in .env")
    return env


def make_client(env: dict[str, str], label: str) -> OpenAI:
    is_local = "localhost" in env["LLM_BASE_URL"] or "127.0.0.1" in env["LLM_BASE_URL"]
    if (label == "local") != is_local:
        sys.exit(f"--model {label} does not match LLM_BASE_URL in .env")
    api_key = env.get("LLM_API_KEY") or ("ollama" if is_local else "")
    if not api_key:
        sys.exit("LLM_API_KEY is not set in .env")
    return OpenAI(base_url=env["LLM_BASE_URL"], api_key=api_key)


SYSTEM_PROMPT = """You are a security analyst in an IoT security operations centre.
You receive one alert bundle: all alerts raised for one device in one 60-second window,
from up to three sources (honeypot, network flows, MQTT broker telemetry).
The "sources" block says which sources sent alerts in this window.

Return one verdict as a JSON object with exactly these fields:
- incident_type: one of {incident_types}
- severity: one of {severities}
- affected_device: the device ID the incident concerns
- evidence: list of alert_id values from the bundle that support the verdict
- recommended_action: one of {actions}
- confidence: a number from 0 to 1

Use only information in the bundle. Return the JSON object and nothing else."""


def build_messages(bundle: dict) -> list[dict[str, str]]:
    visible = {k: v for k, v in bundle.items() if k != "expected_verdict"}
    system = SYSTEM_PROMPT.format(
        incident_types=", ".join(e.value for e in SpikeOnlyIncidentType),
        severities=", ".join(e.value for e in Severity),
        actions=", ".join(e.value for e in SpikeOnlyAction),
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Alert bundle:\n" + json.dumps(visible, indent=1)},
    ]
    if any("expected_verdict" in m["content"] for m in messages):
        sys.exit("ABORT: 'expected_verdict' appears in the prompt")
    return messages


def validate(raw: str, bundle: dict) -> tuple[Verdict | None, str | None]:
    try:
        verdict = Verdict.model_validate_json(raw)
    except ValidationError as exc:
        return None, str(exc)
    known_ids = {a["alert_id"] for a in bundle["alerts"]}
    unknown = [e for e in verdict.evidence if e not in known_ids]
    if unknown:
        return None, f"evidence cites unknown alert_id values: {unknown}"
    return verdict, None


def next_run_id(label: str) -> str:
    count = 0
    if RESULTS_PATH.exists():
        with RESULTS_PATH.open() as f:
            count = sum(1 for row in csv.DictReader(f) if row["model"] == label)
    return f"{label}-{count + 1:02d}"


def run_verdict(label: str) -> None:
    env = load_env()
    client = make_client(env, label)
    bundle = json.loads(BUNDLE_PATH.read_text())
    expected = bundle["expected_verdict"]
    messages = build_messages(bundle)
    run_id = next_run_id(label)

    kwargs: dict = {
        "model": env["LLM_MODEL"],
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "schema": Verdict.model_json_schema()},
        },
    }
    if TEMPERATURE is not None:
        kwargs["temperature"] = TEMPERATURE

    started = time.perf_counter()
    response = client.chat.completions.create(**kwargs)
    latency = time.perf_counter() - started

    raw = response.choices[0].message.content or ""
    verdict, error = validate(raw, bundle)
    usage = response.usage
    tokens_in = usage.prompt_tokens if usage else None
    tokens_out = usage.completion_tokens if usage else None
    matches = bool(
        verdict
        and verdict.incident_type.value == expected["incident_type"]
        and verdict.affected_device == expected["affected_device"]
    )

    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id,
        "utc": datetime.now(UTC).isoformat(),
        "label": label,
        "base_url": env["LLM_BASE_URL"],
        "requested_model": env["LLM_MODEL"],
        "response_model": response.model,
        "system_fingerprint": response.system_fingerprint,
        "prompt_version": PROMPT_VERSION,
        "temperature": TEMPERATURE,
        "response_format": "json_schema",
        "messages": messages,
        "raw_completion": raw,
        "finish_reason": response.choices[0].finish_reason,
        "validation_error": error,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_s": round(latency, 3),
    }, indent=2))

    new_file = not RESULTS_PATH.exists()
    with RESULTS_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "run_id": run_id,
            "model": label,
            "schema_valid": verdict is not None,
            "incident_type": verdict.incident_type.value if verdict else "",
            "severity": verdict.severity.value if verdict else "",
            "affected_device": verdict.affected_device if verdict else "",
            "recommended_action": verdict.recommended_action.value if verdict else "",
            "matches_expected": matches,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_s": round(latency, 3),
        })

    print(verdict.model_dump_json(indent=2) if verdict else f"VALIDATION ERROR: {error}")


FILLER = (
    "This sentence is padding for a context-length check and carries no information. "
)


def marker_test() -> None:
    env = load_env()
    client = make_client(env, "local")
    marker = "MARKER-" + uuid.uuid4().hex[:8].upper()
    # The marker sits at the very start. The filler pushes the prompt past Ollama's
    # 2048-token default, so a truncated context would drop the marker.
    prompt = (
        f"Remember this code: {marker}.\n\n"
        + FILLER * 250
        + "\n\nWhat was the code given at the very start of this message? Reply with the code only."
    )
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=env["LLM_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    latency = time.perf_counter() - started
    reply = response.choices[0].message.content or ""
    tokens_in = response.usage.prompt_tokens if response.usage else None
    passed = marker in reply
    MARKER_LOG.write_text(
        f"utc: {datetime.now(UTC).isoformat()}\n"
        f"base_url: {env['LLM_BASE_URL']}\n"
        f"model: {env['LLM_MODEL']}\n"
        f"marker: {marker}\n"
        f"prompt_tokens: {tokens_in}\n"
        f"latency_s: {latency:.3f}\n"
        f"result: {'PASS' if passed else 'FAIL'}\n"
        f"--- prompt ---\n{prompt}\n"
        f"--- reply ---\n{reply}\n"
    )
    print(f"{'PASS' if passed else 'FAIL'}: marker={marker} prompt_tokens={tokens_in} reply={reply!r}")
    if not passed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model", choices=["local", "hosted"])
    group.add_argument("--marker-test", action="store_true")
    args = parser.parse_args()
    if args.marker_test:
        marker_test()
    else:
        run_verdict(args.model)


if __name__ == "__main__":
    main()
