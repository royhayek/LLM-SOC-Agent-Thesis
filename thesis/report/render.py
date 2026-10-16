"""Render a one-page incident report from a verdict (E7-08, SCRUM-102).

The architecture promises the analyst one clear report with a suggestion, not a flood of alerts
(Arch §2, §5 step 8). `render_report` turns a validated `Verdict` plus node 1's findings and the
audit record into a short Markdown page a human reads in under a minute, and writes it to
`reports/<bundle_id>.md`. The agent only recommends and never executes; the report says so (§1.1).

Evidence ids are resolved to short alert summaries, not raw attacker text. Any attacker-influenced
text (a honeypot command in a summary, the model's free-text findings) is Markdown-escaped, so a
pasted command cannot break or inject the report (ticket gotcha).
"""

from __future__ import annotations

import re
from pathlib import Path

from thesis.agent.models import Findings
from thesis.assemble.bundles import Bundle
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail
from thesis.schema.verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = Path(__file__).resolve().parent / "template.md"
REPORTS_DIR = REPO_ROOT / "reports"

# Inline Markdown specials only. Hyphen, plus and hash are special only at line start, and newlines
# are flattened below, so escaping them would just mangle ids like `iot-cam-01`.
_MD_SPECIAL = re.compile(r"([\\`*_\[\]()|<>~])")


def _md_escape(text: str) -> str:
    """Escape Markdown specials and flatten newlines, so attacker text is inert in the report."""
    return _MD_SPECIAL.sub(r"\\\1", text.replace("\n", " ").replace("\r", " ")).strip()


def report_filename(bundle_id: str) -> str:
    """The on-disk report name for a bundle id, sanitised so the id's ``:`` and ``|`` are legal and
    stable across filesystems. The renderer writes it and the API reads it, so the two agree."""
    safe = bundle_id.replace("/", "_").replace(":", "-").replace("|", "_")
    return f"{safe}.md"


def _alert_summary(alert: Alert) -> str:
    """A one-line, escaped summary of one alert, keyed by its id (never raw attacker text)."""
    d = alert.detail
    label = f"{alert.detector_label or '?'} ({alert.detector_score})"
    if isinstance(d, FlowDetail):
        body = f"flow {d.src_ip}:{d.src_port}->{d.dst_ip}:{d.dst_port} {d.protocol}, {label}"
    elif isinstance(d, MqttDetail):
        body = f"mqtt {d.event} topic={d.topic}, {label}"
    elif isinstance(d, HoneypotDetail):
        body = f"honeypot {d.event} session={d.session_id}, {label}"
    else:  # pragma: no cover - the union is exhaustive
        body = label
    return f"`{alert.alert_id}` — {_md_escape(body)}"


def render_report(
    verdict: Verdict, findings: Findings, bundle: Bundle, *, out_dir: Path = REPORTS_DIR
) -> str:
    """Render the report for an accepted verdict, write `<bundle_id>.md`, return the Markdown."""
    by_id = {a.alert_id: a for a in bundle.alerts}
    evidence_lines = [
        _alert_summary(by_id[e]) if e in by_id else f"`{_md_escape(e)}`" for e in verdict.evidence
    ]
    evidence = "\n".join(f"- {line}" for line in evidence_lines) or "- (none cited)"

    finding_lines = [f"- {_md_escape(f.summary)}" for f in findings.source_findings]
    if findings.cross_source:
        finding_lines.append(f"- Cross-source: {_md_escape(findings.cross_source)}")
    findings_md = "\n".join(finding_lines) or "- (none)"

    report = TEMPLATE_PATH.read_text(encoding="utf-8").format(
        bundle_id=_md_escape(bundle.bundle_id),
        incident_type=verdict.classification.incident_type.value,
        severity=verdict.recommendation.severity.value,
        affected_device=_md_escape(verdict.affected_device),
        recommended_action=verdict.recommendation.recommended_action.value,
        confidence=verdict.classification.confidence,
        evidence=evidence,
        findings=findings_md,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / report_filename(bundle.bundle_id)).write_text(report, encoding="utf-8")
    return report


def word_count(report: str) -> int:
    return len(report.split())


__all__ = ["render_report", "report_filename", "word_count"]
