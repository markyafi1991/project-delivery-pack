#!/usr/bin/env python3
"""Create project scaffolds and generate project-specific SOP runbooks."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

_VAULT_ROOT = Path(__file__).resolve().parents[3]
if str(_VAULT_ROOT / "scripts") not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_VAULT_ROOT / "scripts"))

try:
    from engagement_constants import DATA_CLASSIFICATIONS, ENGAGEMENT_TYPES, PROJECT_KINDS
except ImportError:
    DATA_CLASSIFICATIONS = (
        "synthetic",
        "public",
        "internal",
        "confidential",
        "financial",
        "phi",
    )
    ENGAGEMENT_TYPES = ("analytics", "automation", "advisory")
    PROJECT_KINDS = ("client", "portfolio")


@dataclass(frozen=True)
class ProjectMetadata:
    kind: str
    name: str
    industry: str
    engagement_type: str
    data_classification: str
    deliverables: tuple[str, ...]
    source: str = ""
    status: str = ""
    started: str = ""
    project_path: str = ""


@dataclass(frozen=True)
class Procedure:
    title: str
    path: str
    phase: str
    reason: str


PROCEDURES = {
    "lead_qualification": Procedure(
        "SOP-03: Lead Qualification & Scoping",
        "01_Operations/SOPs/SOP-03_Lead_Qualification.md",
        "Before work begins",
        "Confirm fit, scope, and commercial guardrails.",
    ),
    "client_onboarding": Procedure(
        "SOP - Client Onboarding",
        "01_Operations/SOPs/SOP - Client Onboarding.md",
        "Before work begins",
        "Run the standard relationship and kickoff process.",
    ),
    "secure_onboarding": Procedure(
        "SOP-01: Secure Client Onboarding & Data Access",
        "01_Operations/SOPs/SOP-01_Secure_Client_Onboarding.md",
        "Before work begins",
        "Establish legal, access, credential, and communication controls.",
    ),
    "data_handling": Procedure(
        "SOP-02: HIPAA & Financial Data Handling Protocol",
        "01_Operations/SOPs/SOP-02_HIPAA_Data_Handling.md",
        "During execution",
        "Apply enhanced handling controls for sensitive client data.",
    ),
    "project_delivery": Procedure(
        "SOP - Project Delivery",
        "01_Operations/SOPs/SOP - Project Delivery.md",
        "During execution",
        "Use the standard delivery lifecycle, scope controls, and close process.",
    ),
    "qa_handoff": Procedure(
        "SOP-04: Report QA & Delivery Handoff",
        "01_Operations/SOPs/SOP-04_Report_QA_Handoff.md",
        "Before close or publish",
        "Apply the report QA gate and package the handoff.",
    ),
    "contingency": Procedure(
        "SOP-06: Contingency & Incident Response Protocol",
        "01_Operations/SOPs/SOP-06_Contingency_Protocol.md",
        "During execution",
        "Prepare the incident, scope-creep, and business-continuity response.",
    ),
    "portfolio": Procedure(
        "Portfolio Excellence Playbook",
        "04_Portfolio/Portfolio Excellence Playbook.md",
        "Before work begins",
        "Pass the admission test and build a buyer-readable proof asset.",
    ),
    "synthetic_data": Procedure(
        "Synthetic Data Generation",
        "04_Portfolio/Synthetic Data Generation.md",
        "During execution",
        "Keep the portfolio artifact synthetic and reproducible.",
    ),
}


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def wiki_link(path: str) -> str:
    return f"[[{Path(path).stem}]]"


# Exact strings render_client_dossier substitutes in the live client dossier template
# (06_Templates/Notes/Client Dossier Template.md). If the template wording changes, these
# stop matching; replace_anchor raises instead of silently emitting an un-substituted dossier.
# A test asserts every anchor is still present in the real template.
CLIENT_DOSSIER_ANCHORS = (
    "# (Client name)",
    "| Industry / niche | |",
    "| Source | (Upwork / referral / direct) |",
    "| Status | prospect / proposal-sent / active / delivered / dormant |",
    "| Folder | `02_Clients/.../` |",
    "| Proposal | `03_Proposals/...` |",
    "## Context",
)


def replace_anchor(body: str, old: str, new: str) -> str:
    if old not in body:
        raise ValueError(
            f"Client dossier template anchor not found: {old!r}. "
            "06_Templates/Notes/Client Dossier Template.md changed; update "
            "CLIENT_DOSSIER_ANCHORS and render_client_dossier to match."
        )
    return body.replace(old, new, 1)


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Project name cannot be empty.")
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned or "\x00" in cleaned:
        raise ValueError("Project name must be a plain name without path separators.")
    return cleaned


def validate_metadata(metadata: ProjectMetadata) -> None:
    validate_name(metadata.name)
    if metadata.kind not in PROJECT_KINDS:
        raise ValueError(f"Unsupported project kind: {metadata.kind}")
    if metadata.engagement_type not in ENGAGEMENT_TYPES:
        raise ValueError(f"Unsupported engagement type: {metadata.engagement_type}")
    if metadata.data_classification not in DATA_CLASSIFICATIONS:
        raise ValueError(f"Unsupported data classification: {metadata.data_classification}")
    if metadata.kind == "portfolio" and metadata.data_classification not in {"synthetic", "public"}:
        raise ValueError(
            "Portfolio projects may use only synthetic or public data. "
            "Real client, confidential, financial, or PHI data belongs outside 04_Portfolio."
        )
    if not metadata.deliverables:
        raise ValueError("Provide at least one deliverable.")


def is_report_work(metadata: ProjectMetadata) -> bool:
    text = " ".join(metadata.deliverables).lower()
    terms = ("dashboard", "report", "power bi", "pbix", "semantic model", "analytics")
    return metadata.engagement_type == "analytics" or any(term in text for term in terms)


def applicable_procedures(metadata: ProjectMetadata) -> tuple[list[Procedure], list[str]]:
    keys: list[str]
    gaps: list[str] = []
    if metadata.kind == "client":
        keys = [
            "lead_qualification",
            "client_onboarding",
            "secure_onboarding",
            "project_delivery",
            "contingency",
        ]
        if metadata.data_classification in {"confidential", "financial", "phi"}:
            keys.append("data_handling")
        if is_report_work(metadata):
            keys.append("qa_handoff")
        if metadata.engagement_type == "automation":
            gaps.append(
                "No canonical automation-delivery SOP exists. Use the Project Delivery SOP "
                "and capture automation-specific controls after this engagement."
            )
    else:
        keys = ["portfolio", "project_delivery"]
        if metadata.data_classification == "synthetic":
            keys.append("synthetic_data")
        if is_report_work(metadata):
            keys.append("qa_handoff")
        if metadata.engagement_type == "automation":
            gaps.append(
                "No canonical portfolio automation-demo SOP exists. Capture the reusable "
                "build and verification pattern after publishing."
            )
    return [PROCEDURES[key] for key in keys], gaps


def project_paths(root: Path, metadata: ProjectMetadata) -> tuple[Path, Path, Path]:
    area_name = "02_Clients" if metadata.kind == "client" else "04_Portfolio"
    if metadata.project_path:
        raw_path = Path(metadata.project_path)
        candidate = raw_path if raw_path.is_absolute() else root / raw_path
        folder = candidate.resolve()
        try:
            relative = folder.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"Project path must stay inside the vault root: {root}") from exc
        if not relative.parts or relative.parts[0] != area_name:
            raise ValueError(
                f"{metadata.kind} project path must live under {area_name}/, got "
                f"{relative.as_posix()!r}."
            )
        if len(relative.parts) < 2:
            raise ValueError("Project path must include a project folder name.")
        if any(part in {"client-comms", "contracts", "intake"} for part in relative.parts):
            raise ValueError("Project path cannot point inside a confidential client subfolder.")
        if "data" in relative.parts and "raw" in relative.parts:
            raise ValueError("Project path cannot point inside data/raw.")
        dossier = folder.with_suffix(".md")
        return dossier, folder, folder / "SOP Runbook.md"

    area = root / area_name
    dossier = area / f"{metadata.name}.md"
    folder = area / metadata.name
    return dossier, folder, folder / "SOP Runbook.md"


def render_frontmatter(metadata: ProjectMetadata, note_type: str, today: str) -> str:
    tags = ["clients" if metadata.kind == "client" else "portfolio"]
    if note_type == "sop":
        tags.append("sop")
    lines = [
        "---",
        f"type: {note_type}",
        f"status: {metadata.status}",
        f"project-kind: {metadata.kind}",
        f"engagement-type: {metadata.engagement_type}",
        f"data-classification: {metadata.data_classification}",
        f"industry: {yaml_quote(metadata.industry)}",
    ]
    if metadata.project_path:
        lines.append(f"project-path: {yaml_quote(metadata.project_path)}")
    lines.append("deliverables:")
    lines.extend(f"  - {yaml_quote(item)}" for item in metadata.deliverables)
    if note_type in ("client", "portfolio"):
        lines.append(
            "client-type: real"
            if metadata.kind == "client"
            else (
                "client-type: synthetic-portfolio"
                if metadata.data_classification == "synthetic"
                else "client-type: portfolio"
            )
        )
    if metadata.kind == "client":
        lines.extend(
            [
                f"source: {yaml_quote(metadata.source)}",
                f"started: {yaml_quote(metadata.started)}",
                "revenue: 0",
            ]
        )
    lines.extend(
        [
            f"created: {today}",
            f"updated: {today}",
            "tags:",
            *(f"  - {tag}" for tag in tags),
            "---",
        ]
    )
    return "\n".join(lines)


def render_client_dossier(root: Path, metadata: ProjectMetadata, folder: Path, today: str) -> str:
    template_path = root / "06_Templates/Notes/Client Dossier Template.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Required client dossier template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    frontmatter_end = template.find("\n---\n", 4)
    if not template.startswith("---\n") or frontmatter_end == -1:
        raise ValueError(f"Client dossier template has invalid frontmatter: {template_path}")
    body = template[frontmatter_end + 5 :].lstrip()
    body = replace_anchor(body, "# (Client name)", f"# {metadata.name}")
    body = replace_anchor(
        body, "| Industry / niche | |", f"| Industry / niche | {metadata.industry or 'TBD'} |"
    )
    body = replace_anchor(
        body,
        "| Source | (Upwork / referral / direct) |",
        f"| Source | {metadata.source or 'TBD'} |",
    )
    body = replace_anchor(
        body,
        "| Status | prospect / proposal-sent / active / delivered / dormant |",
        f"| Status | {metadata.status} |",
    )
    body = replace_anchor(
        body,
        "| Folder | `02_Clients/.../` |",
        f"| Folder | `{folder.relative_to(folder.parents[1])}/` |",
    )
    body = replace_anchor(
        body,
        "| Proposal | `03_Proposals/...` |",
        (
            f"| Proposal | `03_Proposals/...` |\n"
            f"| Engagement type | {metadata.engagement_type} |\n"
            f"| Data classification | {metadata.data_classification} |"
        ),
    )
    deliverables = "\n".join(f"- {item}" for item in metadata.deliverables)
    body = replace_anchor(body, "## Context", f"## Deliverables\n\n{deliverables}\n\n## Context")
    body = body.rstrip() + "\n\n## Operating runbook\n\nSee [[SOP Runbook]].\n"
    return f"{render_frontmatter(metadata, 'client', today)}\n\n{body}"


def render_portfolio_dossier(metadata: ProjectMetadata, folder: Path, today: str) -> str:
    deliverables = "\n".join(f"- {item}" for item in metadata.deliverables)
    evidence_label = (
        "Synthetic portfolio demonstration"
        if metadata.data_classification == "synthetic"
        else "Public-data portfolio demonstration"
    )
    return f"""{render_frontmatter(metadata, "portfolio", today)}

