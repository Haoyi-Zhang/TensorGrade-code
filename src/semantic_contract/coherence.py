"""Parametric support-coherence queries for rational linear consumers.

Input/output lengths are affine. Coefficients and nonzero diagonal scales are
piecewise constant with affine guards. Allowed occupancy masks are all cliques
of the declared reflexive, symmetric compatibility relation. This definition
makes a compatible two-cell support realizable; arbitrary producer images are
not covered by the necessity direction.
"""
from __future__ import annotations
from dataclasses import asdict
from fractions import Fraction
from itertools import combinations, product
from typing import Any
import re
from .ir import expression, both, either, rational, Unsupported
from .solver import Solver
from .replay import integer_expression, ReplayError
from .oracle import same_kernel


def load(raw):
    if not isinstance(raw,dict) or set(raw)-{'id','parameters','precondition','input_extent','output_extent','scales','weights','compatible','family','expected'}:
        raise Unsupported('unknown consumer fields')
    if not re.fullmatch(r'[A-Za-z0-9-]{1,80}',raw.get('id','')): raise Unsupported('identifier')
    params=raw['parameters']
    if (not isinstance(params,list) or not 1<=len(params)<=4 or
        any(not isinstance(n,str) or not re.fullmatch(r'n[0-3]',n) for n in params) or len(set(params))!=len(params)):
        raise Unsupported('shape parameters')
    names=set(params)
    n=expression(raw['input_extent'],names);m=expression(raw['output_extent'],names)
    pre=expression(raw['precondition'],names,True)
    compat=expression(raw['compatible'],names|{'u0','v0'},True)
    def rules(rs,allowed,nonzero):
        if not isinstance(rs,list) or not 1<=len(rs)<=8:raise Unsupported('one to eight partition rules')
        out=[]
        for r in rs:
            if not isinstance(r,dict) or set(r)!={'guard','coefficient'}:raise Unsupported('rule fields')
            if not isinstance(r['coefficient'], str) or len(r['coefficient']) > 32:
                raise Unsupported('coefficient must be a short rational string')
            q=Fraction(r['coefficient'])
            if max(abs(q.numerator),q.denominator)>=2**16:raise Unsupported('coefficient bit cap')
            if nonzero and not q:raise Unsupported('scale must be nonzero')
            out.append((expression(r['guard'],allowed,True),q))
        return out
    ss=rules(raw['scales'],names|{'u0'},True)
    ws=rules(raw['weights'],names|{'u0','i0'},False)
    return params,n,m,pre,compat,ss,ws

def _renamed(s,old,new):
    # Tokens rather than textual substrings; all identifiers are from the schema.
    return re.sub(r'\b'+old+r'\b',new,s)

def _piecewise(rs):
    result='0'
    for g,c in reversed(rs):result=f'(ite {g.smt()} {rational(c)} {result})'
    return result

def check_coherence(raw: dict[str,Any], solver: Solver) -> dict:
    try:params,n,m,pre,compat,scales,weights=load(raw)
    except (Unsupported,KeyError,TypeError,ValueError,ZeroDivisionError) as e:
        return {'id':raw.get('id','unidentified') if isinstance(raw,dict) else 'unidentified','admission':'unsupported','reason':str(e)}
    rec=[];pd={p:'Int' for p in params};decl=pd|{'i0':'Int','u0':'Int','v0':'Int'}
    def query(label,ds,ass):
        ans=solver.check(ds,ass)
        rec.append({'obligation':label,**asdict(ans)})
        return ans
    feasibility=query('precondition',pd,[pre.smt()])
    if feasibility.status!='sat':
        return {'id':raw['id'],'admission':'vacuous' if feasibility.status=='unsat' else 'unknown','queries':rec}
    nd=n.smt();md=m.smt();p=pre.smt()
    u=both(['(<= 0 u0)',f'(< u0 {nd})']);v=_renamed(u,'u0','v0')
    i=both(['(<= 0 i0)',f'(< i0 {md})'])
    invalid=[('nonnegative-dimensions',pd,[p,either([f'(< {nd} 0)',f'(< {md} 0)'])])]
    for label,rs,dom in [('scale-partition',scales,u),('weight-partition',weights,both([i,u]))]:
        missing=f'(not {either(g.smt() for g,_ in rs)})'
        overlap=either(both([g.smt(),h.smt()]) for (g,_),(h,_) in combinations(rs,2))
        invalid.append((label,decl,[p,dom,either([missing,overlap])]))
    comp=compat.smt()
    diagonal=_renamed(comp,'v0','u0')
    swap=_renamed(_renamed(_renamed(comp,'u0','tmp0'),'v0','u0'),'tmp0','v0')
    invalid.append(('compatibility-reflexive',decl,[p,u,f'(not {diagonal})']))
    invalid.append(('compatibility-symmetric',decl,[p,u,v,f'(xor {comp} {swap})']))
    for label,ds,ass in invalid:
        ans=query(label,ds,ass)
        if ans.status!='unsat':
            return {'id':raw['id'],'admission':'invalid' if ans.status=='sat' else 'unknown',
                    'reason':label,'queries':rec}
    su=_piecewise(scales);sv=_renamed(su,'u0','v0')
    wu=_piecewise(weights);wv=_renamed(wu,'u0','v0')
    bad=both([i,u,v,comp,f'(not (= {wu} 0))',f'(not (= {wv} 0))',f'(not (= {su} {sv}))'])
    ans=query('support-coherence',decl,[p,bad])
    return {'id':raw['id'],'admission':'admitted',
            'status':{'unsat':'proved','sat':'refuted','unknown':'unknown'}[ans.status],
            'witness':ans.values if ans.status=='sat' else None,'queries':rec,
            'interpretation':'free input values; clique-compatible occupancy; exact rational arithmetic'}

