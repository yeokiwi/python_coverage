"""On-disk coverage data.

A run writes one JSON file per process to the data directory, containing the
snapshot produced by :meth:`pycov.collector.Collector.snapshot`. The reporter
reads every JSON file in the data directory and merges them.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any

_DATA_DIR_ENV = "PYCOV_DATA_DIR"


def data_dir() -> str:
    return os.environ.get(_DATA_DIR_ENV, ".pycov_data")


def set_data_dir(path: str) -> None:
    os.environ[_DATA_DIR_ENV] = path


def write_snapshot(snap: dict[str, Any]) -> str:
    d = data_dir()
    os.makedirs(d, exist_ok=True)
    token = secrets.token_hex(4)
    fname = f"pycov.{os.getpid()}.{int(time.time()*1000)}.{token}.json"
    fpath = os.path.join(d, fname)
    payload = {
        "statements": [
            {"file_id": fid, "stmt_id": sid, "hits": n}
            for (fid, sid), n in snap["statements"].items()
        ],
        "decisions": [
            {
                "file_id": fid,
                "decision_id": did,
                "observations": [
                    {"cond_values": list(obs[0]), "outcome": obs[1]}
                    for obs in observations
                ],
            }
            for (fid, did), observations in snap["decisions"].items()
        ],
        "file_meta": snap["file_meta"],
    }
    with open(fpath, "w") as fh:
        json.dump(payload, fh)
    return fpath


def load_all(dir_path: str | None = None) -> dict[str, Any]:
    """Merge every snapshot in *dir_path* into a single in-memory snapshot."""
    if dir_path is None:
        dir_path = data_dir()
    merged_statements: dict[tuple[str, int], int] = {}
    merged_decisions: dict[tuple[str, int], set[tuple[tuple, bool]]] = {}
    merged_meta: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(dir_path):
        return {
            "statements": merged_statements,
            "decisions": merged_decisions,
            "file_meta": merged_meta,
        }
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(dir_path, name)) as fh:
            payload = json.load(fh)
        for s in payload.get("statements", []):
            key = (s["file_id"], s["stmt_id"])
            merged_statements[key] = merged_statements.get(key, 0) + s["hits"]
        for d in payload.get("decisions", []):
            key = (d["file_id"], d["decision_id"])
            bucket = merged_decisions.setdefault(key, set())
            for obs in d["observations"]:
                bucket.add((tuple(obs["cond_values"]), obs["outcome"]))
        for fid, m in payload.get("file_meta", {}).items():
            merged_meta.setdefault(fid, m)
    return {
        "statements": merged_statements,
        "decisions": merged_decisions,
        "file_meta": merged_meta,
    }


def clean(dir_path: str | None = None) -> int:
    if dir_path is None:
        dir_path = data_dir()
    if not os.path.isdir(dir_path):
        return 0
    removed = 0
    for name in os.listdir(dir_path):
        if name.endswith(".json"):
            os.remove(os.path.join(dir_path, name))
            removed += 1
    return removed
