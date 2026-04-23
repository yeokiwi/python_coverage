"""Build the report model consumed by the text/JSON/HTML reporters.

A "snapshot" is the dict returned by :func:`pycov.persistence.load_all`.
``build(snapshot)`` returns a dict shaped as::

    {
      "files": {path: FileReport, ...},
      "totals": {...aggregated across files...},
    }
"""
from __future__ import annotations

from typing import Any

from ..analysis import decisions as dec_mod
from ..analysis import mcdc_masking, mcdc_unique, statements as stmt_mod


def build(snapshot: dict[str, Any]) -> dict[str, Any]:
    files = {}
    totals = {
        "statements": {"total": 0, "covered": 0},
        "decisions": {"total": 0, "covered": 0},
        "mcdc_unique": {"total": 0, "covered": 0},
        "mcdc_masking": {"total": 0, "covered": 0},
    }
    for file_id, meta in snapshot["file_meta"].items():
        meta_with_id = dict(meta)
        meta_with_id["file_id"] = file_id
        stmt = stmt_mod.summarize(meta_with_id, snapshot["statements"])
        dec = dec_mod.summarize(
            file_id, meta["decisions"], snapshot["decisions"]
        )
        mcdc_u = []
        mcdc_m = []
        mcdc_u_total = 0
        mcdc_u_covered = 0
        mcdc_m_total = 0
        mcdc_m_covered = 0
        for d in meta["decisions"]:
            key = (file_id, d["id"])
            obs_set = snapshot["decisions"].get(key, set())
            obs_list = sorted(obs_set, key=repr)  # deterministic order
            # normalise dict in meta (JSON meta may lose tuple types; both dicts and tuples work here)
            d_full = {
                "n_conds": d.get("n_conds", len(d.get("conditions", []))),
                "tree": d.get("tree"),
                "conditions": d.get("conditions", []),
            }
            u = mcdc_unique.analyse(d_full, [(tuple(v), o) for v, o in obs_list])
            m = mcdc_masking.analyse(d_full, [(tuple(v), o) for v, o in obs_list])
            mcdc_u.append({"decision_id": d["id"], "lineno": d["lineno"], "src": d["src"], "conditions": u})
            mcdc_m.append({"decision_id": d["id"], "lineno": d["lineno"], "src": d["src"], "conditions": m})
            mcdc_u_total += len(u)
            mcdc_u_covered += sum(1 for x in u if x["covered"])
            mcdc_m_total += len(m)
            mcdc_m_covered += sum(1 for x in m if x["covered"])
        files[meta["path"]] = {
            "file_id": file_id,
            "path": meta["path"],
            "statements": stmt,
            "decisions": dec,
            "mcdc_unique": {"total": mcdc_u_total, "covered": mcdc_u_covered, "decisions": mcdc_u},
            "mcdc_masking": {"total": mcdc_m_total, "covered": mcdc_m_covered, "decisions": mcdc_m},
        }
        totals["statements"]["total"] += stmt["total"]
        totals["statements"]["covered"] += stmt["covered"]
        totals["decisions"]["total"] += dec["total"]
        totals["decisions"]["covered"] += dec["covered"]
        totals["mcdc_unique"]["total"] += mcdc_u_total
        totals["mcdc_unique"]["covered"] += mcdc_u_covered
        totals["mcdc_masking"]["total"] += mcdc_m_total
        totals["mcdc_masking"]["covered"] += mcdc_m_covered
    return {"files": files, "totals": totals}


def percent(covered: int, total: int) -> float:
    if total == 0:
        return 100.0
    return round(100.0 * covered / total, 2)
