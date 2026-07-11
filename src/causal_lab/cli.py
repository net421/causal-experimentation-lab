"""Command-line entry point for the complete experiment pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyze
from .data import generate_experiment, write_csv
from .reporting import (
    render_human_review,
    render_report,
    write_json,
    write_manifest,
    write_robustness_csv,
)


def run(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    data_path = root / "data/generated/experiment_units.csv"
    results_path = root / "reports/generated/results.json"
    report_path = root / "reports/generated/experiment_report.md"
    robustness_path = root / "reports/generated/robustness_checks.csv"
    review_path = root / "reports/generated/human_review_packet.md"

    rows = generate_experiment(config)
    write_csv(rows, data_path)
    results = analyze(rows, config)
    write_json(results, results_path)
    write_robustness_csv(results, robustness_path)
    render_report(results, config, report_path)
    render_human_review(results, review_path)
    evidence = [data_path, results_path, report_path, robustness_path, review_path]
    source_root = config_path.resolve().parents[1]
    write_manifest(
        evidence,
        root,
        root / "reports/generated/run_manifest.json",
        provenance_root=source_root,
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the causal experiment end to end")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config.resolve() if args.config else root / "config/experiment.json"
    results = run(root, config_path)
    primary = results["primary"]["adjusted"]
    print(
        f"{results['experiment_id']}: adjusted effect={primary['estimate']:.2f}, "
        f"95% CI [{primary['ci_low']:.2f}, {primary['ci_high']:.2f}], "
        f"status={results['decision']['machine_status']}"
    )


if __name__ == "__main__":
    main()
