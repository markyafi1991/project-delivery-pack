"""Validate and normalize launch-engagement intake payloads."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import _paths  # noqa: F401

from engagement_constants import (
    CLIENT_STATUSES,
    DATA_CLASSIFICATIONS,
    DELIVERY_LANES,
    ENGAGEMENT_TYPES,
    PROJECT_KINDS,
    SENSITIVE_PROJECT_PARTS,
    SOFTWARE_CODE_SKIP_PHASES,
)
from intake_readiness import validate_readiness
from intake_schema import Intake
from kit_registry import load_kits


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Name is required.")
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned or "\x00" in cleaned:
        raise ValueError("Name must be a plain name without path separators.")
    return cleaned


def normalize_relative_path(root: Path, raw_path: str) -> str:
    raw = Path(raw_path).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Project path must stay inside the vault root: {root}") from exc


def expected_area(kind: str) -> str:
    return "02_Clients" if kind == "client" else "04_Portfolio"


def default_project_path(kind: str, name: str) -> str:
    return f"{expected_area(kind)}/{name}"


def normalize_project_path(root: Path, kind: str, name: str, raw_path: str | None) -> str:
    relative = normalize_relative_path(root, raw_path) if raw_path else default_project_path(kind, name)
    parts = Path(relative).parts
    if not parts:
        raise ValueError("Project path cannot be empty.")
    if parts[0] != expected_area(kind):
        raise ValueError(
            f"{kind} project paths must live under {expected_area(kind)}/, got {relative!r}."
        )
    if len(parts) < 2:
        raise ValueError("Project path must include a project folder name.")
    if any(part in SENSITIVE_PROJECT_PARTS for part in parts):
        raise ValueError("Project path cannot point inside a confidential client subfolder.")
    if "data" in parts and "raw" in parts:
        raise ValueError("Project path cannot point inside data/raw.")
    return relative


def normalize_intake(payload: dict[str, object], root: Path) -> Intake:
    kind = payload.get("kind")
    name = payload.get("name")
    delivery_lane = payload.get("delivery_lane")

    if not kind or kind not in PROJECT_KINDS:
        raise ValueError(f"Required field 'kind' must be one of {PROJECT_KINDS}")
    if not name or not str(name).strip():
        raise ValueError("Required field 'name' cannot be empty.")
    name = validate_name(str(name))
    if not delivery_lane or delivery_lane not in DELIVERY_LANES:
        raise ValueError(f"Required field 'delivery_lane' must be one of {DELIVERY_LANES}")

    industry = payload.get("industry", "")
    engagement_type = payload.get("engagement_type", "analytics")
    if engagement_type not in ENGAGEMENT_TYPES:
        raise ValueError(f"Unsupported engagement_type: {engagement_type}")

    data_classification = payload.get("data_classification")
    if not data_classification:
        data_classification = "internal" if kind == "client" else "synthetic"
    if data_classification not in DATA_CLASSIFICATIONS:
        raise ValueError(f"Unsupported data classification: {data_classification}")
    if kind == "portfolio" and data_classification not in {"synthetic", "public"}:
        raise ValueError("Portfolio projects may use only synthetic or public data.")

    raw_deliverables = payload.get("deliverables") or []
    if isinstance(raw_deliverables, str):
        raw_deliverables = [raw_deliverables]
    deliverables = tuple(str(item).strip() for item in raw_deliverables if str(item).strip())
    if not deliverables:
        deliverables = ("Dashboard",)

    try:
        starting_phase = int(payload.get("starting_phase", 0))
    except (TypeError, ValueError):
        starting_phase = 0
    if starting_phase < 0 or starting_phase > 9:
        raise ValueError("starting_phase must be between 0 and 9.")

    kit = str(payload.get("kit", ""))
    if delivery_lane == "tool-built-bi":
        if not kit:
            raise ValueError("Tool-built BI engagements require 'kit'.")
        kits = load_kits(root)
        if kits and kit not in kits:
            raise ValueError(f"Unknown kit {kit!r}. Available kits: {', '.join(sorted(kits))}")
        if not kits:
            print(
                f"Warning: no kit manifests found under 06_Templates/Kits; "
                f"cannot verify kit {kit!r} exists before deploy.",
                file=sys.stderr,
            )
    elif kit:
        raise ValueError("'kit' is only valid when delivery_lane is tool-built-bi.")

    # Kit phases (3-6) never apply to Linear-tracked code builds, but phases 7-9
    # (readout/value/close) remain valid resume points — gate on the skip set, not >= 3.
    if delivery_lane == "software-code" and starting_phase in SOFTWARE_CODE_SKIP_PHASES:
        raise ValueError(
            "Software/code builds route to Linear; kit phases 3-6 do not apply. "
            "Resume at phase 0-2 or 7-9 instead."
        )

    source = str(payload.get("source", ""))
    if kind == "client" and not source:
        raise ValueError("Client engagements require 'source' for CRM registration.")

    status = str(payload.get("status", "")) or ("prospect" if kind == "client" else "active")
    if kind == "client" and status not in CLIENT_STATUSES:
        raise ValueError(f"Unsupported client status: {status}")

    raw_project_path = payload.get("project_path")
    project_path = normalize_project_path(root, kind, name, raw_project_path if raw_project_path else None)

    include_portfolio_readout = bool(payload.get("include_portfolio_readout", False))

    intake = Intake(
        kind=kind,
        name=name,
        industry=str(industry).strip(),
        engagement_type=engagement_type,
        data_classification=data_classification,
        deliverables=deliverables,
        delivery_lane=delivery_lane,
        project_path=project_path,
        starting_phase=starting_phase,
        kit=kit,
        source=source,
        status=status,
        include_portfolio_readout=include_portfolio_readout,
    )
    missing = validate_readiness(root, intake)
    if missing:
        lines = "\n  - ".join(missing)
        raise ValueError(
            "Starting phase is not ready; required prior-phase artifacts are missing:\n  - "
            + lines
        )
    return intake
