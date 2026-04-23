"""Evaluate a serialized boolean expression tree against an observation.

The tree nodes are dicts produced by ``ast_transform._ExprTreeBuilder``:

    {"op": "and", "children": [...]}
    {"op": "or",  "children": [...]}
    {"op": "not", "child":    {...}}
    {"op": "cond", "id": N, "src": "..."}

``evaluate`` walks the tree using the condition values recorded for a single
observation and, for each sub-expression, reports:

  - the operand's observed value (True, False, or None if short-circuited)
  - whether that operand was "relevant" to its parent's outcome, i.e. its
    value influenced the parent's boolean result (the masking definition).

``relevant_conditions`` returns the set of condition ids that were *not*
masked in the observation.
"""
from __future__ import annotations

from typing import Any, Iterable


def _node_value(node: dict[str, Any], cond_values: tuple) -> bool | None:
    op = node["op"]
    if op == "cond":
        v = cond_values[node["id"]]
        return None if v is None else bool(v)
    if op == "not":
        inner = _node_value(node["child"], cond_values)
        return None if inner is None else (not inner)
    # and / or
    result: bool | None = None
    for ch in node["children"]:
        cv = _node_value(ch, cond_values)
        if cv is None:
            return result  # short-circuited past here: parent's value is fixed
        if op == "and":
            if cv is False:
                return False
            result = True
        else:  # or
            if cv is True:
                return True
            result = False
    return result


def evaluate(tree: dict[str, Any], cond_values: tuple) -> bool | None:
    return _node_value(tree, cond_values)


def relevant_conditions(tree: dict[str, Any], cond_values: tuple) -> set[int]:
    """Return cond ids whose value is *not* masked in this observation."""
    out: set[int] = set()
    _collect(tree, cond_values, True, out)
    return out


def _collect(
    node: dict[str, Any], cond_values: tuple, parent_relevant: bool, out: set[int]
) -> None:
    op = node["op"]
    if op == "cond":
        if parent_relevant and cond_values[node["id"]] is not None:
            out.add(node["id"])
        return
    if op == "not":
        _collect(node["child"], cond_values, parent_relevant, out)
        return
    # and / or:
    # An operand is relevant iff its sibling operands that were evaluated
    # before it all returned the non-decisive value (True for 'and', False
    # for 'or'). Operands evaluated AFTER the current one don't affect its
    # own relevance under masking rules (they couldn't have, since evaluation
    # hadn't reached them).
    decisive = False if op == "and" else True
    prev_all_non_decisive = True
    for ch in node["children"]:
        cv = _node_value(ch, cond_values)
        child_relevant = parent_relevant and prev_all_non_decisive and cv is not None
        _collect(ch, cond_values, child_relevant, out)
        if cv is None:
            break  # remaining operands weren't evaluated
        if cv == decisive:
            # this operand decided the result; nothing after it matters
            break
        # non-decisive value; continue
        prev_all_non_decisive = prev_all_non_decisive and (cv != decisive)


def condition_ids(tree: dict[str, Any]) -> Iterable[int]:
    if tree["op"] == "cond":
        yield tree["id"]
        return
    if tree["op"] == "not":
        yield from condition_ids(tree["child"])
        return
    for ch in tree["children"]:
        yield from condition_ids(ch)
