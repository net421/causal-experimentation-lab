from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from causal_lab.cli import run


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_pipeline_writes_verified_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            results = run(destination, ROOT / "config/experiment.json")
            self.assertIn(results["decision"]["machine_status"], {
                "eligible_for_human_review",
                "evidence_threshold_not_met",
            })
            manifest_path = destination / "reports/generated/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["files"]), 5)
            provenance = {entry["path"]: entry for entry in manifest["provenance"]}
            for required in [
                "config/experiment.json",
                "docs/hypotheses/register.json",
                "pyproject.toml",
                "requirements-lock.txt",
                "runtime-lock.json",
                "src/causal_lab/analysis.py",
            ]:
                self.assertIn(required, provenance)
            self.assertEqual(manifest["runtime"]["python_version"], "3.12.13")
            self.assertEqual(manifest["runtime"]["numpy"], "2.3.5")
            for entry in manifest["files"]:
                artifact = destination / entry["path"]
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                self.assertEqual(digest, entry["sha256"])
                self.assertGreater(entry["bytes"], 0)
            for entry in manifest["provenance"]:
                artifact = ROOT / entry["path"]
                self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
