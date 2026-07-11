# Causal Experimentation Lab

A complete, reproducible causal-analysis case study for a supply-chain priority-replenishment intervention. It generates deterministic synthetic data, runs a randomized A/B analysis with pre-specified ANCOVA adjustment, quantifies uncertainty, performs robustness checks, applies explicit decision gates, and emits review-ready evidence.

The repository demonstrates analytical practice. It does **not** claim that the intervention works in a real supply chain, and its automated result never authorizes deployment.

## What is implemented

- Seeded 1:1 complete randomization of 500 synthetic distribution centers.
- Unadjusted difference in means and covariate-adjusted OLS ANCOVA.
- HC1 robust standard errors, 95% intervals, and two-sided p-values.
- Pre-analysis hypothesis register and detailed hypothesis cards.
- Minimum practical effect, alpha, power target, and sample-size calculation.
- Balance checks, permutation inference, baseline placebo, winsorization, regional estimates, and leave-one-region-out refits.
- Machine-readable results, human-readable experiment report, review packet, robustness table, dataset, and SHA-256 evidence manifest.
- Unit, analysis, policy, and end-to-end artifact-integrity tests.
- GitHub Actions workflow that regenerates evidence and rejects drift.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make check
```

The direct pipeline command is:

```bash
python -m causal_lab.cli --root .
```

Expected console output includes the computed adjusted effect, confidence interval, and one of the two governed machine statuses: `eligible_for_human_review` or `evidence_threshold_not_met`.

## Evidence outputs

| Output | Purpose |
|---|---|
| `data/generated/experiment_units.csv` | Complete synthetic experiment dataset |
| `reports/generated/results.json` | Estimates, uncertainty, balance, power, robustness, and gates |
| `reports/generated/experiment_report.md` | Decision-oriented narrative generated from results |
| `reports/generated/robustness_checks.csv` | Compact sensitivity-analysis table |
| `reports/generated/human_review_packet.md` | Governance boundary and review questions |
| `reports/generated/run_manifest.json` | Byte size and SHA-256 digest for every evidence file |

## Pre-specified analysis

The primary outcome is 8-week post-assignment gross margin per center. The estimand is the intention-to-treat average effect. The primary estimator is the treatment coefficient from:

```text
post margin ~ treatment + baseline margin + baseline stockout rate + capacity + region
```

The minimum practical effect is $250 per center. Passing requires the adjusted point estimate to meet that threshold, its 95% interval to exclude zero, p ≤ 0.05, planned power ≥ 0.80, all pre-treatment absolute standardized mean differences ≤ 0.10, permutation p ≤ 0.05, and positive leave-one-region-out effects.

The exact configuration lives in `config/experiment.json`; the hypothesis register lives in `docs/hypotheses/register.json`.

## Repository map

```text
config/                 Locked experiment and decision parameters
data/generated/         Reproducible synthetic cohort
docs/hypotheses/        Hypothesis register and cards
reports/generated/      Computed evidence and human-review boundary
src/causal_lab/         Data, inference, decision, reporting, and CLI code
tests/                  Determinism, estimation, governance, and pipeline tests
.github/workflows/      Reproduction gate for every push and pull request
```

## Interpretation boundary

The data-generating process contains a known synthetic treatment effect so the implementation can be tested. The reported estimate is still calculated from noisy observed outcomes; the code does not insert the known effect into the estimator. Results support claims about reproducibility and statistical workflow only. Real operational claims require a real randomized pilot, cost and harm measurement, contamination controls, monitored rollback criteria, and accountable human approval.

## Technical notes

NumPy is the only runtime dependency. Tests use Python's standard `unittest` framework. The normal approximation is appropriate for this 500-unit demonstration and is named in every methodological artifact. Subgroup results are exploratory and not adjusted for multiple testing.

## License

MIT

