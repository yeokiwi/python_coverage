"""Report model + text reporter smoke test."""
from __future__ import annotations

import textwrap

import pytest

from pycov.ast_transform import instrument
from pycov.collector import get_collector
from pycov.report import model as report_model, text as text_report


@pytest.fixture(autouse=True)
def reset_collector():
    get_collector().reset()


def test_full_pipeline_on_tiny_module(tmp_path):
    src = textwrap.dedent(
        """
        def classify(n):
            if n % 3 == 0 and n % 5 == 0:
                return "FB"
            if n % 3 == 0:
                return "F"
            return "x"

        classify(15)
        classify(3)
        classify(1)
        """
    )
    path = str(tmp_path / "m.py")
    with open(path, "w") as fh:
        fh.write(src)
    code, _ = instrument(path, src)
    exec(code, {"__name__": "__main__", "__file__": path})
    snap = get_collector().snapshot()
    report = report_model.build(snap)
    assert path in report["files"]
    out = text_report.render(report)
    assert "TOTAL" in out


def test_text_collapses_missed_ranges():
    from pycov.report.text import _collapse_ranges

    assert _collapse_ranges([1, 2, 3, 5, 6, 10]) == "1-3, 5-6, 10"
    assert _collapse_ranges([]) == ""
