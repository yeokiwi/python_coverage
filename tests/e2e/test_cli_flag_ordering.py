"""Regression: pycov flags must be recognised when placed before the target,
and a friendly warning is emitted when they appear after it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _env():
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    src = os.path.join(ROOT, "src")
    env["PYTHONPATH"] = src + (os.pathsep + pythonpath if pythonpath else "")
    return env


def test_flags_before_target_generate_all_reports(tmp_path):
    target = os.path.join(ROOT, "examples", "fizzbuzz.py")
    out = tmp_path / "report"
    cmd = [
        sys.executable, "-m", "pycov", "run",
        "--data-dir", str(tmp_path / "data"),
        "--report", "text,json,html",
        "--output", str(out),
        "--include", f"{ROOT}/examples/*",
        target, "15",
    ]
    r = subprocess.run(cmd, env=_env(), capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (out / "coverage.json").exists()
    assert (out / "index.html").exists()


def test_double_dash_separator_works(tmp_path):
    target = os.path.join(ROOT, "examples", "fizzbuzz.py")
    out = tmp_path / "report"
    cmd = [
        sys.executable, "-m", "pycov", "run",
        "--data-dir", str(tmp_path / "data"),
        "--report", "json",
        "--output", str(out),
        "--include", f"{ROOT}/examples/*",
        "--", target, "15",
    ]
    r = subprocess.run(cmd, env=_env(), capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads((out / "coverage.json").read_text())
    assert any("fizzbuzz.py" in p for p in payload["files"])


def test_misplaced_flags_warn_on_stderr(tmp_path):
    target = os.path.join(ROOT, "examples", "fizzbuzz.py")
    # Deliberately misplaced: --report and --output appear after the target.
    cmd = [
        sys.executable, "-m", "pycov", "run",
        "--data-dir", str(tmp_path / "data"),
        "--include", f"{ROOT}/examples/*",
        target, "15",
        "--report", "text,json,html",
        "--output", str(tmp_path / "report"),
    ]
    r = subprocess.run(cmd, env=_env(), capture_output=True, text=True, cwd=str(tmp_path))
    # Run still succeeds (it still produces a text report on stdout).
    assert r.returncode == 0, r.stderr
    # But the warning tells the user what they did wrong.
    assert "appeared after the target script" in r.stderr
    assert "--report" in r.stderr
    assert "--output" in r.stderr
