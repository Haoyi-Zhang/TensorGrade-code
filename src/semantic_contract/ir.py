"""Typed, finite-read, rational tensor IR.  Expressions are parsed, never eval'ed."""
from __future__ import annotations
import ast
from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any

class Unsupported(ValueError): pass

@dataclass(frozen=True)
class Expr:
    text: str
    tree: ast.AST
    boolean: bool
    def smt(self) -> str:
        return _smt(self.tree)
    def concrete(self, env: dict[str,int]) -> int | bool:
        return _concrete(self.tree,env)

def expression(text: str, names: set[str], boolean: bool = False) -> Expr:
    if not isinstance(text,str) or len(text)>512:
        raise Unsupported('expression must be a string of at most 512 characters')
    try: tree=ast.parse(text,mode='eval').body
    except (SyntaxError,ValueError) as e: raise Unsupported('malformed expression') from e
    if sum(1 for _ in ast.walk(tree))>128: raise Unsupported('expression-node budget')
    def check(n):
        if isinstance(n,ast.Constant):
            if type(n.value) is bool: return ('bool',False)
            if type(n.value) is int and abs(n.value)<2**31: return ('int',True)
            raise Unsupported('only 31-bit integer constants and Boolean literals')
        if isinstance(n,ast.Name) and n.id in names: return ('int',False)
        if isinstance(n,ast.UnaryOp):
            typ,const=check(n.operand)
            if isinstance(n.op,ast.Not) and typ=='bool': return ('bool',False)
            if isinstance(n.op,(ast.USub,ast.UAdd)) and typ=='int': return ('int',const)
        if isinstance(n,ast.BinOp):
            a,ac=check(n.left);b,bc=check(n.right)
            if a==b=='int':
                if isinstance(n.op,(ast.Add,ast.Sub)): return ('int',ac and bc)
                if isinstance(n.op,ast.Mult) and (ac or bc): return ('int',ac and bc)
        if isinstance(n,ast.BoolOp) and isinstance(n.op,(ast.And,ast.Or)):
            if all(check(v)[0]=='bool' for v in n.values): return ('bool',False)
        if isinstance(n,ast.Compare):
            if (all(isinstance(o,(ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)) for o in n.ops)
                and all(check(v)[0]=='int' for v in [n.left,*n.comparators])):
                return ('bool',False)
        raise Unsupported('outside affine/Boolean shape grammar')
    got=check(tree)[0]
    if got != ('bool' if boolean else 'int'): raise Unsupported('expression sort mismatch')
    return Expr(text,tree,boolean)

def _smt(n):
    if isinstance(n,ast.Constant):
        if type(n.value) is bool:return 'true' if n.value else 'false'
        return str(n.value) if n.value>=0 else f'(- {-n.value})'
    if isinstance(n,ast.Name):return n.id
    if isinstance(n,ast.UnaryOp):
        if isinstance(n.op,ast.UAdd):return _smt(n.operand)
        return f"({'not' if isinstance(n.op,ast.Not) else '-'} {_smt(n.operand)})"
    if isinstance(n,ast.BinOp):
        op={ast.Add:'+',ast.Sub:'-',ast.Mult:'*'}[type(n.op)]
        return f'({op} {_smt(n.left)} {_smt(n.right)})'
    if isinstance(n,ast.BoolOp):return '('+('and' if isinstance(n.op,ast.And) else 'or')+' '+' '.join(_smt(x) for x in n.values)+')'
    if isinstance(n,ast.Compare):
        parts=[];left=n.left
        for o,right in zip(n.ops,n.comparators):
            op={ast.Eq:'=',ast.NotEq:'distinct',ast.Lt:'<',ast.LtE:'<=',ast.Gt:'>',ast.GtE:'>='}[type(o)]
            parts.append(f'({op} {_smt(left)} {_smt(right)})');left=right
        return both(parts)
    raise AssertionError('unvalidated AST')

def _concrete(n,env):
    if isinstance(n,ast.Constant):return n.value
    if isinstance(n,ast.Name):return env[n.id]
    if isinstance(n,ast.UnaryOp):
        v=_concrete(n.operand,env)
        if isinstance(n.op,ast.Not):return not v
        return -v if isinstance(n.op,ast.USub) else v
    if isinstance(n,ast.BinOp):
        a,b=_concrete(n.left,env),_concrete(n.right,env)
        return a+b if isinstance(n.op,ast.Add) else a-b if isinstance(n.op,ast.Sub) else a*b
    if isinstance(n,ast.BoolOp):
        vs=(_concrete(x,env) for x in n.values)
        return all(vs) if isinstance(n.op,ast.And) else any(vs)
    if isinstance(n,ast.Compare):
        left=_concrete(n.left,env)
        for o,r in zip(n.ops,n.comparators):
            right=_concrete(r,env)
            ok = (left==right if isinstance(o,ast.Eq) else left!=right if isinstance(o,ast.NotEq)
                  else left<right if isinstance(o,ast.Lt) else left<=right if isinstance(o,ast.LtE)
                  else left>right if isinstance(o,ast.Gt) else left>=right)
            if not ok:return False
            left=right
        return True
    raise AssertionError('unvalidated AST')

