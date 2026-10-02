"""Portable CSV/JSON exports and an escaped, standalone HTML report."""

import csv
from html import escape
import io
import json
from pathlib import Path


def measurement_csv(result):
    out = io.StringIO(newline="")
    fields = ["test", "sample", "frequency_hz", "amplitude_v", "frequency_error_hz", "amplitude_error_v", "status", "attempt_count", "error"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for test in result["results"]:
        for sample in test["samples"]:
            f, a = sample["frequency_hz"], sample["amplitude_v"]
            writer.writerow({"test": test["name"], **sample,
                "frequency_error_hz": f - test["case"]["frequency_hz"] if f is not None else None,
                "amplitude_error_v": a - test["case"]["amplitude_v"] if a is not None else None})
    return out.getvalue()


def _fmt(value):
    return "N/A" if value is None else f"{value:.6g}"


def html_report(result):
    blocks = []
    for test in result["results"]:
        table = []
        for key, label in (("frequency", "Frequency (Hz)"), ("amplitude", "Amplitude (V)")):
            stats = test[key]
            table.append(f"<tr><td>{label}</td>" + "".join(f"<td>{_fmt(stats[k])}</td>" for k in ("n", "mean", "std", "standard_error", "mean_error", "min", "max")) + "</tr>")
        case = test["case"]
        failures = [r for r in test["samples"] if r["status"] != "PASS"]
        failed_rows = "".join(f"<tr><td>{r['sample']}</td><td>{r['status']}</td><td>{_fmt(r['frequency_hz'])}</td><td>{_fmt(r['amplitude_v'])}</td><td>{escape(r['error'] or 'Outside configured tolerance')}</td></tr>" for r in failures)
        blocks.append(f"""<section><h2>{escape(test['name'])} <span class='{test['status']}'>{test['status']}</span></h2>
<p>Targets: {case['frequency_hz']:g} Hz ± {case['frequency_tolerance_hz']:g} Hz; {case['amplitude_v']:g} V ± {case['amplitude_tolerance_v']:g} V.</p>
<p>Passed: {test['pass_count']} · Out of limit: {test['fail_count']} · Unresolved errors: {test['error_count']} · Failed acquisition attempts (including recovered): {test['failed_attempts']}</p>
<table><tr><th>Measurement</th><th>Valid n</th><th>Mean</th><th>Sample std</th><th>Std error</th><th>Mean error</th><th>Min</th><th>Max</th></tr>{''.join(table)}</table>
<h3>Failed or missing readings</h3><table><tr><th>Sample</th><th>Status</th><th>Hz</th><th>V</th><th>Reason</th></tr>{failed_rows or '<tr><td colspan="5">None</td></tr>'}</table></section>""")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Measurement report</title>
<style>body{{font:15px system-ui,sans-serif;background:#f4f7fb;color:#17263b;margin:32px auto;padding:0 24px;max-width:1100px}}section{{background:white;border:1px solid #dce3ee;border-radius:10px;padding:20px;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #dde4ed;overflow-wrap:anywhere}}th{{background:#edf2f8}}.PASS{{color:#167344}}.FAIL,.ERROR{{color:#ad302b}}small{{color:#526176}}</style>
<h1>{escape(result['plan']['title'])}</h1><p><b>{result['status']}</b> · {escape(result['mode'])} · {escape(result['created_at'])}</p>
<p>Instrument: {escape(result['instrument'])}<br>Run ID: {escape(result['run_id'])}<br>Execution time: {result['elapsed_seconds']:.4f} seconds</p>
<p>{escape(result['fatal_error'] or '')}</p>{''.join(blocks)}
<small>Simulation results are software-generated, not physical measurements or calibration evidence. Limits apply to every valid reading, inclusively. Missing readings make the test ERROR; a passing mean cannot override a failed reading. Standard error describes simulated repeatability only; it is not a complete measurement uncertainty budget. JSON export includes configuration and all acquisition attempts.</small></html>"""


def export_run(result, directory="outputs"):
    directory = Path(directory) / result["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "measurements.csv").write_text(measurement_csv(result), encoding="utf-8")
    (directory / "run.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    (directory / "report.html").write_text(html_report(result), encoding="utf-8")
    return directory
