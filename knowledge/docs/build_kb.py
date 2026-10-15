"""Build the curated knowledge base (E5-02, SCRUM-34).

A small, curated corpus — not a general RAG collection (record §5) — of short, descriptive
documents covering the attack techniques, their mitigations and detection, and incident-handling
guidance for the six families (E1-02). The agent's retrieval tool (E5-04) reads these.

    python -m knowledge.docs.build_kb      # (re)writes knowledge/docs/*.md and INDEX.md

Sourcing, and why every citation is checked:
- ATT&CK technique, mitigation and detection content is taken from the MITRE ATT&CK Enterprise
  pages for the techniques recorded in `knowledge/attack_families.yaml` (v19.2), read on
  2026-10-15; descriptions are paraphrased and each doc cites the technique/mitigation page URL.
  ATT&CK is licensed CC BY 4.0.
- Incident-handling excerpts reuse the **already-verified** verbatim quotes in
  `knowledge/action_catalog.yaml` (E0-04, each checked against its source 2026-10-04), with the
  same source and locator. No new citation is introduced and none is invented.

Documents are **descriptive**: they describe techniques, generic defensive controls and IR
principles. They never state the correct catalog action for a family, which would turn retrieval
into an answer key and inflate H2 (ticket gotcha). Vulnerability databases are out of scope (§5).
"""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "knowledge" / "docs"
CATALOG = ROOT / "knowledge" / "action_catalog.yaml"
FAMILIES = ROOT / "knowledge" / "attack_families.yaml"

ATTACK_VERSION = "MITRE ATT&CK Enterprise v19.2"
ACCESSED = "accessed 2026-10-15"


def _attack_source(kind: str, ident: str, name: str) -> str:
    sub = ident.replace(".", "/")
    base = "techniques" if kind == "technique" else "mitigations"
    return f"{ATTACK_VERSION}, {ident} {name}, https://attack.mitre.org/{base}/{sub}/ ({ACCESSED})"


# --- Verified ATT&CK mitigations (descriptions paraphrased from the technique/mitigation pages) --
MITIGATIONS: dict[str, dict[str, str]] = {
    "M1036": {
        "name": "Account Use Policies",
        "body": "Lock accounts after a set number of failed login attempts, and use conditional"
        " access policies that block logins from non-compliant devices or outside defined IP"
        " ranges. This slows repetitive credential guessing against a service.",
    },
    "M1032": {
        "name": "Multi-factor Authentication",
        "body": "Require a second authentication factor, particularly on externally facing"
        " services, so that a guessed or stolen password alone does not grant access.",
    },
    "M1027": {
        "name": "Password Policies",
        "body": "Set and enforce password policies following recognised guidance (for example"
        " NIST), so that accounts resist dictionary and common-password guessing.",
    },
    "M1051": {
        "name": "Update Software",
        "body": "Keep authentication and management services up to date, so that they support"
        " stronger password complexity and lockout policy enforcement.",
    },
    "M1018": {
        "name": "User Account Management",
        "body": "Manage accounts over their lifecycle and proactively reset or disable accounts"
        " known or suspected to be compromised during a guessing attempt.",
    },
    "M1042": {
        "name": "Disable or Remove Feature or Program",
        "body": "Close unnecessary ports and disable unused services so that less of the attack"
        " surface is visible to service-discovery scans.",
    },
    "M1031": {
        "name": "Network Intrusion Prevention",
        "body": "Use network intrusion detection and prevention systems to detect and block remote"
        " service scans before they enumerate the environment.",
    },
    "M1030": {
        "name": "Network Segmentation",
        "body": "Segment the network so that critical servers and devices are isolated from"
        " untrusted segments, limiting what a scan or flood can reach.",
    },
    "M1037": {
        "name": "Filter Network Traffic",
        "body": "Filter attack traffic, ideally upstream (ISP or CDN), and on-premises by blocking"
        " offending source addresses, ports or protocols; SYN cookies help against SYN floods.",
    },
    "M1056": {
        "name": "Pre-compromise",
        "body": "This activity happens largely outside the defender's environment and cannot be"
        " easily prevented with internal controls; reduce the data exposed to external parties.",
    },
}

