"""Unique-cause MC/DC.

A condition C is covered iff there exist two observations where only C's
value differs (all other evaluated conditions match, with None treated as
a value that must match) and the observed outcome differs.
"""
from __future__ import annotations

from typing import Any


def analyse(decision_meta: dict[str, Any], observations: list[tuple]) -> list[dict[str, Any]]:
    n = decision_meta["n_conds"]
    obs_list = list(observations)
    results: list[dict[str, Any]] = []
    for c in range(n):
        covered = False
        witness: tuple[int, int] | None = None
        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                vi, oi = obs_list[i]
                vj, oj = obs_list[j]
                if vi[c] is None or vj[c] is None or vi[c] == vj[c]:
                    continue
                if oi == oj:
                    continue
                # all other conditions must match
                others_match = True
                for k in range(n):
                    if k == c:
                        continue
                    if vi[k] != vj[k]:
                        others_match = False
                        break
                if not others_match:
                    continue
                covered = True
                witness = (i, j)
                break
            if covered:
                break
        cond_src = next(
            (cc["src"] for cc in decision_meta["conditions"] if cc["id"] == c),
            f"cond{c}",
        )
        results.append(
            {
                "cond_id": c,
                "src": cond_src,
                "covered": covered,
                "witness": list(witness) if witness else None,
            }
        )
    return results