# The following replay uses the separate direct interpreter, not SMT expressions.
def _at(rules,env):
    selected=[Fraction(r['coefficient']) for r in rules if integer_expression(r['guard'],env,True)]
    if len(selected)!=1:raise ReplayError('partition not total and disjoint at witness')
    return selected[0]

def replay_coherence(raw,witness):
    try:
        env={name:int(Fraction(witness[name])) for name in raw['parameters']+['i0','u0','v0']}
        if any(Fraction(witness[k])!=v for k,v in env.items()):raise ReplayError('nonintegral witness')
        n=integer_expression(raw['input_extent'],env,False);m=integer_expression(raw['output_extent'],env,False)
        if not integer_expression(raw['precondition'],env,True):raise ReplayError('precondition')
        i,u,v=env['i0'],env['u0'],env['v0']
        if not (0<=i<m and 0<=u<n and 0<=v<n and u!=v):raise ReplayError('witness bounds/distinctness')
        for a,b in product((u,v),repeat=2):
            if not integer_expression(raw['compatible'],env|{'u0':a,'v0':b},True):raise ReplayError('unrealizable support')
        a=_at(raw['weights'],env);b=_at(raw['weights'],env|{'u0':v})
        du=_at(raw['scales'],env);dv=_at(raw['scales'],env|{'u0':v})
        x,y=b,-a
        before=a*x+b*y;after=a*du*x+b*dv*y
        if not a or not b or not du or not dv or before!=0 or after==0:
            raise ReplayError('cancellation witness does not discriminate')
        return {'valid':True,'parameters':env,'input_extent':n,'output_extent':m,
                'cells':[{'index':u,'value':str(x),'stored':True},{'index':v,'value':str(y),'stored':True}],
                'before_value':str(before),'after_value':str(after),
                'weights':[str(a),str(b)],'scales':[str(du),str(dv)]}
    except (KeyError,ValueError,TypeError,ReplayError,ZeroDivisionError) as e:
        return {'valid':False,'reason':str(e)}

def concrete_coherence_oracle(raw,env,max_cells=6):
    """Enumerate legal masks, then compare rational row kernels; no pair test."""
    if not integer_expression(raw['precondition'],env,True):return {'status':'outside-precondition','obligations':0}
    n=integer_expression(raw['input_extent'],env,False);m=integer_expression(raw['output_extent'],env,False)
    if not (0<=n<=max_cells and 0<=m<=max_cells):raise ReplayError('oracle shape cap')
    answer=True;obligations=0;legal=0
    for bits in product((False,True),repeat=n):
        cells=[j for j,b in enumerate(bits) if b]
        if not all(integer_expression(raw['compatible'],env|{'u0':u,'v0':v},True) for u,v in product(cells,repeat=2)):
            continue
        legal+=1
        for i in range(m):
            row={};scaled={}
            for j in cells:
                loc=env|{'u0':j,'i0':i}
                row[j]=_at(raw['weights'],loc)
                scaled[j]=row[j]*_at(raw['scales'],loc)
            answer &= same_kernel(row,scaled);obligations+=1
    return {'status':'checked','support_preserved':bool(answer),'obligations':obligations,'legal_masks':legal}
