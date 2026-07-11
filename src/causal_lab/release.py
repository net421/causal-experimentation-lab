"""Fail-closed validation and normalized release envelope for causal evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

CORE_EVIDENCE = {
    "data/generated/experiment_units.csv",
    "reports/generated/results.json",
    "reports/generated/experiment_report.md",
    "reports/generated/robustness_checks.csv",
    "reports/generated/human_review_packet.md",
}
REQUIRED_COLUMNS = {
    "unit_id", "region", "capacity_index", "baseline_gross_margin",
    "baseline_stockout_rate", "treatment", "post_gross_margin", "post_stockout_rate",
}
NUMERIC_COLUMNS = {
    "capacity_index", "baseline_gross_margin", "baseline_stockout_rate",
    "post_gross_margin", "post_stockout_rate",
}
ALLOWED_REGIONS = {"north", "south", "east", "west"}
REQUIRED_GATES = {
    "point_estimate_meets_practical_threshold",
    "confidence_interval_excludes_zero",
    "primary_p_value_within_alpha",
    "planned_power_meets_target",
    "covariate_balance_within_limit",
    "randomization_inference_supports_effect",
    "leave_one_region_out_effects_positive",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and value not in {"", "."}


def validate_manifest(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = _load_json(root / "reports/generated/run_manifest.json")
    _check(checks, "manifest_version", int(manifest.get("manifest_version", 0)) >= 2,
           f"version={manifest.get('manifest_version')}")
    entries = list(manifest.get("files", [])) + list(manifest.get("provenance", []))
    paths = [str(item.get("path", "")) for item in entries]
    _check(checks, "manifest_unique_paths", len(paths) == len(set(paths)), f"entries={len(paths)}")
    _check(checks, "manifest_core_evidence_coverage", CORE_EVIDENCE.issubset(set(paths)),
           f"covered={len(CORE_EVIDENCE.intersection(paths))}/{len(CORE_EVIDENCE)}")
    all_valid = True
    for item in entries:
        relative = str(item.get("path", ""))
        valid_path = _safe_relative_path(relative)
        path = root / relative if valid_path else root / "__invalid_manifest_path__"
        valid = (
            valid_path and path.is_file()
            and path.stat().st_size == int(item.get("bytes", -1))
            and _sha256(path) == item.get("sha256")
        )
        all_valid = all_valid and valid
    _check(checks, "manifest_hashes_and_sizes", all_valid, f"validated_entries={len(entries)}")
    return manifest


def validate_dataset(root: Path, config: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    with (root / "data/generated/experiment_units.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        rows = list(reader)
    expected_n = int(config["sample_size_total"])
    _check(checks, "dataset_required_columns", REQUIRED_COLUMNS.issubset(columns), f"columns={len(columns)}")
    _check(checks, "dataset_expected_row_count", len(rows) == expected_n, f"rows={len(rows)}")
    unit_ids = [row.get("unit_id", "") for row in rows]
    _check(checks, "dataset_unique_nonempty_unit_ids",
           len(unit_ids) == len(set(unit_ids)) and all(unit_ids), f"unique={len(set(unit_ids))}")
    no_missing = all(all(str(row.get(column, "")).strip() for column in REQUIRED_COLUMNS) for row in rows)
    _check(checks, "dataset_no_missing_required_values", no_missing, f"rows={len(rows)}")
    treatments: list[int] = []
    finite_numeric = bounded_stockouts = valid_treatment = valid_regions = True
    for row in rows:
        try:
            treatment = int(row["treatment"])
            treatments.append(treatment)
            valid_treatment = valid_treatment and treatment in {0, 1}
            for column in NUMERIC_COLUMNS:
                finite_numeric = finite_numeric and math.isfinite(float(row[column]))
            bounded_stockouts = bounded_stockouts and all(
                0.0 <= float(row[column]) <= 1.0
                for column in ("baseline_stockout_rate", "post_stockout_rate")
            )
            valid_regions = valid_regions and row["region"] in ALLOWED_REGIONS
        except (KeyError, TypeError, ValueError):
            valid_treatment = finite_numeric = bounded_stockouts = valid_regions = False
    treated = sum(value == 1 for value in treatments)
    control = sum(value == 0 for value in treatments)
    _check(checks, "dataset_binary_treatment", valid_treatment, f"observations={len(treatments)}")
    _check(checks, "dataset_exact_one_to_one_allocation", treated == control == expected_n // 2,
           f"treated={treated}, control={control}")
    _check(checks, "dataset_finite_numeric_values", finite_numeric, f"rows={len(rows)}")
    _check(checks, "dataset_stockout_bounds", bounded_stockouts, "expected_range=[0,1]")
    _check(checks, "dataset_allowed_regions", valid_regions, f"allowed={sorted(ALLOWED_REGIONS)}")
    return {"rows": len(rows), "treated": treated, "control": control}


def validate_results(root: Path, config: dict[str, Any], dataset: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    results = _load_json(root / "reports/generated/results.json")
    decision = results.get("decision", {})
    gates = decision.get("gates", {})
    adjusted = results.get("primary", {}).get("adjusted", {})
    sample = results.get("sample", {})
    _check(checks, "results_experiment_id_matches_config",
           results.get("experiment_id") == config.get("experiment_id"), f"experiment_id={results.get('experiment_id')}")
    _check(checks, "results_sample_reconciles_to_dataset",
           sample.get("total") == dataset["rows"] and sample.get("treated") == dataset["treated"] and sample.get("control") == dataset["control"],
           f"sample={sample}")
    _check(checks, "results_required_gates_present", REQUIRED_GATES.issubset(set(gates)),
           f"present={len(REQUIRED_GATES.intersection(gates))}/{len(REQUIRED_GATES)}")
    _check(checks, "results_gate_values_boolean", all(isinstance(value, bool) for value in gates.values()), f"gates={len(gates)}")
    expected_status = "eligible_for_human_review" if gates and all(gates.values()) else "evidence_threshold_not_met"
    _check(checks, "results_machine_status_reconciles", decision.get("machine_status") == expected_status,
           f"status={decision.get('machine_status')}")
    _check(checks, "results_never_authorize_deployment", decision.get("deployment_authorized") is False,
           f"deployment_authorized={decision.get('deployment_authorized')}")
    _check(checks, "results_require_human_review", decision.get("human_review_required") is True,
           f"human_review_required={decision.get('human_review_required')}")
    numeric_fields = ["estimate", "standard_error", "ci_low", "ci_high", "p_value"]
    finite = all(isinstance(adjusted.get(name), (int, float)) and math.isfinite(float(adjusted[name])) for name in numeric_fields)
    _check(checks, "results_primary_values_finite", finite, f"fields={numeric_fields}")
    _check(checks, "results_primary_interval_ordered",
           finite and adjusted["ci_low"] <= adjusted["estimate"] <= adjusted["ci_high"], "ci_low <= estimate <= ci_high")
    _check(checks, "results_primary_p_value_bounded",
           finite and 0.0 <= adjusted["p_value"] <= 1.0, "expected_range=[0,1]")
    practical = float(config["minimum_practical_effect"])
    alpha = float(config["alpha"])
    reconciled = (
        gates.get("point_estimate_meets_practical_threshold") == (adjusted.get("estimate", -math.inf) >= practical)
        and gates.get("confidence_interval_excludes_zero") == (adjusted.get("ci_low", -math.inf) > 0.0)
        and gates.get("primary_p_value_within_alpha") == (adjusted.get("p_value", math.inf) <= alpha)
    )
    _check(checks, "results_primary_gates_reconcile", reconciled, f"mpe={practical}, alpha={alpha}")
    return results


def build_release_envelope(root: Path) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, Any]] = []
    config = _load_json(root / "config/experiment.json")
    manifest = validate_manifest(root, checks)
    dataset = validate_dataset(root, config, checks)
    results = validate_results(root, config, dataset, checks)
    passed = all(item["passed"] for item in checks)
    adjusted = results["primary"]["adjusted"]
    return {
        "schema_version": "1.0.0",
        "experiment_id": results["experiment_id"],
        "evidence_status": "pass" if passed else "fail",
        "machine_status": results["decision"]["machine_status"] if passed else "evidence_validation_failed",
        "design": {
            "type": "randomized_controlled_experiment",
            "allocation": config["allocation"],
            "sample_size_total": dataset["rows"],
            "estimand": results["estimand"],
        },
        "primary_effect": {
            "estimate": adjusted["estimate"],
            "standard_error": adjusted["standard_error"],
            "ci_low": adjusted["ci_low"],
            "ci_high": adjusted["ci_high"],
            "p_value": adjusted["p_value"],
            "minimum_practical_effect": float(config["minimum_practical_effect"]),
        },
        "deployment_authorized": False,
        "human_review_required": True,
        "synthetic_data": True,
        "claim_boundary": (
            "Validated evidence describes a synthetic randomized experiment workflow only; "
            "it does not authorize a pilot or production deployment."
        ),
        "manifest": {
            "version": manifest["manifest_version"],
            "evidence_file_count": len(manifest.get("files", [])),
            "provenance_file_count": len(manifest.get("provenance", [])),
        },
        "checks_passed": sum(item["passed"] for item in checks),
        "check_count": len(checks),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    envelope = build_release_envelope(args.root)
    text = json.dumps(envelope, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if envelope["evidence_status"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
