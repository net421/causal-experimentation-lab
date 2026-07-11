"""Small statistical toolkit used by the experiment pipeline.

Only NumPy is required. Inference uses large-sample normal intervals and the
reports label that assumption explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, erfc, sqrt
from statistics import NormalDist

import numpy as np


@dataclass(frozen=True)
class Estimate:
    estimate: float
    standard_error: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "estimate": self.estimate,
            "standard_error": self.standard_error,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value": self.p_value,
            "n": self.n,
        }


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def two_sided_normal_p(z_score: float) -> float:
    return erfc(abs(z_score) / sqrt(2.0))


def interval(estimate: float, standard_error: float, alpha: float) -> tuple[float, float]:
    critical = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    return estimate - critical * standard_error, estimate + critical * standard_error


def difference_in_means(
    outcome: np.ndarray, treatment: np.ndarray, alpha: float = 0.05
) -> Estimate:
    treated = outcome[treatment == 1]
    control = outcome[treatment == 0]
    estimate = float(treated.mean() - control.mean())
    se = float(sqrt(treated.var(ddof=1) / len(treated) + control.var(ddof=1) / len(control)))
    low, high = interval(estimate, se, alpha)
    return Estimate(estimate, se, low, high, two_sided_normal_p(estimate / se), len(outcome))


def ols_treatment_effect(
    outcome: np.ndarray,
    design: np.ndarray,
    treatment_column: int = 1,
    alpha: float = 0.05,
    robust: bool = True,
) -> Estimate:
    """Return the treatment coefficient from OLS with HC1 or classical SE."""
    n, k = design.shape
    beta, _, rank, _ = np.linalg.lstsq(design, outcome, rcond=None)
    if rank != k:
        raise ValueError("Design matrix is rank deficient")
    residual = outcome - design @ beta
    xtx_inv = np.linalg.inv(design.T @ design)
    if robust:
        meat = design.T @ (design * residual[:, None] ** 2)
        covariance = (n / (n - k)) * xtx_inv @ meat @ xtx_inv
    else:
        variance = float(residual @ residual) / (n - k)
        covariance = variance * xtx_inv
    estimate = float(beta[treatment_column])
    se = float(sqrt(covariance[treatment_column, treatment_column]))
    low, high = interval(estimate, se, alpha)
    return Estimate(estimate, se, low, high, two_sided_normal_p(estimate / se), n)


def standardized_mean_difference(values: np.ndarray, treatment: np.ndarray) -> float:
    treated = values[treatment == 1]
    control = values[treatment == 0]
    pooled_sd = sqrt((treated.var(ddof=1) + control.var(ddof=1)) / 2.0)
    return float((treated.mean() - control.mean()) / pooled_sd) if pooled_sd else 0.0


def required_sample_size_per_arm(
    minimum_effect: float, sigma: float, alpha: float, target_power: float
) -> int:
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_power = NormalDist().inv_cdf(target_power)
    return int(np.ceil(2.0 * sigma**2 * (z_alpha + z_power) ** 2 / minimum_effect**2))


def approximate_power(
    sample_size_per_arm: int, minimum_effect: float, sigma: float, alpha: float
) -> float:
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    noncentrality = minimum_effect / (sigma * sqrt(2.0 / sample_size_per_arm))
    return float(1.0 - normal_cdf(z_alpha - noncentrality) + normal_cdf(-z_alpha - noncentrality))


def winsorize(values: np.ndarray, lower: float = 0.01, upper: float = 0.99) -> np.ndarray:
    low, high = np.quantile(values, [lower, upper])
    return np.clip(values, low, high)


def permutation_p_value(
    outcome: np.ndarray,
    treatment: np.ndarray,
    permutations: int,
    seed: int,
) -> float:
    observed = abs(difference_in_means(outcome, treatment).estimate)
    rng = np.random.default_rng(seed)
    exceedances = 0
    for _ in range(permutations):
        shuffled = rng.permutation(treatment)
        if abs(difference_in_means(outcome, shuffled).estimate) >= observed:
            exceedances += 1
    return float((exceedances + 1) / (permutations + 1))

