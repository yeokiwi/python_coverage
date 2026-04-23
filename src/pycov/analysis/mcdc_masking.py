"""Masking MC/DC.

A condition C is masking-covered iff there exist two observations where:
  - C differs between them,
  - the outcome differs between them,
  - C is *relevant* (non-masked) in both observations,
  - every other condition that differs between the two observations is
    *masked* in both observations (i.e. its value didn't influence the
    outcome on either side).
"""
from __future__ import annotations

from typing import Any

from .expr_tree import relevant_conditions


def analyse(decision_meta: dict[str, Any], observations: list[tuple]) -> list[dict[str, Any]]:
    n = decision_meta["n_conds"]
    tree = decision_meta["tree"]
    obs_list = list(observations)
    rel_cache = [relevant_conditions(tree, obs[0]) for obs in obs_list]
    results: list[dict[str, Any]] = []
    for c in range(n):
        covered = False
        witness: tuple[int, int] | None = None
        for i in range(len(obs_list)):
            if c not in rel_cache[i]:
                continue
            vi, oi = obs_list[i]
            for j in range(i + 1, len(obs_list)):
                if c not in rel_cache[j]:
                    continue
                vj, oj = obs_list[j]
                if vi[c] is None or vj[c] is None or vi[c] == vj[c]:
                    continue
                if oi == oj:
                    continue
                ok = True
                for k in range(n):
                    if k == c:
                        continue
                    if vi[k] == vj[k]:
                        continue
                    # differing non-target condition: both sides must mask it.
                    if k in rel_cache[i] or k in rel_cache[j]:
                        ok = False
                        break
                if not ok:
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
