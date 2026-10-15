"""Property tests for the validator (E7-03, SCRUM-54).

Example tests cover the cases we thought of; these cover the ones we did not (record §6.9): for any
generated input, no action outside the catalog and no unknown evidence id ever passes the
validator. Fixed example budget and seed so the run is reproducible.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st

from thesis.assemble.bundles import Bundle
from thesis.safety.validator import Rejection, RejectionReason, validate
from thesis.schema.alert import Alert, FlowDetail
from thesis.schema.verdict import ACTION_IDS

T0 = datetime(2026, 1, 1, tzinfo=UTC)
EXAMPLES = 1000

# Near-miss actions must be exercised, not just random strings: catalog ids re-cased, spaced or
# suffixed look almost right but are not enum members.
_CASING = st.sampled_from([a.upper() for a in ACTION_IDS] + [a.title() for a in ACTION_IDS])
_SPACED = st.sampled_from([a.replace("_", " ") for a in ACTION_IDS] + [a + "_" for a in ACTION_IDS])
_NOT_AN_ACTION = (
    st.text() | _CASING | _SPACED | st.sampled_from(["", "escalate", "isolate", "block"])
).filter(lambda s: s not in ACTION_IDS)


def _bundle(alert_ids: list[str]) -> Bundle:
    alerts = tuple(
        Alert(
            alert_id=aid,
            source="flows",
            ts=T0,
            subject_device="iot-cam-01",
            detector_score=0.5,
            detector_label="syn_flood",
            detector_name="flow_classifier",
            detail=FlowDetail(
                flow_start=T0,
                duration_s=1.0,
                src_ip="10.77.0.22",
                src_port=5,
                dst_ip="192.0.2.1",
                dst_port=80,
                protocol="tcp",
                packets_fwd=1,
                packets_bwd=0,
                bytes_fwd=1,
                bytes_bwd=0,
            ),
        )
        for aid in dict.fromkeys(alert_ids)  # unique, order-preserving
    )
    return Bundle(
        bundle_id="b",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep",
        sources=("flows",),
        alerts=alerts,
    )


def _verdict(action: str, evidence: list[str]) -> str:
    return json.dumps(
        {
            "classification": {"incident_type": "syn_flood", "confidence": 0.5},
            "recommendation": {"recommended_action": action, "severity": "high"},
            "affected_device": "iot-cam-01",
            "evidence": evidence,
        }
    )


@seed(20261015)
@settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(action=_NOT_AN_ACTION)
def test_no_out_of_catalog_action_ever_passes(action: str) -> None:
    result = validate(_verdict(action, ["f1"]), _bundle(["f1"]))
    assert isinstance(result, Rejection)
    assert result.reason is RejectionReason.ACTION_OUT_OF_SPACE


@seed(20261015)
@settings(max_examples=EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    bundle_ids=st.lists(st.text(min_size=1, max_size=8), max_size=5),
    extra=st.text(min_size=1, max_size=8),
)
def test_unknown_evidence_never_passes(bundle_ids: list[str], extra: str) -> None:
    # `extra` is an evidence id guaranteed not to be in the bundle (the present ids exclude it; the
    # bundle contains only those, possibly none), so citing it must be rejected.
    present = [b for b in bundle_ids if b != extra]
    result = validate(_verdict(ACTION_IDS[0], [*present, extra]), _bundle(present))
    assert isinstance(result, Rejection)
    assert result.reason is RejectionReason.UNKNOWN_EVIDENCE
