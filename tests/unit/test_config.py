"""Include/exclude filter behavior."""
from __future__ import annotations

from pycov.config import Config


def test_defaults_exclude_site_packages():
    c = Config()
    assert c.matches("/home/me/project/app.py") is True
    assert c.matches("/usr/lib/python3/site-packages/foo.py") is False


def test_exclude_pattern_wins_over_include():
    c = Config(include=["/tmp/*"], exclude=["*/vendor/*"])
    assert c.matches("/tmp/app.py") is True
    assert c.matches("/tmp/vendor/bar.py") is False


def test_pycov_itself_excluded():
    c = Config()
    assert c.matches("/tmp/foo/pycov/ast_transform.py") is False
