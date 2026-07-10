from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("validate_intake", SCRIPT_DIR / "validate_intake.py")
assert SPEC and SPEC.loader
validate_intake = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_intake
SPEC.loader.exec_module(validate_intake)

intake_normalize = importlib.import_module("intake_normalize")


class ValidateIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        kit_dir = self.root / "06_Templates/Kits/Power BI Project Kit"
        kit_dir.mkdir(parents=True)
        (kit_dir / "manifest.json").write_text(
            '{"kit": "Power BI Project Kit", "deploy_root": "Power BI Kit", "version": "1.0"}',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_valid_tool_built_portfolio_outputs_commands(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Variance Pack",
            "industry": "Fund administration",
            "engagement_type": "analytics",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "project_path": "04_Portfolio/PowerBI_Variance_Pack",
            "deliverables": ["Power BI dashboard"],
        }

        intake = intake_normalize.normalize_intake(payload, self.root)
        result = validate_intake.build_result(self.root, intake)

        self.assertEqual(intake.data_classification, "synthetic")
        self.assertEqual(intake.project_path, "04_Portfolio/PowerBI_Variance_Pack")
        self.assertEqual(result.work_surface, "ClickUp Portfolio Projects")
        self.assertIn("--project-path", result.start_project_command)
        self.assertEqual(result.kit_deploy_dry_run_command[-1], "--dry-run")
        self.assertNotIn(7, result.phases)

    def test_rejects_sensitive_portfolio_data(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Unsafe Demo",
            "engagement_type": "analytics",
            "data_classification": "financial",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "deliverables": ["Dashboard"],
        }

        with self.assertRaisesRegex(ValueError, "synthetic or public"):
            intake_normalize.normalize_intake(payload, self.root)

    def test_rejects_software_code_with_kit(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Reporting Robot",
            "engagement_type": "automation",
            "delivery_lane": "software-code",
            "kit": "Power BI Project Kit",
            "deliverables": ["Python reporting pipeline"],
        }

        with self.assertRaisesRegex(ValueError, "only valid when delivery_lane is tool-built-bi"):
            intake_normalize.normalize_intake(payload, self.root)

    def test_client_requires_source(self) -> None:
        payload = {
            "kind": "client",
            "name": "Acme Funds",
            "engagement_type": "analytics",
            "data_classification": "financial",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "deliverables": ["Dashboard"],
        }

        with self.assertRaisesRegex(ValueError, "require 'source'"):
            intake_normalize.normalize_intake(payload, self.root)

    def test_rejects_resume_when_required_artifacts_are_missing(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Missing Prior Work",
            "engagement_type": "analytics",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "deliverables": ["Dashboard"],
            "starting_phase": 2,
        }

        with self.assertRaisesRegex(ValueError, "required prior-phase artifacts"):
            intake_normalize.normalize_intake(payload, self.root)

    def test_resume_phase_one_accepts_existing_scaffold(self) -> None:
        (self.root / "04_Portfolio/Resume Demo").mkdir(parents=True)
        (self.root / "04_Portfolio/Resume Demo.md").write_text("# Demo\n", encoding="utf-8")
        (self.root / "04_Portfolio/Resume Demo/SOP Runbook.md").write_text(
            "# Runbook\n", encoding="utf-8"
        )
        payload = {
            "kind": "portfolio",
            "name": "Resume Demo",
            "engagement_type": "analytics",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "deliverables": ["Dashboard"],
            "starting_phase": 1,
        }

        intake = intake_normalize.normalize_intake(payload, self.root)

        self.assertEqual(intake.starting_phase, 1)

    def test_readiness_uses_kit_deploy_root(self) -> None:
        project = self.root / "04_Portfolio/Kit Path Demo"
        project.mkdir(parents=True)
        (self.root / "04_Portfolio/Kit Path Demo.md").write_text("# Demo\n", encoding="utf-8")
        (project / "SOP Runbook.md").write_text("# Runbook\n", encoding="utf-8")
        (project / "Deliverables").mkdir()
        (project / "Deliverables/01_Situation_Assessment.md").write_text("# SA\n", encoding="utf-8")
        (project / "Deliverables/02_KPI_Design.md").write_text("# KPI\n", encoding="utf-8")
        kit_root = project / "Power BI Kit"
        kit_root.mkdir()
        (kit_root / "AI Build Runbook.md").write_text("# Runbook\n", encoding="utf-8")

        payload = {
            "kind": "portfolio",
            "name": "Kit Path Demo",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "starting_phase": 4,
        }

        intake = intake_normalize.normalize_intake(payload, self.root)
        self.assertEqual(intake.starting_phase, 4)

    def test_main_writes_state_file(self) -> None:
        payload_path = self.root / "intake.json"
        payload_path.write_text(
            json.dumps(
                {
                    "kind": "portfolio",
                    "name": "State Test",
                    "delivery_lane": "advisory-only",
                }
            ),
            encoding="utf-8",
        )

        exit_code = validate_intake.main(["--root", str(self.root), "--file", str(payload_path)])

        self.assertEqual(exit_code, 0)
        state_file = self.root / ".cache/launch-engagement/state.json"
        self.assertTrue(state_file.is_file())
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(state["name"], "State Test")
        self.assertEqual(state["phases"], [0, 1, 2, 6, 8, 9])

    def test_inline_json_flag(self) -> None:
        exit_code = validate_intake.main(
            [
                "--root",
                str(self.root),
                "--json",
                '{"kind":"portfolio","name":"Inline","delivery_lane":"advisory-only"}',
            ]
        )
        self.assertEqual(exit_code, 0)

    def test_software_code_rejects_kit_phase_resume(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Code Build",
            "delivery_lane": "software-code",
            "starting_phase": 4,
        }
        with self.assertRaisesRegex(ValueError, "kit phases 3-6 do not apply"):
            intake_normalize.normalize_intake(payload, self.root)

    def test_software_code_allows_late_phase_resume(self) -> None:
        # Phases 7-9 (readout/value/close) are valid resume points for code builds;
        # only kit phases 3-6 are off-limits. Requires prior-phase artifacts to exist.
        project = self.root / "04_Portfolio/Code Resume"
        project.mkdir(parents=True)
        (self.root / "04_Portfolio/Code Resume.md").write_text("# Demo\n", encoding="utf-8")
        (project / "SOP Runbook.md").write_text("# Runbook\n", encoding="utf-8")
        (project / "Deliverables").mkdir()
        (project / "Deliverables/01_Situation_Assessment.md").write_text("# SA\n", encoding="utf-8")
        (project / "Deliverables/02_KPI_Design.md").write_text("# KPI\n", encoding="utf-8")
        payload = {
            "kind": "portfolio",
            "name": "Code Resume",
            "delivery_lane": "software-code",
            "starting_phase": 8,
        }
        intake = intake_normalize.normalize_intake(payload, self.root)
        result = validate_intake.build_result(self.root, intake)
        self.assertEqual(intake.starting_phase, 8)
        self.assertEqual(result.phases, [8, 9])
        self.assertEqual(result.work_surface, "Linear")

    def test_emitted_start_project_command_is_accepted_downstream(self) -> None:
        # Contract test: the whole point of this phase is emitting a command the
        # start-project CLI accepts. Parse the emitted command through the *real*
        # downstream parser so a renamed/removed flag fails here, not in production.
        vault_root = SKILL_DIR.parents[2]
        build_project_path = (
            vault_root / ".claude/skills/start-project/scripts/build_project.py"
        )
        if not build_project_path.is_file():
            self.skipTest("start-project build_project.py not present")

        spec = importlib.util.spec_from_file_location(
            "build_project_contract", build_project_path
        )
        assert spec and spec.loader
        build_project = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = build_project
        spec.loader.exec_module(build_project)

        payload = {
            "kind": "portfolio",
            "name": "Contract Probe",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
            "deliverables": ["Dashboard", "Runbook"],
        }
        intake = intake_normalize.normalize_intake(payload, self.root)
        command = validate_intake.build_result(self.root, intake).start_project_command

        self.assertEqual(command[0], "python3")
        self.assertEqual(command[2], "create")
        # emitted[2:] is the argv the downstream parser must accept (drops python3 + script path)
        args = build_project.build_parser().parse_args(command[2:])
        self.assertEqual(args.command, "create")
        self.assertEqual(args.kind, "portfolio")
        self.assertEqual(args.project_path, intake.project_path)
        self.assertEqual(args.deliverable, ["Dashboard", "Runbook"])

    def test_kit_command_has_expected_shape(self) -> None:
        payload = {
            "kind": "portfolio",
            "name": "Kit Shape",
            "delivery_lane": "tool-built-bi",
            "kit": "Power BI Project Kit",
        }
        intake = intake_normalize.normalize_intake(payload, self.root)
        command = validate_intake.build_result(self.root, intake).kit_deploy_dry_run_command
        self.assertEqual(command[2], "deploy")
        for flag in ("--kit", "--project", "--dry-run"):
            self.assertIn(flag, command)
        self.assertNotIn("--force", command)

    def test_schema_enums_match_constants(self) -> None:
        # Guard the second copy of the field contract: intake.schema.json is not
        # loaded at runtime, so nothing else catches drift from the enums that
        # actually enforce validation.
        import engagement_constants as ec

        schema = json.loads((SKILL_DIR / "intake.schema.json").read_text(encoding="utf-8"))
        props = schema["properties"]
        self.assertEqual(props["kind"]["enum"], list(ec.PROJECT_KINDS))
        self.assertEqual(props["delivery_lane"]["enum"], list(ec.DELIVERY_LANES))
        self.assertEqual(props["engagement_type"]["enum"], list(ec.ENGAGEMENT_TYPES))
        self.assertEqual(props["data_classification"]["enum"], list(ec.DATA_CLASSIFICATIONS))
        self.assertEqual(props["status"]["enum"], list(ec.CLIENT_STATUSES))


if __name__ == "__main__":
    unittest.main()
