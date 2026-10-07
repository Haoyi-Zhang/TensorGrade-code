"""Universal contract queries, with explicit schema/admission/timeout abstention."""
from __future__ import annotations
from dataclasses import asdict
from fractions import Fraction
from typing import Any
from .ir import Case,Program,Unsupported,load_case,both,either,total,rational,domain
from .solver import Solver,Answer,SolverError

ATOMS=('shape','value','zero-support','stored-support','term-order')

def encode(c: Case, omit_congruence: bool=False):
    ts=c.before.terms+c.after.terms
    decl={n:'Int' for n in c.parameters}|{f'i{k}':'Int' for k in range(4)}
    decl.update({f'x{k}':'Real' for k in range(len(ts))})
    decl.update({f'b{k}':'Bool' for k in range(len(ts))})
    assertions=[];defs=[]
    for k,t in enumerate(ts):
        assertions.append(f'(=> (not b{k}) (= x{k} 0))')
        defs.append(f'(define-fun g{k} () Bool {t.guard.smt()})')
    # Occurrence-local strings only: retain every read, including inactive and
    # zero-coefficient reads. No formula, ordering, or congruence is simplified.
    addresses=tuple(tuple(x.smt() for x in t.index) for t in ts)
    congruences=0
    if not omit_congruence:
        for a,t in enumerate(ts):
            for b,u in enumerate(ts[:a]):
                if t.tensor==u.tensor:
                    same=both(f'(= {x} {y})' for x,y in zip(addresses[a],addresses[b]))
                    assertions.append(f'(=> {same} (and (= x{a} x{b}) (= b{a} b{b})))')
                    congruences+=1
    def values(p,offset,label):
        v=total(f'(ite g{k+offset} (* {rational(t.coefficient)} x{k+offset}) 0)' for k,t in enumerate(p.terms))
        defs.append(f'(define-fun {label} () Real {v if p.terms else "0.0"})')
        if p.storage=='dense':m='true'
        elif p.storage=='empty':m='false'
        elif p.storage=='compact':m=f'(not (= {label} 0))'
        else:m=either(f'(and g{k+offset} b{k+offset})' for k in range(len(p.terms)))
        defs.append(f'(define-fun {label}m () Bool {m})')
    split=len(c.before.terms)
    values(c.before,0,'vp');values(c.after,split,'vq')
    # The rank of an active term is the number of preceding active terms.
    for label,start,terms in [('p',0,c.before.terms),('q',split,c.after.terms)]:
        for k in range(len(terms)+1):
            defs.append(f'(define-fun {label}pos{k} () Int {total(f"(ite g{start+j} 1 0)" for j in range(k))})')
    order=[f'(= ppos{split} qpos{len(c.after.terms)})']
    for a,t in enumerate(c.before.terms):
        for b,u in enumerate(c.after.terms):
            same='false' if t.tensor!=u.tensor or t.coefficient!=u.coefficient else both(f'(= {x} {y})' for x,y in zip(addresses[a],addresses[split+b]))
            order.append(f'(=> (and g{a} g{split+b} (= ppos{a} qpos{b})) {same})')
    eqshape='false' if len(c.before.shape)!=len(c.after.shape) else both(f'(= {a.smt()} {b.smt()})' for a,b in zip(c.before.shape,c.after.shape))
    badshape=f'(not {eqshape})'
    badobs={
        'value':'(not (= vp vq))',
        'zero-support':'(xor (= vp 0) (= vq 0))',
        'stored-support':'(xor vpm vqm)',
        'term-order':f'(not {both(order)})'}
    bad={'shape':badshape}
    for atom,b in badobs.items():
        bad[atom]=either([badshape,both([domain(c.before.shape),domain(c.after.shape),b])])
    return decl,assertions,defs,bad,congruences

def grade(raw: dict[str,Any], solver: Solver, omit_congruence: bool=False) -> dict[str,Any]:
    """Never upgrades unknown, invalid, or unsupported inputs to a grade."""
    try:c=load_case(raw)
    except (Unsupported,TypeError,KeyError) as e:
        return {'id':str(raw.get('id','unidentified')) if isinstance(raw,dict) else 'unidentified','admission':'unsupported','reason':str(e),'contracts':{}}
    records=[]
    def query(label,decl,ass,defs=None):
        a=solver.check(decl,ass,defs)
        records.append({'obligation':label,**asdict(a)})
        return a
    pd={n:'Int' for n in c.parameters};pre=c.precondition.smt()
    feasible=query('precondition',pd,[pre])
    if feasible.status!='sat':
        return {'id':c.identifier,'admission':'vacuous' if feasible.status=='unsat' else 'unknown','reason':'precondition feasibility','contracts':{},'queries':records}
    dims=list(d for shp in c.inputs.values() for d in shp)+list(c.before.shape)+list(c.after.shape)
    a=query('nonnegative-dimensions',pd,[pre,either(f'(< {d.smt()} 0)' for d in dims)])
    if a.status!='unsat':
        return {'id':c.identifier,'admission':'invalid' if a.status=='sat' else 'unknown','reason':'negative dimension','contracts':{},'queries':records}
    idd=pd|{f'i{k}':'Int' for k in range(4)}
    bounds=[]
    for p in (c.before,c.after):
        for t in p.terms:
            inbound=both(both([f'(<= 0 {i.smt()})',f'(< {i.smt()} {d.smt()})']) for i,d in zip(t.index,c.inputs[t.tensor]))
            bounds.append(both([domain(p.shape),t.guard.smt(),f'(not {inbound})']))
    a=query('active-read-bounds',idd,[pre,either(bounds)])
    if a.status!='unsat':
        return {'id':c.identifier,'admission':'invalid' if a.status=='sat' else 'unknown','reason':'active read out of bounds','contracts':{},'queries':records}
    decl,ass,defs,bad,congruences=encode(c,omit_congruence)
    # Empty storage is admitted only for a universally zero value; other policies
    # satisfy the tensor well-formedness invariant by construction.
    invalid=[]
    for p,label in [(c.before,'vp'),(c.after,'vq')]:
        if p.storage=='empty':invalid.append(both([domain(p.shape),f'(not (= {label} 0))']))
    if invalid:
        a=query('output-storage-consistency',decl,[pre,*ass,either(invalid)],defs)
        if a.status!='unsat':
            return {'id':c.identifier,'admission':'invalid' if a.status=='sat' else 'unknown','reason':'unstored nonzero output','contracts':{},'queries':records}
    contracts={}
    for atom in ATOMS:
        a=query(atom,decl,[pre,*ass,bad[atom]],defs)
        contracts[atom]={'status':{'sat':'refuted','unsat':'proved','unknown':'unknown'}[a.status],
                         'witness':a.values if a.status=='sat' else None}
    statuses={x:v['status'] for x,v in contracts.items()}
    if not omit_congruence and statuses['value']=='proved' and statuses['zero-support']=='refuted':raise SolverError('value/support closure contradiction')
    if not omit_congruence and statuses['term-order']=='proved' and statuses['value']=='refuted':raise SolverError('order/value closure contradiction')
    return {'id':c.identifier,'family':c.family,'admission':'admitted','contracts':contracts,
            'complete_grade':not omit_congruence and all(v['status']!='unknown' for v in contracts.values()),
            'mode':'defective-congruence-ablation' if omit_congruence else 'production',
            'congruence_pairs':congruences,'terms':len(c.before.terms)+len(c.after.terms),
            'queries':records}
