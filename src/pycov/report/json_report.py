"""JSON report."""
from __future__ import annotations

import datetime as _dt
import json
import platform
import sys
from typing import Any

from .. import __version__


def render(report: dict[str, Any], *, include_raw: bool = False, snapshot: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "meta": {
            "tool": "pycov",
            "tool_version": __version__,
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": sys.platform,
            "created_at": _dt.datetime.utcnow().isoformat() + "Z",
        },
        "totals": report["totals"],
        "files": report["files"],
    }
    if include_raw and snapshot is not None:
        payload["raw"] = {
            "statements": [
                {"file_id": fid, "stmt_id": sid, "hits": n}
                for (fid, sid), n in snapshot["statements"].items()
            ],
            "decisions": [
                {
                    "file_id": fid,
                    "decision_id": did,
                    "observations": [
                        {"cond_values": list(v), "outcome": o}
                        for v, o in obs
                    ],
                }
                for (fid, did), obs in snapshot["decisions"].items()
            ],
        }
    return json.dumps(payload, indent=2, sort_keys=False)
