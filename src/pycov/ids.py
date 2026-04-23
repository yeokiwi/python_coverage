"""Stable identifiers for files, statements, decisions, and conditions."""
from __future__ import annotations

import hashlib
import os


def file_id_for(path: str) -> str:
    """Return a stable 12-char id for an absolute path."""
    abspath = os.path.abspath(path)
    return hashlib.sha1(abspath.encode("utf-8")).hexdigest()[:12]


def source_hash(source: str | bytes) -> str:
    if isinstance(source, str):
        source = source.encode("utf-8")
    return hashlib.sha256(source).hexdigest()
