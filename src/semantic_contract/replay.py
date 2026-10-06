"""Independent exact-rational interpreter and counterexample replay.

This module deliberately imports neither the symbolic IR encoder nor the
solver.  It independently validates the delivered JSON fragment, parses the
restricted affine/Boolean grammar, reconstructs active input cells, and
executes both programs directly.  Duplication is intentional: a malformed
case must not become replayable merely because the symbolic front end accepted
it.
"""
from __future__ import annotations

import ast
from fractions import Fraction
from itertools import product
import re
from typing import Any, Iterable


class ReplayError(ValueError):
    """A case, witness, or certificate is outside the replay contract."""


def replay_source_effects(certificate):
    """Independent ordered-list reference; no solver or adapter calls."""
    from .dense_effects import check_effect_certificate
    return check_effect_certificate(certificate)


_CASE_FIELDS = {
    "id", "parameters", "inputs", "precondition", "before", "after",
    "family", "expected", "provenance",
}
_PROGRAM_FIELDS = {"shape", "terms", "storage"}
_TERM_FIELDS = {"tensor", "index", "coefficient", "guard"}
_STORAGE = {"dense", "union", "compact", "empty"}
_ATOMS = {"shape", "value", "zero-support", "stored-support", "term-order"}
_IDENTIFIER = re.compile(r"[A-Za-z0-9-]{1,80}\Z")
_PARAMETER = re.compile(r"n[0-3]\Z")
_TENSOR = re.compile(r"[A-D]\Z")


def _fraction(value: Any, label: str, *, max_chars: int = 4096) -> Fraction:
    """Parse an exact rational without silently accepting binary floats."""
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if not isinstance(value, str) or len(value) > max_chars:
        raise ReplayError(f"{label} must be an exact rational string or integer")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ReplayError(f"invalid {label}") from exc


def _integral(value: Any, label: str) -> int:
    q = _fraction(value, label)
    if q.denominator != 1:
        raise ReplayError(f"nonintegral {label}")
    return q.numerator



def exact_fraction(value: Any, label: str = "rational", *, max_chars: int = 4096) -> Fraction:
    """Public exact-rational parser shared only by direct replay utilities."""
    return _fraction(value, label, max_chars=max_chars)


def integral_value(value: Any, label: str = "integer") -> int:
    """Public integral parser that rejects booleans, floats, and fractions."""
    return _integral(value, label)

def _parse_expression(
    text: str,
    names: set[str],
    *,
    expected_bool: bool | None,
) -> tuple[ast.AST, str]:
    """Independently validate the declared affine/Boolean grammar."""
    if not isinstance(text, str) or len(text) > 512:
        raise ReplayError("expression must be a string of at most 512 characters")
    try:
        root = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError) as exc:
        raise ReplayError("malformed expression") from exc
    if sum(1 for _ in ast.walk(root)) > 128:
        raise ReplayError("expression-node budget")

    def check(node: ast.AST) -> tuple[str, bool]:
        # The second component says that the integer expression is syntactically
        # constant; multiplication is affine only when at least one side is so.
        if isinstance(node, ast.Constant):
            if type(node.value) is bool:
                return "bool", False
            if type(node.value) is int and abs(node.value) < 2**31:
                return "int", True
            raise ReplayError("only 31-bit integer constants and Boolean literals")
        if isinstance(node, ast.Name):
            if node.id not in names:
                raise ReplayError("undeclared expression name")
            return "int", False
        if isinstance(node, ast.UnaryOp):
            typ, constant = check(node.operand)
            if isinstance(node.op, ast.Not) and typ == "bool":
                return "bool", False
            if isinstance(node.op, (ast.USub, ast.UAdd)) and typ == "int":
                return "int", constant
            raise ReplayError("invalid unary expression")
        if isinstance(node, ast.BinOp):
            left, left_constant = check(node.left)
            right, right_constant = check(node.right)
            if left == right == "int":
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    return "int", left_constant and right_constant
                if isinstance(node.op, ast.Mult) and (left_constant or right_constant):
                    return "int", left_constant and right_constant
            raise ReplayError("outside affine integer grammar")
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            if all(check(value)[0] == "bool" for value in node.values):
                return "bool", False
            raise ReplayError("Boolean operator applied to an integer")
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if not all(
                isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE))
                for op in node.ops
            ):
                raise ReplayError("comparison not supported")
            if not all(check(value)[0] == "int" for value in operands):
                raise ReplayError("comparison operands must be integers")
            return "bool", False
        raise ReplayError("expression outside affine/Boolean replay grammar")

    sort = check(root)[0]
    if expected_bool is not None and sort != ("bool" if expected_bool else "int"):
        raise ReplayError("expression sort mismatch")
    return root, sort


