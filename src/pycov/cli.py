"""pycov command-line interface."""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .config import Config, load_from_pyproject, merge_cli
from .persistence import clean as clean_data, load_all, set_data_dir
from .report import html as html_report, json_report, model as report_model, text as text_report
from .runner import run_module, run_script


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--include", action="append", default=[], help="Glob to include (repeatable)")
    p.add_argument("--exclude", action="append", default=[], help="Glob to exclude (repeatable)")
    p.add_argument("--data-dir", default=".pycov_data", help="Where run data is written/read")


def _add_report_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--report",
        default="text",
        help="Comma-separated: text,json,html,all (default: text)",
    )
    p.add_argument("--output", default="pycov-report", help="Output directory for json/html")
    p.add_argument("--fail-under", type=float, default=None, help="Fail if statement coverage percent is below this")
    p.add_argument("--json-include-raw", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pycov", description="Python statement, decision, MC/DC coverage")
    p.add_argument("--version", action="version", version=f"pycov {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Instrument and run a script")
    _add_common(run_p)
    _add_report_flags(run_p)
    run_p.add_argument("--no-report", action="store_true", help="Skip auto-report after run")
    run_p.add_argument("-m", "--module", help="Run a module instead of a script")
    run_p.add_argument("target", nargs="?", help="Script path to run")
    run_p.add_argument("args", nargs=argparse.REMAINDER, help="Script arguments")

    rep_p = sub.add_parser("report", help="Render a report from saved data")
    _add_common(rep_p)
    _add_report_flags(rep_p)

    clean_p = sub.add_parser("clean", help="Remove saved coverage data")
    _add_common(clean_p)

    return p


def _config_from(args) -> Config:
    pyproject = load_from_pyproject()
    return merge_cli(
        pyproject,
        include=args.include or None,
        exclude=args.exclude or None,
        data_dir=args.data_dir if args.data_dir != ".pycov_data" else None,
    )


def _render(report, snap, formats: list[str], output: str, include_raw: bool) -> None:
    if "text" in formats or "all" in formats:
        sys.stdout.write(text_report.render(report))
    if "json" in formats or "all" in formats:
        os.makedirs(output, exist_ok=True)
        with open(os.path.join(output, "coverage.json"), "w") as fh:
            fh.write(json_report.render(report, include_raw=include_raw, snapshot=snap))
    if "html" in formats or "all" in formats:
        html_report.write(report, output)


def _fail_under(report, threshold) -> int:
    if threshold is None:
        return 0
    t = report["totals"]["statements"]
    pct = 100.0 * t["covered"] / t["total"] if t["total"] else 100.0
    if pct < threshold:
        sys.stderr.write(f"pycov: statement coverage {pct:.2f}% < {threshold:.2f}%\n")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    set_data_dir(os.path.abspath(args.data_dir))
    config = _config_from(args)

    if args.cmd == "clean":
        n = clean_data(args.data_dir)
        sys.stderr.write(f"pycov: removed {n} data file(s) from {args.data_dir}\n")
        return 0

    formats = [f.strip() for f in args.report.split(",") if f.strip()]

    if args.cmd == "run":
        # clean previous data for this run so `pycov run` is idempotent
        clean_data(args.data_dir)
        if args.module:
            rc = run_module(args.module, args.args or [], config)
        else:
            if not args.target:
                parser.error("run requires TARGET or --module MOD")
            rc = run_script(args.target, args.args or [], config)
        # flush happens via atexit; but we need data on disk before reporting
        from .collector import flush as _flush

        _flush()
        if args.no_report:
            return rc
        snap = load_all(args.data_dir)
        report = report_model.build(snap)
        _render(report, snap, formats, args.output, args.json_include_raw)
        fu = _fail_under(report, args.fail_under)
        return rc or fu

    if args.cmd == "report":
        snap = load_all(args.data_dir)
        report = report_model.build(snap)
        _render(report, snap, formats, args.output, args.json_include_raw)
        return _fail_under(report, args.fail_under)

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
