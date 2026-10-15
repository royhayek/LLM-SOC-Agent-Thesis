---
title: 'Detecting T1498.001: Network Denial of Service: Direct Network Flood'
source: 'MITRE ATT&CK Enterprise v19.2, T1498.001 Network Denial of Service: Direct Network Flood, https://attack.mitre.org/techniques/T1498/001/ (accessed 2026-10-15)'
---

# Detecting T1498.001: Network Denial of Service: Direct Network Flood

Detection signals (descriptive, not a decision rule):

- A local process or service generating high-rate outbound traffic (TCP SYN, UDP, ICMP) beyond expected interface throughput or behavioural baselines.
- Excessive outbound packets toward one destination with abnormal resource consumption.
