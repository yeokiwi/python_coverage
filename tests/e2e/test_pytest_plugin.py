"""End-to-end: the pytest plugin collects coverage during a nested pytest run."""
from __future__ import annotations

import os

pytest_plugins = ["pytester"]


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pytest_plugin_emits_json(pytester, monkeypatch):
    monkeypatch.syspath_prepend(os.path.join(ROOT, "src"))
    pytester.makepyfile(
        target="""
        def pick(x):
            if x > 0 and x < 10:
                return 'ok'
            return 'bad'
        """,
        test_target="""
        from target import pick

        def test_in_range():
            assert pick(5) == 'ok'
        """,
    )
    # Make the pycov entry point discoverable inside the nested pytest run.
    monkeypatch.setenv("PYTHONPATH", os.path.join(ROOT, "src"))
    result = pytester.runpytest_subprocess(
        "--pycov",
        f"--pycov-include={pytester.path}/*",
        "--pycov-report=text,json",
        f"--pycov-output={pytester.path}/pycov_out",
        f"--pycov-data-dir={pytester.path}/pycov_data",
        "test_target.py",
    )
    assert result.ret == 0
    # JSON output
    import json

    out = pytester.path / "pycov_out" / "coverage.json"
    assert out.exists()
    payload = json.loads(out.read_text())
    # Both the test file and the module it imports should be instrumented.
    paths = list(payload["files"])
    assert any(p.endswith("/test_target.py") for p in paths), paths
    assert any(p.endswith("/target.py") and not p.endswith("/test_target.py") for p in paths), paths
    target_rep = next(v for k, v in payload["files"].items() if k.endswith("/target.py") and not k.endswith("/test_target.py"))
    # `pick(5)` exercises both inner conditions True; we should have 1 decision.
    assert target_rep["decisions"]["total"] == 2  # T/F per decision * 1 decision
