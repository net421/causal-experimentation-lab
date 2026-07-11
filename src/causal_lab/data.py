"""Deterministic synthetic experiment data generation and CSV I/O."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


COLUMNS = [
    "unit_id",
    "region",
    "capacity_index",
    "baseline_gross_margin",
    "baseline_stockout_rate",
    "treatment",
    "post_gross_margin",
    "post_stockout_rate",
]


def generate_experiment(config: dict) -> list[dict[str, str | int | float]]:
    n = int(config["sample_size_total"])
    if n % 2:
        raise ValueError("sample_size_total must be even for exact allocation")
    rng = np.random.default_rng(int(config["seed"]))
    regions = np.array(["north", "south", "east", "west"])
    region = rng.choice(regions, size=n, p=[0.24, 0.27, 0.25, 0.24])
    region_margin = {"north": 180.0, "south": -90.0, "east": 80.0, "west": -40.0}
    capacity = np.clip(rng.normal(100.0, 15.0, n), 55.0, 150.0)
    baseline_margin = np.clip(
        9_500.0
        + 34.0 * capacity
        + np.array([region_margin[x] for x in region])
        + rng.normal(0.0, 1_150.0, n),
        6_000.0,
        None,
    )
    baseline_stockout = np.clip(
        0.105 - 0.00028 * capacity + rng.normal(0.0, 0.014, n), 0.015, 0.18
    )

    # Randomize within region. Odd strata receive their extra treated unit in a
    # seeded random order so allocation remains exactly 1:1 overall.
    treatment = np.zeros(n, dtype=int)
    region_indices = {name: np.flatnonzero(region == name) for name in regions}
    treated_targets = {name: len(indices) // 2 for name, indices in region_indices.items()}
    remaining = n // 2 - sum(treated_targets.values())
    odd_regions = [name for name, indices in region_indices.items() if len(indices) % 2]
    for name in rng.permutation(odd_regions)[:remaining]:
        treated_targets[str(name)] += 1
    for name, indices in region_indices.items():
        selected = rng.permutation(indices)[: treated_targets[name]]
        treatment[selected] = 1
    true_effect = float(config["data_generating_process"]["gross_margin_effect"])
    stockout_effect = float(config["data_generating_process"]["stockout_rate_effect"])
    post_margin = (
        2_050.0
        + 0.83 * baseline_margin
        + 4.5 * capacity
        + np.array([region_margin[x] for x in region])
        + true_effect * treatment
        + rng.normal(0.0, float(config["data_generating_process"]["outcome_sigma"]), n)
    )
    post_stockout = np.clip(
        0.018
        + 0.62 * baseline_stockout
        + stockout_effect * treatment
        + rng.normal(0.0, 0.010, n),
        0.0,
        0.2,
    )
    return [
        {
            "unit_id": f"DC-{i + 1:04d}",
            "region": str(region[i]),
            "capacity_index": round(float(capacity[i]), 6),
            "baseline_gross_margin": round(float(baseline_margin[i]), 6),
            "baseline_stockout_rate": round(float(baseline_stockout[i]), 8),
            "treatment": int(treatment[i]),
            "post_gross_margin": round(float(post_margin[i]), 6),
            "post_stockout_rate": round(float(post_stockout[i]), 8),
        }
        for i in range(n)
    ]


def write_csv(rows: list[dict], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(source: Path) -> list[dict[str, str]]:
    with source.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_arrays(rows: list[dict[str, str | int | float]]) -> dict[str, np.ndarray]:
    numeric = [
        "capacity_index",
        "baseline_gross_margin",
        "baseline_stockout_rate",
        "treatment",
        "post_gross_margin",
        "post_stockout_rate",
    ]
    arrays = {key: np.array([float(row[key]) for row in rows]) for key in numeric}
    arrays["region"] = np.array([str(row["region"]) for row in rows])
    return arrays
