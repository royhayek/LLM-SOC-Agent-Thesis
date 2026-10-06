"""Attack family F5: botnet traffic (E1-12; ADR-0003).

PROVISIONAL. F5 replays a fixed slice of a published botnet capture (CICIoT2023 [8], or Bot-IoT
[6]), retargeted so the bot is the compromised testbed device D and the command-and-control
destination is a fixed non-routable address no testbed host answers. The capture slice is not
redistributed: `scenarios/botnet_manifest.yaml` names it and its SHA-256, and Roy places the
slice at the manifest's local path (ADR-0003). The runner verifies the digest, retargets with
`tcprewrite`, and replays with `tcpreplay` from the attacker container (source rewritten to D).
Expected sources: flows only.

Until the slice is provided and the manifest's SHA-256 is set, F5 cannot run, so its visibility
and repeatability tolerance are unset (its slow test skips). This family is not yet done.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Final

import yaml  # type: ignore[import-untyped]

from thesis.scenario.families.base import (
    ATTACKER_SERVICE,
    DEVICE_SERVICE,
    SERVICE_IP,
    ContainerAttackRunner,
)
from thesis.scenario.schedule import AttackFamily, Episode

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST: Final = REPO_ROOT / "scenarios" / "botnet_manifest.yaml"
PLACEHOLDER_SHA: Final = "UNVERIFIED-PLACEHOLDER"


class BotnetManifestError(RuntimeError):
    """The manifest is still provisional, or the local slice is missing or does not match."""


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def capture_path(manifest: dict[str, Any]) -> Path:
    p = Path(manifest["source"]["local_path"])
    return p if p.is_absolute() else REPO_ROOT / p


def verify_slice(manifest: dict[str, Any]) -> Path:
    """Return the local slice path once its SHA-256 matches the manifest, else raise."""
    expected = manifest["source"]["sha256"]
    if expected == PLACEHOLDER_SHA:
        raise BotnetManifestError(
            "botnet_manifest.yaml is provisional: its sha256 is a placeholder. Provide the "
            "dataset slice and set the real digest before running F5 (E1-12)."
        )
    path = capture_path(manifest)
    if not path.is_file():
        raise BotnetManifestError(f"botnet slice not found at {path} (set source.local_path)")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise BotnetManifestError(f"botnet slice SHA-256 {digest} does not match the manifest")
    return path


class BotnetRunner(ContainerAttackRunner):
    family = AttackFamily.BOTNET

    def service_for(self, episode: Episode) -> str:
        return ATTACKER_SERVICE

    def command(self, episode: Episode) -> str:
        manifest = load_manifest()
        verify_slice(manifest)  # refuses to build a command for a provisional/mismatched slice
        d_ip = SERVICE_IP[DEVICE_SERVICE[episode.target_device]]
        dst = manifest["retargeting"]["dst_ip"]
        pps = int(episode.parameters.get("replay_pps", manifest["retargeting"]["replay_pps"]))
        container_slice = "/tmp/botnet_slice.pcap"  # the slice is mounted here in the container
        retargeted = "/tmp/botnet_retargeted.pcap"
        # Rewrite the source to D and the destination to the non-routable C2, then replay from
        # the attacker container at a fixed rate. The slice is mounted read-only into the container.
        return (
            f"tcprewrite --infile={container_slice} --outfile={retargeted} "
            f"--dstipmap=0.0.0.0/0:{dst} --srcipmap=0.0.0.0/0:{d_ip} --fixcsum && "
            f"tcpreplay --intf1=eth0 --pps={pps} {retargeted}"
        )
