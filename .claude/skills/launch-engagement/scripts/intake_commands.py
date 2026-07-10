"""Build downstream skill commands from normalized intake."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import _paths  # noqa: F401

from engagement_constants import ADVISORY_ONLY_SKIP_PHASES, SOFTWARE_CODE_SKIP_PHASES
from intake_schema import Intake


def resolve_skill_script(root: Path, skill: str, filename: str) -> str:
    for base in (".claude/skills", ".agents/skills"):
        candidate = root / base / skill / "scripts" / filename
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return f".claude/skills/{skill}/scripts/{filename}"


def build_start_project_command(root: Path, intake: Intake) -> list[str]:
    command = [
        "python3",
        resolve_skill_script(root, "start-project", "build_project.py"),
        "create",
        "--kind",
        intake.kind,
        "--name",
        intake.name,
        "--industry",
        intake.industry,
        "--engagement-type",
        intake.engagement_type,
        "--data-classification",
        intake.data_classification,
        "--project-path",
        intake.project_path,
    ]
    for deliverable in intake.deliverables:
        command.extend(["--deliverable", deliverable])
    if intake.source:
        command.extend(["--source", intake.source])
    if intake.status:
        command.extend(["--status", intake.status])
    return command


def build_kit_command(root: Path, intake: Intake) -> list[str]:
    if intake.delivery_lane != "tool-built-bi":
        return []
    return [
        "python3",
        resolve_skill_script(root, "project-kit", "deploy_kit.py"),
        "deploy",
        "--kit",
        intake.kit,
        "--project",
        intake.project_path,
        "--dry-run",
    ]


def phase_plan(intake: Intake) -> list[int]:
    phases = list(range(intake.starting_phase, 10))
    if intake.kind == "portfolio" and not intake.include_portfolio_readout and 7 in phases:
        phases.remove(7)
    if intake.delivery_lane == "software-code":
        phases = [phase for phase in phases if phase not in SOFTWARE_CODE_SKIP_PHASES]
    if intake.delivery_lane == "advisory-only":
        phases = [phase for phase in phases if phase not in ADVISORY_ONLY_SKIP_PHASES]
    return phases
