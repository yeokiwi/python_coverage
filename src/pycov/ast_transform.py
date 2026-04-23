"""AST instrumentation.

Parses source, inserts statement probes, wraps every decision predicate with
enter/exit probes, and wraps each leaf condition with ``_pycov_cond``. The
rewritten tree is compiled and returned alongside a metadata dict describing
the statements, decisions, conditions, and boolean-expression tree for each
decision (used later by the MC/DC analyser).
"""
from __future__ import annotations

import ast
from typing import Any

from .ids import file_id_for

PROBES_MODULE = "pycov.probes"

STMT_FN = "_pycov_stmt"
DEC_ENTER = "_pycov_decision_enter"
DEC_EXIT = "_pycov_decision_exit"
COND_FN = "_pycov_cond"
REGISTER_FN = "_pycov_register_file"


class _ExprTreeBuilder:
    """Walk a predicate AST, produce a serialisable boolean-expression tree
    and wrap each leaf operand with ``_pycov_cond``.

    The returned tree structure:
        {"op": "and"|"or",       "children": [...]}
        {"op": "not",            "child":    {...}}
        {"op": "cond", "id": N,  "src":      "<unparsed source>"}
    """

    def __init__(self, file_id: str, decision_id: int, src_lookup):
        self.file_id = file_id
        self.decision_id = decision_id
        self.src_lookup = src_lookup
        self.next_cond_id = 0
        self.leaves: list[dict[str, Any]] = []

    def build(self, node: ast.AST) -> tuple[ast.AST, dict[str, Any]]:
        wrapped, tree = self._visit(node)
        return wrapped, tree

    def _visit(self, node: ast.AST) -> tuple[ast.AST, dict[str, Any]]:
        if isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            new_values = []
            children = []
            for v in node.values:
                wrapped, tree = self._visit(v)
                new_values.append(wrapped)
                children.append(tree)
            new_node = ast.copy_location(
                ast.BoolOp(op=node.op, values=new_values), node
            )
            return new_node, {"op": op, "children": children}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            wrapped, tree = self._visit(node.operand)
            new_node = ast.copy_location(
                ast.UnaryOp(op=ast.Not(), operand=wrapped), node
            )
            return new_node, {"op": "not", "child": tree}
        # leaf
        cid = self.next_cond_id
        self.next_cond_id += 1
        src = self.src_lookup(node)
        self.leaves.append({"id": cid, "src": src})
        wrapped = _call(
            COND_FN,
            [
                ast.Constant(self.file_id),
                ast.Constant(self.decision_id),
                ast.Constant(cid),
                node,
            ],
        )
        ast.copy_location(wrapped, node)
        return wrapped, {"op": "cond", "id": cid, "src": src}


def _call(name: str, args: list[ast.AST]) -> ast.Call:
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=args, keywords=[])


def _stmt_probe(file_id: str, stmt_id: int, location: ast.AST) -> ast.stmt:
    call = _call(
        STMT_FN, [ast.Constant(file_id), ast.Constant(stmt_id)]
    )
    expr = ast.Expr(value=call)
    ast.copy_location(call, location)
    ast.copy_location(expr, location)
    return expr


