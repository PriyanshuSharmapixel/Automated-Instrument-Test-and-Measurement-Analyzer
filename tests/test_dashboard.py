"""Exercise actual Streamlit execution without starting a browser/server."""

from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_normal_bias_and_saved_history(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYZER_OUTPUT_DIR", str(tmp_path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.subheader[0].value == "Run outcome: PASS"
    app.selectbox[0].select("bias").run()
    app.button[0].click().run()
    assert not app.exception
    assert app.subheader[0].value == "Run outcome: FAIL"
    assert len(app.selectbox[1].options) == 2
    earlier = app.selectbox[1].value
    ids = list(app.selectbox[1].options)
    # selectbox .options exposes formatted labels; select the original saved ID.
    from analyzer.storage import RunStore
    normal_id = next(r["run_id"] for r in RunStore(tmp_path / "runs.sqlite3").list_runs() if r["status"] == "PASS")
    app.selectbox[1].select(normal_id).run()
    assert not app.exception
    assert app.subheader[0].value == "Run outcome: PASS"
