"""Optional on-disk cache of compiled, instrumented code.

Not strictly required; the importer can instrument on every load. The cache
skips AST rewriting when the source + tool + python versions haven't
changed.
"""
from __future__ import annotations

import marshal
import os
import sys
from typing import Any

from . import __version__
from .ids import file_id_for, source_hash


def cache_dir() -> str:
    return os.environ.get("PYCOV_CACHE_DIR", ".pycov_cache")


def _key(source: str) -> str:
    return f"{source_hash(source)}-{__version__}-py{sys.version_info.major}{sys.version_info.minor}"


def _paths(path: str, source: str) -> tuple[str, str]:
    fid = file_id_for(path)
    base = os.path.join(cache_dir(), fid, _key(source))
    return base + ".pyc", base + ".meta.json"


def load(path: str, source: str) -> tuple[Any, dict[str, Any]] | None:
    import json

    code_path, meta_path = _paths(path, source)
    if not (os.path.exists(code_path) and os.path.exists(meta_path)):
        return None
    try:
        with open(code_path, "rb") as fh:
            code = marshal.load(fh)
        with open(meta_path) as fh:
            meta = json.load(fh)
    except Exception:
        return None
    return code, meta


def store(path: str, source: str, code: Any, meta: dict[str, Any]) -> None:
    import json

    code_path, meta_path = _paths(path, source)
    os.makedirs(os.path.dirname(code_path), exist_ok=True)
    with open(code_path, "wb") as fh:
        marshal.dump(code, fh)
    with open(meta_path, "w") as fh:
        json.dump(meta, fh)
