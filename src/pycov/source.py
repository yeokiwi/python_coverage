"""Source loading + line caching helpers."""
from __future__ import annotations

import tokenize


def read_source(path: str) -> str:
    with tokenize.open(path) as fh:
        return fh.read()