def _is_docstring(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_future_import(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
    )


class Instrumenter(ast.NodeTransformer):
    """Transform a module AST to inject pycov probes."""

    def __init__(self, path: str, source: str) -> None:
        self.path = path
        self.source = source
        self.file_id = file_id_for(path)
        self.next_stmt_id = 0
        self.next_decision_id = 0
        self.statements: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []

    # -- public -----------------------------------------------------
    def run(self, tree: ast.Module) -> tuple[ast.Module, dict[str, Any]]:
        # instrument body lists
        tree = self.visit(tree)
        # prelude: import probes + register file
        prelude = self._build_prelude()
        # skip past docstring + __future__ imports
        insert_at = 0
        body = tree.body
        if body and _is_docstring(body[0]):
            insert_at = 1
        while insert_at < len(body) and _is_future_import(body[insert_at]):
            insert_at += 1
        tree.body = body[:insert_at] + prelude + body[insert_at:]
        ast.fix_missing_locations(tree)
        meta = {
            "file_id": self.file_id,
            "path": self.path,
            "statements": self.statements,
            "decisions": self.decisions,
        }
        return tree, meta

    # -- helpers ----------------------------------------------------
    def _new_stmt_id(self, node: ast.AST) -> int:
        sid = self.next_stmt_id
        self.next_stmt_id += 1
        self.statements.append(
            {
                "id": sid,
                "lineno": getattr(node, "lineno", 0),
                "end_lineno": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                "col_offset": getattr(node, "col_offset", 0),
                "kind": type(node).__name__,
            }
        )
        return sid

    def _new_decision_id(self, node: ast.AST) -> int:
        did = self.next_decision_id
        self.next_decision_id += 1
        return did

    def _src(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:  # pragma: no cover
            return "<expr>"

    def _wrap_decision(self, node: ast.expr) -> ast.expr:
        """Return a new expression that records a decision observation.

        Trivially-constant predicates (``if True:``, ``while False:``) are
        returned unchanged — instrumenting them adds an uncoverable branch
        that would skew coverage numbers for no diagnostic value.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float, str, type(None))):
            return node
        did = self._new_decision_id(node)
        builder = _ExprTreeBuilder(self.file_id, did, self._src)
        wrapped_inner, tree = builder.build(node)
        n_conds = builder.next_cond_id
        src = self._src(node)
        self.decisions.append(
            {
                "id": did,
                "lineno": getattr(node, "lineno", 0),
                "end_lineno": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                "col_offset": getattr(node, "col_offset", 0),
                "n_conds": n_conds,
                "conditions": builder.leaves,
                "tree": tree,
                "src": src,
            }
        )
        # Build:  (enter(...) and False) or exit(..., <wrapped_inner>)
        enter_call = _call(
            DEC_ENTER,
            [
                ast.Constant(self.file_id),
                ast.Constant(did),
                ast.Constant(n_conds),
            ],
        )
        left = ast.BoolOp(
            op=ast.And(), values=[enter_call, ast.Constant(False)]
        )
        exit_call = _call(
            DEC_EXIT,
            [
                ast.Constant(self.file_id),
                ast.Constant(did),
                wrapped_inner,
            ],
        )
        combo = ast.BoolOp(op=ast.Or(), values=[left, exit_call])
        ast.copy_location(combo, node)
        return combo

    def _probe_then(self, node: ast.stmt) -> list[ast.stmt]:
        probe = _stmt_probe(self.file_id, self._new_stmt_id(node), node)
        return [probe, node]

    # -- unused helpers removed ------------------------------------

    # -- node visitors ---------------------------------------------
    def visit_Module(self, node: ast.Module) -> ast.Module:
        node.body = self._visit_body(node.body, module_like=True)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit_defaults(node)
        node.body = self._visit_body(node.body, module_like=True)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit_defaults(node)
        node.body = self._visit_body(node.body, module_like=True)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.generic_visit_defaults(node)
        node.body = self._visit_body(node.body, module_like=True)
        return node

    def generic_visit_defaults(self, node: ast.AST) -> None:
        """Visit decorators/default args so nested decisions inside them are
        still instrumented, but don't wrap the whole decorator expression."""
        for field in ("decorator_list", "bases", "keywords", "returns"):
            vals = getattr(node, field, None)
            if isinstance(vals, list):
                setattr(node, field, [self._visit_expr(v) for v in vals])
            elif vals is not None:
                setattr(node, field, self._visit_expr(vals))
        args = getattr(node, "args", None)
        if args is not None:
            args.defaults = [self._visit_expr(v) for v in args.defaults]
            args.kw_defaults = [
                None if v is None else self._visit_expr(v) for v in args.kw_defaults
            ]

    def _visit_expr(self, node: ast.AST) -> ast.AST:
        return self.visit(node)

    def visit_If(self, node: ast.If) -> ast.AST:
        node.test = self._wrap_decision(self._visit_expr(node.test))
        node.body = self._visit_body(node.body)
        node.orelse = self._visit_body(node.orelse)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        node.test = self._wrap_decision(self._visit_expr(node.test))
        node.body = self._visit_body(node.body)
        node.orelse = self._visit_body(node.orelse)
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        node.iter = self._visit_expr(node.iter)
        node.body = self._visit_body(node.body)
        node.orelse = self._visit_body(node.orelse)
        return node

    def visit_AsyncFor(self, node: ast.AsyncFor) -> ast.AST:
        node.iter = self._visit_expr(node.iter)
        node.body = self._visit_body(node.body)
        node.orelse = self._visit_body(node.orelse)
        return node

    def visit_With(self, node: ast.With) -> ast.AST:
        for item in node.items:
            item.context_expr = self._visit_expr(item.context_expr)
        node.body = self._visit_body(node.body)
        return node

    def visit_AsyncWith(self, node: ast.AsyncWith) -> ast.AST:
        for item in node.items:
            item.context_expr = self._visit_expr(item.context_expr)
        node.body = self._visit_body(node.body)
        return node

    def visit_Try(self, node: ast.Try) -> ast.AST:
        node.body = self._visit_body(node.body)
        for h in node.handlers:
            if h.type is not None:
                h.type = self._visit_expr(h.type)
            h.body = self._visit_body(h.body)
        node.orelse = self._visit_body(node.orelse)
        node.finalbody = self._visit_body(node.finalbody)
        return node

    # Python 3.11+: TryStar (except*) has the same shape as Try
    def visit_TryStar(self, node):  # pragma: no cover - 3.11+
        return self.visit_Try(node)  # type: ignore[arg-type]

    def visit_Match(self, node: ast.Match) -> ast.AST:
        node.subject = self._visit_expr(node.subject)
        new_cases = []
        for case in node.cases:
            if case.guard is not None:
                case.guard = self._wrap_decision(self._visit_expr(case.guard))
            case.body = self._visit_body(case.body)
            new_cases.append(case)
        node.cases = new_cases
        return node

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        node.test = self._wrap_decision(self._visit_expr(node.test))
        if node.msg is not None:
            node.msg = self._visit_expr(node.msg)
        return node

    def visit_IfExp(self, node: ast.IfExp) -> ast.AST:
        node.test = self._wrap_decision(self._visit_expr(node.test))
        node.body = self._visit_expr(node.body)
        node.orelse = self._visit_expr(node.orelse)
        return node

    def _visit_comprehensions(self, generators: list[ast.comprehension]) -> None:
        for gen in generators:
            gen.iter = self._visit_expr(gen.iter)
            gen.ifs = [self._wrap_decision(self._visit_expr(i)) for i in gen.ifs]

    def visit_ListComp(self, node: ast.ListComp) -> ast.AST:
        self._visit_comprehensions(node.generators)
        node.elt = self._visit_expr(node.elt)
        return node

    def visit_SetComp(self, node: ast.SetComp) -> ast.AST:
        self._visit_comprehensions(node.generators)
        node.elt = self._visit_expr(node.elt)
        return node

    def visit_DictComp(self, node: ast.DictComp) -> ast.AST:
        self._visit_comprehensions(node.generators)
        node.key = self._visit_expr(node.key)
        node.value = self._visit_expr(node.value)
        return node

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ast.AST:
        self._visit_comprehensions(node.generators)
        node.elt = self._visit_expr(node.elt)
        return node

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        node.body = self._visit_expr(node.body)
        return node

    # -- body-list core --------------------------------------------
    def _visit_body(
        self, body: list[ast.stmt], *, module_like: bool = False
    ) -> list[ast.stmt]:
        out: list[ast.stmt] = []
        i = 0
        # preserve docstring at the top of module/function/class bodies
        if module_like and body and _is_docstring(body[0]):
            out.append(body[0])
            i = 1
        while i < len(body):
            stmt = body[i]
            if _is_future_import(stmt):
                out.append(stmt)
                i += 1
                continue
            visited = self.visit(stmt)
            out.extend(self._probe_then(visited))
            i += 1
        return out

    # -- prelude ---------------------------------------------------
    def _build_prelude(self) -> list[ast.stmt]:
        """Emit: probe imports + registry call with this file's metadata."""
        import_probes = ast.ImportFrom(
            module=PROBES_MODULE,
            names=[
                ast.alias(name=STMT_FN, asname=None),
                ast.alias(name=DEC_ENTER, asname=None),
                ast.alias(name=DEC_EXIT, asname=None),
                ast.alias(name=COND_FN, asname=None),
            ],
            level=0,
        )
        import_register = ast.ImportFrom(
            module="pycov._registry",
            names=[ast.alias(name="register_from_meta", asname="_pycov_register")],
            level=0,
        )
        reg_call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="_pycov_register", ctx=ast.Load()),
                args=[_literal(self._meta_for_register())],
                keywords=[],
            )
        )
        return [import_probes, import_register, reg_call]

    def _meta_for_register(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "path": self.path,
            "statements": self.statements,
            "decisions": self.decisions,
        }


def _literal(value: Any) -> ast.expr:
    """Convert a plain JSON-ish Python value to an ast.expr literal."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return ast.Constant(value=value)
    if isinstance(value, list):
        return ast.List(elts=[_literal(v) for v in value], ctx=ast.Load())
    if isinstance(value, tuple):
        return ast.Tuple(elts=[_literal(v) for v in value], ctx=ast.Load())
    if isinstance(value, dict):
        return ast.Dict(
            keys=[_literal(k) for k in value.keys()],
            values=[_literal(v) for v in value.values()],
        )
    raise TypeError(f"unsupported literal type: {type(value).__name__}")


def instrument(path: str, source: str) -> tuple[Any, dict[str, Any]]:
    """Parse and instrument *source* loaded from *path*. Returns (code, meta)."""
    tree = ast.parse(source, filename=path)
    inst = Instrumenter(path, source)
    new_tree, meta = inst.run(tree)
    code = compile(new_tree, path, "exec", dont_inherit=True)
    return code, meta
