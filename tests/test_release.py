from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from causal_lab.cli import run
from causal_lab.release import build_release_envelope


class ReleaseEnvelopeTests(unittest.TestCase):
    def test_generated_bundle_passes_and_never_authorizes_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[1]
            result = run(root, source / "config/experiment.json")
            envelope = build_release_envelope(root)
            self.assertEqual(result["decision"]["machine_status"], "eligible_for_human_review")
            self.assertEqual(envelope["evidence_status"], "pass")
            self.assertFalse(envelope["deployment_authorized"])
            self.assertTrue(envelope["human_review_required"])

    def test_tampered_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[1]
            run(root, source / "config/experiment.json")
            report = root / "reports/generated/experiment_report.md"
            report.write_text("tampered\n", encoding="utf-8")
            envelope = build_release_envelope(root)
            self.assertEqual(envelope["evidence_status"], "fail")
            self.assertEqual(envelope["machine_status"], "evidence_validation_failed")

    def test_release_envelope_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[1]
            run(root, source / "config/experiment.json")
            first = json.dumps(build_release_envelope(root), indent=2, sort_keys=True) + "\n"
            second = json.dumps(build_release_envelope(root), indent=2, sort_keys=True) + "\n"
            self.assertEqual(first.encode(), second.encode())


if __name__ == "__main__":
    unittest.main()
