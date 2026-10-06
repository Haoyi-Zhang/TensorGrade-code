"""Construct and check at-most-two-stored-cell counterexamples.

The construction uses concrete coefficient rows at a solver-selected shape,
not the solver's rational values. The checker is a direct interpreter and does
not load a solver or the symbolic IR encoder. It validates refutations only.
"""
from __future__ import annotations
from fractions import Fraction
from .replay import (ReplayError, integer_expression, shape_of, in_bounds,
                     active_reads, evaluate, validate_replay_case, exact_fraction, integral_value)
from .oracle import coefficient_row,same_kernel


def _source_sequence_templates(sequence):
    for call in sequence.calls:
        if call.pending:
            raise ReplayError('sequence pre-map belongs to previous call, not call template')


def source_effect_certificate(sequence, results):
    """Bind exported state and the final dense block, not all five helpers."""
    from .dense_effects import node_record, pending_record, transition_record
    _source_sequence_templates(sequence)
    if len(sequence.calls) != len(results):
        raise ReplayError('source call count')
    calls = []
    dense_comment = {'kind': 'Comment', 'fields': {'text': 'Resolve dense coordinates'}}
    for index, result in enumerate(results):
        if result.pending != result.dense.post:
            raise ReplayError(f'call {index}: source exported pending binding')
        transition = transition_record(result.dense)
        nodes = node_record(result.nodes)
        starts = [i for i, node in enumerate(nodes) if node == dense_comment]
        # The dense block is last and has one leading top-level comment iff
        # nonempty. Earlier helper nodes are not certified by this format.
        emitted = transition['emitted']
        if emitted:
            if len(starts) != 1 or nodes[starts[0]:] != emitted:
                raise ReplayError(f'call {index}: source dense emission binding')
        elif starts:
            raise ReplayError(f'call {index}: source dense emission binding')
        calls.append(transition)
    return {'kind': 'p06-ordered-map', 'case_id': sequence.case_id,
            'initial_pending': pending_record(sequence.initial_pending),
            'calls': calls}


def check_source_effect_certificate(sequence, cert):
    from .dense_effects import node_record, pending_record
    from .replay import replay_source_effects
    try:
        _source_sequence_templates(sequence)
        # Bind replay to supplied inputs, not a self-selected certificate case.
        if cert['case_id'] != sequence.case_id or cert['initial_pending'] != pending_record(sequence.initial_pending):
            raise ReplayError('source case binding')
        if len(cert['calls']) != len(sequence.calls):
            raise ReplayError('source call count')
        for call, transition in zip(sequence.calls, cert['calls']):
            offered = [{'coordinate': node_record(it.coordinate), 'value': node_record(it.value),
                        'dependencies': list(it.dependencies)} for it in call.dense_iterators]
            if transition['offered'] != offered or transition['defined'] != list(call.defined_index_vars):
                raise ReplayError('source call input binding')
        return replay_source_effects(cert)
    except (ReplayError, KeyError, TypeError, ValueError) as exc:
        return {'valid': False, 'reason': str(exc)}


def _kernel_witness(a,b):
    keys=sorted(set(a)|set(b))
    for k in keys:
        if (a.get(k,0)==0)!=(b.get(k,0)==0):return {k:Fraction(1)}
    for j in keys:
        for k in keys:
            aj,ak=a.get(j,Fraction(0)),a.get(k,Fraction(0))
            bj,bk=b.get(j,Fraction(0)),b.get(k,Fraction(0))
            if aj*bk != ak*bj:
                return {key:value for key,value in [(j,ak),(k,-aj)] if value}
    raise ReplayError('rows have the same kernel')


def _stored_witness(bp,ap,pt,qt,pr,qr):
    p,q=bp['storage'],ap['storage']
    pk={key for _,key,_ in pt};qk={key for _,key,_ in qt}
    if p=='compact' and q=='compact':return _kernel_witness(pr,qr)
    if p=='dense' or q=='dense':
        if p==q:raise ReplayError('equal dense storage')
        return {}
    # dense has been handled; empty and empty-union are constantly false.
    if p=='union' and not pk:p='empty'
    if q=='union' and not qk:q='empty'
    if p==q=='union':
        diff=pk^qk
        if not diff:raise ReplayError('equal union storage')
        return {sorted(diff)[0]:Fraction(0)}
    if p=='union':return {sorted(pk)[0]:Fraction(0)}
    if q=='union':return {sorted(qk)[0]:Fraction(0)}
    if p=='compact' and q=='empty' and pr:return {sorted(pr)[0]:Fraction(1)}
    if q=='compact' and p=='empty' and qr:return {sorted(qr)[0]:Fraction(1)}
    raise ReplayError('no stored-support mismatch')


