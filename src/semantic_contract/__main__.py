"""Bounded command-line grading and solver-free certificate replay."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
try:
 import resource
except ImportError:
 resource=None

def load(path):
 if path.stat().st_size>1024*1024:raise ValueError('input exceeds 1 MiB CLI limit')
 return json.loads(path.read_text())

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
 for name in ('grade','consumer','replay'):
  q=sub.add_parser(name);q.add_argument('input',type=Path);q.add_argument('--output',type=Path)
  if name=='replay':q.add_argument('certificate',type=Path)
  else:q.add_argument('--timeout-ms',type=int,default=1500)
 args=p.parse_args()
 try:
  if resource is not None:
   resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(105,110))
  if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  raw=load(args.input)
  if args.action=='replay':
   from .certificates import check_certificate
   result=check_certificate(raw,load(args.certificate));code=0 if result['valid'] else 3
  else:
   from .solver import Solver
   from .checker import grade
   from .coherence import check_coherence
   with Solver(args.timeout_ms) as solver:result=(grade if args.action=='grade' else check_coherence)(raw,solver)
   decided=result.get('complete_grade') if args.action=='grade' else result.get('status') in ('proved','refuted')
   code=0 if result['admission']=='admitted' and decided else 2
  text=json.dumps(result,indent=2,sort_keys=True)+'\n'
  if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
  else:print(text,end='')
  return code
 except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError) as e:
  print(f'Input/runtime error: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
