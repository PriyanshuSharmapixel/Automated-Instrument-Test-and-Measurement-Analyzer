# Automated Instrument Test and Measurement Analyzer

[GitHub repository](https://github.com/PriyanshuSharmapixel/Automated-Instrument-Test-and-Measurement-Analyzer) · [Automated checks](https://github.com/PriyanshuSharmapixel/Automated-Instrument-Test-and-Measurement-Analyzer/actions)

A Python tool for running repeatable **simulated** instrument tests, checking every reading against tolerance limits, analyzing repeatability, and keeping an auditable run history. It includes a command-line runner, a Streamlit dashboard, SQLite storage, and CSV/JSON/HTML reports.

**Version 1 is software-only.** It does not communicate with physical equipment, emulate a specific instrument, or measure an actual signal. The simulator returns numerical frequency and amplitude responses with configurable noise and deliberately injected faults. There are no API keys, paid services, or GPU requirements.

## What problem it solves

An engineer has a list of measurement targets and acceptance limits. Manually taking readings, calculating errors, recording failures, and creating reports is repetitive. This application automates that workflow and preserves the configuration and all acquisition attempts so a result can be investigated later.

Example: verify a nominal 1 MHz reading within ±100 Hz and a nominal 1 V reading within ±0.02 V, repeated 20 times. Both limits must hold on **every valid reading**. A missing reading is an error; a passing average cannot hide a failed sample.

## Capabilities

- JSON test plans containing named tests, targets, limits, and repeat counts.
- Repeatable seeded noise, plus bias, drift, timeout, and malformed-response scenarios.
- An instrument interface that separates acquisition from analysis.
- Inclusive per-reading tolerance checks and distinct PASS / FAIL / ERROR outcomes.
- Bounded retries for timeout/invalid-response errors, with unsuccessful attempts retained.
- Mean, sample standard deviation, standard error, range, and signed mean error.
- SQLite run history with complete JSON snapshots and duplicate-run protection.
- Measurement CSV, full JSON evidence, and standalone HTML reports.
- Dashboard plots with acceptance limits, sample tables, attempt logs, and history.
- Automated behavioral and dashboard tests plus a GitHub Actions workflow.

## Start on Windows (PowerShell)

Install Python 3.11 or newer. Open a terminal in the project root, where `app.py` is located. If starting from GitHub:

```powershell
git clone https://github.com/PriyanshuSharmapixel/Automated-Instrument-Test-and-Measurement-Analyzer.git
cd Automated-Instrument-Test-and-Measurement-Analyzer
```

Then create the environment and launch the dashboard:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Using the environment's Python directly avoids needing to activate a PowerShell script. Streamlit prints the local address, normally `http://localhost:8501`.

Run the command-line workflow:

```powershell
.\.venv\Scripts\python.exe -m analyzer.cli --config configs/demo.json --output outputs
```

Run automated checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Start on Linux / macOS / WSL

```bash
git clone https://github.com/PriyanshuSharmapixel/Automated-Instrument-Test-and-Measurement-Analyzer.git
cd Automated-Instrument-Test-and-Measurement-Analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

From another terminal with the same environment:

```bash
python -m analyzer.cli --config configs/demo.json --output outputs
python -m pytest -q
```

Optional editable installation provides the `instrument-analyzer` command:

```bash
python -m pip install -e '.[dev]'
instrument-analyzer --config configs/demo.json
```

## Try these scenarios

The supplied plan has two tests and 40 requested readings in total.

| Scenario | What is injected | What to inspect |
| --- | --- | --- |
| normal | Small Gaussian noise around each target | PASS, reproducible measurements with the same seed |
| bias | +0.2% frequency offset and +0.1 V amplitude offset | FAIL, consistently shifted readings |
| drift | Growing offset per acquisition | FAIL, a trend that crosses the limits |
| timeout | A simulated TimeoutError every N acquisitions | Failed attempts and recovery with retries enabled |
| malformed | Invalid strings / non-finite values every N acquisitions | Validation and recorded raw responses |

Fault injection is a deterministic software schedule, not a model of a device's real failure rate. Set `fault_every=1` to make every acquisition fail. Set retries to zero to observe unresolved missing readings. Fault schedules restart for each test; the seeded noise generator continues across tests.

The UI's scenario, seed, retry, and fault-interval controls override those values in an uploaded plan. Targets, noise levels, and repeat counts come from the plan. Saved runs display their original configuration even if current controls have changed.

## Configuration

Edit `configs/demo.json` or upload a new JSON file in the dashboard. Units are **Hz** and **V**. Tolerances are absolute, not percentages, and amplitude is a nominal instrument response rather than a waveform-derived RMS value.

```json
{
  "title": "1 MHz verification",
  "simulation": {
    "seed": 42,
    "scenario": "normal",
    "frequency_noise_hz": 10,
    "amplitude_noise_v": 0.002,
    "fault_every": 7
  },
  "retries": 1,
  "tests": [
    {
      "name": "Reference",
      "frequency_hz": 1000000,
      "amplitude_v": 1,
      "frequency_tolerance_hz": 100,
      "amplitude_tolerance_v": 0.02,
      "repeats": 20
    }
  ]
}
```

There must be 1–30 uniquely named tests and 2–1000 readings per test. Retry count is 0–3. Numeric inputs must be finite; targets/tolerances/noise cannot be negative, and frequency must be positive. Unknown configuration fields are rejected.

## How outcomes are decided

For each sample, both frequency and amplitude must fall within target ± tolerance, inclusively.

- **PASS:** all requested samples are valid and within limits.
- **FAIL:** all requested samples are valid, but at least one is outside a limit.
- **ERROR:** at least one sample remains invalid/missing after retries, or an unexpected device error stops the run.

Run status prioritizes ERROR over FAIL over PASS. Out-of-limit measurements are never retried merely to obtain a passing result. An acquisition means a frequency/amplitude pair: if either response is invalid, the whole pair is excluded from summary statistics. Every unsuccessful acquisition attempt remains in the JSON and dashboard, including attempts that subsequently recover.

## Analysis definitions

For n valid readings x and nominal target t:

- Mean: sum(x) / n.
- Sample standard deviation: sqrt(sum((x − mean)^2) / (n − 1)).
- Standard error of the mean: sample standard deviation / sqrt(n).
- Signed mean error: mean − t.
- Per-reading error: reading − t.

No valid readings produces null statistics, never a fabricated zero. A single valid reading has no sample standard deviation or standard error. These statistics describe simulated repeatability; they are not a complete calibration uncertainty budget or proof of hardware accuracy.

## Files and architecture

| File | Responsibility |
| --- | --- |
| `app.py` | Dashboard, history selection, plots, downloads |
| `analyzer/config.py` | Dataclasses and strict JSON validation |
| `analyzer/instrument.py` | Instrument protocol and reproducible simulator |
| `analyzer/runner.py` | Acquisition, retries, decisions, statistics |
| `analyzer/storage.py` | Atomic SQLite run snapshots |
| `analyzer/reports.py` | CSV, JSON, escaped HTML |
| `analyzer/cli.py` | Terminal entry point and exit status |
| `tests/` | Behavior checks and Streamlit AppTest |
| `configs/demo.json` | Ready-to-run two-test plan |
| `sample_results/` | Example runs and reports from this version |
| `docs/BUILD_AND_LEARN.md` | A staged learning plan and interview discussion |
| `.github/workflows/tests.yml` | CI definition for Python 3.11 and 3.12 |

The command-line path saves reports under `outputs/<run-id>/`, a database at `outputs/runs.sqlite3`, and a `runner.log`. The dashboard saves runs in the database and provides report downloads. Neither entry point deletes previous runs. Only simulation samples are deterministic; timestamps, IDs, and execution times vary.

CLI exit codes: 0 = PASS; 1 = FAIL; 2 = ERROR or invalid arguments. FAIL/ERROR still produce reports for successfully started runs. Logs and outputs should stay outside Git; `.gitignore` excludes them.

## Connection to test and measurement engineering

The project demonstrates Python/OOP, configuration-driven testing, response validation, failure investigation, numerical analysis, persistent evidence, and reproducible tests. Those are transferable to engineering automation.

Rohde & Schwarz provides [RsInstrument](https://github.com/Rohde-Schwarz/RsInstrument), a Python communication library for SCPI-based instruments. Its [official examples](https://github.com/Rohde-Schwarz/Examples) provide model-specific starting points.

This project currently **does not use RsInstrument**. Its command log uses a small **illustrative SCPI-style dialect**, not a documented command set for real equipment. An actual hardware adapter would implement `identify`, `configure`, `acquire`, and `close` using the specific instrument's manual and RsInstrument. It needs real-device tests, timeout configuration, settling/trigger handling, command error checks, unit verification, and independent reference measurements before claiming hardware support. Keep simulation and hardware evidence separate.

## Portfolio claims and next steps

Describe this version as a **simulated instrument test automation tool**. Do not describe it as a deployed RF testing system, real-time acquisition tool, calibrated instrument, or a project developed for R&S.

Next useful improvements: compare two runs, add reviewed imported measurement data with provenance, validate against a laboratory instrument, or add waveform/FFT analysis as a separate module. Machine learning is optional; demonstrate reliable acquisition and testing first.

See `VALIDATION.md` for the environment and checks actually executed. Check the repository's Actions tab for the current GitHub CI result.
