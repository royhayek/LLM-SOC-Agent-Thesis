"""Attack family F5: botnet traffic (E1-12; ADR-0003).

F5 replays a fixed slice of a published botnet capture (CICIoT2023 [8] Mirai GREeth flood),
retargeted so the bot is the compromised testbed device D and the command-and-control
destination is a fixed non-routable address no testbed host answers. The capture slice is not
redistributed: `scenarios/botnet_manifest.yaml` names it and its SHA-256, and the slice is
placed at the manifest's local path (ADR-0003), mounted read-only into the attacker container
at `/slices`. The runner verifies the digest, retargets with `tcprewrite`, and replays with
`tcpreplay` from the attacker container (source rewritten to D). Expected sources: flows only.

The slice is git-ignored, so it is present on the machine that ran F5 but absent in CI: the
runner (and the slow test, `test_f5_run.py`) raise/skip with `BotnetManifestError` when the
slice is missing or its digest does not match the manifest.
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
    """The manifest SHA-256 is unset, or the local slice is missing or does not match."""


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
        verify_slice(manifest)  # refuses to build a command for a missing or mismatched slice
        d_ip = SERVICE_IP[DEVICE_SERVICE[episode.target_device]]
        dst = manifest["retargeting"]["dst_ip"]
        pps = int(episode.parameters.get("replay_pps", manifest["retargeting"]["replay_pps"]))
        # data/external is mounted read-only at /slices in the attacker container (compose).
        container_slice = f"/slices/{Path(manifest['source']['local_path']).name}"
        retargeted = "/tmp/botnet_retargeted.pcap"
        # Rewrite the source to D and the destination to the non-routable C2 (outer IP header only;
        # keying is by IP, record §4.1), then replay from the attacker container at a fixed rate.
        return (
            f"tcprewrite --infile={container_slice} --outfile={retargeted} "
            f"--dstipmap=0.0.0.0/0:{dst} --srcipmap=0.0.0.0/0:{d_ip} --fixcsum && "
            f"tcpreplay --intf1=eth0 --pps={pps} {retargeted}"
        )
