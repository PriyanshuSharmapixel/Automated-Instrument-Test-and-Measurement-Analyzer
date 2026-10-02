"""Behavioral checks of decisions, failure recovery, persistence and exports."""

from dataclasses import replace
import csv
import io
import json
import math
import pytest
from analyzer.config import Plan, Simulation, TestCase as Case, parse_plan
from analyzer.instrument import SimulatedInstrument
from analyzer.reports import export_run, html_report, measurement_csv
from analyzer.runner import parse_reading, run_plan, statistics, within_limit
from analyzer.storage import RunStore


def plan(**settings):
    return Plan("Test plan", (Case("Reference", 1e6, 1, 100, 0.02, 20),), Simulation(**settings))


@pytest.mark.parametrize("value,expected", [(99, True), (101, True), (98.999, False), (101.001, False), (math.nan, False)])
def test_inclusive_limits(value, expected):
    assert within_limit(value, 100, 1) is expected


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "broken"])
def test_invalid_measurements(raw):
    with pytest.raises(ValueError):
        parse_reading(raw)


@pytest.mark.parametrize("changes", [{"repeats": True}, {"repeats": 1}, {"amplitude_v": math.nan}, {"frequency_hz": 0}, {"frequency_tolerance_hz": -1}])
def test_invalid_cases(changes):
    fields = dict(name="a", frequency_hz=100, amplitude_v=1, frequency_tolerance_hz=1, amplitude_tolerance_v=0.1, repeats=20)
    with pytest.raises(ValueError):
        Case(**(fields | changes))


def test_configuration_rejects_unknown_and_duplicate_fields():
    data = plan().to_dict()
    with pytest.raises(ValueError):
        parse_plan(data | {"typo": 1})
    data["tests"] = [data["tests"][0], data["tests"][0]]
    with pytest.raises(ValueError):
        parse_plan(data)


def test_reproducible_samples_and_normal_pass():
    a, b = run_plan(plan()), run_plan(plan())
    assert a["status"] == "PASS"
    assert a["results"] == b["results"]
    assert a["run_id"] != b["run_id"]


@pytest.mark.parametrize("scenario", ["bias", "drift"])
def test_fault_scenarios_fail(scenario):
    result = run_plan(plan(scenario=scenario))
    assert result["status"] == "FAIL"
    assert result["results"][0]["fail_count"] > 0


@pytest.mark.parametrize("scenario", ["timeout", "malformed"])
def test_recovered_attempts_remain_visible(scenario):
    result = run_plan(plan(scenario=scenario))
    test = result["results"][0]
    assert result["status"] == "PASS"
    assert test["failed_attempts"] > 0 and test["error_count"] == 0
    assert any(r["attempt_count"] == 2 for r in test["samples"])
    assert len(test["attempts"]) == 20 + test["failed_attempts"]


@pytest.mark.parametrize("scenario", ["timeout", "malformed"])
def test_persistent_fault_is_error_not_zero_or_pass(scenario):
    result = run_plan(plan(scenario=scenario, fault_every=1))
    test = result["results"][0]
    assert result["status"] == "ERROR"
    assert test["error_count"] == 20
    assert test["frequency"]["mean"] is None
    assert test["failed_attempts"] == 40
    json.dumps(result, allow_nan=False)


def test_no_retries_records_missing_samples():
    result = run_plan(replace(plan(scenario="timeout"), retries=0))
    assert result["status"] == "ERROR"
    assert result["results"][0]["error_count"] == 2


def test_statistics_sample_std_and_standard_error():
    values = statistics([1, 2, 3], 2)
    assert values["std"] == 1
    assert values["mean_error"] == 0
    assert values["standard_error"] == pytest.approx(1 / math.sqrt(3))
    assert statistics([1], 1)["std"] is None


def test_failing_reading_cannot_be_hidden_by_a_passing_mean():
    class Alternating(SimulatedInstrument):
        def acquire(self):
            self.acquisitions += 1
            return str(1e6 + (200 if self.acquisitions % 2 else -200)), "1"
    result = run_plan(plan(), Alternating(Simulation()))
    test = result["results"][0]
    assert test["frequency"]["mean_error"] == 0
    assert test["status"] == "FAIL" and test["fail_count"] == 20
    assert all(row["attempt_count"] == 1 for row in test["samples"])


def test_device_is_closed_after_unexpected_failure():
    class Broken(SimulatedInstrument):
        def configure(self, case):
            raise RuntimeError("Disconnected")
    device = Broken(Simulation())
    result = run_plan(plan(), device)
    assert result["status"] == "ERROR" and device.closed


def test_storage_round_trip_and_duplicate_guard(tmp_path):
    result = run_plan(plan())
    store = RunStore(tmp_path / "runs.db")
    store.save(result)
    assert store.get(result["run_id"]) == result
    assert store.list_runs()[0]["status"] == "PASS"
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        store.save(result)
    with pytest.raises(KeyError):
        store.get("missing")


def test_reports_and_html_escaping(tmp_path):
    result = run_plan(replace(plan(), title="<script>bad</script>"))
    rows = list(csv.DictReader(io.StringIO(measurement_csv(result))))
    assert len(rows) == 20 and rows[0]["status"] == "PASS"
    assert "<script>bad</script>" not in html_report(result)
    assert "&lt;script&gt;" in html_report(result)
    directory = export_run(result, tmp_path)
    assert json.loads((directory / "run.json").read_text()) == result
    assert (directory / "report.html").is_file()
