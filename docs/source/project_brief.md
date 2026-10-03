# LLM-Based Autonomous SOC Agent for IoT Cyberattack Detection and Response

This project focuses on the design of an autonomous AI agent for a lightweight Security Operations Center dedicated to IoT environments. The agent should be able to observe alerts, analyze logs, classify incidents, suggest actions, and generate structured security reports.

The system will act as an intelligent assistant for a security analyst. It may analyze MQTT anomalies, suspicious network flows, failed login attempts, honeypot logs, or abnormal behavior of connected devices.

The agent should not automatically execute dangerous actions. Its role is to assist, classify, explain, and recommend actions in a controlled and auditable way.

### Generative AI Dimension

The project is based on agentic AI and LLM-based reasoning. The system should use a Large Language Model to:

- interpret security alerts;
- correlate several logs;
- generate hypotheses about attacks;
- ask for missing information;
- produce incident reports;
- recommend mitigation actions;
- explain the reasoning in a structured format.

The agent can be connected to tools such as log parsers, anomaly detectors, MQTT monitors, or vulnerability databases. A major part of the work is to control the agent’s behavior and avoid unsafe or excessive autonomy.

### Expected Work

- Build a small IoT cybersecurity testbed.
- Generate normal and malicious scenarios.
- Collect alerts from rule-based or machine-learning-based detectors.
- Design an LLM-based agent workflow.
- Connect the agent to tools for log analysis and incident classification.
- Implement safety constraints and validation rules.
- Generate structured reports: incident type, severity, affected device, evidence, recommended action.
- Compare the agent’s decisions with predefined ground truth.
- Evaluate response quality, reliability, and robustness.

### Expected Outcome

A controlled LLM-based SOC assistant capable of analyzing IoT security alerts, classifying incidents, and generating clear and structured response recommendations.
