from __future__ import annotations

import json
import copy
import unittest
from pathlib import Path

from causal_lab.analysis import analyze
from causal_lab.data import generate_experiment


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/experiment.json").read_text(encoding="utf-8"))


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = analyze(generate_experiment(CONFIG), CONFIG)

    def test_adjusted_estimate_recovers_synthetic_effect(self) -> None:
        estimate = self.results["primary"]["adjusted"]["estimate"]
        standard_error = self.results["primary"]["adjusted"]["standard_error"]
        true_effect = CONFIG["data_generating_process"]["gross_margin_effect"]
        self.assertLess(abs(estimate - true_effect), 3.0 * standard_error)

    def test_interval_is_ordered_and_finite(self) -> None:
        result = self.results["primary"]["adjusted"]
        self.assertLess(result["ci_low"], result["estimate"])
        self.assertLess(result["estimate"], result["ci_high"])
        self.assertGreater(result["standard_error"], 0.0)

    def test_power_calculation_matches_allocation(self) -> None:
        power = self.results["power"]
        self.assertEqual(power["actual_per_arm"], 250)
        self.assertGreaterEqual(power["approximate_planned_power"], power["target"])

    def test_machine_cannot_authorize_deployment(self) -> None:
        decision = self.results["decision"]
        self.assertFalse(decision["deployment_authorized"])
        self.assertTrue(decision["human_review_required"])

    def test_robustness_checks_cover_every_region(self) -> None:
        regions = {"east", "north", "south", "west"}
        self.assertEqual(set(self.results["robustness"]["leave_one_region_out"]), regions)
        self.assertEqual(set(self.results["robustness"]["subgroup_unadjusted_effects"]), regions)

    def test_region_is_in_balance_gate(self) -> None:
        balance = self.results["balance_standardized_mean_differences"]
        self.assertEqual(
            {key for key in balance if key.startswith("region_")},
            {"region_east", "region_north", "region_south", "region_west"},
        )
        self.assertTrue(self.results["decision"]["gates"]["covariate_balance_within_limit"])

    def test_region_imbalance_fails_balance_gate(self) -> None:
        rows = copy.deepcopy(generate_experiment(CONFIG))
        north_controls = [row for row in rows if row["region"] == "north" and row["treatment"] == 0]
        other_treated = [row for row in rows if row["region"] != "north" and row["treatment"] == 1]
        for row in north_controls[:40]:
            row["treatment"] = 1
        for row in other_treated[:40]:
            row["treatment"] = 0
        results = analyze(rows, CONFIG)
        self.assertFalse(results["decision"]["gates"]["covariate_balance_within_limit"])
        self.assertEqual(results["decision"]["machine_status"], "evidence_threshold_not_met")

    def test_numeric_imbalance_fails_balance_gate(self) -> None:
        rows = copy.deepcopy(generate_experiment(CONFIG))
        ordered = sorted(range(len(rows)), key=lambda i: float(rows[i]["capacity_index"]))
        treated = set(ordered[len(rows) // 2 :])
        for index, row in enumerate(rows):
            row["treatment"] = int(index in treated)
        results = analyze(rows, CONFIG)
        self.assertFalse(results["decision"]["gates"]["covariate_balance_within_limit"])


if __name__ == "__main__":
    unittest.main()
