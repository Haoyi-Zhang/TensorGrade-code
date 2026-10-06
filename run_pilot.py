#!/usr/bin/env python3
"""One-worker measured pilot; no downloads, model execution, or third-party code."""
from __future__ import annotations
import argparse,json,os,sys,time
from process_resources import apply_limits, peak_rss_kib, enforced_limits
from itertools import product
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
# Limits cover the complete process; no child workers are created.
apply_limits()
os.environ.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
from semantic_contract.cases import pilot_cases,consumer_cases
from semantic_contract.solver import Solver
from semantic_contract.checker import grade
from semantic_contract.replay import replay
from semantic_contract.oracle import concrete_shape_oracle
from semantic_contract.certificates import small_certificate,check_certificate
from semantic_contract.coherence import check_coherence,replay_coherence,concrete_coherence_oracle

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results'/'pilot.json');args=ap.parse_args()
    start=time.process_time();wall=time.perf_counter();cases=pilot_cases();contexts=consumer_cases();records=[];errors=[]
    oracle_obligations=0;replays=0;oracle_checks=0
    with Solver(timeout_ms=1500) as solver:
        for c in cases:
            g=grade(c,solver);entry={'case':c,'grade':g,'replays':{},'oracles':[]}
            if g['admission']!=c['expected']['admission']:errors.append(f"{c['id']}: admission")
            if g['admission']=='admitted':
                wanted=c['expected'].get('contracts',{})
                for atom,value in g['contracts'].items():
                    if atom in wanted and value['status'] != ('proved' if wanted[atom] else 'refuted'):
                        errors.append(f"{c['id']}: expected {atom}")
                    if value['status']=='refuted':
                        r=replay(c,atom,value['witness']);entry['replays'][atom]=r;replays+=1
                        cert=small_certificate(c,atom,value['witness']);entry.setdefault('small_certificates',{})[atom]={'certificate':cert,'replay':check_certificate(c,cert)}
                        if not r['valid']:errors.append(f"{c['id']}: replay {atom}: {r}")
                # Bounded shape oracle. For rank four, use one nonempty shape.
                sizes=[(1,)*4] if len(c['parameters'])==4 else list(product(range(4),repeat=len(c['parameters'])))
                for vals in sizes:
                    env=dict(zip(c['parameters'],vals));o=concrete_shape_oracle(c,env);entry['oracles'].append({'parameters':env,**o})
                    oracle_obligations+=o['obligations']
                    if o['status']=='checked':
                        oracle_checks+=1
                        for atom,holds in o['contracts'].items():
                            if g['contracts'][atom]['status']=='proved' and not holds:errors.append(f"{c['id']}: oracle {atom}")
            records.append(entry)
        context_records=[]
        for c in contexts:
            g=check_coherence(c,solver);entry={'case':c,'grade':g,'oracles':[]}
            got=g.get('status') if g['admission']=='admitted' else g['admission']
            if got != c['expected']:errors.append(f"{c['id']}: context expected {c['expected']}, got {got}")
            if g['admission']=='admitted':
                if g['status']=='refuted':
                    r=replay_coherence(c,g['witness']);entry['replay']=r;replays+=1
                    if not r['valid']:errors.append(f"{c['id']}: context replay {r}")
                for n in range(6):
                    o=concrete_coherence_oracle(c,{'n0':n});entry['oracles'].append({'n0':n,**o});oracle_obligations+=o['obligations']
                    if o['status']=='checked':
                        oracle_checks+=1
                        if g['status']=='proved' and not o['support_preserved']:errors.append(f"{c['id']}: context oracle")
            context_records.append(entry)
        # A disabled congruence constraint must cause a replay-rejected false alarm.
        control=next(c for c in cases if c['id']=='shape-collision')
        defective=grade(control,solver,omit_congruence=True)
        candidate=defective['contracts']['value'];rr=replay(control,'value',candidate['witness']) if candidate['status']=='refuted' else None
        ablation={'case_id':control['id'],'grade':defective,'replay':rr}
        if candidate['status']!='refuted' or rr is None or rr['valid']:errors.append('congruence ablation did not discriminate')
        query_count=solver.queries;solver_cpu=solver.total_cpu
    report={'study':'pre-lock generated pilot; not a public patch evaluation','case_count':len(cases),'consumer_count':len(contexts),
            'query_count':query_count,'oracle_checks':oracle_checks,'oracle_obligations':oracle_obligations,'replay_count':replays,
            'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,'solver_cpu_seconds':solver_cpu,
            'peak_rss_kib':peak_rss_kib(),
            'limits':{'workers':1,'query_timeout_ms':1500,**enforced_limits()},
            'records':records,'consumer_records':context_records,'congruence_ablation':ablation,'errors':errors}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','consumer_records','congruence_ablation')},indent=2))
    return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
