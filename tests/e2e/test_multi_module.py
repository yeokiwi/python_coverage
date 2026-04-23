"""End-to-end: `pycov run` with a package that has multiple modules."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _env():
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    src = os.path.join(ROOT, "src")
    env["PYTHONPATH"] = src + (os.pathsep + pythonpath if pythonpath else "")
    return env


def test_multi_module_package(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "math_ops.py").write_text(textwrap.dedent(
        """
        def clamp(x, lo, hi):
            if x < lo:
                return lo
            if x > hi:
                return hi
            return x
        """
    ))
    (pkg / "driver.py").write_text(textwrap.dedent(
        """
        from mypkg.math_ops import clamp

        def run():
            return [clamp(v, 0, 10) for v in (-1, 5, 11)]
        """
    ))
    entry = tmp_path / "main.py"
    entry.write_text(textwrap.dedent(
        """
        import sys
        sys.path.insert(0, '.')
        from mypkg.driver import run
        print(run())
        """
    ))

    out = tmp_path / "report"
    cmd = [
        sys.executable, "-m", "pycov", "run",
        "--data-dir", str(tmp_path / "data"),
        "--output", str(out),
        "--report", "json",
        "--include", f"{tmp_path}/*",
        str(entry),
    ]
    r = subprocess.run(cmd, env=_env(), capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    payload = json.loads((out / "coverage.json").read_text())

    paths = list(payload["files"])
    # main.py, mypkg/__init__.py, mypkg/math_ops.py, mypkg/driver.py
    assert any(p.endswith("main.py") for p in paths)
    assert any(p.endswith("math_ops.py") for p in paths)
    assert any(p.endswith("driver.py") for p in paths)

    # math_ops.clamp was called with three values that cover both branches
    # of the first `if` (x < lo) and only True of the second (x > hi) — plus
    # the fall-through. Expect decisions[total] >= 4 (two decisions, T+F each).
    ops = next(v for k, v in payload["files"].items() if k.endswith("math_ops.py"))
    assert ops["decisions"]["total"] == 4
    assert ops["decisions"]["covered"] == 4  # all four (T/F of both decisions) hit
