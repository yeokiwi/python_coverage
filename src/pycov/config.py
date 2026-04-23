"""Runtime configuration for pycov."""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field


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
