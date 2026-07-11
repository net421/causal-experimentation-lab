# Experiment results: SC-PRIORITY-REPLENISHMENT-001

Generated from the committed pipeline. Values below are computed, not manually entered.

## Question and design

Does a simulated priority-replenishment intervention increase 8-week gross margin per distribution center? The synthetic experiment assigns 500 centers exactly 1:1 to intervention or control with seed `423`. The primary estimand is the intention-to-treat average effect.

## Primary result

The pre-specified ANCOVA estimate is **$357.45 per center** (95% CI $217.52 to $497.39; large-sample two-sided p=5.54063e-07). It adjusts for baseline gross margin, baseline stockout rate, capacity, and region; HC1 robust standard errors are used.

The unadjusted difference is $399.82. The minimum practical effect was pre-specified as $250.00.

The secondary adjusted stockout-rate estimate is **-1.91 percentage points** (95% CI -2.09 to -1.73).

## Power and allocation

- Required sample per arm: 161
- Actual sample per arm: 250
- Approximate planned power at the minimum practical effect: 0.937
- Target power: 0.80

## Baseline balance

Absolute standardized mean differences must be no larger than 0.1.

- `capacity_index`: -0.059
- `baseline_gross_margin`: 0.043
- `baseline_stockout_rate`: -0.002
- `region_east`: 0.000
- `region_north`: 0.000
- `region_south`: 0.009
- `region_west`: -0.009

## Decision gates

- PASS — `point_estimate_meets_practical_threshold`
- PASS — `confidence_interval_excludes_zero`
- PASS — `primary_p_value_within_alpha`
- PASS — `planned_power_meets_target`
- PASS — `covariate_balance_within_limit`
- PASS — `randomization_inference_supports_effect`
- PASS — `leave_one_region_out_effects_positive`

Machine status: **eligible_for_human_review**. Deployment is **not authorized** by this analysis. A human reviewer must assess operational feasibility, harm, cost, and external validity.

## Decision implication

If a real randomized pilot produced evidence of comparable quality and passed safety and cost review, the result would justify consideration of a controlled rollout rather than immediate broad deployment. This synthetic exercise demonstrates the decision process only; it is not evidence that the intervention works in a real supply chain.

## Limitations

- The data are synthetic and cannot establish an effect in a real operation.
- Confidence intervals and p-values use large-sample normal approximations.
- The analysis estimates intention-to-treat under the simulated random assignment.
- Subgroup estimates are exploratory and are not multiplicity adjusted.
