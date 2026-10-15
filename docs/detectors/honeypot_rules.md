# Honeypot rules (E4-05, SCRUM-58)

Rule-based detector (record §6.2). Honeypot activity is malicious by definition, so every alert
scores above zero; the rules separate the *type* of activity. Thresholds come from each rule's
meaning, not from the attack families (no label leakage).

| Rule | Condition | Label | Score |
|---|---|---|---|
| Command execution | event is a command (`command.input` / `command.failed`) | `command_execution` | 1.0 |
| Successful login | event is `login_success` | `login_success` | 0.9 |
| Brute force | `login_failed`, and the session has ≥ 10 failed logins | `brute_force` | 0.8 |
| Failed login | `login_failed`, fewer than 10 in the session | `failed_login` | 0.5 |
| Contact | session connect/close, client version/kex | `contact` | 0.3 |

Brute force threshold: **10 failed logins per session** — repeated guessing, independent of any
family. `apply_rules()` counts failed logins per `session_id` and scores every alert.
