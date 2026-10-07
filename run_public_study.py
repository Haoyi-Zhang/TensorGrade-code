#!/usr/bin/env python3
"""Run the frozen dependency-free public-source adapter study."""
from __future__ import annotations
import argparse,csv,json,os,sys,time
from process_resources import apply_limits, peak_rss_kib, enforced_limits
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
apply_limits()
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
from semantic_contract.public_adapters import ADAPTERS,SOURCE_PINS,verify_adapter,verify_p01_candidate,verify_p06_effects,mutation_study

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/public-study.json');ap.add_argument('--corpus',type=Path,default=ROOT/'data/public-corpus.csv');ap.add_argument('--budget',type=int,default=64);ap.add_argument('--seed',type=int,default=20260915);args=ap.parse_args()
 start=time.process_time();wall=time.perf_counter()
 corpus_path=args.corpus if args.corpus.is_absolute() else ROOT/args.corpus
 corpus=list(csv.DictReader(corpus_path.open()))
 evidence=json.loads((ROOT/'data/public-adapter-evidence.json').read_text())
 adapter_results=[verify_adapter(a) for a in ADAPTERS]
 p01_candidate=verify_p01_candidate()
 p06_effects=verify_p06_effects()
 mutations=mutation_study(candidate_slot_cap=args.budget,seed=args.seed)
 errors=[]
 if any(x['mismatch_count'] for x in adapter_results):errors.append('adapter mismatch')
 if p06_effects['errors']:errors.append('P06 multi-call effects mismatch')
 p06=next(x for x in adapter_results if x['adapter']=='P06')
 if p06['effect_replay_failures']:errors.append('P06 single-call effect replay mismatch')
 admitted=[x for x in corpus if x['decision']=='admitted']
 if sorted(x['adapter_id'] for x in admitted)!=sorted(ADAPTERS):errors.append('corpus/adapter mismatch')
 if next(x for x in corpus if x['id']=='P01')['decision']!='abstained':errors.append('P01 admission repair missing')
 for adapter_id in ('P01','P04','P06','P08'):
  record=evidence['records'][adapter_id]
  pin=SOURCE_PINS[adapter_id]
  if (record['parent_commit']!=pin['parent'] or record['parent_tree_sha']!=pin['parent_tree']
      or record['child_commit']!=pin['child'] or record['child_tree_sha']!=pin['child_tree']
      or record['decision']!=pin['decision']):
   errors.append(f'{adapter_id} source-pin mismatch')
 if p01_candidate['successful_domain_mismatch_count']!=0:errors.append('P01 successful-domain diagnostic mismatch')
 if sum(not row['same'] for row in p01_candidate['scalar_boundary_controls'])!=3:errors.append('P01 boundary controls changed')
 p08=next(x for x in adapter_results if x['adapter']=='P08')
 if p08.get('excluded_domain_count')!=4 or any(x['same'] for x in p08.get('excluded_domain_controls',[])):
  errors.append('P08 excluded controls changed')
 p08_evidence=evidence['records']['P08']['fixed_production_callsite_invariant']
 if p08_evidence['inventory_summary']['direct_tensorvar_call_expressions']!=20:
  errors.append('P08 fixed-production call-site inventory changed')
 if evidence['records']['P04']['bounded_validation']['states']!=30:
  errors.append('P04 coverage-map state count changed')
 if evidence['records']['P06']['bounded_validation']['label_only_comparison_used']:
  errors.append('P06 reverted to label-only comparison')
 report={
  'study':'frozen public-source adapter coverage and synthetic negative controls',
  'repository':'bobbyyyan/scorch','corpus_count':len(corpus),
  'development_count':sum(x['split']=='development' for x in corpus),
  'held_out_count':sum(x['split']=='held-out' for x in corpus),
  'admitted_count':len(admitted),'abstained_count':sum(x['decision']=='abstained' for x in corpus),
  'coverage':len(admitted)/len(corpus),
  'development_admitted':sum(x['split']=='development' and x['decision']=='admitted' for x in corpus),
  'held_out_admitted':sum(x['split']=='held-out' and x['decision']=='admitted' for x in corpus),
  'corpus':corpus,'adapter_results':adapter_results,'p01_candidate':p01_candidate,'p06_effects':p06_effects,
  'source_evidence':'data/public-adapter-evidence.json','mutation_study':mutations,
  'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
  'peak_rss_kib':peak_rss_kib(),'limits':enforced_limits(),'errors':errors,
  'interpretation':('Admitted means every production hunk was dispositioned and a source-derived invariant, '
   'independent before/after model, universal argument, and unchanged-downstream congruence were retained. '
   'P01 is an abstained candidate: its 1--4 operand range is only a finite validation boundary. '
   'P06 compares ordered post maps as well as full LLIR nodes; 400 single-call effect replays and '
   'eight multi-call sequences totaling 22 calls are checked independently. '
   'P08 has 96 equivalence-domain cases and four separately executed excluded-domain controls. '
   'The study does not execute upstream Scorch or constitute independent proof review. Mutants are synthetic controls.')}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('corpus','adapter_results','p01_candidate','p06_effects','mutation_study')},indent=2))
 return bool(errors)
if __name__=='__main__':raise SystemExit(main())
