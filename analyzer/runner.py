"""Acquisition, bounded retry, per-reading decisions, and descriptive statistics."""

from datetime import datetime, timezone
import logging
import math
from time import perf_counter
from uuid import uuid4
import numpy as np
from .config import Plan
from .instrument import Instrument, SimulatedInstrument

logger = logging.getLogger(__name__)


def within_limit(value, target, tolerance):
    return math.isfinite(value) and target - tolerance <= value <= target + tolerance


def parse_reading(raw):
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("Instrument returned a non-finite measurement")
    return value


def statistics(values, target):
    if not values:
        return {"n": 0, "mean": None, "std": None, "standard_error": None, "min": None, "max": None, "mean_error": None}
    std = float(np.std(values, ddof=1)) if len(values) > 1 else None
    return {
        "n": len(values), "mean": float(np.mean(values)), "std": std,
        "standard_error": std / math.sqrt(len(values)) if std is not None else None,
        "min": float(min(values)), "max": float(max(values)),
        "mean_error": float(np.mean(values)) - target,
    }


def run_plan(plan: Plan, instrument: Instrument | None = None):
    started = perf_counter()
    device = instrument if instrument is not None else SimulatedInstrument(plan.simulation)
    result = {
        "schema_version": 1, "run_id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "simulation" if isinstance(device, SimulatedInstrument) else "external-adapter",
        "plan": plan.to_dict(), "instrument": "unavailable", "results": [], "fatal_error": None,
    }
    try:
        result["instrument"] = device.identify()
        for case in plan.tests:
            logger.info("Running %s", case.name)
            device.configure(case)
            rows, attempts = [], []
            for index in range(1, case.repeats + 1):
                row = {"sample": index, "frequency_hz": None, "amplitude_v": None,
                       "status": "ERROR", "error": None, "attempt_count": 0}
                for attempt in range(1, plan.retries + 2):
                    raw_f = raw_a = None
                    row["attempt_count"] = attempt
                    try:
                        raw_f, raw_a = device.acquire()
                        f, a = parse_reading(raw_f), parse_reading(raw_a)
                        passed = within_limit(f, case.frequency_hz, case.frequency_tolerance_hz) and within_limit(a, case.amplitude_v, case.amplitude_tolerance_v)
                        row.update(frequency_hz=f, amplitude_v=a, status="PASS" if passed else "FAIL", error=None)
                        attempts.append({"sample": index, "attempt": attempt, "status": "OK", "error": None, "raw_frequency": raw_f, "raw_amplitude": raw_a})
                        break  # Valid out-of-limit readings are NOT retried to obtain a pass.
                    except (TimeoutError, ValueError, OSError) as exc:
                        row["error"] = f"{type(exc).__name__}: {exc}"
                        attempts.append({"sample": index, "attempt": attempt, "status": "ERROR", "error": row["error"], "raw_frequency": raw_f, "raw_amplitude": raw_a})
                        logger.warning("%s sample %d attempt %d: %s", case.name, index, attempt, row["error"])
                rows.append(row)
            valid = [row for row in rows if row["status"] != "ERROR"]
            errors = sum(row["status"] == "ERROR" for row in rows)
            failures = sum(row["status"] == "FAIL" for row in rows)
            result["results"].append({
                "name": case.name, "case": case.__dict__, "samples": rows, "attempts": attempts,
                "status": "ERROR" if errors else "FAIL" if failures else "PASS",
                "pass_count": len(rows) - errors - failures, "fail_count": failures,
                "error_count": errors, "failed_attempts": sum(a["status"] == "ERROR" for a in attempts),
                "frequency": statistics([r["frequency_hz"] for r in valid], case.frequency_hz),
                "amplitude": statistics([r["amplitude_v"] for r in valid], case.amplitude_v),
            })
    except Exception as exc:
        result["fatal_error"] = f"{type(exc).__name__}: {exc}"
        logger.exception("Run stopped unexpectedly")
    finally:
        try:
            device.close()
        except Exception as exc:
            result["fatal_error"] = (result["fatal_error"] or "") + f" Close error: {exc}"
        result["elapsed_seconds"] = perf_counter() - started
        result["command_log"] = list(getattr(device, "command_log", []))
    statuses = [test["status"] for test in result["results"]]
    result["status"] = "ERROR" if result["fatal_error"] or "ERROR" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
    return result
