"""Solver-free replay of P06 ordered-map transition certificates.

This reference uses ordered lists rather than either adapter's dictionary.
It interprets source map operations, not LLIR numerical execution. LLIR trees
are validated structural payloads, never evaluated as Python or native code.
No changed adapter implementation is imported by the replay path.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any


class EffectError(ValueError):
    pass


def node_record(value: Any) -> Any:
    """Encode trusted adapter nodes without dropping fields or tuple order."""
    if is_dataclass(value):
        return {"kind": type(value).__name__,
                "fields": {f.name: node_record(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, tuple):
        return [node_record(x) for x in value]
    if value is None or type(value) in (str, bool):
        return value
    raise EffectError("unsupported node payload")


def pending_record(entries) -> list[dict]:
    return [{"statement": node_record(e.statement), "dependencies": list(e.dependencies)} for e in entries]


def transition_record(effect) -> dict:
    return {
        "pre": pending_record(effect.pre),
        "offered": [{"coordinate": node_record(e.coordinate), "value": node_record(e.value),
                     "dependencies": list(e.dependencies)} for e in effect.offered],
        "defined": list(effect.defined), "inserted": list(effect.inserted),
        "snapshot": pending_record(effect.snapshot), "retained": list(effect.retained),
        "post": pending_record(effect.post), "emitted": node_record(effect.emitted),
    }


def _names(xs):
    if not isinstance(xs, list) or len(xs) > 128 or any(type(x) is not str or not x or len(x) > 128 for x in xs):
        raise EffectError("index-variable names")
    return xs


_EXPR_FIELDS = {
    "Var": {"name", "typ", "is_ptr"}, "Literal": {"value"},
    "BinOp": {"left", "op", "right"}, "UnaryOp": {"op", "operand"},
    "Cast": {"typ", "expr"}, "Sizeof": {"typ"}, "Call": {"name", "args"},
    "Array": {"values", "typ"}, "ArrayAccess": {"array", "index"},
}


def _node(node, depth=0, budget=None):
    if budget is None:
        budget = [512]
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise EffectError("node budget")
    if not isinstance(node, dict) or set(node) != {"kind", "fields"}:
        raise EffectError("node schema")
    kind, data = node["kind"], node["fields"]
    if type(kind) is not str or kind not in _EXPR_FIELDS or not isinstance(data, dict) or set(data) != _EXPR_FIELDS[kind]:
        raise EffectError("expression fields")
    for name, value in data.items():
        if name == "is_ptr":
            if type(value) is not bool:
                raise EffectError("pointer flag")
        elif name in ("left", "right", "operand", "expr", "array", "index"):
            _node(value, depth + 1, budget)
        elif name in ("args", "values"):
            if not isinstance(value, list) or len(value) > 128:
                raise EffectError("expression list")
            for child in value:
                _node(child, depth + 1, budget)
        elif type(value) is not str or len(value) > 512:
            raise EffectError("expression string")
    return node


def _declaration(stmt):
    if not isinstance(stmt, dict) or set(stmt) != {"kind", "fields"} or stmt["kind"] != "VarInit":
        raise EffectError("declaration schema")
    data = stmt["fields"]
    if not isinstance(data, dict) or set(data) != {"var", "value", "op", "cast"}:
        raise EffectError("declaration fields")
    _node(data["var"])
    if data["var"]["kind"] != "Var":
        raise EffectError("destination must be a variable")
    _node(data["value"])
    if type(data["op"]) is not str or len(data["op"]) > 32 or type(data["cast"]) is not bool:
        raise EffectError("declaration flags")
    return stmt


def _pending(entries):
    if not isinstance(entries, list) or len(entries) > 128:
        raise EffectError("pending-map budget")
    seen = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"statement", "dependencies"}:
            raise EffectError("pending entry fields")
        _declaration(entry["statement"])
        _names(entry["dependencies"])
        if entry["statement"] in seen:
            raise EffectError("duplicate map key")
        seen.append(entry["statement"])
    return entries


def reference_transition(pre, offered, defined):
    """Independent source semantics: collect by name, then stable partition.

    Defined names are a fixed snapshot; emitting a declaration does not define
    an IndexVar. Empty dependencies are ready. The insertion sweep precedes all
    removals, so a ready old entry still suppresses a same-name new declaration.
    """
    _pending(pre)
    _names(defined)
    if not isinstance(offered, list) or len(offered) > 128:
        raise EffectError("iterator budget")
    entries = list(pre)
    insert_flags = []
    for offer in offered:
        if not isinstance(offer, dict) or set(offer) != {"coordinate", "value", "dependencies"}:
            raise EffectError("iterator fields")
        _node(offer["coordinate"])
        if offer["coordinate"]["kind"] != "Var":
            raise EffectError("iterator coordinate")
        _names(offer["dependencies"])
        if offer["value"] is None:
            insert_flags.append(None)
            continue
        _node(offer["value"])
        name = offer["coordinate"]["fields"]["name"]
        if any(e["statement"]["fields"]["var"]["fields"]["name"] == name for e in entries):
            insert_flags.append(False)
            continue
        statement = {"kind": "VarInit", "fields": {
            "var": offer["coordinate"], "value": offer["value"], "op": "=", "cast": False}}
        entries.append({"statement": statement, "dependencies": offer["dependencies"]})
        insert_flags.append(True)
    _pending(entries)
    # Membership against name-equal IndexVars; repetitions in dep lists survive
    # as payload but do not change readiness (upstream uses set inclusion).
    retain = [any(dep not in defined for dep in e["dependencies"]) for e in entries]
    ready = [e["statement"] for e, keep in zip(entries, retain) if not keep]
    post = [e for e, keep in zip(entries, retain) if keep]
    emitted = ([{"kind": "Comment", "fields": {"text": "Resolve dense coordinates"}}] + ready) if ready else []
    return {"pre": pre, "offered": offered, "defined": defined,
            "inserted": insert_flags, "snapshot": entries, "retained": retain,
            "post": post, "emitted": emitted}


def check_effect_certificate(cert):
    """Check every pre/post link and effect, not just the last output tree."""
    try:
        if not isinstance(cert, dict) or set(cert) != {"kind", "case_id", "initial_pending", "calls"}:
            raise EffectError("certificate fields")
        if cert["kind"] != "p06-ordered-map" or type(cert["case_id"]) is not str or not cert["case_id"]:
            raise EffectError("certificate identity")
        current = _pending(cert["initial_pending"])
        calls = cert["calls"]
        if not isinstance(calls, list) or not 1 <= len(calls) <= 64:
            raise EffectError("call budget")
        for index, call in enumerate(calls):
            if not isinstance(call, dict) or set(call) != {"pre", "offered", "defined", "inserted", "snapshot", "retained", "post", "emitted"}:
                raise EffectError("transition fields")
            if call["pre"] != current:
                raise EffectError(f"call {index}: persistent pre-map link")
            expected = reference_transition(current, call["offered"], call["defined"])
            # Strict Boolean flags: Python otherwise equates False with 0.
            if not isinstance(call["inserted"], list) or any(x is not None and type(x) is not bool for x in call["inserted"]):
                raise EffectError("insert flags")
            if not isinstance(call["retained"], list) or any(type(x) is not bool for x in call["retained"]):
                raise EffectError("retain flags")
            _pending(call["snapshot"])
            _pending(call["post"])
            emitted = call["emitted"]
            if not isinstance(emitted, list) or len(emitted) > 129:
                raise EffectError("emitted-node budget")
            if emitted:
                if emitted[0] != {"kind": "Comment", "fields": {"text": "Resolve dense coordinates"}}:
                    raise EffectError("dense comment")
                for declaration in emitted[1:]:
                    _declaration(declaration)
            if call != expected:
                raise EffectError(f"call {index}: source effect mismatch")
            current = call["post"]
        return {"valid": True, "case_id": cert["case_id"], "call_count": len(calls),
                "remaining_entries": len(current)}
    except (EffectError, KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "reason": str(exc)}
