"""Self-contained HTML report: index page + one page per source file."""
from __future__ import annotations

import html
import os
import shutil
from typing import Any

from .. import __version__
from .model import percent


def write(report: dict[str, Any], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    css_src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "pycov.css")
    css_dst = os.path.join(out_dir, "pycov.css")
    try:
        shutil.copyfile(css_src, css_dst)
    except Exception:
        pass

    index_html = _render_index(report)
    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "w") as fh:
        fh.write(index_html)
    for path, file_rep in report["files"].items():
        fhtml = _render_file(path, file_rep)
        fname = _safe_name(path) + ".html"
        with open(os.path.join(out_dir, fname), "w") as fh:
            fh.write(fhtml)
    return index_path


def _safe_name(path: str) -> str:
    return path.replace(os.sep, "_").replace("/", "_").replace(":", "_").replace("..", "dotdot")


def _bar(covered: int, total: int) -> str:
    pct = percent(covered, total)
    cls = "low" if pct < 60 else ("mid" if pct < 85 else "")
    return f'<span class="bar {cls}"><span style="width:{pct}%"></span></span>'


def _render_index(report: dict[str, Any]) -> str:
    t = report["totals"]
    rows: list[str] = []
    for path, f in sorted(report["files"].items()):
        fname = _safe_name(path) + ".html"
        s, d, u, m = f["statements"], f["decisions"], f["mcdc_unique"], f["mcdc_masking"]
        rows.append(
            f'<tr>'
            f'<td><a href="{html.escape(fname)}">{html.escape(path)}</a></td>'
            f'<td>{_bar(s["covered"], s["total"])} {s["covered"]}/{s["total"]} ({percent(s["covered"], s["total"]):.1f}%)</td>'
            f'<td>{_bar(d["covered"], d["total"])} {d["covered"]}/{d["total"]} ({percent(d["covered"], d["total"]):.1f}%)</td>'
            f'<td>{_bar(u["covered"], u["total"])} {u["covered"]}/{u["total"]} ({percent(u["covered"], u["total"]):.1f}%)</td>'
            f'<td>{_bar(m["covered"], m["total"])} {m["covered"]}/{m["total"]} ({percent(m["covered"], m["total"]):.1f}%)</td>'
            f'</tr>'
        )
    body = (
        f'<h1>pycov report</h1>'
        f'<div class="legend">tool v{__version__}. MCDC-U = unique-cause MC/DC, MCDC-M = masking MC/DC.</div>'
        f'<div class="totals"><table>'
        f'<tr><th>Statements</th><td>{t["statements"]["covered"]}/{t["statements"]["total"]} ({percent(t["statements"]["covered"], t["statements"]["total"]):.1f}%)</td></tr>'
        f'<tr><th>Decisions</th><td>{t["decisions"]["covered"]}/{t["decisions"]["total"]} ({percent(t["decisions"]["covered"], t["decisions"]["total"]):.1f}%)</td></tr>'
        f'<tr><th>MCDC unique-cause</th><td>{t["mcdc_unique"]["covered"]}/{t["mcdc_unique"]["total"]} ({percent(t["mcdc_unique"]["covered"], t["mcdc_unique"]["total"]):.1f}%)</td></tr>'
        f'<tr><th>MCDC masking</th><td>{t["mcdc_masking"]["covered"]}/{t["mcdc_masking"]["total"]} ({percent(t["mcdc_masking"]["covered"], t["mcdc_masking"]["total"]):.1f}%)</td></tr>'
        f'</table></div>'
        f'<table><thead><tr><th>File</th><th>Statements</th><th>Branch</th><th>MCDC-U</th><th>MCDC-M</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )
    return _page("pycov report", body)


def _render_file(path: str, f: dict[str, Any]) -> str:
    src_lines = _read_source(path)
    stmt_covered_lines: set[int] = set(f["statements"].get("covered_lines", []))
    stmt_missed_lines: set[int] = set(f["statements"]["missed_lines"])
    dec_by_line: dict[int, list[dict[str, Any]]] = {}
    for d in f["decisions"]["decisions"]:
        dec_by_line.setdefault(d["lineno"], []).append(d)
    mcu_by_line: dict[int, list[dict[str, Any]]] = {}
    for d in f["mcdc_unique"]["decisions"]:
        mcu_by_line.setdefault(d["lineno"], []).append(d)
    mcm_by_line: dict[int, list[dict[str, Any]]] = {}
    for d in f["mcdc_masking"]["decisions"]:
        mcm_by_line.setdefault(d["lineno"], []).append(d)

    # crude covered-line inference: a line is covered iff it's not in missed
    # AND there's some statement on it. We don't know exact statement linenos,
    # so we rely on the missed set only — non-missed executable lines stay
    # 'nonexec' in the render. That's fine; users see missed lines clearly.
    out_lines: list[str] = []
    for i, src in enumerate(src_lines, start=1):
        esc = html.escape(src)
        cls = "nonexec"
        if i in stmt_missed_lines:
            cls = "missed"
        elif i in stmt_covered_lines:
            cls = "covered"
        chips = ""
        for d in dec_by_line.get(i, []):
            t_cls = "t-cov" if d["true_seen"] else "t-miss"
            f_cls = "f-cov" if d["false_seen"] else "f-miss"
            chips += f'<span class="chip {t_cls}" title="decision #{d["decision_id"]} T">T</span>'
            chips += f'<span class="chip {f_cls}" title="decision #{d["decision_id"]} F">F</span>'
        for d in mcu_by_line.get(i, []):
            for c in d["conditions"]:
                cls2 = "covered" if c["covered"] else "missed"
                tip = html.escape(f"unique-cause: {c['src']} ({'OK' if c['covered'] else 'MISS'})")
                chips += f'<span class="chip {cls2}" title="{tip}">U{c["cond_id"]}</span>'
        for d in mcm_by_line.get(i, []):
            for c in d["conditions"]:
                cls2 = "covered" if c["covered"] else "missed"
                tip = html.escape(f"masking: {c['src']} ({'OK' if c['covered'] else 'MISS'})")
                chips += f'<span class="chip {cls2}" title="{tip}">M{c["cond_id"]}</span>'
        out_lines.append(f'<span class="line {cls}">{esc}{chips}</span>')
    body = (
        f'<p><a href="index.html">&larr; index</a></p>'
        f'<h1>{html.escape(path)}</h1>'
        f'<pre class="source">{"".join(out_lines)}</pre>'
    )
    return _page(os.path.basename(path), body)


def _read_source(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().splitlines()
    except Exception:
        return []


def _page(title: str, body: str) -> str:
    return (
        f'<!doctype html><html><head><meta charset="utf-8">'
        f'<title>{html.escape(title)}</title>'
        f'<link rel="stylesheet" href="pycov.css">'
        f'</head><body>{body}</body></html>'
    )