# --- Verified ATT&CK techniques: id -> (name, paraphrased description, mitigation ids) ------------
TECHNIQUES: dict[str, dict[str, object]] = {
    "T1110": {
        "name": "Brute Force",
        "desc": "Adversaries gain access to accounts by systematically guessing or cracking"
        " passwords, either interactively against a service or offline against captured hashes.",
        "mitigations": ["M1036", "M1032", "M1027", "M1018"],
    },
    "T1110.001": {
        "name": "Brute Force: Password Guessing",
        "desc": "Adversaries guess login credentials without prior knowledge of them, typically"
        " using a list of common or likely passwords against a service such as SSH.",
        "mitigations": ["M1036", "M1032", "M1027", "M1051", "M1018"],
    },
    "T1046": {
        "name": "Network Service Discovery",
        "desc": "Adversaries enumerate services running on remote hosts and network infrastructure"
        " — for example with port scans — to find potential targets for later exploitation.",
        "mitigations": ["M1042", "M1031", "M1030"],
    },
    "T1595": {
        "name": "Active Scanning",
        "desc": "Adversaries probe victim infrastructure with direct network traffic during"
        " reconnaissance to gather information that supports later targeting and access.",
        "mitigations": ["M1056"],
    },
    "T1498": {
        "name": "Network Denial of Service",
        "desc": "Adversaries exhaust a target's network bandwidth by directing high-volume traffic"
        " at a resource or the infrastructure it depends on, blocking availability to users.",
        "mitigations": ["M1037"],
    },
    "T1498.001": {
        "name": "Network Denial of Service: Direct Network Flood",
        "desc": "Adversaries flood a target directly with high-volume traffic (often from a botnet)"
        " to saturate its network capacity and degrade availability.",
        "mitigations": ["M1037"],
    },
    "T1499": {
        "name": "Endpoint Denial of Service",
        "desc": "Adversaries deny a service's availability by exhausting the resources of the"
        " system hosting it, without necessarily saturating the network around it.",
        "mitigations": ["M1037"],
    },
    "T1499.002": {
        "name": "Endpoint Denial of Service: Service Exhaustion Flood",
        "desc": "Adversaries overwhelm a network service (such as a web or messaging service) with"
        " a high volume of requests, exhausting the CPU or memory that serves it.",
        "mitigations": ["M1037"],
    },
    "T1584.005": {
        "name": "Compromise Infrastructure: Botnet",
        "desc": "Adversaries compromise many third-party systems to form a botnet, which they then"
        " coordinate for large-scale tasks such as distributed denial-of-service attacks.",
        "mitigations": ["M1056"],
    },
}

# --- Verified ATT&CK detection notes per technique (paraphrased from the pages' detection rows) ---
DETECTION: dict[str, list[str]] = {
    "T1110.001": [
        "Repeated authentication failures against the same or similar accounts from one or more"
        " source addresses, sometimes followed by a success from the same host.",
        "Series of failed SSH or service logins recorded in the host's auth logs or syslog.",
    ],
    "T1046": [
        "A process or host making rapid connections to many services or hosts in a short window.",
        "Sequential probing of destination IPs or ports visible in netflow or packet telemetry.",
    ],
    "T1499.002": [
        "High-frequency repetitive requests from a single or small set of source IPs to a service.",
        "A spike in inbound connections that exhausts worker threads or server CPU and memory.",
    ],
    "T1498.001": [
        "A local process or service generating high-rate outbound traffic (TCP SYN, UDP, ICMP)"
        " beyond expected interface throughput or behavioural baselines.",
        "Excessive outbound packets toward one destination with abnormal resource consumption.",
    ],
    "T1584.005": [
        "Much of this activity occurs outside the target's visibility; detection focuses on the"
        " related flood stages (endpoint or network denial of service) seen on the network.",
    ],
}

# --- Family -> ATT&CK mapping for the index (from attack_families.yaml techniques) ---
FAMILY_MAP: dict[str, dict[str, object]] = {
    "ssh_brute_force": {"techniques": ["T1110.001", "T1110"], "detection": "T1110.001"},
    "port_scan": {"techniques": ["T1046", "T1595"], "detection": "T1046"},
    "mqtt_publish_flood": {"techniques": ["T1499.002", "T1499"], "detection": "T1499.002"},
    "mqtt_brute_force": {"techniques": ["T1110.001", "T1110"], "detection": "T1110.001"},
    "syn_flood": {"techniques": ["T1498.001", "T1498"], "detection": "T1498.001"},
    "botnet": {"techniques": ["T1584.005", "T1498.001"], "detection": "T1584.005"},
}


def _write(slug: str, title: str, source: str, body: str) -> str:
    front = f"---\ntitle: {title!r}\nsource: {source!r}\n---\n\n"
    (DOCS / f"{slug}.md").write_text(front + f"# {title}\n\n{body}\n", encoding="utf-8")
    return slug


def _mitigation_slug(mid: str) -> str:
    return f"mitigation-{mid.lower()}"


def _technique_slug(tid: str) -> str:
    return "technique-" + tid.lower().replace(".", "-")


def _detection_slug(tid: str) -> str:
    return "detection-" + tid.lower().replace(".", "-")