def _evaluate_expression(node: ast.AST, env: dict[str, int]) -> int | bool:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env or type(env[node.id]) is not int:
            raise ReplayError("missing or noninteger expression binding")
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_expression(node.operand, env)
        if isinstance(node.op, ast.Not):
            if type(value) is not bool:
                raise ReplayError("not applied to an integer")
            return not value
        if type(value) is not int:
            raise ReplayError("integer unary operator applied to a Boolean")
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left = _evaluate_expression(node.left, env)
        right = _evaluate_expression(node.right, env)
        if type(left) is not int or type(right) is not int:
            raise ReplayError("arithmetic applied to a Boolean")
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        raise ReplayError("integer operator not supported")
    if isinstance(node, ast.BoolOp):
        values = [_evaluate_expression(value, env) for value in node.values]
        if any(type(value) is not bool for value in values):
            raise ReplayError("Boolean operator applied to an integer")
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare):
        left = _evaluate_expression(node.left, env)
        if type(left) is not int:
            raise ReplayError("comparison operand must be an integer")
        for operator, term in zip(node.ops, node.comparators):
            right = _evaluate_expression(term, env)
            if type(right) is not int:
                raise ReplayError("comparison operand must be an integer")
            if isinstance(operator, ast.Eq):
                okay = left == right
            elif isinstance(operator, ast.NotEq):
                okay = left != right
            elif isinstance(operator, ast.Lt):
                okay = left < right
            elif isinstance(operator, ast.LtE):
                okay = left <= right
            elif isinstance(operator, ast.Gt):
                okay = left > right
            elif isinstance(operator, ast.GtE):
                okay = left >= right
            else:  # already excluded by the validator
                raise ReplayError("comparison not supported")
            if not okay:
                return False
            left = right
        return True
    raise ReplayError("unvalidated replay expression")


def integer_expression(
    text: str,
    env: dict[str, int],
    expected_bool: bool | None = None,
    *,
    allowed_names: Iterable[str] | None = None,
) -> int | bool:
    """Validate and evaluate one expression in the independent grammar.

    ``expected_bool`` should be supplied by all semantic callers.  ``None`` is
    retained only for the small public helper surface and still validates the
    grammar and infers the sort.
    """
    if not isinstance(env, dict) or any(type(value) is not int for value in env.values()):
        raise ReplayError("expression environment must contain integers")
    names = set(env) if allowed_names is None else set(allowed_names)
    if not names.issubset(env):
        raise ReplayError("allowed expression name lacks a binding")
    root, sort = _parse_expression(text, names, expected_bool=expected_bool)
    result = _evaluate_expression(root, env)
    if sort == "bool" and type(result) is not bool:
        raise ReplayError("Boolean expression produced a non-Boolean")
    if sort == "int" and type(result) is not int:
        raise ReplayError("integer expression produced a noninteger")
    return result


def _validate_shape(shape: Any, names: set[str], label: str) -> None:
    if not isinstance(shape, list) or len(shape) > 4:
        raise ReplayError(f"{label} rank exceeds four")
    for dimension in shape:
        _parse_expression(dimension, names, expected_bool=False)


