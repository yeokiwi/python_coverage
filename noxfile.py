"""Multi-Python test matrix. Run: ``uv run nox`` or ``nox -s tests-3.12``."""
from __future__ import annotations

import nox

PYTHONS = ["3.10", "3.11", "3.12", "3.13"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session) -> None:
    session.install("-e", ".[pytest]")
    session.install("pytest")
    session.run("pytest", *session.posargs)
