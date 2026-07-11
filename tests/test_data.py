from __future__ import annotations

import json
import unittest
from pathlib import Path

from causal_lab.data import generate_experiment


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/experiment.json").read_text(encoding="utf-8"))


class DataGenerationTests(unittest.TestCase):
    def test_generation_is_deterministic(self) -> None:
        self.assertEqual(generate_experiment(CONFIG), generate_experiment(CONFIG))

    def test_assignment_is_exactly_balanced(self) -> None:
        rows = generate_experiment(CONFIG)
        assigned = sum(int(row["treatment"]) for row in rows)
        self.assertEqual(len(rows), 500)
        self.assertEqual(assigned, 250)

    def test_identifiers_are_unique(self) -> None:
        rows = generate_experiment(CONFIG)
        self.assertEqual(len({row["unit_id"] for row in rows}), len(rows))


if __name__ == "__main__":
    unittest.main()

