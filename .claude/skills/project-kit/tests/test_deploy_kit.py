from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).parents[1] / "scripts" / "deploy_kit.py"
SPEC = importlib.util.spec_from_file_location("deploy_kit", SCRIPT)
assert SPEC and SPEC.loader
deploy_kit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = deploy_kit
SPEC.loader.exec_module(deploy_kit)


class DeployKitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        deploy_kit.VAULT_ROOT = str(self.root)
        deploy_kit.DEFAULT_KITS_ROOT = str(self.root / "06_Templates/Kits")
        self.kit = self.root / "06_Templates/Kits/Sample Kit"
        self.kit.mkdir(parents=True)
        self.project = self.root / "04_Portfolio/Demo"
        self.project.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def args(self, **overrides):
        values = {
            "kit": "Sample Kit",
            "project": "04_Portfolio/Demo",
            "kits_root": None,
            "dest_name": None,
            "dry_run": True,
            "force": False,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def write_manifest(self, deployable: str = "README.md") -> None:
        (self.kit / "manifest.json").write_text(
            '{"kit": "Sample Kit", "version": "1.0", "deploy_root": "Kit", '
            f'"deployable": [{{"path": "{deployable}", "kind": "file"}}]}}',
            encoding="utf-8",
        )

    def test_dry_run_inside_allowed_project_succeeds(self) -> None:
        self.write_manifest()
        (self.kit / "README.md").write_text("# Kit\n", encoding="utf-8")

        self.assertEqual(deploy_kit.deploy(self.args()), 0)

    def test_missing_manifest_file_returns_nonzero(self) -> None:
        self.write_manifest("MISSING.md")

        self.assertEqual(deploy_kit.deploy(self.args()), 3)

    def test_rejects_project_outside_allowed_roots(self) -> None:
        self.write_manifest()
        outside = self.root / "08_Learning/Demo"
        outside.mkdir(parents=True)

        self.assertEqual(deploy_kit.deploy(self.args(project=str(outside))), 2)

    def test_rejects_confidential_client_subfolder(self) -> None:
        self.write_manifest()
        confidential = self.root / "02_Clients/Acme/data/raw"
        confidential.mkdir(parents=True)

        self.assertEqual(deploy_kit.deploy(self.args(project=str(confidential))), 2)


if __name__ == "__main__":
    unittest.main()
