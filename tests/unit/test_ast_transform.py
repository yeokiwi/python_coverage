"""Coverage for :mod:`pycov.ast_transform`: run instrumented code, verify probes."""
from __future__ import annotations

import textwrap

import pytest

from pycov.ast_transform import instrument
from pycov.collector import get_collector


@pytest.fixture(autouse=True)
def reset_collector():
    get_collector().reset()
    yield
    get_collector().reset()


def _run(src: str, name: str = "<test>"):
    code, meta = instrument(name, textwrap.dedent(src))
    ns: dict = {"__name__": "__main__", "__file__": name}
    exec(code, ns)
    return ns, meta


def test_statement_counts_match_source():
    ns, meta = _run(
        """
        x = 1
        y = 2
        z = x + y
        """
    )
    assert len(meta["statements"]) == 3
    c = get_collector()
    hits = sum(v for (fid, _sid), v in c.statements.items() if fid == meta["file_id"])
    assert hits == 3


def test_docstring_is_preserved():
    ns, meta = _run(
        """
        \"\"\"module doc\"\"\"
        def f():
            \"\"\"fn doc\"\"\"
            return 1
        f()
        """
    )
    assert ns["f"].__doc__ == "fn doc"
    # module doc preserved by exec'ing into a namespace — __doc__ is set by
    # the module loader, not exec, so we only assert function doc here.


def test_future_import_order():
    src = '''\
from __future__ import annotations
x = 1
'''
    code, meta = instrument("<future>", src)
    ns: dict = {}
    exec(code, ns)
    assert ns["x"] == 1


def test_and_decision_observations():
    ns, meta = _run(
        """
        def f(a, b):
            if a and b:
                return 1
            return 0
        f(True, True)
        f(True, False)
        f(False, True)
        """
    )
    c = get_collector()
    assert len(meta["decisions"]) == 1
    did = meta["decisions"][0]["id"]
    obs = c.decisions[(meta["file_id"], did)]
    # three distinct observations: (T,T,T), (T,F,F), (F,None,F)
    assert ((True, True), True) in obs
    assert ((True, False), False) in obs
    assert ((False, None), False) in obs


def test_or_short_circuits_middle_condition():
    ns, meta = _run(
        """
        def f(a, b, c):
            if a or b or c:
                return 1
            return 0
        f(False, True, False)
        """
    )
    c = get_collector()
    obs = list(c.decisions[(meta["file_id"], meta["decisions"][0]["id"])])
    assert obs == [((False, True, None), True)]


def test_not_unwraps_leaf():
    ns, meta = _run(
        """
        def f(a):
            if not a:
                return 1
            return 0
        f(True)
        f(False)
        """
    )
    d = meta["decisions"][0]
    assert d["n_conds"] == 1
    assert d["tree"]["op"] == "not"


def test_conditional_expression_is_decision():
    ns, meta = _run(
        """
        def f(a):
            return 1 if a else 0
        f(True)
        f(False)
        """
    )
    assert len(meta["decisions"]) == 1
    c = get_collector()
    key = (meta["file_id"], meta["decisions"][0]["id"])
    outcomes = {o for _, o in c.decisions[key]}
    assert outcomes == {True, False}


def test_comprehension_filter_is_decision():
    ns, meta = _run(
        """
        xs = [x for x in range(4) if x % 2 == 0]
        """
    )
    assert len(meta["decisions"]) == 1


def test_assert_is_decision():
    ns, meta = _run(
        """
        x = 1
        assert x == 1
        """
    )
    assert len(meta["decisions"]) == 1


def test_match_guard_is_decision():
    ns, meta = _run(
        """
        def f(x):
            match x:
                case n if n > 0:
                    return "pos"
                case _:
                    return "other"
        f(1)
        f(-1)
        """
    )
    assert any(d["src"] == "n > 0" for d in meta["decisions"])


def test_while_is_decision():
    ns, meta = _run(
        """
        def f(n):
            i = 0
            while i < n:
                i += 1
            return i
        f(3)
        """
    )
    assert any("i < n" in d["src"].replace(" ", "").replace("<", " < ") or "<" in d["src"] for d in meta["decisions"])


def test_try_except_finally_bodies_probed():
    ns, meta = _run(
        """
        def f(x):
            try:
                if x == 0:
                    raise ValueError()
                y = 1
            except ValueError:
                y = -1
            finally:
                z = 'done'
            return (y, z)
        f(0)
        f(1)
        """
    )
    assert len(meta["statements"]) >= 6


def test_decorator_not_rewritten_as_decision():
    ns, meta = _run(
        """
        def deco(fn):
            return fn

        @deco
        def f():
            return 1
        f()
        """
    )
    # No decisions inside decorator expressions themselves.
    assert all("deco" not in d["src"] for d in meta["decisions"])


def test_nested_decisions_use_stack():
    ns, meta = _run(
        """
        def f(a, b, c):
            if a:
                if b and c:
                    return 1
            return 0
        f(True, True, True)
        f(True, False, True)
        f(False, False, False)
        """
    )
    c = get_collector()
    # two decisions registered
    assert len(meta["decisions"]) == 2
    # inner (b and c) should have observations under its own decision id
    inner_did = [d["id"] for d in meta["decisions"] if d["n_conds"] == 2][0]
    inner_obs = c.decisions[(meta["file_id"], inner_did)]
    assert any(o[1] is True for o in inner_obs)
    assert any(o[1] is False for o in inner_obs)
