# Methodology

## Identification

Complete randomization makes treatment independent of potential outcomes in the synthetic cohort. The unadjusted difference in means is design-consistent. ANCOVA is pre-specified to improve precision, not to repair assignment. The pipeline reports both.

## Uncertainty

The main analysis uses an OLS treatment coefficient with HC1 sandwich standard errors. Confidence intervals and p-values use the standard normal approximation. A permutation p-value for the unadjusted effect tests Fisher's sharp null that no unit has any treatment effect; it provides design-based corroboration and is not a test of only the average-effect null.

## Power

The normal-approximation sample-size calculation assumes a standard deviation of $800, a two-sided alpha of 0.05, target power of 0.80, and a minimum practical effect of $250. The required and actual samples per arm are emitted in `results.json`.

## Robustness

The pipeline compares classical and HC1 standard errors, winsorizes the outcome at the 1st and 99th percentiles, checks a baseline placebo difference, computes a seeded permutation p-value, reports regional exploratory effects, and refits ANCOVA after leaving out each region.

The included hypothesis file is a transparent analysis specification for a synthetic demonstration. It was not deposited in an external registry before data generation and therefore is not represented as a prospective preregistration.

## Decision boundary

Automated logic can reject evidence or mark it eligible for review. It cannot authorize deployment. The generated human review packet defines the additional governed record required for a real decision.
