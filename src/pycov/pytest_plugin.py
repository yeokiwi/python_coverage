"""pytest integration. Registered via entry point ``pytest11 = pycov.pytest_plugin``."""
from __future__ import annotations

import os

from . import collector as _collector, importer, persistence
from .config import Config, load_from_pyproject, merge_cli
from .report import html as html_report, json_report, model as report_model, text as text_report


def pytest_addoption(parser) -> None:
    group = parser.getgroup("pycov", "pycov coverage")
    group.addoption("--pycov", action="store_true", help="Enable pycov coverage")
    group.addoption("--pycov-include", action="append", default=[], help="Path glob to include (repeatable)")
    group.addoption("--pycov-exclude", action="append", default=[], help="Path glob to exclude (repeatable)")
    group.addoption("--pycov-report", default="text", help="Comma-separated: text,json,html,all")
    group.addoption("--pycov-output", default="pycov-report", help="Output directory for json/html")
    group.addoption("--pycov-data-dir", default=".pycov_data", help="Run data directory")
    group.addoption("--pycov-fail-under", type=float, default=None)


def pytest_configure(config) -> None:
    if not config.getoption("--pycov"):
        return
    data_dir = os.path.abspath(config.getoption("--pycov-data-dir"))
    persistence.set_data_dir(data_dir)
    persistence.clean(data_dir)
    pyproject = load_from_pyproject()
    cli_include = config.getoption("--pycov-include")
    cli_exclude = config.getoption("--pycov-exclude")
    cfg = merge_cli(
        pyproject,
        include=cli_include or None,
        exclude=cli_exclude or None,
        data_dir=data_dir,
    )
    config._pycov_cfg = cfg
    importer.install(cfg)
    _collector.get_collector().reset()


def pytest_sessionfinish(session, exitstatus) -> None:
    config = session.config
    if not config.getoption("--pycov"):
        return
    _collector.flush()
    formats = [f.strip() for f in config.getoption("--pycov-report").split(",") if f.strip()]
    output = config.getoption("--pycov-output")
    snap = persistence.load_all(persistence.data_dir())
    report = report_model.build(snap)
    if "text" in formats or "all" in formats:
        import sys

        sys.stdout.write("\n" + text_report.render(report))
    if "json" in formats or "all" in formats:
        os.makedirs(output, exist_ok=True)
        with open(os.path.join(output, "coverage.json"), "w") as fh:
            fh.write(json_report.render(report))
    if "html" in formats or "all" in formats:
        html_report.write(report, output)
    threshold = config.getoption("--pycov-fail-under")
    if threshold is not None:
        t = report["totals"]["statements"]
        pct = 100.0 * t["covered"] / t["total"] if t["total"] else 100.0
        if pct < threshold:
            session.exitstatus = 2
