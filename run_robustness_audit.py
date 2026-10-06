#!/usr/bin/env python3
"""Post-hoc multi-seed robustness audit for the generated finite-read campaign.

This audit is deliberately separate from the frozen 64-case paper campaign and
its 801 retained queries. It checks whether the same checker/oracle/replay
relationships survive several additional generator seeds; it is not a statistical
generalization claim or an independent implementation.
"""
from __future__ import annotations
import argparse,json,os,sys,time
from process_resources import apply_limits, peak_rss_kib, enforced_limits
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
apply_limits()
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
if hasattr(os,'sched_getaffinity'): os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
from semantic_contract.cases import generated_cases
from semantic_contract.solver import Solver
from semantic_contract.checker import grade
from semantic_contract.oracle import concrete_shape_oracle
from semantic_contract.replay import replay
from semantic_contract.certificates import small_certificate,check_certificate

DEFAULT_SEEDS=(7,19,43,101,2026,4099,8191,16381)
LETTER={'shape':'S','value':'V','zero-support':'Z','stored-support':'M','term-order':'O'}
ORDER=('shape','zero-support','value','term-order','stored-support')
def grade_name(g): return ''.join(LETTER[a] for a in ORDER if g['contracts'].get(a,{}).get('status')=='proved') or 'empty'

def main()->bool:
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=ROOT/'results/robustness-audit.json')
    ap.add_argument('--cases-per-seed',type=int,default=32)
    ap.add_argument('--seeds',type=int,nargs='*',default=list(DEFAULT_SEEDS))
    args=ap.parse_args()
    if not 1<=args.cases_per_seed<=64: raise ValueError('cases-per-seed must be 1..64')
    if not args.seeds or len(set(args.seeds))!=len(args.seeds): raise ValueError('unique nonempty seeds required')
    start=time.process_time(); wall=time.perf_counter(); errors=[]; per_seed=[]
    total_queries=total_replays=total_certs=total_oracles=total_obligations=0
    grades=Counter()
    with Solver(1500) as solver:
        q0=solver.queries
        for seed in args.seeds:
            records=[]; seed_replays=seed_certs=seed_oracles=seed_obligations=0
            for case in generated_cases(args.cases_per_seed,seed):
                result=grade(case,solver)
                if result['admission']!='admitted':
                    errors.append(f"seed {seed} {case['id']}: {result['admission']}")
                    continue
                if not result.get('complete_grade'):
                    errors.append(f"seed {seed} {case['id']}: incomplete semantic grade")
                    continue
                grades[grade_name(result)]+=1
                for n in (1,2):
                    oracle=concrete_shape_oracle(case,{'n0':n})
                    seed_oracles+=1; seed_obligations+=oracle.get('obligations',0)
                    if oracle['status']!='checked':
                        errors.append(f"seed {seed} {case['id']}: oracle unavailable")
                    for atom,holds in oracle.get('contracts',{}).items():
                        if not holds and result['contracts'][atom]['status']=='proved':
                            errors.append(f"seed {seed} {case['id']}: oracle contradiction {atom}")
                for atom,atom_result in result['contracts'].items():
                    if atom_result['status']!='refuted': continue
                    rr=replay(case,atom,atom_result['witness']); seed_replays+=1
                    cert=small_certificate(case,atom,atom_result['witness'])
                    cr=check_certificate(case,cert); seed_certs+=1
                    if not rr['valid'] or not cr['valid']:
                        errors.append(f"seed {seed} {case['id']}: invalid replay {atom}")
                records.append({'id':case['id'],'grade':grade_name(result)})
            per_seed.append({'seed':seed,'case_count':len(records),'replays':seed_replays,
                'certificates':seed_certs,'oracle_checks':seed_oracles,
                'oracle_obligations':seed_obligations})
            total_replays+=seed_replays; total_certs+=seed_certs
            total_oracles+=seed_oracles; total_obligations+=seed_obligations
        total_queries=solver.queries-q0
    report={'study':'post-hoc multi-seed robustness audit; excluded from frozen paper counts',
        'seeds':list(args.seeds),'cases_per_seed':args.cases_per_seed,
        'case_count':len(args.seeds)*args.cases_per_seed,'query_count':total_queries,
        'oracle_checks':total_oracles,'oracle_obligations':total_obligations,
        'refutation_replays':total_replays,'compact_certificates':total_certs,
        'realized_grades':dict(sorted(grades.items())),'per_seed':per_seed,
        'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
        'peak_rss_kib':peak_rss_kib(),
        'limits':enforced_limits(),
        'errors':errors,
        'interpretation':'Sensitivity check against one fixed generator seed. Same code paths and finite n=1,2 oracle are reused; this is not independent validation or population-level evidence.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('per_seed',)},indent=2))
    return bool(errors)
if __name__=='__main__': raise SystemExit(main())