# {metadata.name} (portfolio build)

> [!warning] **{evidence_label}, not a real client engagement.**
> Use only {metadata.data_classification} data. Never include real client information.

## Strategic job

(What reason to hire Algonquin Consult will this prove?)

## Audience and decision

(Who uses it, and what decision becomes easier?)

## Industry

{metadata.industry or "TBD"}

## Deliverables

{deliverables}

## Folder

`{folder.relative_to(folder.parents[1])}/`

## Operating runbook

See [[SOP Runbook]].
"""


def render_runbook(
    root: Path,
    metadata: ProjectMetadata,
    procedures: Iterable[Procedure],
    gaps: list[str],
    today: str,
) -> str:
    procedures = list(procedures)
    missing = [procedure for procedure in procedures if not (root / procedure.path).exists()]
    grouped: dict[str, list[Procedure]] = {}
    for procedure in procedures:
        grouped.setdefault(procedure.phase, []).append(procedure)

    frontmatter = render_frontmatter(metadata, "sop", today)
    sections: list[str] = []
    for phase in ("Before work begins", "During execution", "Before close or publish"):
        phase_procedures = grouped.get(phase, [])
        if not phase_procedures:
            continue
        lines = [f"## {phase}", ""]
        for procedure in phase_procedures:
            exists = (root / procedure.path).exists()
            marker = "Required" if exists else "MISSING"
            lines.append(
                f"- [ ] **{marker}:** {wiki_link(procedure.path)} — {procedure.reason}"
            )
        sections.append("\n".join(lines))

    gap_lines = list(gaps)
    gap_lines.extend(
        f"Expected canonical procedure is missing: `{procedure.path}`." for procedure in missing
    )
    gap_text = "\n".join(f"- {gap}" for gap in gap_lines) if gap_lines else "- None identified."
    deliverables = "\n".join(f"- {item}" for item in metadata.deliverables)
    sections_text = "\n\n".join(sections)

    return f"""{frontmatter}

