"""pycov - statement, decision, and MC/DC coverage for Python."""
from __future__ import annotations

__version__ = "0.1.0"

from .collector import Collector, get_collector, flush
from .config import Config

__all__ = ["Collector", "Config", "__version__", "flush", "get_collector"]
