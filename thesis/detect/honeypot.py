"""Honeypot rule-based detector (E4-05, SCRUM-58).

Honeypot activity is malicious by definition, but the *type* still matters for classification
(record §6.2): a small, documented rule set separates brute force, successful login and command
execution. Thresholds come from the rule's meaning, not from the attack families, so they do not
leak a label into the detector. Each honeypot alert gets a score in [0, 1] and a label; the scores
and the command sequences feed the reduction.
"""

from __future__ import annotations

from collections import Counter

from thesis.schema.alert import Alert, HoneypotDetail

# A session with at least this many failed logins is brute force. Set from the meaning of "brute
# force" (repeated guessing), not from any family's episode length.
BRUTE_FORCE_MIN_FAILURES = 10

# Score and label per rule, most severe first. Command execution is post-compromise, the worst.
_COMMAND = (1.0, "command_execution")
_LOGIN_SUCCESS = (0.9, "login_success")
_BRUTE_FORCE = (0.8, "brute_force")
_FAILED_LOGIN = (0.5, "failed_login")
_CONTACT = (0.3, "contact")


def score_event(event: str, failed_in_session: int) -> tuple[float, str]:
    """Score one honeypot alert given how many failed logins its session has."""
    if event in ("command", "command_execution", "command_failed"):
        return _COMMAND
    if event == "login_success":
        return _LOGIN_SUCCESS
    if event == "login_failed":
        return _BRUTE_FORCE if failed_in_session >= BRUTE_FORCE_MIN_FAILURES else _FAILED_LOGIN
    return _CONTACT  # session_connect / session_closed / client_version / client_kex


def apply_rules(alerts: list[Alert]) -> dict[str, tuple[float, str]]:
    """Score every honeypot alert; the brute-force rule uses per-session failed-login counts."""
    failures: Counter[str] = Counter()
    for a in alerts:
        if isinstance(a.detail, HoneypotDetail) and a.detail.event == "login_failed":
            failures[a.detail.session_id] += 1
    out: dict[str, tuple[float, str]] = {}
    for a in alerts:
        if not isinstance(a.detail, HoneypotDetail):
            continue
        out[a.alert_id] = score_event(a.detail.event, failures[a.detail.session_id])
    return out


__all__ = ["BRUTE_FORCE_MIN_FAILURES", "apply_rules", "score_event"]