def both(xs):
    xs=list(xs)
    return 'true' if not xs else xs[0] if len(xs)==1 else '(and '+' '.join(xs)+')'
def either(xs):
    xs=list(xs)
    return 'false' if not xs else xs[0] if len(xs)==1 else '(or '+' '.join(xs)+')'
def total(xs):
    xs=list(xs)
    return '0' if not xs else xs[0] if len(xs)==1 else '(+ '+' '.join(xs)+')'
def rational(q: Fraction) -> str:
    a=str(q.numerator) if q.numerator>=0 else f'(- {-q.numerator})'
    return a if q.denominator==1 else f'(/ {a} {q.denominator})'

@dataclass(frozen=True)
class Term:
    tensor: str
    index: tuple[Expr,...]
    coefficient: Fraction
    guard: Expr
@dataclass(frozen=True)
class Program:
    shape: tuple[Expr,...]
    terms: tuple[Term,...]
    storage: str
@dataclass(frozen=True)
class Case:
    identifier: str
    parameters: tuple[str,...]
    inputs: dict[str,tuple[Expr,...]]
    precondition: Expr
    before: Program
    after: Program
    family: str

def load_case(raw: dict[str,Any]) -> Case:
    if not isinstance(raw,dict):raise Unsupported('case must be an object')
    allowed={'id','parameters','inputs','precondition','before','after','family','expected','provenance'}
    if set(raw)-allowed:raise Unsupported('unknown case field')
    identifier=raw.get('id','')
    if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,80}',identifier):raise Unsupported('invalid case identifier')
    params=raw.get('parameters')
    if not isinstance(params,list) or not 1<=len(params)<=4 or len(set(params))!=len(params):raise Unsupported('one to four unique shape parameters required')
    if any(not isinstance(x,str) or not re.fullmatch(r'n[0-3]',x) for x in params):raise Unsupported('parameters must be n0..n3')
    pnames=set(params);names=pnames|{f'i{k}' for k in range(4)}
    inputs=raw.get('inputs')
    if not isinstance(inputs,dict) or not 1<=len(inputs)<=4:raise Unsupported('one to four inputs required')
    ins={}
    for tensor,shape in inputs.items():
        if not isinstance(tensor,str) or not re.fullmatch(r'[A-D]',tensor):raise Unsupported('input names must be A..D')
        if not isinstance(shape,list) or not 0<=len(shape)<=4:raise Unsupported('input rank exceeds four')
        ins[tensor]=tuple(expression(x,pnames) for x in shape)
    pre=expression(raw.get('precondition'),pnames,True)
    def program(p):
        if not isinstance(p,dict) or set(p)!={'shape','terms','storage'}:raise Unsupported('program fields must be shape, terms, storage')
        if not isinstance(p['shape'],list) or len(p['shape'])>4:raise Unsupported('output rank exceeds four')
        shp=tuple(expression(x,pnames) for x in p['shape'])
        local_names=pnames|{f'i{k}' for k in range(len(shp))}
        if p['storage'] not in ('dense','union','compact','empty'):raise Unsupported('unsupported storage policy')
        if not isinstance(p['terms'],list) or len(p['terms'])>32:raise Unsupported('term budget exceeds 32')
        terms=[]
        for t in p['terms']:
            if not isinstance(t,dict) or set(t)!={'tensor','index','coefficient','guard'}:raise Unsupported('invalid term fields')
            if t['tensor'] not in ins:raise Unsupported('undeclared tensor')
            idx=t['index']
            if not isinstance(idx,list) or len(idx)!=len(ins[t['tensor']]):raise Unsupported('read rank mismatch')
            if not isinstance(t['coefficient'],str) or len(t['coefficient'])>32:raise Unsupported('coefficient must be a short rational string')
            try:q=Fraction(t['coefficient'])
            except (ValueError,ZeroDivisionError) as e:raise Unsupported('invalid rational coefficient') from e
            if max(abs(q.numerator),q.denominator)>=2**16:raise Unsupported('coefficient bit budget')
            terms.append(Term(t['tensor'],tuple(expression(x,local_names) for x in idx),q,expression(t['guard'],local_names,True)))
        return Program(shp,tuple(terms),p['storage'])
    before,after=program(raw.get('before')),program(raw.get('after'))
    # Tensor-IR nodes: one output, one store, and up to two operators per term.
    if any(2+2*len(p.terms)>96 for p in (before,after)):raise Unsupported('IR-node budget')
    return Case(identifier,tuple(params),ins,pre,before,after,str(raw.get('family','unspecified')))

def domain(shape: tuple[Expr,...]) -> str:
    return both(both([f'(<= 0 i{k})',f'(< i{k} {d.smt()})']) for k,d in enumerate(shape))
