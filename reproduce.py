#!/usr/bin/env python3
"""Bounded sequential reproduction with whole-process CPU and peak RSS records."""
from __future__ import annotations
import argparse,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU,(105,110))
 if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/reproduced');args=ap.parse_args()
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 commands=[('unit-tests',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
 ('reference-audit',[sys.executable,'audit_references.py','--output',str(out/'reference-audit.json')]),
 ('pilot',[sys.executable,'run_pilot.py','--output',str(out/'pilot.json')]),
 ('diagnostics',[sys.executable,'run_diagnostics.py','--output',str(out/'diagnostics.json')]),
 ('robustness-audit',[sys.executable,'run_robustness_audit.py','--output',str(out/'robustness-audit.json')]),
 ('public-study',[sys.executable,'run_public_study.py','--corpus','data/public-corpus.csv','--output',str(out/'public-study.json'),'--seed','20260915','--budget','64'])]
 records=[]
 for name,cmd in commands:
  before=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.perf_counter()
  p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True,preexec_fn=limits)
  timed_out=False
  try:log,_=p.communicate(timeout=115)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(p.pid,signal.SIGKILL);log,_=p.communicate()
  after=resource.getrusage(resource.RUSAGE_CHILDREN)
  (out/(name+'.txt')).write_text(log)
  rec={'name':name,'command':cmd[1:],'exit_code':p.returncode,'wall_timeout':timed_out,
   'wall_seconds':time.perf_counter()-wall,
   'process_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
   'child_peak_rss_kib_upper_bound':after.ru_maxrss}
  # Runtime output paths are not scientific inputs; retain relative result names.
  rec['command']=[x.replace(str(out)+'/','') for x in rec['command']]
  records.append(rec);print(json.dumps(rec),flush=True)
  if timed_out or p.returncode:break
 report={'runs':records,'total_process_cpu_seconds':sum(r['process_cpu_seconds'] for r in records),
  'all_commands_succeeded':len(records)==6 and all(r['exit_code']==0 and not r['wall_timeout'] for r in records),
  'interpretation':'Command success and finite checks are not machine-checked general proofs, upstream execution, or independent review of the public adapters.',
  'limits':{'sequential_workers':1,'address_space_bytes':2*1024**3,'wall_seconds_per_child':115,'cpu_soft_seconds':105,'cpu_hard_seconds':110}}
 (out/'execution.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 return not report['all_commands_succeeded']
if __name__=='__main__':raise SystemExit(main())
