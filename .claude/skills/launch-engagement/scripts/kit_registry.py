"""Load kit manifests from 06_Templates/Kits/."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KitInfo:
    name: str
    deploy_root: str


def load_kits(root: Path) -> dict[str, KitInfo]:
    kits_root = root / "06_Templates" / "Kits"
    if not kits_root.exists():
        return {}

    kits: dict[str, KitInfo] = {}
    for child in kits_root.iterdir():
        manifest = child / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        name = str(data.get("kit") or child.name)
        deploy_root = str(data.get("deploy_root") or child.name)
        kits[name] = KitInfo(name=name, deploy_root=deploy_root)
    return kits


def kit_deploy_root(root: Path, kit_name: str) -> str:
    kits = load_kits(root)
    if kit_name not in kits:
        raise ValueError(f"Unknown kit {kit_name!r}. Available kits: {', '.join(sorted(kits))}")
    return kits[kit_name].deploy_root
