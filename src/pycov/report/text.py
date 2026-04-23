"""Plain-text report."""
from __future__ import annotations

from typing import Any

from .model import percent


def _collapse_ranges(lines: list[int]) -> str:
    if not lines:
        return ""
    lines = sorted(set(lines))
    parts: list[str] = []
    start = prev = lines[0]
    for n in lines[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


def render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    header = f"{'File':<50} {'Stmts':>10} {'Branch':>10} {'MCDC-U':>10} {'MCDC-M':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    for path, f in sorted(report["files"].items()):
        s = f["statements"]
        d = f["decisions"]
        u = f["mcdc_unique"]
        m = f["mcdc_masking"]
        lines.append(
            f"{_short(path):<50} "
            f"{s['covered']}/{s['total']} ({percent(s['covered'], s['total']):>5.1f}%) "
            f"{d['covered']}/{d['total']} ({percent(d['covered'], d['total']):>5.1f}%) "
            f"{u['covered']}/{u['total']} ({percent(u['covered'], u['total']):>5.1f}%) "
            f"{m['covered']}/{m['total']} ({percent(m['covered'], m['total']):>5.1f}%)"
        )
        missed = s["missed_lines"]
        if missed:
            lines.append(f"    missed stmts: {_collapse_ranges(missed)}")
        for dec in d["decisions"]:
            if not (dec["true_seen"] and dec["false_seen"]):
                miss = []
                if not dec["true_seen"]:
                    miss.append("T")
                if not dec["false_seen"]:
                    miss.append("F")
                lines.append(
                    f"    L{dec['lineno']} branch missing {'/'.join(miss)}: {dec['src']}"
                )
        for dec in u["decisions"]:
            for cond in dec["conditions"]:
                if not cond["covered"]:
                    lines.append(
                        f"    L{dec['lineno']} mcdc-unique missing: '{cond['src']}'"
                    )
        for dec in m["decisions"]:
            for cond in dec["conditions"]:
                if not cond["covered"]:
                    lines.append(
                        f"    L{dec['lineno']} mcdc-masking missing: '{cond['src']}'"
                    )
    lines.append("-" * len(header))
    t = report["totals"]
    lines.append(
        f"{'TOTAL':<50} "
        f"{t['statements']['covered']}/{t['statements']['total']} ({percent(t['statements']['covered'], t['statements']['total']):>5.1f}%) "
        f"{t['decisions']['covered']}/{t['decisions']['total']} ({percent(t['decisions']['covered'], t['decisions']['total']):>5.1f}%) "
        f"{t['mcdc_unique']['covered']}/{t['mcdc_unique']['total']} ({percent(t['mcdc_unique']['covered'], t['mcdc_unique']['total']):>5.1f}%) "
        f"{t['mcdc_masking']['covered']}/{t['mcdc_masking']['total']} ({percent(t['mcdc_masking']['covered'], t['mcdc_masking']['total']):>5.1f}%)"
    )
    return "\n".join(lines) + "\n"


def _short(path: str) -> str:
    return path if len(path) <= 50 else "..." + path[-47:]
