---
title: 'Detecting T1499.002: Endpoint Denial of Service: Service Exhaustion Flood'
source: 'MITRE ATT&CK Enterprise v19.2, T1499.002 Endpoint Denial of Service: Service Exhaustion Flood, https://attack.mitre.org/techniques/T1499/002/ (accessed 2026-10-15)'
---

# Detecting T1499.002: Endpoint Denial of Service: Service Exhaustion Flood

Detection signals (descriptive, not a decision rule):

- High-frequency repetitive requests from a single or small set of source IPs to a service.
- A spike in inbound connections that exhausts worker threads or server CPU and memory.
