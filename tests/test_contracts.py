"""Executable finite checks; the general arguments are in proofs/core.md."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
from copy import deepcopy
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from semantic_contract.ir import expression,Unsupported,load_case
from semantic_contract.solver import Solver,Answer,sexprs,scalar,SolverError
from semantic_contract.checker import grade,ATOMS
from semantic_contract.replay import replay
from semantic_contract.certificates import small_certificate,check_certificate
from semantic_contract.cases import pilot_cases,consumer_cases,generated_cases
from semantic_contract.coherence import check_coherence,replay_coherence
from semantic_contract.oracle import same_kernel

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.solver=Solver(1500);cls.cases={c['id']:c for c in pilot_cases()}
 @classmethod
 def tearDownClass(cls):cls.solver.close()
 def test_affine_grammar(self):
  e=expression('2*n0-i0+3',{'n0','i0'});self.assertEqual(e.concrete({'n0':4,'i0':2}),9)
  for text in ('n0*i0','n0//2','f(n0)','n0[0]','n0**2'):
   with self.assertRaises(Unsupported):expression(text,{'n0','i0'})
 def test_boolean_sort(self):
  with self.assertRaises(Unsupported):expression('n0+1',{'n0'},True)
  self.assertTrue(expression('n0>=1 and n0<4',{'n0'},True).concrete({'n0':2}))
 def test_rational_parser(self):
  self.assertEqual(scalar(sexprs('(/ (- 5) 7)')[0]),Fraction(-5,7))
  for t in ('(',')'):
   with self.assertRaises(SolverError):sexprs(t)
 def test_solver_sat_unsat(self):
  self.assertEqual(self.solver.check({'x':'Real'},['(= x (/ 1 3))']).values['x'],'1/3')
  self.assertEqual(self.solver.check({'x':'Int'},['(> x 0)','(< x 0)']).status,'unsat')
 def test_all_nine_closed_grades(self):
  got=set()
  for c in self.cases.values():
   g=grade(c,self.solver)
   if g.get('complete_grade'):
    G=frozenset(a for a,r in g['contracts'].items() if r['status']=='proved');got.add(G)
    if 'term-order' in G:self.assertIn('value',G)
    if 'value' in G:self.assertIn('zero-support',G)
    if G:self.assertIn('shape',G)
  self.assertEqual(len(got),9)
 def test_admission_not_a_grade(self):
  for name in ('active-read-oob','negative-dimension','unstored-nonzero','empty-precondition','nonaffine-index','alias-outside-fragment'):
   g=grade(self.cases[name],self.solver);self.assertNotEqual(g['admission'],'admitted');self.assertFalse(g['contracts'])
 def test_empty_sum_real_sort_regression(self):
  g=grade(self.cases['zero-output-storage'],self.solver)
  self.assertEqual(g['contracts']['value']['status'],'proved')
  self.assertEqual(g['contracts']['stored-support']['status'],'refuted')
 def test_congruence_negative_control(self):
  c=self.cases['shape-collision'];g=grade(c,self.solver,True)
  self.assertFalse(g['complete_grade']);self.assertEqual(g['contracts']['value']['status'],'refuted')
  self.assertFalse(replay(c,'value',g['contracts']['value']['witness'])['valid'])
 def test_unknown_never_becomes_complete(self):
  class Unknown:
   def check(self,*_a,**_k):return Answer('unknown',{},0.,0.,0,'deliberate unit-test injection')
  self.assertEqual(grade(self.cases['identity'],Unknown())['admission'],'unknown')
 def test_late_shape_witness(self):
  c=self.cases['late-shape-threshold'];g=grade(c,self.solver);w=g['contracts']['value']['witness']
  self.assertGreater(int(w['n0']),32);self.assertTrue(replay(c,'value',w)['valid'])
 def test_sparse_certificates_and_tampering(self):
  c=self.cases['storage-without-support'];g=grade(c,self.solver);cert=small_certificate(c,'zero-support',g['contracts']['zero-support']['witness'])
  self.assertLessEqual(len(cert['cells']),2);self.assertTrue(check_certificate(c,cert)['valid'])
  bad=deepcopy(cert);bad['case_id']='wrong';self.assertFalse(check_certificate(c,bad)['valid'])
  bad=deepcopy(cert)
  for v in bad['cells']:v['value']='0'
  self.assertFalse(check_certificate(c,bad)['valid'])
  bad=deepcopy(cert);bad['cells'][0]['index']=[0.5];self.assertFalse(check_certificate(c,bad)['valid'])
  bad=deepcopy(cert);bad['cells']*=3;self.assertFalse(check_certificate(c,bad)['valid'])
 def test_explicit_stored_zero_is_needed(self):
  c=self.cases['stored-zero-elimination'];g=grade(c,self.solver);cert=small_certificate(c,'stored-support',g['contracts']['stored-support']['witness'])
  self.assertEqual(len(cert['cells']),1);self.assertEqual(Fraction(cert['cells'][0]['value']),0)
 def test_consumer_oracles(self):
  for c in consumer_cases():
   g=check_coherence(c,self.solver);got=g.get('status') if g['admission']=='admitted' else g['admission']
   self.assertEqual(got,c['expected'])
   if got=='refuted':self.assertTrue(replay_coherence(c,g['witness'])['valid'])
 def test_consumer_input_errors(self):
  for raw in (None,[],42):self.assertEqual(check_coherence(raw,self.solver)['admission'],'unsupported')
  c=deepcopy(consumer_cases()[0]);c['scales'][0]['coefficient']=1.5
  self.assertEqual(check_coherence(c,self.solver)['admission'],'unsupported')
 def test_correlated_image_counterexample(self):
  # On the image (t,t), sum gives 2t before and 3t after. Free-image necessity
  # must not be generalized to arbitrary producer ranges.
  for t in (Fraction(-7,3),Fraction(0),Fraction(11,5)):
   self.assertEqual(2*t==0,3*t==0)
  self.assertFalse(same_kernel({0:1,1:1},{0:1,1:2}))
 def test_retained_inputs_match_generator(self):
  self.assertEqual(json.loads((ROOT/'data/diagnostic-cases.json').read_text()),generated_cases(64,1729))
  for c in self.cases.values():self.assertEqual(json.loads((ROOT/'data/examples'/f"{c['id']}.json").read_text()),c)
if __name__=='__main__':unittest.main()
