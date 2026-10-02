"""Streamlit dashboard: configure, execute, inspect, export, and revisit runs."""

from dataclasses import replace
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from analyzer.config import load_plan, parse_plan
from analyzer.reports import html_report, measurement_csv
from analyzer.runner import run_plan
from analyzer.storage import RunStore

ROOT = Path(__file__).resolve().parent
OUTPUT = Path(os.environ.get("ANALYZER_OUTPUT_DIR", str(ROOT / "outputs")))
st.set_page_config(page_title="Instrument Test Analyzer", layout="wide")
st.title("Instrument Test & Measurement Analyzer")
st.caption("Run repeatable tests, inspect measurement limits, and keep the evidence.")
st.info("Software simulation: no physical instrument is connected. Measurements and faults are generated locally.")
store = RunStore(OUTPUT / "runs.sqlite3")

with st.sidebar:
    st.header("Test setup")
    uploaded = st.file_uploader("Optional test plan (JSON)", type=["json"])
    scenario = st.selectbox("Scenario", ["normal", "bias", "drift", "timeout", "malformed"])
    st.caption("Bias adds an offset. Drift grows across a test. Timeout and malformed inject faults at the chosen acquisition interval.")
    seed = st.number_input("Random seed", min_value=0, max_value=4294967295, value=42, step=1)
    retries = st.number_input("Retries per missing/invalid reading", min_value=0, max_value=3, value=1, step=1)
    fault_every = st.number_input("Inject fault every N acquisitions", min_value=1, max_value=1000, value=7, step=1)
    run_clicked = st.button("Run test plan", type="primary", use_container_width=True)
    st.caption("Noise and measurement targets come from the JSON plan. The controls above override its seed, scenario, retries and fault interval.")

try:
    plan = parse_plan(json.loads(uploaded.getvalue().decode("utf-8"))) if uploaded else load_plan(ROOT / "configs/demo.json")
    plan = replace(plan, retries=int(retries), simulation=replace(plan.simulation, seed=int(seed), scenario=scenario, fault_every=int(fault_every)))
except (ValueError, UnicodeError, OSError) as exc:
    st.error(f"Invalid test plan: {exc}")
    st.stop()

with st.expander("Current targets and limits", expanded=True):
    st.dataframe(pd.DataFrame([t.__dict__ for t in plan.tests]), hide_index=True, use_container_width=True)
    st.download_button("Download current configuration", json.dumps(plan.to_dict(), indent=2), "test-plan.json", "application/json")

if run_clicked:
    with st.spinner("Acquiring simulated measurements..."):
        run = run_plan(plan)
        store.save(run)
        st.session_state["selected_run"] = run["run_id"]

runs = store.list_runs()
if runs:
    with st.sidebar:
        labels = {r["run_id"]: f"{r['created_at'][:19]} | {r['status']} | {r['title']} | {r['run_id'][:8]}" for r in runs}
        ids = list(labels)
        active = st.session_state.get("selected_run", ids[0])
        selected = st.selectbox("Saved runs", ids, index=ids.index(active) if active in ids else 0, format_func=labels.get)
        st.session_state["selected_run"] = selected
    result = store.get(selected)
    st.subheader(f"Run outcome: {result['status']}")
    st.caption(f"Showing saved configuration: {result['plan']['simulation']['scenario']} · seed {result['plan']['simulation']['seed']} · {result['created_at']} · {result['instrument']}")
    if result["fatal_error"]:
        st.error(result["fatal_error"])
    tests = result["results"]
    cols = st.columns(4)
    cols[0].metric("Tests completed", f"{len(tests)}/{len(result['plan']['tests'])}")
    cols[1].metric("Out-of-limit readings", sum(t["fail_count"] for t in tests))
    cols[2].metric("Unresolved errors", sum(t["error_count"] for t in tests))
    cols[3].metric("Failed acquisition attempts", sum(t["failed_attempts"] for t in tests))
    for test in tests:
        st.markdown(f"### {test['name']} — {test['status']}")
        summary, readings, attempts = st.tabs(["Analysis", "Readings", "Acquisition attempts"])
        with summary:
            st.dataframe(pd.DataFrame({"Frequency (Hz)": test["frequency"], "Amplitude (V)": test["amplitude"]}).T, use_container_width=True)
            data = pd.DataFrame(test["samples"])
            for column, target, tolerance, label in (
                ("frequency_hz", "frequency_hz", "frequency_tolerance_hz", "Frequency (Hz)"),
                ("amplitude_v", "amplitude_v", "amplitude_tolerance_v", "Amplitude (V)"),
            ):
                chart = data.set_index("sample")[[column]].rename(columns={column: label})
                chart["Lower limit"] = test["case"][target] - test["case"][tolerance]
                chart["Upper limit"] = test["case"][target] + test["case"][tolerance]
                st.line_chart(chart)
            st.caption("Sample standard deviation uses n−1. Standard error = sample std / √n. Invalid pairs are excluded from statistics and remain recorded as errors.")
        with readings:
            st.dataframe(pd.DataFrame(test["samples"]), hide_index=True, use_container_width=True)
        with attempts:
            st.dataframe(pd.DataFrame(test["attempts"]), hide_index=True, use_container_width=True)
    with st.expander("Simulated command log"):
        st.code("\n".join(result["command_log"]), language="text")
    st.subheader("Export this run")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Measurement CSV", measurement_csv(result), f"{selected}-measurements.csv", "text/csv")
    c2.download_button("Complete JSON", json.dumps(result, indent=2, allow_nan=False), f"{selected}-run.json", "application/json")
    c3.download_button("HTML report", html_report(result), f"{selected}-report.html", "text/html")
else:
    st.write("Choose a scenario and select **Run test plan**. Use the normal scenario first, then bias and timeout to inspect failures and recovery.")
