"""Executable source adapters for the frozen Scorch public-patch study.

The admitted adapters are dependency-free semantic models of complete changed
production regions.  They do not import or execute Scorch.  Each adapter is
paired with immutable parent/child commits and an explicit hunk disposition in
``data/public-adapter-evidence.json``.

P01 remains executable as a *rejected candidate adapter*.  Its 1--4 operand
range is a finite validation boundary, not an upstream source restriction, and
mixed scalar/non-scalar source inputs expose different exception classes across
the parent and child.  It is therefore not counted as an admitted complete
source adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import permutations, product
import random
from typing import Any, Callable, Iterable, Sequence


SOURCE_PINS = {
    "P01": {
        "parent": "b061b530c08141bf01f190ccb515906e4570f8cf",
        "parent_tree": "c14df7e097884f46e36c42fbddf761b627ef2515",
        "child": "72c55d36de12f45a4dcdd222f760b0fb6c3b6276",
        "child_tree": "ddca30e628378ad419ca4fb2462beac96291226c",
        "decision": "abstained",
    },
    "P04": {
        "parent": "08a92fe381cbddcbcfa2a616644f65b149d50287",
        "parent_tree": "94f3271ae26446aa344098e1d84c03c5efb3198d",
        "child": "d7a9cdc82819750c1a1285cded8385165ea51371",
        "child_tree": "90f89cde813156464b6fefbf016b3de4597568fc",
        "decision": "admitted",
    },
    "P06": {
        "parent": "404e10762f866303758ec60ac6a9cf996be7da0c",
        "parent_tree": "a304c3a16ed566c20f91c83cb2fc9ea0681993e3",
        "child": "2105686711292cd1d1eb2438035b555fa644bf2a",
        "child_tree": "618ebda80bca1961391c7c352017db5abadd8e4d",
        "decision": "admitted",
    },
    "P08": {
        "parent": "b606b3078082ba78a57ed818b848db7214026788",
        "parent_tree": "43fa6a5fd0547dd6bd4b6f9692ff2c7207a51622",
        "child": "33532a3092035a93d4e78936e089c69fa6f3d3e9",
        "child_tree": "49d2a0fb1f710b4ea97bea54d9bb6bee5e5afc24",
        "decision": "admitted",
    },
}


# ---------------------------------------------------------------------------
# P01 candidate: exec/eval CIN construction -> direct constructor calls
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IVar:
    name: str


@dataclass(frozen=True)
class Access:
    tensor: str
    indices: tuple[str, ...]

    def __mul__(self, other: "Expr") -> "Mul":
        return Mul(self, other)


@dataclass(frozen=True)
class Mul:
    left: "Expr"
    right: "Expr"

    def __mul__(self, other: "Expr") -> "Mul":
        return Mul(self, other)


Expr = Access | Mul


@dataclass(frozen=True)
class Assign:
    lhs: Access
    rhs: Expr


@dataclass(frozen=True)
class Loop:
    index: str
    stmt: "Stmt"


Stmt = Assign | Loop


class TVar:
    """Relevant TensorVar overloads, restricted to observable AST state."""

    def __init__(self, name: str):
        self.name = name
        self.assignment: Assign | None = None

    @staticmethod
    def _indices(key: Any) -> tuple[str, ...]:
        # The upstream TensorAccess constructor accepts an empty tuple and does
        # not validate arity here.  Preserve that source behavior so scalar
        # accesses remain a real boundary control rather than an adapter filter.
        xs = key if isinstance(key, tuple) else (key,)
        if not all(isinstance(x, IVar) for x in xs):
            raise TypeError("indices must be IVar values")
        return tuple(x.name for x in xs)

    def __getitem__(self, key: Any) -> Access:
        return Access(self.name, self._indices(key))

    def __setitem__(self, key: Any, value: Expr) -> None:
        self.assignment = Assign(Access(self.name, self._indices(key)), value)


@dataclass(frozen=True)
class EinsumBuildSpec:
    operands: tuple[tuple[str, ...], ...]
    result: tuple[str, ...]
    schedule: tuple[str, ...]

    def validate_source_shape(self) -> None:
        # The source has 26 temporary tensor names.  The 1--4 exhaustive range
        # below is deliberately only a finite validation boundary.
        if not 1 <= len(self.operands) <= 26:
            raise ValueError("one to twenty-six operands")
        names = {x for op in self.operands for x in op} | set(self.result)
        if any(len(x) != 1 or not x.islower() for x in names):
            raise ValueError("controlled single-letter index names only")
        if len(set(self.schedule)) != len(self.schedule) or set(self.schedule) != names:
            raise ValueError("schedule must be a permutation of used names")

    def validate_success_domain(self) -> None:
        self.validate_source_shape()
        if not self.result or any(not x for x in self.operands):
            raise ValueError("candidate success domain excludes scalar accesses")


def _scope(spec: EinsumBuildSpec) -> tuple[list[TVar], TVar, dict[str, IVar]]:
    names = sorted(set(spec.schedule))
    return (
        [TVar(chr(ord("A") + i)) for i in range(len(spec.operands))],
        TVar("R"),
        {name: IVar(name) for name in names},
    )


def build_cin_before_source(spec: EinsumBuildSpec) -> Stmt:
    """Execute the parent source-region construction, including failures."""
    spec.validate_source_shape()
    tensor_vars, result_tensor_var, index_var_dict = _scope(spec)
    # This is the source assertion.  It excludes the all-scalar expression but
    # does not exclude one scalar operand in an otherwise indexed expression.
    assert index_var_dict, "index_var_dict is empty"
    rhs = ""
    for i, _tensor_var in enumerate(tensor_vars):
        inside = ", ".join(
            f'index_var_dict["{index_str}"]' for index_str in spec.operands[i]
        )
        rhs += f"tensor_vars[{i}][{inside}]"
        if i < len(tensor_vars) - 1:
            rhs += " * "
    lhs_inside = ", ".join(
        f'index_var_dict["{index_str}"]' for index_str in spec.result
    )
    code = f"result_tensor_var[{lhs_inside}] = {rhs}"
    local = {
        "tensor_vars": tensor_vars,
        "result_tensor_var": result_tensor_var,
        "index_var_dict": index_var_dict,
    }
    exec(code, {"__builtins__": {}}, local)
    if result_tensor_var.assignment is None:
        raise AssertionError("assignment was not created")
    rhs_text = "result_tensor_var.assignment"
    for index_str in spec.schedule[::-1]:
        rhs_text = f'Loop(index_var_dict["{index_str}"].name, {rhs_text})'
    return eval(rhs_text, {"__builtins__": {}, "Loop": Loop}, local)


def build_cin_after_source(spec: EinsumBuildSpec) -> Stmt:
    """Execute the child source-region construction, including failures."""
    spec.validate_source_shape()
    tensor_vars, result_tensor_var, index_var_dict = _scope(spec)
    assert index_var_dict, "index_var_dict is empty"
    rhs_expr: Expr | None = None
    for i, tensor_var in enumerate(tensor_vars):
        indices = [index_var_dict[s] for s in spec.operands[i]]
        # An empty operand takes the tuple branch, yielding an empty-index access.
        access = tensor_var[indices[0]] if len(indices) == 1 else tensor_var[tuple(indices)]
        rhs_expr = access if rhs_expr is None else rhs_expr * access
    lhs_indices = [index_var_dict[s] for s in spec.result]
    lhs_key: Any = lhs_indices[0] if len(lhs_indices) == 1 else tuple(lhs_indices)
    result_tensor_var[lhs_key] = rhs_expr  # type: ignore[arg-type]
    if result_tensor_var.assignment is None:
        raise AssertionError("assignment was not created")
    cin_stmt: Stmt = result_tensor_var.assignment
    for index_str in reversed(spec.schedule):
        cin_stmt = Loop(index_var_dict[index_str].name, cin_stmt)
    return cin_stmt


def p01_exhaustive_specs() -> list[EinsumBuildSpec]:
    """Finite successful-domain validation: 1--4 operands, not a source bound."""
    patterns = (("i",), ("j",), ("i", "j"), ("j", "i"), ("i", "i"), ("i", "j", "k"))
    results = (("i",), ("j",), ("i", "j"), ("j", "i"), ("i", "k"))
    out: list[EinsumBuildSpec] = []
    for nops in (1, 2, 3, 4):
        for operands in product(patterns, repeat=nops):
            used = {x for op in operands for x in op}
            for result in results:
                if not set(result).issubset(used):
                    continue
                names = sorted(used | set(result))
                for schedule in permutations(names):
                    out.append(EinsumBuildSpec(tuple(operands), tuple(result), tuple(schedule)))
    return out


def p01_scalar_boundary_cases() -> list[EinsumBuildSpec]:
    """Source-reachable mixed/scalar shapes that invalidate full admission."""
    return [
        EinsumBuildSpec(((), ("i",)), ("i",), ("i",)),
        EinsumBuildSpec((("i",), ()), ("i",), ("i",)),
        EinsumBuildSpec((("i",),), (), ("i",)),
        EinsumBuildSpec(((),), (), ()),
    ]


# ---------------------------------------------------------------------------
# Shared LLIR node model used by P04 and P06
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Literal:
    value: str


@dataclass(frozen=True)
class Var:
    name: str
    typ: str = "int"
    is_ptr: bool = False


@dataclass(frozen=True)
class Cast:
    typ: str
    expr: "Node"


@dataclass(frozen=True)
class Sizeof:
    typ: str


@dataclass(frozen=True)
class BinOp:
    left: "Node"
    op: str
    right: "Node"


@dataclass(frozen=True)
class UnaryOp:
    op: str
    operand: "Node"


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple["Node", ...]


@dataclass(frozen=True)
class Array:
    values: tuple["Node", ...]
    typ: str = "int"


@dataclass(frozen=True)
class ArrayAccess:
    array: "Node"
    index: "Node"


@dataclass(frozen=True)
class CallStmt:
    name: str
    args: tuple["Node", ...]


@dataclass(frozen=True)
class VarInit:
    var: Var
    value: "Node"
    op: str = "="
    cast: bool = False


@dataclass(frozen=True)
class AssignNode:
    var: Var
    value: "Node"
    op: str = "="


@dataclass(frozen=True)
class WhileLoop:
    cond: "Node"
    body: tuple["Node", ...]


@dataclass(frozen=True)
class ForLoop:
    init: "Node | None"
    cond: "Node"
    update: "Node"
    body: tuple["Node", ...]


@dataclass(frozen=True)
class ForLoopAuto:
    var: Var
    array: "Node"
    body: tuple["Node", ...]


@dataclass(frozen=True)
class IfNode:
    cond: "Node | None" = None
    then_body: tuple["Node", ...] = ()
    else_body: tuple["Node", ...] = ()
    cond_list: tuple["Node", ...] = ()
    then_body_list: tuple[tuple["Node", ...], ...] = ()
    make_last_case_else: bool = False


@dataclass(frozen=True)
class VarDecl:
    var: Var


@dataclass(frozen=True)
class Increment:
    var: Var


@dataclass(frozen=True)
class Function:
    name: str
    args: tuple[Var, ...]
    return_type: str
    body: tuple["Node", ...]


@dataclass(frozen=True)
class Return:
    value: "Node"


@dataclass(frozen=True)
class Comment:
    text: str


@dataclass(frozen=True)
class Blank:
    pass


Node = (
    Literal | Var | Cast | Sizeof | BinOp | UnaryOp | Call | Array | ArrayAccess |
    CallStmt | VarInit | AssignNode | WhileLoop | ForLoop | ForLoopAuto | IfNode |
    VarDecl | Increment | Function | Return | Comment | Blank
)


def _indent(text: str, level: int) -> str:
    # The pinned dispatcher prefixes the string once, including multiline text.
    return "  " * level + text


# ---------------------------------------------------------------------------
# P04: monolithic LLIR renderer -> extracted helper dispatch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RenderCase:
    case_id: str
    node: Node | tuple[Node, ...] | str
    indent_level: int = 0
    no_semicolon: bool = False
    no_comments: bool = False


def _parent_render(
    node: Node | tuple[Node, ...] | str,
    level: int = 0,
    no_semicolon: bool = False,
    no_comments: bool = False,
) -> str:
    """Independent monolithic reference transcribed from the fixed parent."""
    if isinstance(node, str):
        return "  " * level + node
    if isinstance(node, tuple):
        lines = [_parent_render(x, level, False, no_comments) for x in node]
        return "\n".join(line for line in lines if line != "")
    if isinstance(node, Comment):
        if no_comments:
            return ""
        return _parent_render("// " + node.text, level, False, no_comments)
    if isinstance(node, Blank):
        return _parent_render(" ", level, False, no_comments)
    if isinstance(node, Literal):
        return _parent_render(str(node.value), level, False, no_comments)
    if isinstance(node, VarInit):
        return _parent_render(
            f"{node.var.typ} {node.var.name} {node.op} {_parent_render(node.value, 0, False, no_comments)};",
            level, False, no_comments,
        )
    if isinstance(node, AssignNode):
        suffix = "" if no_semicolon else ";"
        return _parent_render(
            f"{node.var.name} {node.op} {_parent_render(node.value, 0, False, no_comments)}{suffix}",
            level, False, no_comments,
        )
    if isinstance(node, Cast):
        return _parent_render(f"({node.typ}) {_parent_render(node.expr, 0, False, no_comments)}", level, False, no_comments)
    if isinstance(node, Sizeof):
        return _parent_render(f"sizeof({node.typ})", level, False, no_comments)
    if isinstance(node, BinOp):
        return _parent_render(
            f"{_parent_render(node.left, 0, False, no_comments)} {node.op} {_parent_render(node.right, 0, False, no_comments)}",
            level, False, no_comments,
        )
    if isinstance(node, UnaryOp):
        return _parent_render(f"{node.op} {_parent_render(node.operand, 0, False, no_comments)}", level, False, no_comments)
    if isinstance(node, Call):
        return _parent_render(
            f"{node.name}({', '.join(_parent_render(a, 0, False, no_comments) for a in node.args)})",
            level, False, no_comments,
        )
    if isinstance(node, CallStmt):
        return _parent_render(
            f"{node.name}({', '.join(_parent_render(a, 0, False, no_comments) for a in node.args)});",
            level, False, no_comments,
        )
    if isinstance(node, Array):
        return _parent_render("{" + ", ".join(_parent_render(v, 0, False, no_comments) for v in node.values) + "}", level, False, no_comments)
    if isinstance(node, ArrayAccess):
        return _parent_render(
            f"{_parent_render(node.array, 0, False, no_comments)}[{_parent_render(node.index, 0, False, no_comments)}]",
            level, False, no_comments,
        )
    if isinstance(node, WhileLoop):
        return (
            _parent_render(f"while ({_parent_render(node.cond, 0, False, no_comments)}) {{", level, False, no_comments)
            + "\n" + _parent_render(node.body, level + 1, False, no_comments)
            + "\n" + _parent_render("}", level, False, no_comments)
        )
    if isinstance(node, ForLoop):
        init = _parent_render(node.init, 0, False, no_comments) if node.init is not None else ";"
        header = f"for ({init} {_parent_render(node.cond, 0, False, no_comments)}; {_parent_render(node.update, 0, True, no_comments)}) {{"
        return _parent_render(header, level, False, no_comments) + "\n" + _parent_render(node.body, level + 1, False, no_comments) + "\n" + _parent_render("}", level, False, no_comments)
    if isinstance(node, ForLoopAuto):
        header = f"for ({node.var.typ} {_parent_render(node.var, 0, False, no_comments)} : {_parent_render(node.array, 0, False, no_comments)}) {{"
        return _parent_render(header, level, False, no_comments) + "\n" + _parent_render(node.body, level + 1, False, no_comments) + "\n" + _parent_render("}", level, False, no_comments)
    if isinstance(node, IfNode):
        result = ""
        if node.cond_list:
            if not node.then_body_list or len(node.cond_list) != len(node.then_body_list):
                raise AssertionError("branch mismatch")
            total = len(node.cond_list) + (1 if node.else_body else 0)
            for i, cond in enumerate(node.cond_list):
                if i == 0:
                    header = f"if ({_parent_render(cond, 0, False, no_comments)}) {{"
                elif node.make_last_case_else and i == total - 1:
                    header = "} else {"
                else:
                    header = f"}} else if ({_parent_render(cond, 0, False, no_comments)}) {{"
                result += _parent_render(header, level, False, no_comments) + "\n"
                result += _parent_render(node.then_body_list[i], level + 1, False, no_comments) + "\n"
        else:
            if node.cond is None or not node.then_body:
                raise AssertionError("missing branch")
            result += _parent_render(f"if ({_parent_render(node.cond, 0, False, no_comments)}) {{", level, False, no_comments) + "\n"
            result += _parent_render(node.then_body, level + 1, False, no_comments) + "\n"
        if node.else_body:
            result += _parent_render("} else {", level, False, no_comments) + "\n"
            result += _parent_render(node.else_body, level + 1, False, no_comments) + "\n"
        return result + _parent_render("}", level, False, no_comments)
    if isinstance(node, Var):
        return node.name
    if isinstance(node, VarDecl):
        return _parent_render(f"{node.var.typ} {node.var.name};", level, False, no_comments)
    if isinstance(node, Increment):
        return _parent_render(node.var.name + "++" + ("" if no_semicolon else ";"), level, False, no_comments)
    if isinstance(node, Function):
        header = f"{node.return_type} {node.name}({', '.join(f'{a.typ} {a.name}' for a in node.args)}) {{"
        return _parent_render(header, level, False, no_comments) + "\n" + _parent_render(node.body, level + 1, False, no_comments) + "\n" + _parent_render("}", level, False, no_comments)
    if isinstance(node, Return):
        return _parent_render(f"return {_parent_render(node.value, 0, False, no_comments)};", level, False, no_comments)
    return _parent_render(f"No code gen implemented for node type: {type(node).__name__}", level, False, no_comments)


def _child_render_expression(node: Node, level: int, no_comments: bool) -> str:
    if isinstance(node, Literal):
        return _indent(str(node.value), level)
    if isinstance(node, Cast):
        return _indent(f"({node.typ}) {_child_render(node.expr, 0, False, no_comments)}", level)
    if isinstance(node, Sizeof):
        return _indent(f"sizeof({node.typ})", level)
    if isinstance(node, BinOp):
        return _indent(f"{_child_render(node.left, 0, False, no_comments)} {node.op} {_child_render(node.right, 0, False, no_comments)}", level)
    if isinstance(node, UnaryOp):
        return _indent(f"{node.op} {_child_render(node.operand, 0, False, no_comments)}", level)
    if isinstance(node, Call):
        return _indent(f"{node.name}({', '.join(_child_render(a, 0, False, no_comments) for a in node.args)})", level)
    if isinstance(node, Array):
        return _indent("{" + ", ".join(_child_render(v, 0, False, no_comments) for v in node.values) + "}", level)
    if isinstance(node, ArrayAccess):
        return _indent(f"{_child_render(node.array, 0, False, no_comments)}[{_child_render(node.index, 0, False, no_comments)}]", level)
    raise ValueError(f"unknown expression {type(node).__name__}")


def _child_render_loop(node: WhileLoop | ForLoop | ForLoopAuto, level: int, no_comments: bool) -> str:
    if isinstance(node, WhileLoop):
        header = f"while ({_child_render(node.cond, 0, False, no_comments)}) {{"
    elif isinstance(node, ForLoop):
        init = _child_render(node.init, 0, False, no_comments) if node.init is not None else ";"
        header = f"for ({init} {_child_render(node.cond, 0, False, no_comments)}; {_child_render(node.update, 0, True, no_comments)}) {{"
    else:
        header = f"for ({node.var.typ} {_child_render(node.var, 0, False, no_comments)} : {_child_render(node.array, 0, False, no_comments)}) {{"
    return _indent(header, level) + "\n" + _child_render(node.body, level + 1, False, no_comments) + "\n" + _indent("}", level)


def _child_render_conditional(node: IfNode, level: int, no_comments: bool) -> str:
    result = ""
    if node.cond_list:
        if not node.then_body_list or len(node.cond_list) != len(node.then_body_list):
            raise AssertionError("branch mismatch")
        total = len(node.cond_list) + (1 if node.else_body else 0)
        for i, cond in enumerate(node.cond_list):
            if i == 0:
                header = f"if ({_child_render(cond, 0, False, no_comments)}) {{"
            elif node.make_last_case_else and i == total - 1:
                header = "} else {"
            else:
                header = f"}} else if ({_child_render(cond, 0, False, no_comments)}) {{"
            result += _indent(header, level) + "\n"
            result += _child_render(node.then_body_list[i], level + 1, False, no_comments) + "\n"
    else:
        if node.cond is None or not node.then_body:
            raise AssertionError("missing branch")
        result += _indent(f"if ({_child_render(node.cond, 0, False, no_comments)}) {{", level) + "\n"
        result += _child_render(node.then_body, level + 1, False, no_comments) + "\n"
    if node.else_body:
        result += _indent("} else {", level) + "\n"
        result += _child_render(node.else_body, level + 1, False, no_comments) + "\n"
    return result + _indent("}", level)


def _child_render_function(node: Function, level: int, no_comments: bool) -> str:
    header = f"{node.return_type} {node.name}({', '.join(f'{a.typ} {a.name}' for a in node.args)}) {{"
    return _indent(header, level) + "\n" + _child_render(node.body, level + 1, False, no_comments) + "\n" + _indent("}", level)


def _child_render(
    node: Node | tuple[Node, ...] | str,
    level: int = 0,
    no_semicolon: bool = False,
    no_comments: bool = False,
) -> str:
    """Independent helper-dispatch implementation transcribed from the child."""
    if isinstance(node, str):
        return _indent(node, level)
    if isinstance(node, tuple):
        lines = [_child_render(x, level, False, no_comments) for x in node]
        return "\n".join(line for line in lines if line != "")
    if isinstance(node, Comment):
        return "" if no_comments else _indent("// " + node.text, level)
    if isinstance(node, Blank):
        return _indent(" ", level)
    if isinstance(node, VarInit):
        return _indent(f"{node.var.typ} {node.var.name} {node.op} {_child_render(node.value, 0, False, no_comments)};", level)
    if isinstance(node, AssignNode):
        return _indent(f"{node.var.name} {node.op} {_child_render(node.value, 0, False, no_comments)}" + ("" if no_semicolon else ";"), level)
    if isinstance(node, (Literal, Cast, Sizeof, BinOp, UnaryOp, Call, Array, ArrayAccess)):
        return _child_render_expression(node, level, no_comments)
    if isinstance(node, CallStmt):
        return _indent(f"{node.name}({', '.join(_child_render(a, 0, False, no_comments) for a in node.args)});", level)
    if isinstance(node, (WhileLoop, ForLoop, ForLoopAuto)):
        return _child_render_loop(node, level, no_comments)
    if isinstance(node, IfNode):
        return _child_render_conditional(node, level, no_comments)
    if isinstance(node, Var):
        return node.name
    if isinstance(node, VarDecl):
        return _indent(f"{node.var.typ} {node.var.name};", level)
    if isinstance(node, Increment):
        return _indent(node.var.name + "++" + ("" if no_semicolon else ";"), level)
    if isinstance(node, Function):
        return _child_render_function(node, level, no_comments)
    if isinstance(node, Return):
        return _indent(f"return {_child_render(node.value, 0, False, no_comments)};", level)
    return _indent(f"No code gen implemented for node type: {type(node).__name__}", level)


def render_parent(case: RenderCase) -> str:
    return _parent_render(case.node, case.indent_level, case.no_semicolon, case.no_comments)


def render_child(case: RenderCase) -> str:
    return _child_render(case.node, case.indent_level, case.no_semicolon, case.no_comments)


@dataclass
class ParentRenderSession:
    """Persistent comment flag in the pinned parent lowerer."""
    no_comments: bool = False

    def render(self, case: RenderCase) -> str:
        if case.no_comments:
            self.no_comments = True
        return _parent_render(case.node, case.indent_level, case.no_semicolon, self.no_comments)


@dataclass
class ChildRenderSession:
    """Persistent comment flag in the extracted child dispatcher."""
    no_comments: bool = False

    def render(self, case: RenderCase) -> str:
        if case.no_comments:
            self.no_comments = True
        return _child_render(case.node, case.indent_level, case.no_semicolon, self.no_comments)


P04_MUTANTS = (
    "omit-call-semicolon",
    "reverse-function-args",
    "drop-array-braces",
    "increment-always-semicolon",
    "drop-final-brace",
    "conditional-change-condition",
    "conditional-drop-else",
    "conditional-drop-closing-brace",
)


def _change_first_condition(node: IfNode) -> IfNode:
    def changed(cond: Node) -> Node:
        if isinstance(cond, BinOp):
            return BinOp(cond.left, "<=" if cond.op == "<" else "!=", cond.right)
        return UnaryOp("!", cond)
    if node.cond_list:
        return replace(node, cond_list=(changed(node.cond_list[0]),) + node.cond_list[1:])
    if node.cond is not None:
        return replace(node, cond=changed(node.cond))
    return node


def render_mutant(case: RenderCase, mutant: str) -> str:
    node = case.node
    if mutant == "reverse-function-args" and isinstance(node, Function):
        return render_child(replace(case, node=replace(node, args=tuple(reversed(node.args)))))
    if mutant == "drop-array-braces" and isinstance(node, Array):
        return ", ".join(_child_render(v) for v in node.values)
    if mutant == "increment-always-semicolon" and isinstance(node, ForLoop):
        init = _child_render(node.init) if node.init is not None else ";"
        header = f"for ({init} {_child_render(node.cond)}; {_child_render(node.update, 0, False)}) {{"
        return _indent(header, case.indent_level) + "\n" + _child_render(node.body, case.indent_level + 1) + "\n" + _indent("}", case.indent_level)
    if mutant == "conditional-change-condition" and isinstance(node, IfNode):
        return render_child(replace(case, node=_change_first_condition(node)))
    if mutant == "conditional-drop-else" and isinstance(node, IfNode) and node.else_body:
        return render_child(replace(case, node=replace(node, else_body=())))
    base = render_child(case)
    if mutant == "omit-call-semicolon" and isinstance(node, CallStmt):
        return base[:-1]
    if mutant == "drop-final-brace" and isinstance(node, Function):
        return base.rsplit("\n", 1)[0]
    if mutant == "conditional-drop-closing-brace" and isinstance(node, IfNode):
        return base.rsplit("\n", 1)[0] if "\n" in base else base[:-1]
    return base


def p04_cases() -> list[RenderCase]:
    x, y = Var("x"), Var("y")
    cases = [
        RenderCase("literal-zero", Literal("0")),
        RenderCase("literal-one", Literal("1")),
        RenderCase("var", x),
        RenderCase("cast", Cast("float", x)),
        RenderCase("sizeof", Sizeof("int")),
        RenderCase("binop", BinOp(x, "+", Literal("1"))),
        RenderCase("unary", UnaryOp("-", x)),
        RenderCase("call-expression", Call("f", (x, Literal("2")))),
        RenderCase("array", Array((x, Literal("3")), "int")),
        RenderCase("array-access", ArrayAccess(Var("a", "int*"), x)),
        RenderCase("comment-visible", Comment("note")),
        RenderCase("comment-suppressed", Comment("note"), no_comments=True),
        RenderCase("blank", Blank()),
        RenderCase("call-statement", CallStmt("f", (x, y))),
        RenderCase("var-init", VarInit(Var("z"), BinOp(x, "+", y))),
        RenderCase("assign", AssignNode(x, y)),
        RenderCase("while", WhileLoop(BinOp(x, "<", y), (Increment(x),))),
        RenderCase("for-with-init", ForLoop(VarInit(x, Literal("0")), BinOp(x, "<", Literal("4")), Increment(x), (CallStmt("g", (x,)),))),
        RenderCase("for-init-none", ForLoop(None, BinOp(x, "<", Literal("4")), Increment(x), (CallStmt("g", (x,)),))),
        RenderCase("for-auto", ForLoopAuto(Var("v", "auto"), Var("arr", "auto"), (CallStmt("use", (Var("v"),)),))),
        RenderCase("if-simple", IfNode(cond=BinOp(x, "<", y), then_body=(AssignNode(x, y),))),
        RenderCase("if-simple-else", IfNode(cond=BinOp(x, "<", y), then_body=(AssignNode(x, y),), else_body=(AssignNode(y, x),))),
        RenderCase("if-chain-else", IfNode(cond_list=(BinOp(x, "<", y), BinOp(x, "==", y)), then_body_list=((AssignNode(x, y),), (AssignNode(y, x),)), else_body=(Return(x),))),
        RenderCase("if-last-case-else", IfNode(cond_list=(BinOp(x, "<", y), BinOp(x, "==", y)), then_body_list=((AssignNode(x, y),), (AssignNode(y, x),)), make_last_case_else=True)),
        RenderCase("var-decl", VarDecl(Var("q", "float"))),
        RenderCase("increment", Increment(x)),
        RenderCase("increment-no-semicolon", Increment(x), no_semicolon=True),
        RenderCase("return", Return(x)),
        RenderCase("function", Function("kernel", (Var("a", "int"), Var("b", "float")), "void", (CallStmt("use", (x,)), Return(Literal("0"))))),
        RenderCase("list-sequence", (Comment("sequence"), Blank(), CallStmt("use", (x,)))),
    ]
    return cases


def p04_coverage_map() -> dict[str, list[str]]:
    return {
        "Comment": ["comment-visible", "comment-suppressed", "list-sequence"],
        "BlankLine": ["blank", "list-sequence"],
        "Literal/Var/Cast/Sizeof/BinOp/UnaryOp/Call/Array/ArrayAccess": [
            "literal-zero", "var", "cast", "sizeof", "binop", "unary",
            "call-expression", "array", "array-access",
        ],
        "FunctionCallStmt/VarInit/Assign": ["call-statement", "var-init", "assign"],
        "WhileLoop": ["while"],
        "ForLoop.init-present": ["for-with-init"],
        "ForLoop.init-none": ["for-init-none"],
        "ForLoopAuto": ["for-auto"],
        "IfThenElse.simple": ["if-simple", "if-simple-else"],
        "IfThenElse.cond-list": ["if-chain-else"],
        "IfThenElse.make-last-case-else": ["if-last-case-else"],
        "VarDecl/Increment/Return/Function": ["var-decl", "increment", "increment-no-semicolon", "return", "function"],
        "list-dispatch": ["list-sequence"],
    }


# ---------------------------------------------------------------------------
# P06: monolithic coordinate resolution -> CoordinateResolver helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IteratorState:
    tensor: str
    coordinate: bool
    has_child: bool

    @property
    def level(self) -> int:
        return 0

    @property
    def levels(self) -> int:
        return 2 if self.has_child else 1

    @property
    def iterator_var(self) -> Var:
        return Var(f"p{self.tensor}0", "int")

    @property
    def iterator_end_var(self) -> Var:
        return Var(f"p{self.tensor}0_end", "int")

    @property
    def coord_var(self) -> Var:
        return Var(f"i_{self.tensor}", "int")

    @property
    def coord_value(self) -> Node:
        return ArrayAccess(Var(f"{self.tensor}0_crd", "int*"), self.iterator_var)


@dataclass(frozen=True)
class PendingCoordinate:
    statement: VarInit
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class DenseIteratorState:
    coordinate: Var
    value: Node | None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class DenseTransition:
    pre: tuple[PendingCoordinate, ...]
    offered: tuple[DenseIteratorState, ...]
    defined: tuple[str, ...]
    # None = no value (source truthiness guard); False = name already pending.
    inserted: tuple[bool | None, ...]
    snapshot: tuple[PendingCoordinate, ...]
    retained: tuple[bool, ...]
    post: tuple[PendingCoordinate, ...]
    emitted: tuple[Node, ...]


@dataclass(frozen=True)
class CoordResult:
    nodes: tuple[Node, ...]
    pending: tuple[PendingCoordinate, ...]
    dense: DenseTransition


@dataclass(frozen=True)
class CoordState:
    iterators: tuple[IteratorState, ...]
    dense_universe: bool
    result_has_index: bool
    current_dense: bool
    child_compressed: bool
    dense_iterators: tuple[DenseIteratorState, ...] = ()
    defined_index_vars: tuple[str, ...] = ()
    pending: tuple[PendingCoordinate, ...] = ()

    @property
    def index_var(self) -> Var:
        return Var("i", "int")


def _dense_stmt(i: int) -> VarInit:
    return VarInit(Var(f"pD{i}", "int"), BinOp(Var(f"base{i}", "int"), "+", Literal(str(i + 1))))


def coord_before(s: CoordState) -> CoordResult:
    """Independent full-field transcription of the parent monolithic block."""
    out: list[Node] = []
    iterators = s.iterators
    if len(iterators) > 1 or s.dense_universe:
        if iterators:
            out.append(Comment("Load coordinates"))
            for it in iterators:
                out.append(VarInit(it.coord_var, it.coord_value))
        if not s.dense_universe:
            out.extend((
                Blank(),
                Comment("Resolve coordinates"),
                VarInit(s.index_var, Call("std::min", (Array(tuple(it.coord_var for it in iterators), "int"),))),
                Blank(),
            ))
    elif len(iterators) == 1:
        out.extend((
            Comment("Resolve coordinates"),
            VarInit(s.index_var, iterators[0].coord_value),
            Blank(),
        ))

    if s.result_has_index and s.current_dense and s.child_compressed:
        pos = Var("R1_pos_index", "int")
        out.extend((
            Comment("Assemble COMPRESSED level"),
            ForLoop(
                None,
                BinOp(pos, "<", s.index_var),
                Increment(pos),
                (AssignNode(Var("R1_pos[R1_pos_index + 1]", "int"), Call("R1_crd.size", ())),),
            ),
        ))

    end_nodes: list[Node] = []
    for it in iterators:
        if it.coordinate and it.has_child:
            next_end = Var(f"p{it.tensor}1_end", "int")
            end_nodes.extend((
                AssignNode(next_end, BinOp(it.iterator_var, "+", Literal("1"))),
                WhileLoop(
                    BinOp(
                        BinOp(next_end, "<", it.iterator_end_var),
                        "&&",
                        BinOp(ArrayAccess(Var(f"{it.tensor}0_crd", "int*"), next_end), "==", s.index_var),
                    ),
                    (Increment(next_end),),
                ),
                Blank(),
            ))
    if end_nodes:
        out.append(Comment("Find iterator end for coordinate level"))
        out.extend(end_nodes)

    # Parent lines 697--732: the lowerer-owned dictionary survives this call.
    d = {p.statement: p.dependencies for p in s.pending}
    inserted: list[bool | None] = []
    for it in s.dense_iterators:
        if it.value is not None:
            stmt = VarInit(it.coordinate, it.value)
            names = [key.var.name for key in list(d.keys())]
            if stmt.var.name not in names:
                d[stmt] = it.dependencies
                inserted.append(True)
            else:
                inserted.append(False)
        else:
            inserted.append(None)
    defined = set(s.defined_index_vars)
    snapshot = tuple(PendingCoordinate(stmt, deps) for stmt, deps in d.items())
    retained: list[bool] = []
    dense_nodes: list[Node] = []
    for stmt, deps in d.copy().items():
        keep = not set(deps).issubset(defined)
        retained.append(keep)
        if not keep:
            dense_nodes.append(stmt)
            del d[stmt]
    if dense_nodes:
        out.append(Comment("Resolve dense coordinates"))
        out.extend(dense_nodes)
    post = tuple(PendingCoordinate(stmt, deps) for stmt, deps in d.items())
    effect = DenseTransition(s.pending, s.dense_iterators, s.defined_index_vars,
                             tuple(inserted), snapshot, tuple(retained), post,
                             tuple(([Comment("Resolve dense coordinates")] + dense_nodes) if dense_nodes else []))
    return CoordResult(tuple(out), post, effect)


def coord_after(s: CoordState) -> CoordResult:
    """Independent helper decomposition with complete LLIR node fields."""
    def load_coordinates() -> list[Node]:
        if not (len(s.iterators) > 1 or s.dense_universe) or not s.iterators:
            return []
        return [Comment("Load coordinates"), *(VarInit(it.coord_var, it.coord_value) for it in s.iterators)]

    def resolve_coordinates() -> list[Node]:
        if len(s.iterators) > 1 or s.dense_universe:
            if s.dense_universe:
                return []
            return [
                Blank(),
                Comment("Resolve coordinates"),
                VarInit(s.index_var, Call("std::min", (Array(tuple(it.coord_var for it in s.iterators), "int"),))),
                Blank(),
            ]
        if len(s.iterators) == 1:
            return [Comment("Resolve coordinates"), VarInit(s.index_var, s.iterators[0].coord_value), Blank()]
        return []

    def assemble_compressed() -> list[Node]:
        if not (s.result_has_index and s.current_dense and s.child_compressed):
            return []
        pos = Var("R1_pos_index", "int")
        return [
            Comment("Assemble COMPRESSED level"),
            ForLoop(
                None,
                BinOp(pos, "<", s.index_var),
                Increment(pos),
                (AssignNode(Var("R1_pos[R1_pos_index + 1]", "int"), Call("R1_crd.size", ())),),
            ),
        ]

    def coordinate_ends() -> list[Node]:
        nodes: list[Node] = []
        for it in s.iterators:
            if not (it.coordinate and it.has_child):
                continue
            next_end = Var(f"p{it.tensor}1_end", "int")
            nodes.extend((
                AssignNode(next_end, BinOp(it.iterator_var, "+", Literal("1"))),
                WhileLoop(
                    BinOp(
                        BinOp(next_end, "<", it.iterator_end_var),
                        "&&",
                        BinOp(ArrayAccess(Var(f"{it.tensor}0_crd", "int*"), next_end), "==", s.index_var),
                    ),
                    (Increment(next_end),),
                ),
                Blank(),
            ))
        return [] if not nodes else [Comment("Find iterator end for coordinate level"), *nodes]

    def dense_coordinates() -> DenseTransition:
        # Child lines 271--315. Deliberately independent of the parent path.
        pending = {entry.statement: entry.dependencies for entry in s.pending}
        insert_flags: list[bool | None] = []
        for iterator in s.dense_iterators:
            if iterator.value is None:
                insert_flags.append(None)
                continue
            declaration = VarInit(iterator.coordinate, iterator.value)
            to_resolve_names = [declaration.var.name for declaration in pending.keys()]
            if declaration.var.name in to_resolve_names:
                insert_flags.append(False)
                continue
            pending[declaration] = iterator.dependencies
            insert_flags.append(True)
        known = set(s.defined_index_vars)
        copied = pending.copy()
        scan = tuple(PendingCoordinate(stmt, deps) for stmt, deps in copied.items())
        nodes: list[Node] = []
        keep_flags: list[bool] = []
        for declaration, dependencies in copied.items():
            ready = set(dependencies).issubset(known)
            keep_flags.append(not ready)
            if ready:
                nodes.append(declaration)
                del pending[declaration]
        remaining = tuple(PendingCoordinate(stmt, deps) for stmt, deps in pending.items())
        emitted = () if not nodes else (Comment("Resolve dense coordinates"), *nodes)
        return DenseTransition(s.pending, s.dense_iterators, s.defined_index_vars,
                               tuple(insert_flags), scan, tuple(keep_flags), remaining, emitted)

    prefix = tuple(load_coordinates() + resolve_coordinates() + assemble_compressed() + coordinate_ends())
    effect = dense_coordinates()
    return CoordResult(prefix + effect.emitted, effect.post, effect)


P06_MUTANTS = (
    "drop-load",
    "max-not-min",
    "assemble-last",
    "coord-end-off-by-one",
    "drop-dense",
)


def _map_node(node: Node, fn: Callable[[Node], Node]) -> Node:
    """Recursively transform a full LLIR node tree."""
    if isinstance(node, Cast): node = replace(node, expr=_map_node(node.expr, fn))
    elif isinstance(node, BinOp): node = replace(node, left=_map_node(node.left, fn), right=_map_node(node.right, fn))
    elif isinstance(node, UnaryOp): node = replace(node, operand=_map_node(node.operand, fn))
    elif isinstance(node, Call): node = replace(node, args=tuple(_map_node(x, fn) for x in node.args))
    elif isinstance(node, Array): node = replace(node, values=tuple(_map_node(x, fn) for x in node.values))
    elif isinstance(node, ArrayAccess): node = replace(node, array=_map_node(node.array, fn), index=_map_node(node.index, fn))
    elif isinstance(node, CallStmt): node = replace(node, args=tuple(_map_node(x, fn) for x in node.args))
    elif isinstance(node, VarInit): node = replace(node, value=_map_node(node.value, fn))
    elif isinstance(node, AssignNode): node = replace(node, value=_map_node(node.value, fn))
    elif isinstance(node, WhileLoop): node = replace(node, cond=_map_node(node.cond, fn), body=tuple(_map_node(x, fn) for x in node.body))
    elif isinstance(node, ForLoop): node = replace(node, init=_map_node(node.init, fn) if node.init is not None else None, cond=_map_node(node.cond, fn), update=_map_node(node.update, fn), body=tuple(_map_node(x, fn) for x in node.body))
    elif isinstance(node, ForLoopAuto): node = replace(node, array=_map_node(node.array, fn), body=tuple(_map_node(x, fn) for x in node.body))
    elif isinstance(node, IfNode): node = replace(node, cond=_map_node(node.cond, fn) if node.cond is not None else None, then_body=tuple(_map_node(x, fn) for x in node.then_body), else_body=tuple(_map_node(x, fn) for x in node.else_body), cond_list=tuple(_map_node(x, fn) for x in node.cond_list), then_body_list=tuple(tuple(_map_node(x, fn) for x in body) for body in node.then_body_list))
    elif isinstance(node, Function): node = replace(node, body=tuple(_map_node(x, fn) for x in node.body))
    elif isinstance(node, Return): node = replace(node, value=_map_node(node.value, fn))
    return fn(node)


def coord_mutant(s: CoordState, mutant: str) -> CoordResult:
    result = coord_after(s)
    out = list(result.nodes)
    if mutant == "drop-load":
        if out and isinstance(out[0], Comment) and out[0].text == "Load coordinates":
            out.pop(0)
            while out and isinstance(out[0], VarInit) and out[0].var.name.startswith("i_"):
                out.pop(0)
    elif mutant == "max-not-min":
        out = [_map_node(x, lambda n: replace(n, name="std::max") if isinstance(n, Call) and n.name == "std::min" else n) for x in out]
    elif mutant == "assemble-last":
        for i in range(len(out) - 1):
            if isinstance(out[i], Comment) and out[i].text == "Assemble COMPRESSED level" and isinstance(out[i + 1], ForLoop):
                block = out[i:i + 2]
                del out[i:i + 2]
                out.extend(block)
                break
    elif mutant == "coord-end-off-by-one":
        changed = False
        new_out: list[Node] = []
        for node in out:
            def tweak(n: Node) -> Node:
                nonlocal changed
                if (not changed and isinstance(n, AssignNode) and n.var.name.endswith("1_end")
                        and isinstance(n.value, BinOp) and n.value.op == "+"
                        and isinstance(n.value.right, Literal) and n.value.right.value == "1"):
                    changed = True
                    return replace(n, value=replace(n.value, right=Literal("2")))
                return n
            new_out.append(_map_node(node, tweak))
        out = new_out
    elif mutant == "drop-dense":
        for i, node in enumerate(out):
            if isinstance(node, Comment) and node.text == "Resolve dense coordinates":
                out = out[:i]
                break
    return replace(result, nodes=tuple(out))


def p06_cases() -> list[CoordState]:
    out: list[CoordState] = []
    iterator_options = [
        (),
        (IteratorState("B", False, False),),
        (IteratorState("B", True, True),),
        (IteratorState("B", False, False), IteratorState("C", True, True)),
        (IteratorState("B", True, False), IteratorState("C", True, True)),
    ]
    ready_options = ((), (False,), (True,), (False, True), (True, False))
    for its, dense, result_has, current_dense, child_comp, ready in product(
        iterator_options, (False, True), (False, True), (False, True), (False, True), ready_options
    ):
        # Preserve the frozen 400 schedules and emitted fixtures, but readiness
        # now follows actual dependency-set inclusion, never an input oracle bit.
        offered = tuple(DenseIteratorState(_dense_stmt(i).var, _dense_stmt(i).value,
                                           ("i",) if bit else ("j",))
                        for i, bit in enumerate(ready))
        out.append(CoordState(tuple(its), dense, result_has, current_dense, child_comp,
                              offered, ("i",)))
    return out


@dataclass(frozen=True)
class CoordSequence:
    case_id: str
    initial_pending: tuple[PendingCoordinate, ...]
    calls: tuple[CoordState, ...]


def coord_sequence(sequence: CoordSequence, step=coord_after) -> tuple[CoordResult, ...]:
    """Thread the same lowerer-owned map across calls; never reset it."""
    pending = sequence.initial_pending
    results = []
    for call in sequence.calls:
        if call.pending:
            raise ValueError("sequence pre-map belongs to previous call, not call template")
        result = step(replace(call, pending=pending))
        results.append(result)
        pending = result.pending
    return tuple(results)


def p06_effect_cases() -> list[CoordSequence]:
    """Additional deterministic multi-call controls, outside the frozen 400."""
    def offer(name, value, deps=()):
        return DenseIteratorState(Var(name), value, tuple(deps))
    def entry(name, value, deps=()):
        return PendingCoordinate(VarInit(Var(name), value), tuple(deps))
    def call(offers=(), defined=()):
        return CoordState((), False, False, False, False, tuple(offers), tuple(defined))
    zero, one, two = Literal("0"), Literal("1"), Literal("2")
    affine = BinOp(BinOp(Var("pA0"), "*", Var("A1_size")), "+", Var("j"))
    return [
        CoordSequence("initial-mixed-order", (entry("a", one, ("i",)), entry("b", affine, ("j",)), entry("c", zero)),
                      (call(defined=("i",)), call(defined=("i", "j")), call())),
        CoordSequence("first-name-wins", (),
                      (call((offer("a", one, ("j",)), offer("a", two))),
                       call(defined=("j",)), call((offer("a", two),)))),
        CoordSequence("ready-old-suppresses-new", (entry("a", one),),
                      (call((offer("a", two, ("j",)),)), call((offer("a", two),)))),
        CoordSequence("unready-old-suppresses-ready", (entry("a", affine, ("j", "j")),),
                      (call((offer("a", two),)), call(), call(defined=("j", "j")))),
        CoordSequence("absent-and-zero-values", (),
                      (call((offer("skip", None), offer("zero", zero))), call())),
        CoordSequence("no-definition-cascade", (),
                      (call((offer("j", one, ("i",)), offer("b", affine, ("j",))), ("i",)),
                       call(defined=("i",)), call(defined=("i", "j")))),
        CoordSequence("retained-order-and-appends", (entry("b", two, ("j",)), entry("a", one, ("i",))),
                      (call((offer("c", zero), offer("d", affine, ("k",))), ("i",)),
                       call(defined=("j",)), call(defined=("k",)))),
        CoordSequence("retained-only-no-output", (entry("b", two, ("j",)), entry("a", one, ("i",))),
                      (call(), call((offer("c", affine, ("k",)),)), call())),
    ]


def verify_p06_effects() -> dict[str, Any]:
    from copy import deepcopy
    from .certificates import source_effect_certificate, check_source_effect_certificate
    sequences = p06_effect_cases()
    rows, errors = [], []
    for sequence in sequences:
        before = coord_sequence(sequence, coord_before)
        after = coord_sequence(sequence, coord_after)
        cert = source_effect_certificate(sequence, before)
        replay = check_source_effect_certificate(sequence, cert)
        if before != after or not replay["valid"]:
            errors.append(sequence.case_id)
        rows.append({"case_id": sequence.case_id, "calls": len(before),
                     "same": before == after, "replay": replay, "certificate": cert})
    controls = []
    for label, sequence, replacement in (
        ("drop-unready", sequences[7], "empty"),
        ("reverse-unready", sequences[7], "reverse"),
        ("retain-ready", sequences[0], "snapshot"),
    ):
        cert = source_effect_certificate(sequence, coord_sequence(sequence, coord_after))
        bad = deepcopy(cert)
        first = bad["calls"][0]
        first["post"] = ([] if replacement == "empty" else
                         list(reversed(first["post"])) if replacement == "reverse" else first["snapshot"])
        checked = check_source_effect_certificate(sequence, bad)
        same_output = first["emitted"] == cert["calls"][0]["emitted"]
        if checked["valid"] or not same_output:
            errors.append(label)
        controls.append({"control": label, "output_unchanged": same_output, "replay": checked})
    return {"sequence_count": len(sequences), "call_count": sum(len(s.calls) for s in sequences),
            "rows": rows, "state_only_controls": controls, "errors": errors,
            "interpretation": "Additional P06 multi-call state-effect diagnostics; not added to the frozen 526-state or 18-mutant denominators."}


def node_kind_signature(nodes: tuple[Node, ...]) -> tuple[str, ...]:
    """Top-level kind signature, deliberately weaker than full-node equality."""
    return tuple(type(x).__name__ for x in nodes)


# ---------------------------------------------------------------------------
# P08: mode-order initialization cleanup
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModeInit:
    explicit: tuple[int, ...] | None
    shape_rank: int | None       # 0 represents an empty/scalar shape tuple
    format_order: int | None    # 0 represents a present zero-order format object


def mode_before(x: ModeInit) -> tuple[int, ...] | None:
    mode: list[int] | tuple[int, ...] | None
    mode = x.explicit if x.explicit else (list(range(x.shape_rank)) if x.shape_rank else None)
    if not mode:
        if x.format_order is None:
            raise AttributeError("format is absent")
        mode = list(range(x.format_order))
    return tuple(mode) if mode is not None else None


def mode_after(x: ModeInit) -> tuple[int, ...] | None:
    if x.explicit:
        mode: Sequence[int] | None = x.explicit
    elif x.shape_rank:
        mode = list(range(x.shape_rank))
    elif x.format_order is not None:
        mode = list(range(x.format_order))
    else:
        mode = None
    return tuple(mode) if mode is not None else None


def p08_is_excluded_control(x: ModeInit) -> bool:
    """Partition the finite grid for reporting; this is not reachability evidence.

    Admission relies on the immutable fixed-production call-site inventory in
    ``data/public-adapter-evidence.json``.  These four combinations are executed
    solely to expose the parent-exception/child-``None`` boundary.
    """
    return not (bool(x.explicit) or bool(x.shape_rank) or x.format_order is not None)


P08_MUTANTS = (
    "ignore-explicit",
    "shape-off-by-one",
    "format-off-by-one",
    "reverse-default",
    "empty-is-explicit",
)


def mode_mutant(x: ModeInit, mutant: str) -> tuple[int, ...] | None:
    if mutant == "empty-is-explicit" and x.explicit is not None:
        return tuple(x.explicit)
    if mutant != "ignore-explicit" and x.explicit:
        return tuple(x.explicit)
    if x.shape_rank:
        n = x.shape_rank - 1 if mutant == "shape-off-by-one" else x.shape_rank
        v = tuple(range(max(n, 0)))
        return tuple(reversed(v)) if mutant == "reverse-default" else v
    if x.format_order is not None:
        n = x.format_order - 1 if mutant == "format-off-by-one" else x.format_order
        v = tuple(range(max(n, 0)))
        return tuple(reversed(v)) if mutant == "reverse-default" else v
    return None


def _all_p08_cases() -> list[ModeInit]:
    return [
        ModeInit(explicit, shape, fmt)
        for explicit, shape, fmt in product(
            (None, (), (0,), (1, 0)),
            (None, 0, 1, 2, 3),
            (None, 0, 1, 2, 3),
        )
    ]


def p08_cases() -> list[ModeInit]:
    return [x for x in _all_p08_cases() if not p08_is_excluded_control(x)]


def p08_excluded_cases() -> list[ModeInit]:
    return [x for x in _all_p08_cases() if p08_is_excluded_control(x)]


# ---------------------------------------------------------------------------
# Shared evaluation and bounded selection
# ---------------------------------------------------------------------------

ADAPTERS = {
    "P04": {
        "cases": p04_cases,
        "before": render_parent,
        "after": render_child,
        "mutants": P04_MUTANTS,
        "mutate": render_mutant,
    },
    "P06": {
        "cases": p06_cases,
        "before": coord_before,
        "after": coord_after,
        "mutants": P06_MUTANTS,
        "mutate": coord_mutant,
    },
    "P08": {
        "cases": p08_cases,
        "before": mode_before,
        "after": mode_after,
        "mutants": P08_MUTANTS,
        "mutate": mode_mutant,
    },
}


def _safe_call(fn: Callable[[Any], Any], case: Any) -> tuple[str, Any]:
    try:
        return ("value", fn(case))
    except Exception as exc:  # exception class is part of the adapter observable
        return ("exception", type(exc).__name__)


def verify_adapter(adapter_id: str) -> dict[str, Any]:
    adapter = ADAPTERS[adapter_id]
    cases = list(adapter["cases"]())
    mismatches = []
    for i, case in enumerate(cases):
        left = _safe_call(adapter["before"], case)
        right = _safe_call(adapter["after"], case)
        if left != right:
            mismatches.append({
                "index": i,
                "before": repr(left),
                "after": repr(right),
                "case": repr(case),
            })
    result: dict[str, Any] = {
        "adapter": adapter_id,
        "bounded_case_count": len(cases),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:10],
        "source_pin": SOURCE_PINS[adapter_id],
    }
    if adapter_id == "P04":
        result["coverage_map"] = p04_coverage_map()
    if adapter_id == "P06":
        from .certificates import source_effect_certificate, check_source_effect_certificate
        failures = []
        for i, case in enumerate(cases):
            sequence = CoordSequence(f"p06-single-{i}", case.pending, (replace(case, pending=()),))
            cert = source_effect_certificate(sequence, (coord_before(case),))
            checked = check_source_effect_certificate(sequence, cert)
            if not checked["valid"]:
                failures.append({"index": i, "reason": checked.get("reason")})
        result["observable"] = "complete ordered LLIR nodes and ordered post pending-coordinate map"
        result["effect_replay_count"] = len(cases)
        result["effect_replay_failures"] = failures
    if adapter_id == "P08":
        excluded = []
        for case in p08_excluded_cases():
            excluded.append({
                "case": repr(case),
                "before": repr(_safe_call(mode_before, case)),
                "after": repr(_safe_call(mode_after, case)),
                "same": _safe_call(mode_before, case) == _safe_call(mode_after, case),
            })
        result["excluded_domain_count"] = len(excluded)
        result["excluded_domain_controls"] = excluded
    return result


def verify_p01_candidate() -> dict[str, Any]:
    successful = p01_exhaustive_specs()
    success_mismatches = []
    for i, case in enumerate(successful):
        left = _safe_call(build_cin_before_source, case)
        right = _safe_call(build_cin_after_source, case)
        if left != right:
            success_mismatches.append({"index": i, "case": repr(case), "before": repr(left), "after": repr(right)})
    boundary = []
    for case in p01_scalar_boundary_cases():
        left = _safe_call(build_cin_before_source, case)
        right = _safe_call(build_cin_after_source, case)
        boundary.append({"case": repr(case), "before": repr(left), "after": repr(right), "same": left == right})
    return {
        "adapter": "P01",
        "decision": "abstained",
        "successful_domain_case_count": len(successful),
        "successful_domain_mismatch_count": len(success_mismatches),
        "successful_domain_mismatches": success_mismatches[:10],
        "scalar_boundary_case_count": len(boundary),
        "scalar_boundary_controls": boundary,
        "admission_failure": (
            "The 1--4 operand range is a finite validation boundary, not a source restriction. "
            "Per-operand and result non-scalarity is not enforced by the source; mixed scalar/indexed "
            "inputs reach the changed hunk and can change the exception class."
        ),
        "source_pin": SOURCE_PINS["P01"],
    }


def _developer_indices(adapter_id: str, n: int) -> list[int]:
    cases = list(ADAPTERS[adapter_id]["cases"]())
    if adapter_id == "P04":
        preferred = [0, 10, 13, 17, 18, 20, 21, 22, 23, 28, len(cases) - 1]
    elif adapter_id == "P06":
        preferred = [0, len(cases) // 4, len(cases) // 2, 3 * len(cases) // 4, len(cases) - 1]
    else:
        preferred = [0, len(cases) // 3, 2 * len(cases) // 3, len(cases) - 1]
    return [preferred[i % len(preferred)] % len(cases) for i in range(n)]


def _evenly_spaced_enumeration_indices(adapter_id: str, n: int) -> tuple[list[int], int]:
    """Enumeration-index grid; not semantic feature stratification."""
    cases = list(ADAPTERS[adapter_id]["cases"]())
    if n >= len(cases):
        unique = list(range(len(cases)))
    elif n == 1:
        unique = [0]
    else:
        unique = sorted({round(i * (len(cases) - 1) / (n - 1)) for i in range(n)})
    indices = (unique * ((n + len(unique) - 1) // len(unique)))[:n]
    return indices, len(unique)


def _random_indices(adapter_id: str, n: int, rng: random.Random) -> list[int]:
    cases = list(ADAPTERS[adapter_id]["cases"]())
    return [rng.randrange(len(cases)) for _ in range(n)]


def mutation_study(candidate_slot_cap: int = 64, seed: int = 20260915) -> dict[str, Any]:
    """Run admitted-adapter mutants with early stopping.

    ``candidate_slot_cap`` is the maximum number of selected input slots *per
    mutant*.  Detection stops at the first distinguishing slot, so actual
    executions are recorded and usually smaller than the cap.
    """
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    policy_meta: dict[str, Any] = {}
    for adapter_id, adapter in ADAPTERS.items():
        cases = list(adapter["cases"]())
        even_indices, even_unique = _evenly_spaced_enumeration_indices(adapter_id, candidate_slot_cap)
        methods = {
            "repeated-developer-indices": _developer_indices(adapter_id, candidate_slot_cap),
            "seeded-random-with-replacement": _random_indices(adapter_id, candidate_slot_cap, rng),
            "evenly-spaced-enumeration-indices": even_indices,
        }
        policy_meta[adapter_id] = {
            "domain_size": len(cases),
            "candidate_slot_cap_per_mutant": candidate_slot_cap,
            "developer_unique_indices_in_full_schedule": len(set(methods["repeated-developer-indices"])),
            "random_unique_indices_in_full_schedule": len(set(methods["seeded-random-with-replacement"])),
            "even_grid_unique_indices_before_repetition": even_unique,
            "even_grid_repeats_because_domain_smaller_than_cap": len(cases) < candidate_slot_cap,
            "enumeration_order_dependency": True,
        }
        for mutant in adapter["mutants"]:
            row: dict[str, Any] = {"adapter": adapter_id, "mutant": mutant}
            for method, indices in methods.items():
                detected = False
                first: int | None = None
                actual = 0
                seen: set[int] = set()
                for slot, index in enumerate(indices, 1):
                    actual += 1
                    seen.add(index)
                    case = cases[index]
                    expected = _safe_call(adapter["before"], case)
                    got = _safe_call(lambda value: adapter["mutate"](value, mutant), case)
                    if expected != got:
                        detected = True
                        first = slot
                        break
                row[method] = {
                    "detected": detected,
                    "first_detection_slot": first,
                    "candidate_slot_cap": candidate_slot_cap,
                    "actual_executions": actual,
                    "distinct_indices_executed": len(seen),
                }
            rows.append(row)
    summary: dict[str, Any] = {}
    methods = (
        "repeated-developer-indices",
        "seeded-random-with-replacement",
        "evenly-spaced-enumeration-indices",
    )
    for method in methods:
        detected = sum(1 for row in rows if row[method]["detected"])
        summary[method] = {
            "detected": detected,
            "total": len(rows),
            "rate": detected / len(rows),
            "actual_executions": sum(row[method]["actual_executions"] for row in rows),
            "candidate_slots_if_no_early_stop": len(rows) * candidate_slot_cap,
        }
    return {
        "seed": seed,
        "candidate_slot_cap_per_mutant": candidate_slot_cap,
        "mutant_count": len(rows),
        "rows": rows,
        "summary": summary,
        "policy_metadata": policy_meta,
        "interpretation": (
            "The third policy is an evenly spaced grid over enumeration indices, not semantic-feature "
            "stratification. Small domains are exhausted and then repeated to fill the candidate-slot cap. "
            "All policies stop at first detection; actual executions are recorded."
        ),
    }
