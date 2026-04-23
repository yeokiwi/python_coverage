"""Runtime probe functions invoked by instrumented source.

These are deliberately tiny. Naming starts with ``_pycov_`` so instrumented
code is easy to identify when inspected. They are registered into the target
module's namespace by :mod:`pycov.ast_transform` via a module-top ``import``.
"""
from __future__ import annotations

from .collector import get_collector

__all__ = [
    "_pycov_stmt",
    "_pycov_decision_enter",
    "_pycov_cond",
    "_pycov_decision_exit",
]


def _pycov_stmt(file_id: str, stmt_id: int) -> None:
    get_collector().record_statement(file_id, stmt_id)


def _pycov_decision_enter(file_id: str, decision_id: int, n_conds: int) -> bool:
    get_collector().enter_decision(file_id, decision_id, n_conds)
    return False


def _pycov_cond(file_id: str, decision_id: int, cond_id: int, value):
    get_collector().record_condition(file_id, decision_id, cond_id, bool(value))
    return value


def _pycov_decision_exit(file_id: str, decision_id: int, outcome):
    get_collector().exit_decision(file_id, decision_id, bool(outcome))
    return outcome