def _validate_program(program: Any, parameters: set[str], inputs: dict[str, Any]) -> None:
    if not isinstance(program, dict) or set(program) != _PROGRAM_FIELDS:
        raise ReplayError("program fields must be shape, terms, storage")
    _validate_shape(program["shape"], parameters, "output")
    if program["storage"] not in _STORAGE:
        raise ReplayError("unsupported storage policy")
    terms = program["terms"]
    if not isinstance(terms, list) or len(terms) > 32:
        raise ReplayError("term budget exceeds 32")
    local_names = parameters | {f"i{k}" for k in range(len(program["shape"]))}
    for term in terms:
        if not isinstance(term, dict) or set(term) != _TERM_FIELDS:
            raise ReplayError("invalid term fields")
        tensor = term["tensor"]
        if tensor not in inputs:
            raise ReplayError("undeclared tensor")
        index = term["index"]
        if not isinstance(index, list) or len(index) != len(inputs[tensor]):
            raise ReplayError("read rank mismatch")
        for coordinate in index:
            _parse_expression(coordinate, local_names, expected_bool=False)
        _parse_expression(term["guard"], local_names, expected_bool=True)
        if not isinstance(term["coefficient"], str) or len(term["coefficient"]) > 32:
            raise ReplayError("coefficient must be a short rational string")
        coefficient = _fraction(term["coefficient"], "coefficient", max_chars=32)
        if max(abs(coefficient.numerator), coefficient.denominator) >= 2**16:
            raise ReplayError("coefficient bit budget")
    if 2 + 2 * len(terms) > 96:
        raise ReplayError("IR-node budget")


def validate_replay_case(raw: Any) -> None:
    """Independently validate the complete finite-read case schema."""
    if not isinstance(raw, dict):
        raise ReplayError("case must be an object")
    if set(raw) - _CASE_FIELDS:
        raise ReplayError("unknown case field")
    identifier = raw.get("id", "")
    if not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier):
        raise ReplayError("invalid case identifier")
    parameters = raw.get("parameters")
    if (
        not isinstance(parameters, list)
        or not 1 <= len(parameters) <= 4
        or len(set(parameters)) != len(parameters)
        or any(not isinstance(name, str) or not _PARAMETER.fullmatch(name) for name in parameters)
    ):
        raise ReplayError("one to four unique parameters n0..n3 required")
    parameter_names = set(parameters)
    inputs = raw.get("inputs")
    if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 4:
        raise ReplayError("one to four inputs required")
    for tensor, shape in inputs.items():
        if not isinstance(tensor, str) or not _TENSOR.fullmatch(tensor):
            raise ReplayError("input names must be A..D")
        _validate_shape(shape, parameter_names, "input")
    _parse_expression(raw.get("precondition"), parameter_names, expected_bool=True)
    _validate_program(raw.get("before"), parameter_names, inputs)
    _validate_program(raw.get("after"), parameter_names, inputs)


def shape_of(shape: list[str], env: dict[str, int]) -> tuple[int, ...]:
    result = tuple(
        integer_expression(dimension, env, False, allowed_names=set(env))
        for dimension in shape
    )
    if any(type(dimension) is not int or dimension < 0 for dimension in result):
        raise ReplayError("invalid dimension")
    return result


def in_bounds(index: tuple[int, ...], shape: tuple[int, ...]) -> bool:
    return len(index) == len(shape) and all(
        type(coordinate) is int and 0 <= coordinate < extent
        for coordinate, extent in zip(index, shape)
    )


def points(shape: tuple[int, ...], cap: int = 4096):
    size = 1
    for extent in shape:
        size *= extent
    if size > cap:
        raise ReplayError("concrete point cap")
    return product(*(range(extent) for extent in shape))


def active_reads(program: dict[str, Any], env: dict[str, int]):
    for number, term in enumerate(program["terms"]):
        if integer_expression(term["guard"], env, True, allowed_names=set(env)):
            key = (
                term["tensor"],
                tuple(
                    integer_expression(expr, env, False, allowed_names=set(env))
                    for expr in term["index"]
                ),
            )
            yield number, key, _fraction(term["coefficient"], "coefficient", max_chars=32)


