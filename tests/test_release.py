from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from causal_lab.cli import run
from causal_lab.release import build_release_envelope


class ReleaseEnvelopeTests(unittest.TestCase):
    def _prepare_bundle(self, directory: str) -> tuple[Path, dict]:
        root = Path(directory)
        source = Path(__file__).resolve().parents[1]
        result = run(root, source / "config/experiment.json")
        manifest = json.loads((root / "reports/generated/run_manifest.json").read_text(encoding="utf-8"))
        for item in manifest["provenance"]:
            relative = Path(item["path"])
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        return root, result

    def test_generated_bundle_passes_and_never_authorizes_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root, result = self._prepare_bundle(directory)
            envelope = build_release_envelope(root)
            self.assertEqual(result["decision"]["machine_status"], "eligible_for_human_review")
            self.assertEqual(envelope["evidence_status"], "pass")
            self.assertFalse(envelope["deployment_authorized"])
            self.assertTrue(envelope["human_review_required"])

    def test_tampered_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._prepare_bundle(directory)
            report = root / "reports/generated/experiment_report.md"
            report.write_text("tampered\n", encoding="utf-8")
            envelope = build_release_envelope(root)
            self.assertEqual(envelope["evidence_status"], "fail")
            self.assertEqual(envelope["machine_status"], "evidence_validation_failed")

    def test_release_envelope_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._prepare_bundle(directory)
            first = json.dumps(build_release_envelope(root), indent=2, sort_keys=True) + "\n"
            second = json.dumps(build_release_envelope(root), indent=2, sort_keys=True) + "\n"
            self.assertEqual(first.encode(), second.encode())


if __name__ == "__main__":
    unittest.main()
