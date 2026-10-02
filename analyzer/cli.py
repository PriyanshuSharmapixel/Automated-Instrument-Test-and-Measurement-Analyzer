"""Run a plan, persist evidence, and expose outcome through the exit code."""

import argparse
import logging
from pathlib import Path
from .config import load_plan
from .reports import export_run
from .runner import run_plan
from .storage import RunStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/demo.json")
    parser.add_argument("--output", default="outputs")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(output / "runner.log", encoding="utf-8"), logging.StreamHandler()])
    try:
        plan = load_plan(args.config)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    result = run_plan(plan)
    RunStore(output / "runs.sqlite3").save(result)
    directory = export_run(result, output)
    print(f"{result['status']}: {len(result['results'])}/{len(plan.tests)} tests completed. Reports: {directory}")
    return {"PASS": 0, "FAIL": 1, "ERROR": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
