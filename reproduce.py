#!/usr/bin/env python3
"""Bounded sequential reproduction with whole-process CPU and peak RSS records."""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time
from process_resources import apply_limits, child_usage, enforced_limits
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def limits():
 apply_limits()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/reproduced');args=ap.parse_args()
 out=args.output.resolve()
 if not out.is_relative_to(ROOT) or out==ROOT or out==ROOT/'results' or out==ROOT/'results/current':ap.error('use a separate output directory inside the artifact')
 if out.exists():ap.error('output already exists; use a new directory (no deletion is performed)')
 out.mkdir(parents=True)
 env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 commands=[('unit-tests',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
 ('reference-audit',[sys.executable,'audit_references.py','--output',str(out/'reference-audit.json')]),
 ('pilot',[sys.executable,'run_pilot.py','--output',str(out/'pilot.json')]),
 ('diagnostics',[sys.executable,'run_diagnostics.py','--output',str(out/'diagnostics.json')]),
 ('robustness-audit',[sys.executable,'run_robustness_audit.py','--output',str(out/'robustness-audit.json')]),
 ('public-study',[sys.executable,'run_public_study.py','--corpus','data/public-corpus.csv','--output',str(out/'public-study.json'),'--seed','20260915','--budget','64'])]
 records=[]
 for name,cmd in commands:
  before=child_usage();wall=time.perf_counter()
  options={'start_new_session':True,'preexec_fn':limits} if os.name=='posix' else {}
  p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',**options)
  timed_out=False
  try:log,_=p.communicate(timeout=115)
  except subprocess.TimeoutExpired:
   timed_out=True
   if os.name=='posix':os.killpg(p.pid,signal.SIGKILL)
   else:p.kill()
   log,_=p.communicate()
  after=child_usage()
  (out/(name+'.txt')).write_text(log,encoding='utf-8')
  rec={'name':name,'command':cmd[1:],'exit_code':p.returncode,'wall_timeout':timed_out,
   'wall_seconds':time.perf_counter()-wall,
   'process_cpu_seconds':after[0]-before[0] if after is not None else None,
   'child_peak_rss_kib_upper_bound':after[1] if after is not None else None}
  # Runtime output paths are not scientific inputs; retain relative result names.
  rec['command']=[x.replace(str(out)+'/','') for x in rec['command']]
  records.append(rec);print(json.dumps(rec),flush=True)
  if timed_out or p.returncode:break
 report={'runs':records,'total_process_cpu_seconds':sum(r['process_cpu_seconds'] for r in records) if all(r['process_cpu_seconds'] is not None for r in records) else None,
  'all_commands_succeeded':len(records)==6 and all(r['exit_code']==0 and not r['wall_timeout'] for r in records),
  'interpretation':'Command success and finite checks are not machine-checked general proofs, upstream execution, or independent review of the public adapters.',
  'total_wall_seconds':sum(r['wall_seconds'] for r in records),
  'limits':{'sequential_workers':1,'wall_seconds_per_child':115,**enforced_limits()}}
 (out/'execution.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 return not report['all_commands_succeeded']
if __name__=='__main__':raise SystemExit(main())
