"""Unique-cause MC/DC correctness against hand-picked observation sets."""
from __future__ import annotations

from pycov.analysis.mcdc_unique import analyse


def _meta(n, tree):
    return {
        "n_conds": n,
        "tree": tree,
        "conditions": [{"id": i, "src": chr(ord("A") + i)} for i in range(n)],
    }


AND2 = {"op": "and", "children": [
    {"op": "cond", "id": 0, "src": "A"},
    {"op": "cond", "id": 1, "src": "B"},
]}


def test_full_truth_table_covers_both():
    # Observations for A and B from the full truth table (non-short-circuit
    # would need 4 obs; short-circuit collapses two).
    obs = [
        ((True, True), True),
        ((True, False), False),
        ((False, None), False),
    ]
    # Under unique-cause with None-as-distinct-value, A is covered iff we have
    # two obs where A differs and B matches. (T,T,T) vs (F,None,F) — B differs
    # (True vs None) — NOT covered under strict matching.
    res = analyse(_meta(2, AND2), obs)
    by = {r["cond_id"]: r for r in res}
    # B is covered: (T,T,T) vs (T,F,F) — A matches, B differs, outcome differs.
    assert by[1]["covered"] is True
    # A is NOT covered under unique-cause because we never observed A alone
    # varying (short-circuit killed B on the False side).
    assert by[0]["covered"] is False


def test_non_short_circuit_covers_a():
    # Pretend we have observations that DID evaluate both conditions:
    obs = [
        ((True, True), True),   # A=T, B=T
        ((False, True), False), # A differs, B matches, outcome differs -> covers A
        ((True, False), False), # covers B vs obs[0]
    ]
    res = analyse(_meta(2, AND2), obs)
    by = {r["cond_id"]: r for r in res}
    assert by[0]["covered"] is True
    assert by[1]["covered"] is True


def test_no_coverage_when_outcomes_same():
    obs = [
        ((True, False), False),
        ((False, False), False),
    ]
    res = analyse(_meta(2, AND2), obs)
    assert not any(r["covered"] for r in res)
