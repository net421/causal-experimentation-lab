"""Generate evidence files from the computed experiment results."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def write_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_robustness_csv(results: dict, path: Path) -> None:
    rows = []
    for label in ["classical_standard_error", "winsorized_outcome", "placebo_baseline_difference"]:
        result = results["robustness"][label]
        rows.append({"check": label, **{k: result[k] for k in ["estimate", "standard_error", "ci_low", "ci_high", "p_value"]}})
    for region, result in results["robustness"]["leave_one_region_out"].items():
        rows.append({"check": f"leave_out_{region}", **{k: result[k] for k in ["estimate", "standard_error", "ci_low", "ci_high", "p_value"]}})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_report(results: dict, config: dict, path: Path) -> None:
    primary = results["primary"]["adjusted"]
    secondary = results["secondary"]["stockout_rate_adjusted"]
    gates = "\n".join(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`" for name, passed in results["decision"]["gates"].items()
    )
    balance = "\n".join(
        f"- `{name}`: {_fmt(value, 3)}" for name, value in results["balance_standardized_mean_differences"].items()
    )
    limitations = "\n".join(f"- {item}" for item in results["limitations"])
    text = f"""# Experiment results: {results['experiment_id']}

Generated from the committed pipeline. Values below are computed, not manually entered.

## Question and design

Does a simulated priority-replenishment intervention increase 8-week gross margin per distribution center? The synthetic experiment assigns {results['sample']['total']} centers exactly 1:1 to intervention or control with seed `{config['seed']}`. The primary estimand is the intention-to-treat average effect.

## Primary result

The pre-specified ANCOVA estimate is **${_fmt(primary['estimate'])} per center** (95% CI ${_fmt(primary['ci_low'])} to ${_fmt(primary['ci_high'])}; large-sample two-sided p={primary['p_value']:.6g}). It adjusts for baseline gross margin, baseline stockout rate, capacity, and region; HC1 robust standard errors are used.

The unadjusted difference is ${_fmt(results['primary']['unadjusted']['estimate'])}. The minimum practical effect was pre-specified as ${_fmt(config['minimum_practical_effect'])}.

The secondary adjusted stockout-rate estimate is **{_fmt(100 * secondary['estimate'], 2)} percentage points** (95% CI {_fmt(100 * secondary['ci_low'], 2)} to {_fmt(100 * secondary['ci_high'], 2)}).

## Power and allocation

- Required sample per arm: {results['power']['required_per_arm']}
- Actual sample per arm: {results['power']['actual_per_arm']}
- Approximate planned power at the minimum practical effect: {results['power']['approximate_planned_power']:.3f}
- Target power: {results['power']['target']:.2f}

## Baseline balance

Absolute standardized mean differences must be no larger than {config['balance_smd_limit']}.

{balance}

## Decision gates

{gates}

Machine status: **{results['decision']['machine_status']}**. Deployment is **not authorized** by this analysis. A human reviewer must assess operational feasibility, harm, cost, and external validity.

## Decision implication

If a real randomized pilot produced evidence of comparable quality and passed safety and cost review, the result would justify consideration of a controlled rollout rather than immediate broad deployment. This synthetic exercise demonstrates the decision process only; it is not evidence that the intervention works in a real supply chain.

## Limitations

{limitations}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_human_review(results: dict, path: Path) -> None:
    status = results["decision"]["machine_status"]
    text = f"""# Human review packet

## Automated evidence status

The pipeline status is **{status}**. This is an invitation to review evidence, not a deployment decision. Automated deployment authorization is fixed to `false`.

## Required review record

A real-world decision must be recorded in an external governed system by an accountable reviewer. The record must include reviewer identity, date, decision (`approve pilot`, `request changes`, or `reject`), rationale, budget impact, affected groups, rollback trigger, and monitoring owner. This repository deliberately contains no fabricated signature or approval.

## Review questions

1. Is the treatment operationally defined well enough to reproduce?
2. Are margin, stockouts, service level, and customer harm measured together?
3. Is randomization feasible without contamination between centers?
4. Are implementation cost and capacity constraints included in the business case?
5. Is there a rollback threshold and a named monitoring owner?
6. Does the real pilot population match the population for which a decision is proposed?

## Current authorization

- Evidence review may proceed: `{str(status == 'eligible_for_human_review').lower()}`
- Pilot authorized by this repository: `false`
- Production rollout authorized by this repository: `false`
"""
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(
    paths: list[Path], root: Path, destination: Path, provenance_root: Path | None = None
) -> None:
    provenance_root = provenance_root or root
    provenance_paths = [
        provenance_root / "config/experiment.json",
        provenance_root / "docs/hypotheses/register.json",
        provenance_root / "pyproject.toml",
        provenance_root / "requirements-lock.txt",
        provenance_root / "runtime-lock.json",
        *sorted((provenance_root / "src/causal_lab").glob("*.py")),
    ]
    manifest = {
        "manifest_version": 2,
        "runtime": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy": version("numpy"),
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "provenance": [
            {
                "path": str(path.relative_to(provenance_root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in provenance_paths
        ],
        "files": [
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(paths)
        ],
    }
    write_json(manifest, destination)
