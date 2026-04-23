"""`pycov run target.py ...` — instruments on import and executes the target."""
from __future__ import annotations

import atexit
import os
import runpy
import sys

from .collector import flush
from .config import Config
from .importer import compile_entry, install


def run_script(target: str, args: list[str], config: Config) -> int:
    install(config)
    # Expose the target's directory on sys.path so its imports resolve.
    target_abs = os.path.abspath(target)
    target_dir = os.path.dirname(target_abs)
    if target_dir not in sys.path:
        sys.path.insert(0, target_dir)
    sys.argv = [target_abs, *args]
    atexit.register(flush)
    # Pre-compile the entry so it's instrumented too. Its prelude will
    # register the file with the collector when exec'd below.
    code, _meta = compile_entry(target_abs)
    ns = {"__name__": "__main__", "__file__": target_abs, "__package__": None}
    try:
        exec(code, ns)
    except SystemExit as e:
        return int(e.code or 0)
    except Exception:
        import traceback

        traceback.print_exc()
        return 1
    return 0


def run_module(module: str, args: list[str], config: Config) -> int:
    install(config)
    sys.argv = [module, *args]
    atexit.register(flush)
    try:
        runpy.run_module(module, run_name="__main__")
    except SystemExit as e:
        return int(e.code or 0)
    return 0
