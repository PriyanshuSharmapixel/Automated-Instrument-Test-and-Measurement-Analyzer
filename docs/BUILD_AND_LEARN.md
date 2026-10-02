# Build, understand, and personalize the project

The code is supplied as a working starting version. Before putting it on your resume, run it, understand its decisions, and make at least one meaningful improvement yourself.

## First run: 30–60 minutes

1. Follow the Windows or WSL setup in README.md.
2. Run the normal plan and open the HTML report.
3. Change the scenario to bias: locate the out-of-limit readings.
4. Try timeout with one retry, then zero retries. Explain why recovered attempts differ from unresolved errors.
5. Change `fault_every` to 1. Confirm that missing measurements produce ERROR, not PASS.
6. Run pytest and inspect one boundary test and one storage test.

## Stage 1 — Configuration and limits

Read `config.py` and the JSON. Learn dataclasses, type annotations, exceptions, and validation. Add a third reference test with a new target and explain the units. Write down what happens at the exact lower and upper limits.

## Stage 2 — Instrument interface

Read `instrument.py`. An interface is a contract: the runner needs identification, configuration, acquisition, and cleanup. The simulator fulfills this contract, so the analysis code does not depend on how readings are acquired.

Observe the difference between a write command that changes settings and a query that returns data. The included command strings are illustrative only. Explain why real instruments need their own model-specific adapters.

## Stage 3 — Runner and failure handling

Read `runner.py`. Follow one sample through both attempts. Check how TimeoutError differs from a valid reading outside tolerance. Investigate `finally`: it closes the device even after an unexpected failure.

Exercise: add a new simulator scenario that produces a single sudden amplitude spike. Add a behavioral test that confirms the run fails even when most measurements pass.

## Stage 4 — Statistics

Recalculate the mean and sample standard deviation of five exported readings manually. Explain why sample standard deviation uses n−1, why standard error falls with sample count under its assumptions, and why neither statistic establishes actual hardware accuracy.

Exercise: add a median and maximum absolute measurement error. Verify both on a known small array before displaying them in the dashboard.

## Stage 5 — Database and reports

Read `storage.py` and `reports.py`. Explain parameterized SQL, the run ID primary key, a transaction, and the difference between CSV measurements and full JSON evidence. SQLite stores the complete run as JSON, with indexed metadata; it is not a normalized per-measurement schema.

Exercise: compare the means of two saved runs in the dashboard, showing the scenarios and tolerances beside the comparison. Do not compare incompatible targets without saying so.

## Stage 6 — Dashboard and regression checks

Read `app.py` and `tests/test_dashboard.py`. Understand Streamlit reruns, session state, and why persistent history is stored in SQLite. AppTest exercises the dashboard without requiring a browser. It checks execution, not pixel-perfect visual layout.

Exercise: add a visible count of recovered samples. Confirm that selecting an old run displays its original configuration.

## Stage 7 — Portfolio presentation

Take screenshots of normal PASS, biased FAIL, and unresolved ERROR. Add a short demo video explaining the workflow and one real bug you fixed. Upload the project to GitHub and check that its Actions workflow passes. Keep generated databases, logs, and virtual environments out of the repository.

## Interview questions to prepare

- Why use an instrument interface rather than write everything in one function?
- Why do you retry communication errors but not out-of-limit measurements?
- How can a mean pass while individual readings fail?
- What happens if an instrument returns NaN or an invalid string?
- How does a seed make the simulation repeatable?
- What is stored in SQLite and how are duplicate runs handled?
- What does the test suite verify, and what does it not establish?
- What must change to support a real oscilloscope or spectrum analyzer?
- Why does this version not need ML?
- How would you test a real hardware adapter without equipment in every CI run?

## Resume wording after you understand and verify the project

Use these as starting points and adjust them to work you have actually performed:

- Developed a Python tool for automated simulated instrument tests, with configuration-driven frequency and amplitude limits and per-reading pass/fail decisions.
- Added response validation, bounded retries, acquisition logs, and SQLite run history to investigate missing and out-of-limit measurements.
- Built a Streamlit dashboard and CSV/JSON/HTML reports for measurement analysis, supported by automated behavior and interface tests.

Only add measured performance numbers after recording a repeatable benchmark. Keep the word "simulated" until real hardware has been integrated and validated.
