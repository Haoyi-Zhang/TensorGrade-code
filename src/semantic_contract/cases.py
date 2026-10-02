"""Deterministic theorem/prototype probes, not a public patch benchmark."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
import random

def term(tensor='A',index=None,coefficient='1',guard='True'):
    return {'tensor':tensor,'index':['i0'] if index is None else index,
            'coefficient':str(coefficient),'guard':guard}
def program(terms,shape=None,storage='union'):
    return {'shape':['n0'] if shape is None else shape,'terms':terms,'storage':storage}
def pair(identifier,before,after,pre='n0 >= 1',inputs=None,params=None,family='semantic-control'):
    return {'id':identifier,'parameters':['n0'] if params is None else params,
            'inputs':{'A':['n0']} if inputs is None else inputs,'precondition':pre,
            'before':before,'after':after,'family':family,'provenance':'generated-original; no public-patch mapping'}

def pilot_cases():
    p=program([term()]);out=[]
    def add(c,admission=None,contracts=None):
        c['expected']={'admission':admission or 'admitted'}
        if contracts is not None:c['expected']['contracts']=dict(zip(
            ('shape','value','zero-support','stored-support','term-order'),contracts))
        out.append(c)
    add(pair('identity',deepcopy(p),deepcopy(p)),contracts=[1,1,1,1,1])
    add(pair('uniform-scale',deepcopy(p),program([term(coefficient='2')])),contracts=[1,0,1,1,0])
    add(pair('nonuniform-scale',deepcopy(p),program([term(guard='i0 == 0'),term(coefficient='2',guard='i0 != 0')])),contracts=[1,0,1,1,0])
    add(pair('support-without-storage',deepcopy(p),program([term(coefficient='2')],storage='compact')),contracts=[1,0,1,0,0])
    add(pair('storage-without-support',program([term(),term('B')]),program([term(),term('B',coefficient='2')]),inputs={'A':['n0'],'B':['n0']}),contracts=[1,0,0,1,0])
    q=program([term(),term('B')]);r=program([term('B'),term()])
    add(pair('reordered-addition',q,r,inputs={'A':['n0'],'B':['n0']}),contracts=[1,1,1,1,0])
    add(pair('merged-duplicate',program([term(),term()]),program([term(coefficient='2')])),contracts=[1,1,1,1,0])
    q=program([term(index=['0']),term(index=['n0-1'])])
    r=program([term(index=['0'],coefficient='2')])
    add(pair('shape-collision',q,r,pre='n0 == 1'),contracts=[1,1,1,1,0])
    add(pair('collision-not-universal',deepcopy(q),deepcopy(r)),contracts=[1,0,0,0,0])
    add(pair('stored-zero-elimination',deepcopy(p),program([term()],storage='compact')),contracts=[1,1,1,0,1])
    add(pair('zero-term-storage',program([term(),term('B',coefficient='0')]),deepcopy(p),inputs={'A':['n0'],'B':['n0']}),contracts=[1,1,1,0,0])
    add(pair('shape-change',program([],storage='dense'),program([],shape=['n0+1'],storage='dense')),contracts=[0,0,0,0,0])
    add(pair('active-read-oob',deepcopy(p),program([term(index=['i0+1'])])),admission='invalid')
    add(pair('negative-dimension',deepcopy(p),deepcopy(p),pre='n0 >= -1'),admission='invalid')
    add(pair('empty-precondition',deepcopy(p),deepcopy(p),pre='n0 < 0 and n0 >= 0'),admission='vacuous')
    add(pair('nonaffine-index',deepcopy(p),program([term(index=['i0*n0'])])),admission='unsupported')
    r=deepcopy(p);r['storage']='aliased'
    add(pair('alias-outside-fragment',deepcopy(p),r),admission='unsupported')
    add(pair('unstored-nonzero',deepcopy(p),program([term()],storage='empty')),admission='invalid')
    add(pair('cancellation-to-empty',program([term(),term(coefficient='-1')]),program([],storage='empty')),contracts=[1,1,1,0,0])
    add(pair('late-shape-threshold',deepcopy(p),program([term(guard='n0 <= 32'),term(coefficient='2',guard='n0 > 32')])),contracts=[1,0,1,1,0])
    trans=program([term(index=['i1','i0'])],shape=['n1','n0'])
    add(pair('rank-two-transpose',deepcopy(trans),deepcopy(trans),pre='n0 >= 0 and n1 >= 0',
             inputs={'A':['n0','n1']},params=['n0','n1']),contracts=[1,1,1,1,1])
    add(pair('empty-output',deepcopy(p),program([term(coefficient='2')]),pre='n0 == 0'),contracts=[1,1,1,1,1])
    scalar=program([term(index=[])],shape=[])
    add(pair('scalar-rank',deepcopy(scalar),deepcopy(scalar),inputs={'A':[]}),contracts=[1,1,1,1,1])
    add(pair('inactive-oob',deepcopy(p),program([term(),term(index=['n0'],guard='False')])),contracts=[1,1,1,1,1])
    add(pair('input-identity-mismatch',deepcopy(p),program([term('B')]),inputs={'A':['n0'],'B':['n0']}),contracts=[1,0,0,0,0])
    add(pair('zero-output-storage',program([],storage='dense'),program([],storage='union')),contracts=[1,1,1,0,1])
    add(pair('rational-normalization',program([term(coefficient='31/19')]),program([term(coefficient='62/38')])),contracts=[1,1,1,1,1])
    # Largest syntactically admitted read count and rank in this pilot.
    ts=[term(index=['i0','i1','i2','i3'],coefficient=str((k%5)-2),
             guard=['True','i0 == 0','i1 < n1-1','i2 == i3'][k%4]) for k in range(32)]
    rank4=program(ts,shape=['n0','n1','n2','n3']);rev=program(list(reversed(deepcopy(ts))),shape=['n0','n1','n2','n3'])
    add(pair('maximal-guarded-reorder',rank4,rev,pre='n0 >= 1 and n1 >= 1 and n2 >= 1 and n3 >= 1',
             params=['n0','n1','n2','n3'],inputs={'A':['n0','n1','n2','n3']},family='encoding-envelope'),contracts=[1,1,1,1,0])
    return out

def generated_cases(count=64,seed=1729):
    if not 0<=count<=192:raise ValueError('generated case cap')
    rng=random.Random(seed);out=[]
    for k in range(count):
        def randterm():
            return term(rng.choice(['A','B']),[rng.choice(['i0','0','n0-1'])],
                        rng.choice(['-2','-1','0','1/2','1','2']),rng.choice(['True','i0==0','i0<n0-1']))
        terms=[randterm() for _ in range(rng.randint(1,5))]
        new=deepcopy(terms);mode=k%8
        if mode==0:rng.shuffle(new)
        elif mode==1:
            for t in new:t['coefficient']=str(2*Fraction(t['coefficient']))
        elif mode==2:new.append(randterm())
        elif mode==3:new=new[:-1]
        elif mode==4:
            t=deepcopy(new[0]);t['coefficient']=str(-Fraction(t['coefficient']));new.extend([deepcopy(new[0]),t])
        elif mode==5:new[0]['index']=['0']
        elif mode==6:new[0]['guard']='n0 <= 4'
        bp=program(terms,storage=rng.choice(['union','compact','dense']))
        qp=program(new,storage=bp['storage'] if mode!=7 else rng.choice(['union','compact','dense']))
        out.append(pair(f'generated-{k:03d}',bp,qp,inputs={'A':['n0'],'B':['n0']},family=f'generated-mode-{mode}'))
    return out

def consumer_cases():
    def rule(g,c):return {'guard':g,'coefficient':str(c)}
    base={'parameters':['n0'],'precondition':'n0 >= 1','input_extent':'n0','output_extent':'1',
          'scales':[rule('True',2)],'weights':[rule('True',1)],'compatible':'True'}
    out=[]
    def add(identifier,expected,**changes):
        raw=deepcopy(base);raw.update(changes);raw['id']=identifier;raw['expected']=expected;out.append(raw)
    add('global-uniform','proved')
    mixed=[rule('u0==0',1),rule('u0!=0',2)]
    add('global-nonuniform','refuted',scales=mixed)
    add('one-hot-masks','proved',scales=mixed,compatible='u0 == v0')
    add('identity-consumer','proved',scales=mixed,output_extent='n0',weights=[rule('u0==i0',1),rule('u0!=i0',0)])
    add('adjacent-stencil','refuted',scales=mixed,output_extent='n0',weights=[rule('u0==i0 or u0==i0+1',1),rule('u0!=i0 and u0!=i0+1',0)])
    add('two-block-reductions','proved',scales=[rule('u0 < 2',2),rule('u0 >= 2',3)],output_extent='2',
        weights=[rule('(i0==0 and u0<2) or (i0==1 and u0>=2)',1),rule('(i0==0 and u0>=2) or (i0==1 and u0<2)',0)])
    add('block-crossing','refuted',scales=mixed,output_extent='2',
        weights=[rule('(i0==0 and u0<2) or (i0==1 and u0>=2)',1),rule('(i0==0 and u0>=2) or (i0==1 and u0<2)',0)])
    add('late-consumer-threshold','refuted',scales=[rule('n0<=32 or u0==0',1),rule('n0>32 and u0!=0',2)])
    add('zero-consumer','proved',scales=mixed,weights=[rule('True',0)])
    add('weighted-cancellation','refuted',scales=mixed,weights=[rule('u0==0','2/3'),rule('u0!=0','-5/7')])
    add('empty-consumer-domain','proved',precondition='n0 == 0')
    add('non-reflexive-mask','invalid',compatible='u0 != v0')
    add('asymmetric-mask','invalid',compatible='u0 <= v0')
    add('overlapping-partition','invalid',scales=[rule('True',1),rule('True',2)])
    add('zero-scale-outside-fragment','unsupported',scales=[rule('True',0)])
    add('missing-partition-cell','invalid',scales=[rule('u0 == 0',2)])
    return out
