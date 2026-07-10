"""Validate and normalize Launch Engagement intake before Phase 0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import _paths  # noqa: F401

from engagement_constants import STATE_DIR, STATE_FILENAME, WORK_SURFACES
from intake_commands import build_kit_command, build_start_project_command, phase_plan
from intake_normalize import normalize_intake
from intake_schema import IntakeResult


def build_result(root: Path, intake) -> IntakeResult:
    state_path = (root / STATE_DIR / STATE_FILENAME).as_posix()
    return IntakeResult(
        intake=intake,
        dossier_path=f"{intake.project_path}.md",
        work_surface=WORK_SURFACES[intake.delivery_lane],
        start_project_command=build_start_project_command(root, intake),
        kit_deploy_dry_run_command=build_kit_command(root, intake),
        phases=phase_plan(intake),
        state_path=state_path,
    )


def load_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            raise FileNotFoundError(f"Input file not found: {args.file}")
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    if args.json:
        return json.loads(args.json)
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    raise ValueError("Provide intake JSON via --file, --json, or stdin.")


def persist_state(root: Path, result: IntakeResult) -> None:
    state_file = root / STATE_DIR / STATE_FILENAME
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Vault root. Defaults to current directory.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", help="Path to JSON file containing intake parameters.")
    source.add_argument("--json", help="Inline JSON intake payload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        payload = load_payload(args)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    try:
        intake = normalize_intake(payload, root)
    except ValueError as exc:
        parser.error(str(exc))

    result = build_result(root, intake)
    try:
        persist_state(root, result)
    except OSError as exc:
        print(f"Warning: Failed to write state to {result.state_path}: {exc}", file=sys.stderr)

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
