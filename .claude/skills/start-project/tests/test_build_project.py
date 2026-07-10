from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_project.py"
SPEC = importlib.util.spec_from_file_location("build_project", SCRIPT)
assert SPEC and SPEC.loader
build_project = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_project
SPEC.loader.exec_module(build_project)

VAULT_ROOT = Path(__file__).parents[4]
REAL_CLIENT_TEMPLATE = VAULT_ROOT / "06_Templates/Notes/Client Dossier Template.md"


class BuildProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self._write_required_sources()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_required_sources(self) -> None:
        for procedure in build_project.PROCEDURES.values():
            path = self.root / procedure.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {procedure.title}\n", encoding="utf-8")
        template_dir = self.root / "02_Clients/_Client_Template"
        template_dir.mkdir(parents=True)
        for filename in ("Client Folder README.md", "Onboarding Checklist.md", "Offboarding Checklist.md"):
            (template_dir / filename).write_text(
                "# Template\nClient: {{Client Name}}\nDate: {{Date}}\n", encoding="utf-8"
            )
        dossier_template = self.root / "06_Templates/Notes/Client Dossier Template.md"
        dossier_template.parent.mkdir(parents=True)
        dossier_template.write_text(
            """---
type: client
status: prospect
created: {{date}}
updated: {{date}}
---

# (Client name)

## Snapshot

| Field | Value |
|---|---|
| Industry / niche | |
| Source | (Upwork / referral / direct) |
| Primary contact | |
| Status | prospect / proposal-sent / active / delivered / dormant |
| Folder | `02_Clients/.../` |
| Proposal | `03_Proposals/...` |

## Context

Template context.

## Template-only section

Preserve this when scaffolding.
""",
            encoding="utf-8",
        )

    def test_creates_financial_client_with_sensitive_data_sop(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="client",
            name="Acme Funds",
            industry="Fund administration",
            engagement_type="analytics",
            data_classification="financial",
            deliverables=("Power BI dashboard",),
            source="Upwork",
            status="active",
        )

        build_project.create_project(self.root, metadata)

        dossier = self.root / "02_Clients/Acme Funds.md"
        project = self.root / "02_Clients/Acme Funds"
        runbook = (project / "SOP Runbook.md").read_text(encoding="utf-8")
        self.assertTrue(dossier.exists())
        self.assertTrue((project / "data/raw").is_dir())
        self.assertIn("SOP-02_HIPAA_Data_Handling", runbook)
        self.assertIn("SOP-04_Report_QA_Handoff", runbook)
        self.assertIn("Template-only section", dossier.read_text(encoding="utf-8"))
        self.assertIn("Acme Funds", (project / "Onboarding Checklist.md").read_text(encoding="utf-8"))
        with self.assertRaises(FileExistsError):
            build_project.create_project(self.root, metadata)

    def test_creates_synthetic_portfolio_without_client_sops(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Cash Flow Demo",
            industry="Financial services",
            engagement_type="analytics",
            data_classification="synthetic",
            deliverables=("Interactive dashboard", "Case study"),
            status="active",
        )

        build_project.create_project(self.root, metadata)

        runbook = (self.root / "04_Portfolio/Cash Flow Demo/SOP Runbook.md").read_text(
            encoding="utf-8"
        )
        dossier = (self.root / "04_Portfolio/Cash Flow Demo.md").read_text(encoding="utf-8")
        self.assertIn("Portfolio Excellence Playbook", runbook)
        self.assertIn("Synthetic Data Generation", runbook)
        self.assertNotIn("SOP - Client Onboarding", runbook)
        self.assertNotIn("SOP-02_HIPAA_Data_Handling", runbook)
        self.assertIn("not a real client engagement", dossier)

    def test_rejects_sensitive_portfolio_data(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Unsafe Demo",
            industry="Healthcare",
            engagement_type="analytics",
            data_classification="phi",
            deliverables=("Dashboard",),
            status="active",
        )
        with self.assertRaisesRegex(ValueError, "Portfolio projects may use only"):
            build_project.create_project(self.root, metadata)

    def test_portfolio_dossier_is_typed_portfolio(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Typed Demo",
            industry="Financial services",
            engagement_type="analytics",
            data_classification="synthetic",
            deliverables=("Dashboard",),
            status="active",
        )

        build_project.create_project(self.root, metadata)

        dossier = (self.root / "04_Portfolio/Typed Demo.md").read_text(encoding="utf-8")
        self.assertIn("type: portfolio", dossier)
        self.assertNotIn("type: client", dossier)
        self.assertIn("client-type: synthetic-portfolio", dossier)

    def test_missing_template_anchor_raises(self) -> None:
        template = self.root / "06_Templates/Notes/Client Dossier Template.md"
        text = template.read_text(encoding="utf-8")
        template.write_text(text.replace("## Context", "## Background"), encoding="utf-8")
        metadata = build_project.ProjectMetadata(
            kind="client",
            name="Drifted Template",
            industry="Operations",
            engagement_type="analytics",
            data_classification="internal",
            deliverables=("Dashboard",),
            status="active",
        )
        with self.assertRaisesRegex(ValueError, "anchor not found"):
            build_project.create_project(self.root, metadata)

    def test_public_portfolio_is_labeled_as_public_data(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Public Data Demo",
            industry="Government",
            engagement_type="analytics",
            data_classification="public",
            deliverables=("Public dashboard",),
            status="active",
        )

        build_project.create_project(self.root, metadata)

        dossier = (self.root / "04_Portfolio/Public Data Demo.md").read_text(encoding="utf-8")
        self.assertIn("Public-data portfolio demonstration", dossier)
        self.assertNotIn("Synthetic portfolio demonstration", dossier)

    def test_custom_project_path_is_honored(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Variance Pack",
            industry="Financial services",
            engagement_type="analytics",
            data_classification="synthetic",
            deliverables=("Dashboard",),
            status="active",
            project_path="04_Portfolio/PowerBI_Variance_Pack",
        )

        messages = build_project.create_project(self.root, metadata)

        self.assertTrue((self.root / "04_Portfolio/PowerBI_Variance_Pack.md").exists())
        self.assertTrue((self.root / "04_Portfolio/PowerBI_Variance_Pack").is_dir())
        self.assertIn("04_Portfolio/PowerBI_Variance_Pack", "\n".join(messages))

    def test_rejects_project_path_in_wrong_area(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="portfolio",
            name="Wrong Area",
            industry="Financial services",
            engagement_type="analytics",
            data_classification="synthetic",
            deliverables=("Dashboard",),
            status="active",
            project_path="02_Clients/Wrong Area",
        )

        with self.assertRaisesRegex(ValueError, "must live under 04_Portfolio"):
            build_project.create_project(self.root, metadata)

    def test_sync_uses_runbook_metadata_and_reports_missing_sop(self) -> None:
        metadata = build_project.ProjectMetadata(
            kind="client",
            name="Automation Client",
            industry="Operations",
            engagement_type="automation",
            data_classification="internal",
            deliverables=("Workflow automation",),
            status="active",
        )
        build_project.create_project(self.root, metadata)
        (self.root / build_project.PROCEDURES["contingency"].path).unlink()
        args = build_project.build_parser().parse_args(
            ["sync", "--dossier", "02_Clients/Automation Client.md"]
        )

        messages = build_project.sync_project(self.root, args)

        runbook = (self.root / "02_Clients/Automation Client/SOP Runbook.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("No canonical automation-delivery SOP exists", runbook)
        self.assertIn("Expected canonical procedure is missing", runbook)
        self.assertIn("Applicable procedures:", messages[1])


class RealTemplateAnchorTests(unittest.TestCase):
    """Guard against the live template drifting away from the script's substitution anchors."""

    @unittest.skipUnless(
        REAL_CLIENT_TEMPLATE.exists(),
        f"Live client dossier template not found at {REAL_CLIENT_TEMPLATE}",
    )
    def test_live_template_contains_every_anchor(self) -> None:
        template = REAL_CLIENT_TEMPLATE.read_text(encoding="utf-8")
        for anchor in build_project.CLIENT_DOSSIER_ANCHORS:
            self.assertIn(
                anchor,
                template,
                msg=(
                    f"Anchor {anchor!r} is missing from {REAL_CLIENT_TEMPLATE}. "
                    "Update CLIENT_DOSSIER_ANCHORS and render_client_dossier together."
                ),
            )


if __name__ == "__main__":
    unittest.main()
