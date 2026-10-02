"""Generate labeled software-only example evidence without modifying live history."""

from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyzer.config import load_plan
from analyzer.runner import run_plan
from analyzer.reports import html_report, measurement_csv


def main():
    baseline = load_plan(ROOT / "configs/demo.json")
    records = []
    for name in ["normal", "bias", "drift", "timeout", "malformed", "persistent_timeout"]:
        scenario = "timeout" if name == "persistent_timeout" else name
        simulation = replace(baseline.simulation, scenario=scenario, fault_every=1 if name == "persistent_timeout" else 7)
        result = run_plan(replace(baseline, simulation=simulation))
        directory = ROOT / "sample_results" / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        (directory / "measurements.csv").write_text(measurement_csv(result), encoding="utf-8")
        (directory / "report.html").write_text(html_report(result), encoding="utf-8")
        records.append({"scenario": name, "status": result["status"],
                        "passed_readings": sum(t["pass_count"] for t in result["results"]),
                        "failed_readings": sum(t["fail_count"] for t in result["results"]),
                        "unresolved_errors": sum(t["error_count"] for t in result["results"]),
                        "failed_attempts": sum(t["failed_attempts"] for t in result["results"])})
    (ROOT / "sample_results" / "summary.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
