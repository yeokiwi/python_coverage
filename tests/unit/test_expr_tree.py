from __future__ import annotations

from pycov.analysis.expr_tree import evaluate, relevant_conditions


AND2 = {"op": "and", "children": [
    {"op": "cond", "id": 0, "src": "A"},
    {"op": "cond", "id": 1, "src": "B"},
]}


def test_and_relevance():
    # (T, T) -> outcome True; both relevant
    assert relevant_conditions(AND2, (True, True)) == {0, 1}
    # (F, None) -> outcome False; A relevant, B short-circuited
    assert relevant_conditions(AND2, (False, None)) == {0}
    # (T, F) -> outcome False; A relevant (evaluated first), B relevant (since A was T)
    assert relevant_conditions(AND2, (True, False)) == {0, 1}


OR_THREE = {"op": "or", "children": [
    {"op": "cond", "id": 0, "src": "A"},
    {"op": "cond", "id": 1, "src": "B"},
    {"op": "cond", "id": 2, "src": "C"},
]}


def test_or_short_circuits_mask_later_operands():
    assert evaluate(OR_THREE, (True, None, None)) is True
    assert relevant_conditions(OR_THREE, (True, None, None)) == {0}
    assert evaluate(OR_THREE, (False, False, True)) is True
    assert relevant_conditions(OR_THREE, (False, False, True)) == {0, 1, 2}


NOT_LEAF = {"op": "not", "child": {"op": "cond", "id": 0, "src": "A"}}


def test_not_is_transparent_for_relevance():
    assert relevant_conditions(NOT_LEAF, (True,)) == {0}
    assert relevant_conditions(NOT_LEAF, (False,)) == {0}
