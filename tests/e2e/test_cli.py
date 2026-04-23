"""End-to-end: pycov run + pycov report produce JSON and HTML outputs."""
from __future__ import annotations

import json
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pycov_env():
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    src = os.path.join(ROOT, "src")
    env["PYTHONPATH"] = src + (os.pathsep + pythonpath if pythonpath else "")
    return env


def test_pycov_run_fizzbuzz_emits_all_reports(tmp_path):
    target = os.path.join(ROOT, "examples", "fizzbuzz.py")
    out = tmp_path / "report"
    data = tmp_path / "data"
    cmd = [
        sys.executable,
        "-m",
        "pycov",
        "run",
        "--data-dir",
        str(data),
        "--output",
        str(out),
        "--report",
        "text,json,html",
        "--include",
        f"{ROOT}/examples/*",
        target,
        "15",
    ]
    result = subprocess.run(cmd, env=_pycov_env(), capture_output=True, text=True, cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "TOTAL" in result.stdout
    # JSON was written
    json_path = out / "coverage.json"
    assert json_path.exists()
    payload = json.loads(json_path.read_text())
    assert "files" in payload
    assert any("fizzbuzz.py" in p for p in payload["files"])
    # HTML was written
    assert (out / "index.html").exists()
    assert (out / "pycov.css").exists()
