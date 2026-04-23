"""Decision (branch) coverage: did the decision evaluate to both True and False?"""
from __future__ import annotations

from typing import Any


def summarize(
    file_id: str,
    decisions_meta: list[dict[str, Any]],
    observations_by_decision: dict[tuple, set],
) -> dict[str, Any]:
    total = len(decisions_meta) * 2  # each decision has T and F branches
    covered = 0
    details: list[dict[str, Any]] = []
    for d in decisions_meta:
        key = (file_id, d["id"])
        observed = observations_by_decision.get(key, set())
        outcomes = {obs[1] for obs in observed}
        true_seen = True in outcomes
        false_seen = False in outcomes
        covered += int(true_seen) + int(false_seen)
        details.append(
            {
                "decision_id": d["id"],
                "lineno": d["lineno"],
                "src": d["src"],
                "true_seen": true_seen,
                "false_seen": false_seen,
            }
        )
    return {
        "total": total,
        "covered": covered,
        "decisions": details,
    }
