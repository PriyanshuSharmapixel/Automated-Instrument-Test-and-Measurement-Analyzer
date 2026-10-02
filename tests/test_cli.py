"""Check the user's command end-to-end, including non-passing exit codes."""

import json
from pathlib import Path
import subprocess
import sys
import pytest
from analyzer.config import load_plan

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario,fault_every,expected", [("normal", 7, 0), ("bias", 7, 1), ("timeout", 1, 2)])
def test_cli_outcomes_and_exported_reports(tmp_path, scenario, fault_every, expected):
    config = load_plan(ROOT / "configs/demo.json").to_dict()
    config["simulation"].update(scenario=scenario, fault_every=fault_every)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(config))
    output = tmp_path / "outputs"
    process = subprocess.run([sys.executable, "-m", "analyzer.cli", "--config", str(path), "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
    assert process.returncode == expected, process.stderr
    assert len(list(output.glob("*/report.html"))) == 1
    assert (output / "runs.sqlite3").is_file()


def test_cli_invalid_config_has_clear_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"tests": []}')
    process = subprocess.run([sys.executable, "-m", "analyzer.cli", "--config", str(path), "--output", str(tmp_path / "out")], cwd=ROOT, capture_output=True, text=True)
    assert process.returncode == 2
    assert "Invalid configuration" in process.stderr
