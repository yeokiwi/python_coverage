"""Prelude-invoked registration of a file's pycov metadata.

The AST transformer emits, as the first few top-level statements of every
instrumented module:

    from pycov._registry import register_from_meta as _pycov_register
    _pycov_register({...file metadata...})

That happens once per import and is idempotent.
"""
from __future__ import annotations

from typing import Any

from .collector import get_collector


def register_from_meta(meta: dict[str, Any]) -> None:
    get_collector().register_file(
        file_id=meta["file_id"],
        path=meta["path"],
        statements=meta["statements"],
        decisions=meta["decisions"],
    )
