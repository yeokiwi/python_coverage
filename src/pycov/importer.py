"""Import hook that transparently instruments matching source files."""
from __future__ import annotations

import sys
from importlib.machinery import FileFinder, SourceFileLoader
from importlib.util import spec_from_file_location
from typing import Iterable

from . import cache as _cache
from .ast_transform import instrument
from .config import Config


class PycovLoader(SourceFileLoader):
    """SourceFileLoader that rewrites source via pycov's AST transformer.

    Bypasses Python's ``__pycache__/*.pyc`` cache so stale bytecode from a
    previous (non-pycov) run can't mask our instrumentation. Our own
    :mod:`pycov.cache` keyed on ``sha256(source) || tool_version || python``
    handles instrumented-code caching.
    """

    def get_code(self, fullname):
        source_path = self.get_filename(fullname)
        source_bytes = self.get_data(source_path)
        return self.source_to_code(source_bytes, source_path)

    def source_to_code(self, data, path, *, _optimize=-1):  # noqa: D401
        if isinstance(data, (bytes, bytearray)):
            source = data.decode("utf-8")
        else:
            source = data
        cached = _cache.load(path, source)
        if cached is not None:
            return cached[0]
        code, _meta = instrument(path, source)
        try:
            _cache.store(path, source, code, _meta)
        except Exception:
            pass
        return code

    def _cache_bytecode(self, source_path, bytecode_path, data):  # noqa: D401
        # Never write our instrumented bytecode to ``__pycache__``; that cache
        # is shared with non-pycov runs and would poison them.
        return False


class PycovFinder:
    """MetaPathFinder that re-routes source files matching the include filter
    through :class:`PycovLoader`. Everything else falls through to the
    default finders."""

    def __init__(self, config: Config):
        self.config = config

    def find_spec(self, fullname: str, path: Iterable[str] | None = None, target=None):
        if path is None:
            path = sys.path
        for entry in path:
            try:
                finder = FileFinder(
                    entry,
                    (PycovLoader, [".py"]),
                )
                spec = finder.find_spec(fullname, target)
            except (ImportError, OSError):
                continue
            if spec is None:
                continue
            filename = getattr(spec, "origin", None)
            if not filename or not filename.endswith(".py"):
                return None
            if not self.config.matches(filename):
                return None
            return spec
        return None


_INSTALLED: PycovFinder | None = None


def install(config: Config) -> PycovFinder:
    global _INSTALLED
    if _INSTALLED is not None:
        _INSTALLED.config = config
        return _INSTALLED
    finder = PycovFinder(config)
    sys.meta_path.insert(0, finder)
    _INSTALLED = finder
    return finder


def uninstall() -> None:
    global _INSTALLED
    if _INSTALLED is not None and _INSTALLED in sys.meta_path:
        sys.meta_path.remove(_INSTALLED)
    _INSTALLED = None


def compile_entry(path: str) -> tuple[object, dict]:
    """Instrument a script that's being run as __main__ (not imported)."""
    from .source import read_source

    source = read_source(path)
    cached = _cache.load(path, source)
    if cached is not None:
        return cached
    code, meta = instrument(path, source)
    try:
        _cache.store(path, source, code, meta)
    except Exception:
        pass
    return code, meta