def evaluate(program: dict[str, Any], env: dict[str, int], cells: dict):
    terms = list(active_reads(program, env))
    value = sum(
        (
            coefficient * cells.get(key, (Fraction(0), False))[0]
            for _, key, coefficient in terms
        ),
        Fraction(0),
    )
    policy = program["storage"]
    if policy == "dense":
        stored = True
    elif policy == "empty":
        stored = False
    elif policy == "compact":
        stored = value != 0
    elif policy == "union":
        stored = any(cells.get(key, (Fraction(0), False))[1] for _, key, _ in terms)
    else:
        raise ReplayError("unknown storage policy")
    if not stored and value != 0:
        raise ReplayError("inconsistent output storage")
    order = [(key, coefficient) for _, key, coefficient in terms]
    return value, stored, order


def replay(raw: dict, atom: str, witness: dict[str, Any]) -> dict:
    try:
        validate_replay_case(raw)
        if atom not in _ATOMS:
            raise ReplayError("unknown observation")
        if not isinstance(witness, dict):
            raise ReplayError("witness must be an object")
        env: dict[str, int] = {}
        for name in raw["parameters"]:
            env[name] = _integral(witness[name], "dimension witness")
        if not integer_expression(
            raw["precondition"], env, True, allowed_names=set(raw["parameters"])
        ):
            raise ReplayError("precondition false")
        inputs = {name: shape_of(shape, env) for name, shape in raw["inputs"].items()}
        before, after = raw["before"], raw["after"]
        before_shape = shape_of(before["shape"], env)
        after_shape = shape_of(after["shape"], env)
        if before_shape != after_shape:
            return {
                "valid": True,
                "mismatch": "shape",
                "requested_observation": atom,
                "parameters": env,
                "before_shape": before_shape,
                "after_shape": after_shape,
                "cells": [],
            }
        if atom == "shape":
            raise ReplayError("shapes equal")
        for axis in range(len(before_shape)):
            env[f"i{axis}"] = _integral(witness[f"i{axis}"], "output index")
        output_index = tuple(env[f"i{axis}"] for axis in range(len(before_shape)))
        if not in_bounds(output_index, before_shape):
            raise ReplayError("output witness outside shape")
        cells: dict[tuple[str, tuple[int, ...]], tuple[Fraction, bool]] = {}
        offset = 0
        for program in (before, after):
            for number, key, _ in active_reads(program, env):
                if not in_bounds(key[1], inputs[key[0]]):
                    raise ReplayError("active read outside shape")
                value = _fraction(witness[f"x{offset + number}"], "input value")
                occupied = witness[f"b{offset + number}"]
                if type(occupied) is not bool:
                    raise ReplayError("nonboolean occupancy")
                if not occupied and value != 0:
                    raise ReplayError("unstored input is nonzero")
                if key in cells and cells[key] != (value, occupied):
                    raise ReplayError("same-cell congruence violated")
                cells[key] = (value, occupied)
            offset += len(program["terms"])
        before_value, before_stored, before_order = evaluate(before, env, cells)
        after_value, after_stored, after_order = evaluate(after, env, cells)
        mismatch = {
            "value": before_value != after_value,
            "zero-support": (before_value == 0) != (after_value == 0),
            "stored-support": before_stored != after_stored,
            "term-order": before_order != after_order,
        }.get(atom)
        if not mismatch:
            raise ReplayError("requested observation agrees")
        return {
            "valid": True,
            "mismatch": atom,
            "parameters": {name: env[name] for name in raw["parameters"]},
            "output_index": output_index,
            "before_value": str(before_value),
            "after_value": str(after_value),
            "before_stored": before_stored,
            "after_stored": after_stored,
            "cells": [
                {
                    "tensor": key[0],
                    "index": key[1],
                    "value": str(value[0]),
                    "stored": value[1],
                }
                for key, value in sorted(cells.items())
            ],
        }
    except (ReplayError, KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
        return {"valid": False, "reason": str(exc)}