# SOP Runbook — {metadata.name}

> [!important] Generated by `.claude/skills/start-project/scripts/build_project.py`.
> Regenerate this file with `sync`; do not place durable project notes here.
> Canonical SOPs remain approval-controlled in `01_Operations/SOPs/`.

## Applicability decision

| Field | Value |
|---|---|
| Project | [[{metadata.name}]] |
| Kind | {metadata.kind} |
| Engagement type | {metadata.engagement_type} |
| Data classification | {metadata.data_classification} |

### Deliverables

{deliverables}

{sections_text}

## Procedure gaps

{gap_text}

## SOP improvement capture

- [ ] Record exceptions where a canonical procedure did not fit the work.
- [ ] Record missing controls, checklists, or handoff steps discovered during execution.
- [ ] Complete the project post-mortem before close.
- [ ] Draft proposed canonical SOP changes with evidence from this project.
- [ ] Obtain owner approval before editing canonical SOPs.
"""


def replace_placeholders(text: str, name: str, today: str) -> str:
    return text.replace("{{Client Name}}", name).replace("{{Date}}", today)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def create_project(root: Path, metadata: ProjectMetadata, dry_run: bool = False) -> list[str]:
    root = root.resolve()
    validate_metadata(metadata)
    dossier, folder, runbook = project_paths(root, metadata)
    if dossier.exists() or folder.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing project: {dossier} or {folder}. Use sync instead."
        )

    procedures, gaps = applicable_procedures(metadata)
    today = date.today().isoformat()
    messages = [
        f"Dossier: {dossier.relative_to(root)}",
        f"Project folder: {folder.relative_to(root)}",
        f"SOP runbook: {runbook.relative_to(root)}",
        "Applicable procedures: " + ", ".join(procedure.title for procedure in procedures),
    ]
    if gaps:
        messages.append("Procedure gaps: " + " | ".join(gaps))
    if dry_run:
        return messages

    runbook_content = render_runbook(root, metadata, procedures, gaps, today)
    copied_templates: dict[str, str] = {}
    if metadata.kind == "client":
        dossier_content = render_client_dossier(root, metadata, folder, today)
        template_dir = root / "02_Clients/_Client_Template"
        for filename in (
            "Client Folder README.md",
            "Onboarding Checklist.md",
            "Offboarding Checklist.md",
        ):
            source = template_dir / filename
            if not source.exists():
                raise FileNotFoundError(f"Required client folder template not found: {source}")
            copied_templates[filename] = replace_placeholders(
                source.read_text(encoding="utf-8"), metadata.name, today
            )
    else:
        dossier_content = render_portfolio_dossier(metadata, folder, today)

    folder.mkdir(parents=True)
    if metadata.kind == "client":
        for relative in (
            "intake",
            "contracts",
            "client-comms",
            "data/raw",
            "models",
            "docs",
            "reports",
            "exports",
        ):
            (folder / relative).mkdir(parents=True, exist_ok=True)
        for filename, content in copied_templates.items():
            write_text(folder / filename, content)
    else:
        for relative in ("project-plans", "data/raw", "models", "docs", "reports", "exports"):
            (folder / relative).mkdir(parents=True, exist_ok=True)

    write_text(dossier, dossier_content)
    write_text(runbook, runbook_content)
    return messages


def parse_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in text[4:end].splitlines():
        if raw_line.startswith("  - ") and current_list:
            value = raw_line[4:].strip().strip('"')
            cast_list = data.setdefault(current_list, [])
            if isinstance(cast_list, list):
                cast_list.append(value)
            continue
        match = re.match(r"^([a-z0-9-]+):(?:\s*(.*))?$", raw_line)
        if not match:
            current_list = None
            continue
        key, raw_value = match.groups()
        raw_value = (raw_value or "").strip()
        if not raw_value:
            data[key] = []
            current_list = key
        else:
            data[key] = raw_value.strip('"')
            current_list = None
    return data


def metadata_from_sync_args(args: argparse.Namespace, root: Path) -> tuple[ProjectMetadata, Path]:
    root = root.resolve()
    dossier = (
        (root / args.dossier).resolve()
        if not Path(args.dossier).is_absolute()
        else Path(args.dossier)
    )
    dossier = dossier.resolve()
    try:
        dossier.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Dossier must be inside the vault root: {root}") from exc
    if not dossier.exists():
        raise FileNotFoundError(f"Dossier not found: {dossier}")
    dossier_data = parse_frontmatter(dossier)
    folder = dossier.with_suffix("")
    if not folder.exists():
        underscore_folder = dossier.with_name(dossier.stem.replace(" ", "_"))
        folder = underscore_folder if underscore_folder.exists() else folder
    runbook_data = (
        parse_frontmatter(folder / "SOP Runbook.md")
        if (folder / "SOP Runbook.md").exists()
        else {}
    )

    def choose(name: str, default: str = "") -> str:
        arg_name = "kind" if name == "project-kind" else name.replace("-", "_")
        arg_value = getattr(args, arg_name, None)
        return str(arg_value or dossier_data.get(name) or runbook_data.get(name) or default)

    deliverables = tuple(
        args.deliverable
        or dossier_data.get("deliverables")
        or runbook_data.get("deliverables")
        or ()
    )
    kind_default = "client" if "02_Clients" in dossier.parts else "portfolio"
    kind = choose("project-kind", kind_default)
    metadata = ProjectMetadata(
        kind=kind,
        name=dossier.stem,
        industry=choose("industry"),
        engagement_type=choose("engagement-type", "analytics"),
        data_classification=choose(
            "data-classification", "synthetic" if kind == "portfolio" else "internal"
        ),
        deliverables=deliverables,
        source=choose("source"),
        status=choose("status", "prospect" if kind == "client" else "active"),
        started=choose("started"),
    )
    return metadata, folder


def sync_project(root: Path, args: argparse.Namespace, dry_run: bool = False) -> list[str]:
    root = root.resolve()
    metadata, folder = metadata_from_sync_args(args, root)
    validate_metadata(metadata)
    procedures, gaps = applicable_procedures(metadata)
    runbook = folder / "SOP Runbook.md"
    messages = [
        f"SOP runbook: {runbook.relative_to(root)}",
        "Applicable procedures: " + ", ".join(procedure.title for procedure in procedures),
    ]
    if gaps:
        messages.append("Procedure gaps: " + " | ".join(gaps))
    if not dry_run:
        write_text(runbook, render_runbook(root, metadata, procedures, gaps, date.today().isoformat()))
    return messages


def add_metadata_arguments(parser: argparse.ArgumentParser, required: bool) -> None:
    parser.add_argument("--kind", choices=PROJECT_KINDS, required=required)
    parser.add_argument("--industry", default="" if required else None)
    parser.add_argument("--engagement-type", choices=ENGAGEMENT_TYPES, required=required)
    parser.add_argument("--data-classification", choices=DATA_CLASSIFICATIONS, required=required)
    parser.add_argument("--deliverable", action="append", help="Repeat for each deliverable.")
    parser.add_argument("--source", default="" if required else None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--started", default="" if required else None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Vault root. Defaults to the current directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a new project scaffold and SOP runbook.")
    create.add_argument("--name", required=True)
    add_metadata_arguments(create, required=True)
    create.add_argument("--project-path", default="")
    create.add_argument("--dry-run", action="store_true")

    sync = subparsers.add_parser("sync", help="Regenerate an existing project's SOP runbook.")
    sync.add_argument("--dossier", required=True)
    add_metadata_arguments(sync, required=False)
    sync.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.command == "create":
            status = args.status or ("prospect" if args.kind == "client" else "active")
            metadata = ProjectMetadata(
                kind=args.kind,
                name=validate_name(args.name),
                industry=args.industry,
                engagement_type=args.engagement_type,
                data_classification=args.data_classification,
                deliverables=tuple(args.deliverable or ()),
                source=args.source,
                status=status,
                started=args.started,
                project_path=args.project_path,
            )
            messages = create_project(root, metadata, args.dry_run)
        else:
            messages = sync_project(root, args, args.dry_run)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print("\n".join(messages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