def small_certificate(raw, atom, witness):
    validate_replay_case(raw)
    if atom not in ('shape', 'value', 'zero-support', 'stored-support', 'term-order'):
        raise ReplayError('observation')
    if not isinstance(witness, dict):
        raise ReplayError('witness must be an object')
    names=list(raw['parameters'])+[f'i{k}' for k in range(max(len(raw['before']['shape']),len(raw['after']['shape'])))]
    env={n:integral_value(witness[n], 'certificate coordinate') for n in names}
    bp,ap=raw['before'],raw['after']
    bs,qs=shape_of(bp['shape'],env),shape_of(ap['shape'],env)
    cells={}
    if bs==qs:
        pt,qt=list(active_reads(bp,env)),list(active_reads(ap,env))
        pr,qr=coefficient_row(pt),coefficient_row(qt)
        if atom=='value':
            ks=[k for k in sorted(set(pr)|set(qr)) if pr.get(k,0)!=qr.get(k,0)]
            if not ks:raise ReplayError('value rows agree')
            cells={ks[0]:Fraction(1)}
        elif atom=='zero-support':cells=_kernel_witness(pr,qr)
        elif atom=='stored-support':cells=_stored_witness(bp,ap,pt,qt,pr,qr)
        elif atom=='term-order':cells={}
        else:raise ReplayError('no shape mismatch')
    cert={'case_id':raw['id'],'observation':atom,'coordinates':env,
          'cells':[{'tensor':k[0],'index':list(k[1]),'value':str(v),'stored':True} for k,v in sorted(cells.items())]}
    checked=check_certificate(raw,cert)
    if not checked['valid']:raise ReplayError('constructed certificate failed: '+checked.get('reason',''))
    return cert


def check_certificate(raw,cert):
    """Check one finite witness. This does NOT certify universal validity."""
    try:
        validate_replay_case(raw)
        if not isinstance(cert, dict) or set(cert) != {'case_id','observation','coordinates','cells'}:
            raise ReplayError('certificate fields')
        if cert['case_id']!=raw['id']:raise ReplayError('case identifier mismatch')
        atom=cert['observation']
        if atom not in ('shape','value','zero-support','stored-support','term-order'):raise ReplayError('observation')
        env=cert['coordinates']
        if not isinstance(env, dict) or any(type(v) is not int for v in env.values()):
            raise ReplayError('noninteger coordinate')
        allowed_coordinates=set(raw['parameters'])|{f'i{k}' for k in range(4)}
        if set(env)-allowed_coordinates or not set(raw['parameters']).issubset(env):
            raise ReplayError('coordinate names')
        if not integer_expression(raw['precondition'],env,True,allowed_names=set(raw['parameters'])):
            raise ReplayError('precondition false')
        ins={n:shape_of(s,env) for n,s in raw['inputs'].items()}
        bp,ap=raw['before'],raw['after'];bs=shape_of(bp['shape'],env);qs=shape_of(ap['shape'],env)
        if any(d < 0 for shp in [*ins.values(), bs, qs] for d in shp):
            raise ReplayError('negative concrete dimension')
        if not isinstance(cert['cells'], list) or len(cert['cells'])>2:
            raise ReplayError('two-cell certificate bound exceeded')
        cells={}
        for cell in cert['cells']:
            if not isinstance(cell, dict) or set(cell) != {'tensor','index','value','stored'}:
                raise ReplayError('input cell fields')
            if not isinstance(cell['index'], list) or any(type(i) is not int for i in cell['index']):
                raise ReplayError('input indices must be integers')
            key=(cell['tensor'],tuple(cell['index']))
            if key[0] not in ins or not in_bounds(key[1],ins[key[0]]):raise ReplayError('input cell bounds')
            if key in cells or cell['stored'] is not True:raise ReplayError('duplicate/nonstored cell')
            if not isinstance(cell['value'],str) or len(cell['value'])>4096:
                raise ReplayError('value encoding cap')
            cells[key]=(exact_fraction(cell['value'], 'cell value'),True)
        if bs!=qs:return {'valid':True,'mismatch':'shape','stored_cells':len(cells)}
        idx=tuple(env[f'i{k}'] for k in range(len(bs)))
        if not in_bounds(idx,bs):raise ReplayError('output coordinate bounds')
        for p in (bp,ap):
            for _,key,_ in active_reads(p,env):
                if not in_bounds(key[1],ins[key[0]]):raise ReplayError('active input read bounds')
        pv,pm,po=evaluate(bp,env,cells);qv,qm,qo=evaluate(ap,env,cells)
        bad={'shape':False,'value':pv!=qv,'zero-support':(pv==0)!=(qv==0),
             'stored-support':pm!=qm,'term-order':po!=qo}[atom]
        if not bad:raise ReplayError('observation agrees')
        return {'valid':True,'mismatch':atom,'stored_cells':len(cells),
                'before_value':str(pv),'after_value':str(qv),'before_stored':pm,'after_stored':qm}
    except (ReplayError,KeyError,ValueError,TypeError,ZeroDivisionError) as e:
        return {'valid':False,'reason':str(e)}