def build() -> dict[str, list[str]]:
    DOCS.mkdir(parents=True, exist_ok=True)
    written: dict[str, list[str]] = {
        "technique": [],
        "mitigation": [],
        "detection": [],
        "family": [],
        "incident": [],
    }

    for mid, m in MITIGATIONS.items():
        _write(
            _mitigation_slug(mid),
            f"Mitigation {mid}: {m['name']}",
            _attack_source("mitigation", mid, m["name"]),
            m["body"],
        )
        written["mitigation"].append(_mitigation_slug(mid))

    for tid, t in TECHNIQUES.items():
        mits = ", ".join(f"{mid} ({MITIGATIONS[mid]['name']})" for mid in t["mitigations"])  # type: ignore[union-attr]
        body = f"{t['desc']}\n\nGeneric ATT&CK mitigations for this technique: {mits}."
        _write(
            _technique_slug(tid),
            f"Technique {tid}: {t['name']}",
            _attack_source("technique", tid, str(t["name"])),
            body,
        )
        written["technique"].append(_technique_slug(tid))

    for tid, lines in DETECTION.items():
        name = str(TECHNIQUES[tid]["name"])
        body = "Detection signals (descriptive, not a decision rule):\n\n" + "\n".join(
            f"- {line}" for line in lines
        )
        _write(
            _detection_slug(tid),
            f"Detecting {tid}: {name}",
            _attack_source("technique", tid, name),
            body,
        )
        written["detection"].append(_detection_slug(tid))

    families = yaml.safe_load(FAMILIES.read_text(encoding="utf-8"))
    for fam in families["families"]:
        fid = fam["id"]
        tech = fam["attack"]
        body = (
            f"{fam['name']} ({fam['covers']}). {fam['target']}\n\n"
            f"ATT&CK technique: {tech['technique']} — {tech['name']}."
        )
        attack_src = _attack_source("technique", tech["technique"], tech["name"])
        src = f"knowledge/attack_families.yaml (E1-02, families-v1.0); {attack_src}"
        _write(f"family-{fid.replace('_', '-')}", f"Attack family: {fam['name']}", src, body)
        written["family"].append(f"family-{fid.replace('_', '-')}")

    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    sources = catalog["sources"]
    seen: set[tuple[str, str, str]] = set()
    n = 0
    for action in catalog["actions"]:
        for cite in action["citations"]:
            key = (cite["source"], cite.get("locator", ""), cite["quote"])
            if key in seen:
                continue
            seen.add(key)
            n += 1
            quote = cite["quote"]
            body = f"> {quote}"
            if cite.get("translation"):
                body += f"\n>\n> (English: {cite['translation']})"
            source = f"{sources[cite['source']]} — {cite.get('locator', '')}".strip(" —")
            _write(
                f"incident-handling-{n:02d}",
                f"Incident-handling guidance ({cite['source']})",
                source,
                body,
            )
            written["incident"].append(f"incident-handling-{n:02d}")

    _write_index(written)
    return written


def _write_index(written: dict[str, list[str]]) -> None:
    n_incident = len(written["incident"])
    lines = [
        "# Knowledge base index (E5-02, SCRUM-34)",
        "",
        "GENERATED by `python -m knowledge.docs.build_kb`. A small, curated, **descriptive** corpus"
        " (record §5): attack techniques, generic defensive controls, detection signals and"
        " incident-handling guidance. Documents never name the correct catalog action for a family;"
        " that reasoning is left to the agent, so retrieval is not an answer key (inflating H2).",
        "",
        f"Total documents: **{sum(len(v) for v in written.values())}**.",
        "",
        "## Out of scope",
        "",
        "Vulnerability databases (CVE/NVD and similar) are **out of scope**: the agent reasons"
        " about attack behaviour and incident handling, not specific software vulnerabilities;"
        " including them would add weeks of curation and a confound to H2 (record §5). Also"
        " excluded: web scraping and any corpus beyond 200 documents.",
        "",
        "## Families → documents",
        "",
    ]
    for fid, fam in FAMILY_MAP.items():
        docs = [f"family-{fid.replace('_', '-')}.md"]
        docs += [f"{_technique_slug(t)}.md" for t in fam["techniques"]]  # type: ignore[union-attr]
        for t in fam["techniques"]:  # type: ignore[union-attr]
            docs += [f"{_mitigation_slug(m)}.md" for m in TECHNIQUES[t]["mitigations"]]  # type: ignore[index]
        docs.append(f"{_detection_slug(str(fam['detection']))}.md")
        unique = list(dict.fromkeys(docs))
        lines.append(f"- **{fid}** ({len(unique)} docs): " + ", ".join(unique))
    lines += [
        "",
        "## General incident-handling documents",
        "",
        "Not keyed to a family (descriptive IR principles, reused from the verified action-catalog"
        f" citations): `incident-handling-01.md` … `incident-handling-{n_incident:02d}.md`.",
    ]
    (DOCS / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    written = build()
    total = sum(len(v) for v in written.values())
    print(
        f"wrote {total} documents to {DOCS}: "
        + ", ".join(f"{k}={len(v)}" for k, v in written.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
