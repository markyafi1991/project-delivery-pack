"""Intake dataclasses for launch-engagement."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Intake:
    kind: str
    name: str
    industry: str
    engagement_type: str
    data_classification: str
    deliverables: tuple[str, ...]
    delivery_lane: str
    project_path: str
    starting_phase: int
    kit: str = ""
    source: str = ""
    status: str = ""
    include_portfolio_readout: bool = False


@dataclass(frozen=True)
class IntakeResult:
    intake: Intake
    dossier_path: str
    work_surface: str
    start_project_command: list[str]
    kit_deploy_dry_run_command: list[str]
    phases: list[int]
    state_path: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self.intake)
        payload["deliverables"] = list(self.intake.deliverables)
        payload["dossier_path"] = self.dossier_path
        payload["work_surface"] = self.work_surface
        payload["start_project_command"] = self.start_project_command
        payload["kit_deploy_dry_run_command"] = self.kit_deploy_dry_run_command
        payload["phases"] = self.phases
        payload["state_path"] = self.state_path
        return payload
