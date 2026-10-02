# Validation record — 2026-10-02

This version was exercised locally with Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, Streamlit 1.64.0 and pytest 9.1.1.

## Executed checks

- `python -m pytest -q`: **33 passed**.
- CLI subprocess tests: normal exits 0, bias exits 1, persistent timeout exits 2. Each produces SQLite history and an HTML report.
- Invalid CLI configuration exits 2 with an actionable error.
- Dashboard AppTest: initial load, normal PASS, biased FAIL, persisted history, and revisiting the original PASS run.
- Editable package installation with `python -m pip install --no-deps --no-build-isolation -e .`.
- Generated six labeled example runs with CSV, full JSON, HTML reports, and `sample_results/summary.json`.

## Example outcomes

Each example uses the supplied two-test plan with 40 requested readings and seed 42.

| Scenario | Run status | Passed readings | Out-of-limit readings | Unresolved errors | Failed attempts |
| --- | --- | ---: | ---: | ---: | ---: |
| normal | PASS | 40 | 0 | 0 | 0 |
| bias | FAIL | 0 | 40 | 0 | 0 |
| drift | FAIL | 3 | 37 | 0 | 0 |
| timeout, retries enabled | PASS | 40 | 0 | 0 | 6 |
| malformed, retries enabled | PASS | 40 | 0 | 0 | 6 |
| persistent timeout | ERROR | 0 | 0 | 40 | 80 |

The last scenario injects a timeout every acquisition; the others use an interval of seven. These outcomes validate configured software behavior. They are not accuracy, fault-detection, or reliability benchmarks on real equipment.

## Scope of evidence

Automated tests verify limit boundaries, finite response parsing, configuration rejection, repeatability, injected failures, bounded retry behavior, device cleanup, SQLite round trips, report escaping, CLI exit codes, and dashboard flows.

Physical hardware, actual R&S command compatibility, Windows execution, and full visual browser layout were not tested. Python 3.11/3.12 CI is configured but has not run on GitHub here. Requirements specify compatible version ranges; future installations can resolve different versions. The recorded environment above identifies this validation run.
