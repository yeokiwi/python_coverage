from __future__ import annotations

from typing import Any


def summarize(file_meta: dict[str, Any], statement_hits: dict[tuple, int]) -> dict[str, Any]:
    stmts = file_meta["statements"]
    total = len(stmts)
    covered = 0
    missed: set[int] = set()
    covered_lines: set[int] = set()
    fid = file_meta.get("file_id") or _infer_file_id(file_meta, statement_hits)
    for s in stmts:
        hits = statement_hits.get((fid, s["id"]), 0)
        if hits > 0:
            covered += 1
            covered_lines.add(s["lineno"])
        else:
            missed.add(s["lineno"])
    # A line with multiple statements where at least one was hit counts as covered.
    missed -= covered_lines
    return {
        "total": total,
        "covered": covered,
        "missed_lines": sorted(missed),
        "covered_lines": sorted(covered_lines),
    }


def _infer_file_id(file_meta, statement_hits):
    # File meta always includes a path; derive the id from statements if
    # the snapshot didn't embed it.
    for (fid, _sid) in statement_hits:
        return fid
    return None
