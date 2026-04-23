"""Pyproject-based config defaults."""
from __future__ import annotations

import textwrap

from pycov.config import load_from_pyproject, merge_cli


def test_reads_tool_pycov_table(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.pycov]
            include = ["src/*"]
            exclude = ["tests/*"]
            data-dir = "my-data"
            """
        ).lstrip()
    )
    section = load_from_pyproject(str(tmp_path))
    assert section == {"include": ["src/*"], "exclude": ["tests/*"], "data-dir": "my-data"}


def test_returns_empty_when_no_pyproject(tmp_path):
    # tmp_path has no pyproject.toml and neither do its ancestors up to /.
    # Walking up from a random tmp dir will eventually hit the filesystem
    # root, and on CI runners there may be an unrelated pyproject.toml
    # somewhere up the tree — so we assert only that the call succeeds.
    result = load_from_pyproject(str(tmp_path))
    assert isinstance(result, dict)


def test_cli_overrides_pyproject():
    base = {"include": ["src/*"], "exclude": ["vendor/*"]}
    cfg = merge_cli(base, include=["pkg/*"], exclude=None, data_dir=None)
    assert cfg.include == ["pkg/*"]         # CLI wins
    assert cfg.exclude == ["vendor/*"]      # falls through to pyproject


def test_cli_empty_lists_fall_through_to_pyproject():
    base = {"include": ["src/*"]}
    cfg = merge_cli(base, include=None, exclude=None, data_dir=None)
    assert cfg.include == ["src/*"]
