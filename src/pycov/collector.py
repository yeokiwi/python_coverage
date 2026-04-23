"""In-process coverage data collector.

Single global instance holds:
  * statement hit counts:   ``{(file_id, stmt_id): count}``
  * decision observations:  ``{(file_id, decision_id): set[(cond_tuple, outcome)]}``
  * expression trees:       ``{(file_id, decision_id): ExprTreeDict}``

Per-thread state (``threading.local``) holds the stack of in-flight decision
observation buffers, so nested decisions on one thread cannot clobber each
other.
"""
from __future__ import annotations

import threading
from typing import Any


class Collector:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tls = threading.local()
        self.statements: dict[tuple[str, int], int] = {}
        self.decisions: dict[tuple[str, int], set[tuple[tuple, bool]]] = {}
        self.expr_trees: dict[tuple[str, int], dict[str, Any]] = {}
        self.file_meta: dict[str, dict[str, Any]] = {}

    # --- registration (called from the import loader) -----------------------
    def register_file(
        self,
        file_id: str,
        path: str,
        statements: list[dict[str, Any]],
        decisions: list[dict[str, Any]],
    ) -> None:
        with self._lock:
            self.file_meta[file_id] = {
                "path": path,
                "statements": {s["id"]: s for s in statements},
                "decisions": {d["id"]: d for d in decisions},
            }
            for d in decisions:
                key = (file_id, d["id"])
                self.expr_trees[key] = d["tree"]
                self.decisions.setdefault(key, set())
            for s in statements:
                self.statements.setdefault((file_id, s["id"]), 0)

    # --- per-thread helpers -------------------------------------------------
    def _stack(self) -> list[list]:
        stack = getattr(self._tls, "stack", None)
        if stack is None:
            stack = []
            self._tls.stack = stack
        return stack

    # --- probe hooks --------------------------------------------------------
    def record_statement(self, file_id: str, stmt_id: int) -> None:
        key = (file_id, stmt_id)
        with self._lock:
            self.statements[key] = self.statements.get(key, 0) + 1

    def enter_decision(self, file_id: str, decision_id: int, n_conds: int) -> None:
        buf = [None] * n_conds
        self._stack().append(buf)

    def record_condition(
        self, file_id: str, decision_id: int, cond_id: int, value: bool
    ) -> None:
        stack = self._stack()
        if not stack:
            return
        stack[-1][cond_id] = value

    def exit_decision(self, file_id: str, decision_id: int, outcome: bool) -> None:
        stack = self._stack()
        if not stack:
            return
        buf = stack.pop()
        obs = (tuple(buf), outcome)
        key = (file_id, decision_id)
        with self._lock:
            self.decisions.setdefault(key, set()).add(obs)

    # --- export -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "statements": dict(self.statements),
                "decisions": {
                    k: [list(obs) for obs in sorted(v, key=repr)]
                    for k, v in self.decisions.items()
                },
                "expr_trees": dict(self.expr_trees),
                "file_meta": {
                    fid: {
                        "path": m["path"],
                        "statements": list(m["statements"].values()),
                        "decisions": list(m["decisions"].values()),
                    }
                    for fid, m in self.file_meta.items()
                },
            }

    def reset(self) -> None:
        with self._lock:
            self.statements.clear()
            self.decisions.clear()
            self.expr_trees.clear()
            self.file_meta.clear()
        self._tls = threading.local()


_GLOBAL: Collector | None = None
_GLOBAL_LOCK = threading.Lock()


def get_collector() -> Collector:
    global _GLOBAL
    if _GLOBAL is None:
        with _GLOBAL_LOCK:
            if _GLOBAL is None:
                _GLOBAL = Collector()
    return _GLOBAL


def flush() -> None:
    """Flush the global collector's data to disk.

    Called at process exit; safe to invoke manually.
    """
    from .persistence import write_snapshot

    snap = get_collector().snapshot()
    if snap["file_meta"]:
        write_snapshot(snap)
