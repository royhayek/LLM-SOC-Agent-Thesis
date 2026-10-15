---
title: 'Detecting T1046: Network Service Discovery'
source: 'MITRE ATT&CK Enterprise v19.2, T1046 Network Service Discovery, https://attack.mitre.org/techniques/T1046/ (accessed 2026-10-15)'
---

# Detecting T1046: Network Service Discovery

Detection signals (descriptive, not a decision rule):

- A process or host making rapid connections to many services or hosts in a short window.
- Sequential probing of destination IPs or ports visible in netflow or packet telemetry.
