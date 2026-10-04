<!-- METHODS.md v1.0, Annex C. Moved verbatim from METHODS.md by SCRUM-24 [E0-03]. The text below the next line is frozen and unchanged (source: no tag (draft ASSUMPTIONs, E0-08)). -->

## Alert schema v0.1: device mapping (draft)

Ticket SCRUM-82 [E0-08], 2026-10-04. These are ASSUMPTIONs, not decisions. Like every section, this text is frozen when its ticket merges and is never edited. A later appended section supersedes it: E3-10 for ASSUMPTIONs 4 and 5, and E3-01 (alert schema v1) for anything else it changes. The rule is implemented once, in `subject_device()` (`thesis/schema/devices.py`).

Record §4.1: D is the non-infrastructure endpoint, and honeypot events key to the honeypot.

- **ASSUMPTION 1. Known devices only.** D must be a testbed device listed in the device table. An external IP, such as the attacker's, is never D.
- **ASSUMPTION 2. Infrastructure-only traffic.** Traffic between infrastructure hosts (gateway, broker, capture sidecar) has no subject device. Normalizers skip it with reason `infrastructure_only` (E3-03).
- **ASSUMPTION 3. No subject, no alert.** When `subject_device()` returns no device, the record is skipped with a counted reason. `Alert.subject_device` is always set.
- **ASSUMPTION 4. External to infrastructure (open).** Traffic from an external host to an infrastructure host, such as an MQTT flood on the broker, has no subject device in v0.1, so it forms no bundle. Whether this case needs an exception to §4.1 depends on the attack families (§10, "Which six attack families?"). E3-10 settles it before the corpus freeze.
- **ASSUMPTION 5. Device to device (open).** Traffic between two testbed devices raises `AmbiguousSubjectError` instead of choosing one. §4.1 does not cover this case. E3-10 settles it before the corpus freeze.
