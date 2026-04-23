"""Runtime configuration for pycov.

Values may come from (in order of lowest to highest precedence):

1. Built-in defaults on the dataclass.
2. A ``[tool.pycov]`` table in a ``pyproject.toml`` found by walking up
   from the current working directory (or an explicit path passed to
   :func:`load_from_pyproject`).
3. Explicit command-line flags.
"""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    import tomli as _toml  # type: ignore[no-redef]


@dataclass
class Config:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    data_dir: str = ".pycov_data"
    cache_dir: str = ".pycov_cache"
    statement: bool = True
    branch: bool = True
    mcdc: bool = True

    DEFAULT_EXCLUDES = (
        "*/pycov/*",
        "*/site-packages/*",
        "*/dist-packages/*",
        "*/.pycov_cache/*",
    )

    def matches(self, path: str) -> bool:
        """Return True if *path* is in scope for instrumentation."""
        abspath = os.path.abspath(path)
        for pattern in (*self.exclude, *self.DEFAULT_EXCLUDES):
            if fnmatch.fnmatch(abspath, pattern):
                return False
        if not self.include:
            return True
        for pattern in self.include:
            if fnmatch.fnmatch(abspath, pattern):
                return True
        return False


def _find_pyproject(start: str) -> str | None:
    cur = os.path.abspath(start)
    while True:
        candidate = os.path.join(cur, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def load_from_pyproject(start_dir: str | None = None) -> dict:
    """Return the ``[tool.pycov]`` table from the nearest ``pyproject.toml``,
    or an empty dict if none is found.
    """
    start = start_dir or os.getcwd()
    path = _find_pyproject(start)
    if path is None:
        return {}
    try:
        with open(path, "rb") as fh:
            data = _toml.load(fh)
    except Exception:
        return {}
    return data.get("tool", {}).get("pycov", {}) or {}


def merge_cli(base: dict, *, include: list[str] | None, exclude: list[str] | None,
              data_dir: str | None) -> Config:
    """Build a :class:`Config` from a pyproject section plus CLI overrides.

    CLI values replace file values when provided. Lists are *replaced*, not
    merged, so a user passing ``--include`` on the command line takes full
    control of the include set (matching coverage.py's behaviour).
    """
    return Config(
        include=list(include) if include else list(base.get("include", [])),
        exclude=list(exclude) if exclude else list(base.get("exclude", [])),
        data_dir=data_dir or base.get("data-dir", ".pycov_data"),
    )
