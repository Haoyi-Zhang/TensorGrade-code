#!/usr/bin/env python3
"""Frozen generated diagnostics and an exhaustive finite rational-kernel probe."""
from __future__ import annotations
import argparse,json,os,sys,time
from process_resources import apply_limits, peak_rss_kib, enforced_limits
from pathlib import Path
from itertools import product
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
apply_limits()
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
from semantic_contract.solver import Solver
from semantic_contract.checker import grade
from semantic_contract.replay import replay
from semantic_contract.oracle import concrete_shape_oracle,same_kernel
from semantic_contract.certificates import small_certificate,check_certificate

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/diagnostics.json');args=ap.parse_args()
 start=time.process_time();wall=time.perf_counter();errors=[];records=[];oracle_obligations=0;replays=0
 cases=json.loads((ROOT/'data/diagnostic-cases.json').read_text())
 if len(cases)!=64:raise ValueError('frozen diagnostic input count')
 with Solver(1500) as solver:
  for c in cases:
   g=grade(c,solver);rec={'case':c,'grade':g,'oracles':[],'replays':{},'small_certificates':{}}
   if g['admission']!='admitted':errors.append(c['id']+': generated case not admitted')
   else:
    if not g.get('complete_grade'):errors.append(c['id']+': incomplete semantic grade')
    for atom,r in g['contracts'].items():
     if r['status']=='refuted':
      rr=replay(c,atom,r['witness']);rec['replays'][atom]=rr;replays+=1
      cert=small_certificate(c,atom,r['witness']);cr=check_certificate(c,cert)
      rec['small_certificates'][atom]={'certificate':cert,'replay':cr}
      if not rr['valid'] or not cr['valid']:errors.append(c['id']+': refutation replay')
    for n in (1,2):
     o=concrete_shape_oracle(c,{'n0':n});rec['oracles'].append({'n0':n,**o});oracle_obligations+=o['obligations']
     if o['status']!='checked':errors.append(c['id']+': small oracle unavailable')
     for atom,holds in o.get('contracts',{}).items():
      if not holds and g['contracts'][atom]['status']=='proved':errors.append(c['id']+': oracle contradiction '+atom)
   records.append(rec)
  queries=solver.queries;solver_cpu=solver.total_cpu
 # Independent direct integer evaluation. No SMT, array encoding, or certificate
 # constructor is used to enumerate the exact truth table of this finite grid.
 rows=list(product((-1,0,1),repeat=3));vectors=rows;algebra=[];vectors_evaluated=0
 for a in rows:
  for b in rows:
   same=True;first=None
   for x in vectors:
    ax=sum(p*q for p,q in zip(a,x));bx=sum(p*q for p,q in zip(b,x));vectors_evaluated+=1
    if (ax==0)!=(bx==0):same=False;first=first or x
   criterion=same_kernel(dict(enumerate(a)),dict(enumerate(b)))
   if bool(criterion)!=same:errors.append('finite kernel disagreement')
   algebra.append({'a':a,'b':b,'same_kernel':same,'first_discriminating_vector':first})
 report={'study':'generated diagnostics and finite algebra checks; not a public patch evaluation',
  'case_count':len(cases),'query_count':queries,'oracle_obligations':oracle_obligations,
  'replay_count':replays,'algebra_row_pairs':len(algebra),'algebra_vector_evaluations':vectors_evaluated,
  'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
  'solver_cpu_seconds':solver_cpu,'peak_rss_kib':peak_rss_kib(),
  'limits':enforced_limits(),
  'records':records,'algebra_records':algebra,'errors':errors}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('records','algebra_records')},indent=2))
 return bool(errors)
if __name__=='__main__':raise SystemExit(main())
