"""Attack family plug-ins (E1-08..E1-13). Each family is one `AttackFamilyRunner`.

`default_registry()` maps every implemented family to its runner; the scenario CLI
(`thesis.scenario.run`) uses it, so a schedule entry runs its family with no manual step.
Methods, parameters and targets come only from ADR-0003 (record §5: no custom attack code).
Every attack runs inside the isolated testbed, behind the E1-01 gate.
"""

from __future__ import annotations

from thesis.scenario.families.f1 import MqttPublishFloodRunner
from thesis.scenario.families.f2 import MqttBruteForceRunner
from thesis.scenario.families.f3 import PortScanRunner
from thesis.scenario.families.f4 import SshBruteForceRunner
from thesis.scenario.families.f6 import SynFloodRunner
from thesis.scenario.runner import AttackFamilyRunner
from thesis.scenario.schedule import AttackFamily

_RUNNERS: tuple[AttackFamilyRunner, ...] = (
    MqttPublishFloodRunner(),
    MqttBruteForceRunner(),
    PortScanRunner(),
    SshBruteForceRunner(),
    SynFloodRunner(),
)


def default_registry() -> dict[AttackFamily, AttackFamilyRunner]:
    """The family -> runner map the CLI uses. Each family appears at most once."""
    registry: dict[AttackFamily, AttackFamilyRunner] = {}
    for runner in _RUNNERS:
        if runner.family in registry:
            raise ValueError(f"two runners for {runner.family}")
        registry[runner.family] = runner
    return registry
