"""Pre-specified causal analysis and robustness checks."""

from __future__ import annotations

from typing import Any

import numpy as np

from .data import as_arrays
from .statistics import (
    Estimate,
    approximate_power,
    difference_in_means,
    ols_treatment_effect,
    permutation_p_value,
    required_sample_size_per_arm,
    standardized_mean_difference,
    winsorize,
)


def design_matrix(arrays: dict[str, np.ndarray], mask: np.ndarray | None = None) -> np.ndarray:
    if mask is None:
        mask = np.ones(len(arrays["treatment"]), dtype=bool)
    regions = arrays["region"][mask]
    columns = [
        np.ones(mask.sum()),
        arrays["treatment"][mask],
        arrays["baseline_gross_margin"][mask] - arrays["baseline_gross_margin"][mask].mean(),
        arrays["baseline_stockout_rate"][mask] - arrays["baseline_stockout_rate"][mask].mean(),
        arrays["capacity_index"][mask] - arrays["capacity_index"][mask].mean(),
    ]
    for region in sorted(set(regions))[1:]:
        columns.append((regions == region).astype(float))
    return np.column_stack(columns)


def _estimate_dict(estimate: Estimate, method: str) -> dict[str, Any]:
    result = estimate.as_dict()
    result["method"] = method
    return result


def analyze(rows: list[dict], config: dict) -> dict[str, Any]:
    arrays = as_arrays(rows)
    treatment = arrays["treatment"].astype(int)
    alpha = float(config["alpha"])
    design = design_matrix(arrays)

    primary_unadjusted = difference_in_means(arrays["post_gross_margin"], treatment, alpha)
    primary_adjusted = ols_treatment_effect(
        arrays["post_gross_margin"], design, alpha=alpha, robust=True
    )
    secondary_adjusted = ols_treatment_effect(
        arrays["post_stockout_rate"], design, alpha=alpha, robust=True
    )
    classical_adjusted = ols_treatment_effect(
        arrays["post_gross_margin"], design, alpha=alpha, robust=False
    )
    winsorized_adjusted = ols_treatment_effect(
        winsorize(arrays["post_gross_margin"]), design, alpha=alpha, robust=True
    )
    placebo = difference_in_means(arrays["baseline_gross_margin"], treatment, alpha)

    balance = {
        key: standardized_mean_difference(arrays[key], treatment)
        for key in ["capacity_index", "baseline_gross_margin", "baseline_stockout_rate"]
    }
    # Treat every level of the categorical stratifier as a pre-treatment
    # covariate. This prevents a balanced numeric table from hiding regional
    # allocation imbalance.
    for region in sorted(set(arrays["region"])):
        balance[f"region_{region}"] = standardized_mean_difference(
            (arrays["region"] == region).astype(float), treatment
        )
    subgroup_effects: dict[str, dict[str, Any]] = {}
    leave_one_region_out: dict[str, dict[str, Any]] = {}
    for region in sorted(set(arrays["region"])):
        region_mask = arrays["region"] == region
        subgroup_effects[region] = _estimate_dict(
            difference_in_means(
                arrays["post_gross_margin"][region_mask], treatment[region_mask], alpha
            ),
            "difference_in_means",
        )
        keep = arrays["region"] != region
        leave_one_region_out[region] = _estimate_dict(
            ols_treatment_effect(
                arrays["post_gross_margin"][keep],
                design_matrix(arrays, keep),
                alpha=alpha,
                robust=True,
            ),
            "ancova_hc1",
        )

    power_cfg = config["power"]
    n_per_arm = int(min((treatment == 0).sum(), (treatment == 1).sum()))
    required = required_sample_size_per_arm(
        float(config["minimum_practical_effect"]),
        float(power_cfg["planning_sigma"]),
        alpha,
        float(power_cfg["target"]),
    )
    achieved = approximate_power(
        n_per_arm,
        float(config["minimum_practical_effect"]),
        float(power_cfg["planning_sigma"]),
        alpha,
    )
    randomization_p = permutation_p_value(
        arrays["post_gross_margin"],
        treatment,
        int(config["robustness"]["permutations"]),
        int(config["seed"]) + 99,
    )

    gates = {
        "point_estimate_meets_practical_threshold": primary_adjusted.estimate
        >= float(config["minimum_practical_effect"]),
        "confidence_interval_excludes_zero": primary_adjusted.ci_low > 0.0,
        "primary_p_value_within_alpha": primary_adjusted.p_value <= alpha,
        "planned_power_meets_target": achieved >= float(power_cfg["target"]),
        "covariate_balance_within_limit": max(abs(x) for x in balance.values())
        <= float(config["balance_smd_limit"]),
        "randomization_inference_supports_effect": randomization_p <= alpha,
        "leave_one_region_out_effects_positive": min(
            value["estimate"] for value in leave_one_region_out.values()
        )
        > 0.0,
    }
    eligible = all(gates.values())
    return {
        "experiment_id": config["experiment_id"],
        "estimand": "intention-to-treat average effect on 8-week gross margin per distribution center",
        "sample": {
            "total": len(rows),
            "treated": int((treatment == 1).sum()),
            "control": int((treatment == 0).sum()),
        },
        "primary": {
            "unadjusted": _estimate_dict(primary_unadjusted, "difference_in_means_normal"),
            "adjusted": _estimate_dict(primary_adjusted, "ancova_ols_hc1"),
        },
        "secondary": {
            "stockout_rate_adjusted": _estimate_dict(secondary_adjusted, "ancova_ols_hc1")
        },
        "power": {
            "planning_sigma": float(power_cfg["planning_sigma"]),
            "minimum_practical_effect": float(config["minimum_practical_effect"]),
            "target": float(power_cfg["target"]),
            "required_per_arm": required,
            "actual_per_arm": n_per_arm,
            "approximate_planned_power": achieved,
        },
        "balance_standardized_mean_differences": balance,
        "robustness": {
            "classical_standard_error": _estimate_dict(classical_adjusted, "ancova_ols_classical"),
            "winsorized_outcome": _estimate_dict(winsorized_adjusted, "ancova_hc1_winsorized_1_99"),
            "placebo_baseline_difference": _estimate_dict(placebo, "difference_in_means_normal"),
            "randomization_inference_p_value": randomization_p,
            "randomization_inference_null": "sharp_null_of_no_unit_level_treatment_effect",
            "subgroup_unadjusted_effects": subgroup_effects,
            "leave_one_region_out": leave_one_region_out,
        },
        "decision": {
            "gates": gates,
            "machine_status": "eligible_for_human_review" if eligible else "evidence_threshold_not_met",
            "deployment_authorized": False,
            "human_review_required": True,
        },
        "limitations": [
            "The data are synthetic and cannot establish an effect in a real operation.",
            "Confidence intervals and p-values use large-sample normal approximations.",
            "The analysis estimates intention-to-treat under the simulated random assignment.",
            "Subgroup estimates are exploratory and are not multiplicity adjusted.",
        ],
    }
