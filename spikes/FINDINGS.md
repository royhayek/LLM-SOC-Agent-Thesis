# E0-01 findings: walking-skeleton spike

## Source states (input for the alert schema, E0-08)

A bundle's `sources` block gives each source one of three states:

- `active`: the source is running and sent alerts in this window.
- `no_alerts`: the source is running and saw nothing in this window.
- `not_in_config`: the source is switched off in this experiment condition. Reserved; not used in the spike bundle.

The spike bundle uses `active` for honeypot and flows, and `no_alerts` for MQTT.
