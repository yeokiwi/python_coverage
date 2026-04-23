"""End-to-end: fizzbuzz JSON coverage has the properties we expect.

These checks verify the shape and a few concrete numeric outcomes rather
than pinning to a brittle full-fixture comparison.
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


def test_fizzbuzz_15_expected_coverage(tmp_path):
    target = os.path.join(ROOT, "examples", "fizzbuzz.py")
    out = tmp_path / "report"
    cmd = [
        sys.executable,
        "-m",
        "pycov",
        "run",
        "--data-dir",
        str(tmp_path / "data"),
        "--output",
        str(out),
        "--report",
        "json",
        "--include",
        f"{ROOT}/examples/*",
        target,
        "15",
    ]
    r = subprocess.run(cmd, env=_env(), capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads((out / "coverage.json").read_text())

    # Exactly one file instrumented.
    file_rep = next(v for k, v in payload["files"].items() if k.endswith("fizzbuzz.py"))

    # Every statement is executed when running with limit=15.
    assert file_rep["statements"]["covered"] == file_rep["statements"]["total"]
    assert file_rep["statements"]["missed_lines"] == []

    # The `classify` function has three `if`s; each True side is taken for
    # some n in 1..15. Plus one decision for the `... if len(argv) > 1 ...`
    # conditional expression, and one for `__name__ == "__main__"`.
    # Exact decisions count can vary if the example changes; we assert a
    # lower bound and that at least one decision had both branches taken.
    assert file_rep["decisions"]["total"] >= 6  # at least 3 decisions * 2 branches
    true_and_false = any(
        d["true_seen"] and d["false_seen"]
        for d in file_rep["decisions"]["decisions"]
    )
    assert true_and_false

    # MC/DC: the outer `n % 3 == 0 and n % 5 == 0` decision has 2 conditions,
    # and with limit=15 the True side fires (n=15). The unique-cause check
    # for "n % 5 == 0" requires observations where only it varied; we expect
    # that one to be covered but "n % 3 == 0" to miss (since n=15 is the
    # only True case and no observation has n % 3 == 0 differing alone while
    # n % 5 == 0 is True).
    outer_dec = next(
        d for d in file_rep["mcdc_unique"]["decisions"]
        if "n % 3" in d["src"] and "n % 5" in d["src"]
    )
    conds = {c["src"]: c for c in outer_dec["conditions"]}
    assert conds["n % 3 == 0"]["covered"] is False
    assert conds["n % 5 == 0"]["covered"] is True

    # Totals must equal the per-file sum (only one file here).
    assert payload["totals"]["statements"]["covered"] == file_rep["statements"]["covered"]
    assert payload["totals"]["statements"]["total"] == file_rep["statements"]["total"]
