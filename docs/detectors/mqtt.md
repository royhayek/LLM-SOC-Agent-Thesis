# MQTT statistical-threshold detector (E4-04, SCRUM-48)

Thresholds fitted on benign training MQTT only (E2-01). Each alert scores in [0, 1]:
publish on a channel never seen in benign traffic (the flood channel) scores 1.0; a payload above the benign p99 scores 0.5-1.0; a refused login scores 0.4 (below the 0.5 decision threshold, so benign irregularities are not anomalies); normal publishes and connects score 0.0.

- Benign channels: ['status', 'telemetry']
- Payload p99: 196.0 bytes
- **False-positive rate on held-out benign training windows: 0.0119** (13/1088 alerts scored above 0.5).
