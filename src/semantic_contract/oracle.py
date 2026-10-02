"""Exact all-rational-values oracle at a bounded, concrete shape.

Coefficient rows are assembled from concrete addresses, with no SMT and no
encoder imports. Stored-mask enumeration is exhaustive under a fixed cell cap.
The oracle is not a proof for untested shape parameters.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import product
from .replay import integer_expression, shape_of, active_reads, points, in_bounds, ReplayError

ATOMS = ('shape','value','zero-support','stored-support','term-order')

class OracleLimit(ValueError): pass

def same_kernel(a: dict, b: dict) -> bool:
    a = {k:v for k,v in a.items() if v}; b = {k:v for k,v in b.items() if v}
    if not a or not b: return not a and not b
    if a.keys() != b.keys(): return False
    pivot = next(iter(a)); ratio = b[pivot]/a[pivot]
    return ratio != 0 and all(b[k] == ratio*a[k] for k in a)

def coefficient_row(terms):
    result = {}
    for _, key, c in terms: result[key] = result.get(key,Fraction(0))+c
    return {k:v for k,v in result.items() if v}

def _mask_observation(program, terms, row, stored):
    policy = program['storage']
    if policy == 'dense': return ('constant',True)
    if policy == 'empty': return ('constant',False)
    if policy == 'union': return ('constant',any(key in stored for _,key,_ in terms))
    if policy == 'compact': return ('linear',{k:v for k,v in row.items() if k in stored})
    raise ReplayError('unknown storage policy')

def equal_mask_observations(a,b):
    if a[0]==b[0]=='constant': return a[1]==b[1]
    if a[0]==b[0]=='linear': return same_kernel(a[1],b[1])
    const,linear = (a,b) if a[0]=='constant' else (b,a)
    # The all-zero value assignment is legal even at stored coordinates.
    return not const[1] and not any(linear[1].values())

def concrete_shape_oracle(raw: dict, parameters: dict[str,int], max_cells: int=10,
                          max_points: int=256) -> dict:
    env = dict(parameters); obligations = 0
    if not integer_expression(raw['precondition'],env,True):
        return {'status':'outside-precondition','obligations':0}
    ins = {k:shape_of(v,env) for k,v in raw['inputs'].items()}
    bp,ap = raw['before'],raw['after']
    bs,qs = shape_of(bp['shape'],env),shape_of(ap['shape'],env)
    result = {a:True for a in ATOMS}
    if bs != qs:
        return {'status':'checked','contracts':{a:False for a in ATOMS},'obligations':5,'points':0}
    npoints=0
    for idx in points(bs,max_points):
        npoints += 1; local = env|{f'i{k}':v for k,v in enumerate(idx)}
        pt,qt = list(active_reads(bp,local)),list(active_reads(ap,local))
        for _,key,_ in pt+qt:
            if not in_bounds(key[1],ins[key[0]]): raise ReplayError('oracle: out of bounds')
        pr,qr = coefficient_row(pt),coefficient_row(qt)
        result['value'] &= pr == qr
        result['zero-support'] &= same_kernel(pr,qr)
        result['term-order'] &= [(key,c) for _,key,c in pt] == [(key,c) for _,key,c in qt]
        obligations += 3
        keys = sorted(set(key for _,key,_ in pt+qt))
        if len(keys)>max_cells: raise OracleLimit('stored-mask cell cap')
        for bits in product((False,True),repeat=len(keys)):
            stored = {k for k,b in zip(keys,bits) if b}
            po = _mask_observation(bp,pt,pr,stored); qo = _mask_observation(ap,qt,qr,stored)
            result['stored-support'] &= equal_mask_observations(po,qo)
            obligations += 1
    return {'status':'checked','contracts':result,'obligations':obligations+1,'points':npoints}
