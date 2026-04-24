"""Multi-Python test matrix. Run: ``nox`` or ``nox -s tests-3.12``.

Intended to be invoked from an activated conda ``pycov`` environment where
``nox`` has been installed via ``pip install nox``. Nox manages its own
per-session virtualenvs, so conda provides only the outer interpreter +
``nox`` driver; the matrix below still needs the target Python versions
resolvable on ``PATH`` (e.g. via ``conda install python=3.10 python=3.11 ...``
into separate conda envs, or a ``pyenv`` install).
"""
from __future__ import annotations

import nox

PYTHONS = ["3.10", "3.11", "3.12", "3.13"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session) -> None:
    session.install("-e", ".[pytest]")
    session.install("pytest")
    session.run("pytest", *session.posargs)
