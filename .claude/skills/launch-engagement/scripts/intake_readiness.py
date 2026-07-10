"""Resume artifact checks keyed to orchestration phase numbers."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import _paths  # noqa: F401

from intake_schema import Intake
from kit_registry import kit_deploy_root


def readiness_requirements(
    root: Path,
    project_path: str,
    starting_phase: int,
    delivery_lane: str,
    kit_name: str,
) -> list[str]:
    requirements: list[str] = []
    if starting_phase >= 1:
        requirements.extend(
            [
                f"{project_path}.md",
                project_path,
                f"{project_path}/SOP Runbook.md",
            ]
        )
    if starting_phase >= 2:
        requirements.append(f"{project_path}/Deliverables/01_Situation_Assessment.md")
    if starting_phase >= 3:
        requirements.append(f"{project_path}/Deliverables/02_KPI_Design.md")
    if starting_phase >= 4 and delivery_lane == "tool-built-bi":
        deploy_root = kit_deploy_root(root, kit_name)
        requirements.append(f"{project_path}/{deploy_root}/AI Build Runbook.md")
    if starting_phase >= 5 and delivery_lane == "tool-built-bi":
        deploy_root = kit_deploy_root(root, kit_name)
        requirements.append(f"{project_path}/{deploy_root}/Build Recipe (TEMPLATE).md")
    return requirements


def validate_readiness(root: Path, intake: Intake) -> list[str]:
    missing: list[str] = []
    for relative in readiness_requirements(
        root,
        intake.project_path,
        intake.starting_phase,
        intake.delivery_lane,
        intake.kit,
    ):
        if not (root / relative).exists():
            missing.append(relative)
    return missing
