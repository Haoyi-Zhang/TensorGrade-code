#!/usr/bin/env python3
"""Reconcile retained raw records without treating timing equality as correctness."""
from pathlib import Path
import argparse,json,collections
LETTER={'shape':'S','value':'V','zero-support':'Z','stored-support':'M','term-order':'O'}
ORDER=('shape','zero-support','value','term-order','stored-support')
def grade_name(g):return ''.join(LETTER[a] for a in ORDER if g['contracts'].get(a,{}).get('status')=='proved') or 'empty'
def summarize(root):
 p=json.loads((root/'pilot.json').read_text());d=json.loads((root/'diagnostics.json').read_text());e=json.loads((root/'execution.json').read_text());u=json.loads((root/'public-study.json').read_text());r=json.loads((root/'reference-audit.json').read_text());v=json.loads((root/'robustness-audit.json').read_text())
 if p['errors'] or d['errors'] or u['errors'] or v['errors'] or not r['passed'] or not e['all_commands_succeeded']:raise ValueError('failed evidence cannot produce success tables')
 ir=p['records']+d['records'];cs=p['consumer_records'];grade_counts=collections.Counter(grade_name(r['grade']) for r in p['records'] if r['grade'].get('complete_grade'))
 for record in ir:
  g=record['grade']
  if g['admission']=='admitted' and (not g.get('complete_grade') or g.get('mode')!='production' or set(g['contracts'])!=set(LETTER) or any(a.get('status') not in ('proved','refuted') for a in g['contracts'].values())):
   raise ValueError('incomplete semantic grade cannot produce success tables: '+str(g.get('id')))
 if any(record['grade']['admission']!='admitted' for record in d['records']):raise ValueError('nonadmitted generated case cannot produce success tables')
 if any(record['grade']['admission']=='admitted' and record['grade'].get('status') not in ('proved','refuted') for record in cs):raise ValueError('inconclusive consumer cannot produce success tables')
 certs=[q['certificate'] for r in ir for q in r.get('small_certificates',{}).values()]
 queries=[q for r in ir+cs for q in r['grade'].get('queries',[])]
 mutation=u['mutation_study']['summary'];p01=u['p01_candidate'];p08=next(x for x in u['adapter_results'] if x['adapter']=='P08')
 effects=u['p06_effects'];p06=next(x for x in u['adapter_results'] if x['adapter']=='P06')
 if effects['errors'] or p06['effect_replay_failures']:raise ValueError('failed P06 effects cannot produce success tables')
 return {'pilot_ir_cases':p['case_count'],'pilot_consumer_cases':p['consumer_count'],
  'pilot_admissions':dict(collections.Counter(r['grade']['admission'] for r in p['records'])),
  'consumer_outcomes':dict(collections.Counter(r['grade'].get('status',r['grade']['admission']) for r in cs)),
  'diagnostic_ir_cases':d['case_count'],'pilot_query_count':p['query_count'],'diagnostic_query_count':d['query_count'],
  'finite_shape_oracle_checks':p['oracle_checks']+2*d['case_count'],
  'finite_shape_oracle_obligations':p['oracle_obligations']+d['oracle_obligations'],
  'algebra_row_pairs':d['algebra_row_pairs'],'algebra_vector_evaluations':d['algebra_vector_evaluations'],
  'successful_refutation_replays':p['replay_count']+d['replay_count'],
  'small_ir_certificates':len(certs),'certificate_stored_cell_counts':dict(collections.Counter(len(x['cells']) for x in certs)),
  'consumer_refutation_replays':sum('replay' in r for r in cs),
  'realized_complete_grades':dict(grade_counts),'realized_grade_count':len(grade_counts),
  'max_query_encoding_bytes':max(q['encoding_bytes'] for q in queries),
  'max_read_occurrences_per_pair':max(r['grade'].get('terms',0) for r in ir),
  'max_congruence_pairs':max(r['grade'].get('congruence_pairs',0) for r in ir),
  'current_whole_process_cpu_seconds':e['total_process_cpu_seconds'],
  'current_peak_rss_kib':max((r['child_peak_rss_kib_upper_bound'] for r in e['runs'] if r['child_peak_rss_kib_upper_bound'] is not None),default=None),
  'current_whole_process_wall_seconds':sum(r['wall_seconds'] for r in e['runs']),
  'invalid_ablation_rejected':p['congruence_ablation']['replay']['valid'] is False,
  'public_corpus_commits':u['corpus_count'],'public_development_commits':u['development_count'],
  'public_held_out_commits':u['held_out_count'],'public_adapter_admissions':u['admitted_count'],
  'public_adapter_abstentions':u['abstained_count'],'public_adapter_coverage':u['coverage'],
  'public_development_admitted':u['development_admitted'],'public_held_out_admitted':u['held_out_admitted'],
  'public_adapter_bounded_cases':sum(x['bounded_case_count'] for x in u['adapter_results']),
  'public_adapter_bounded_mismatches':sum(x['mismatch_count'] for x in u['adapter_results']),
  'p06_single_call_effect_replays':p06['effect_replay_count'],
  'p06_additional_effect_sequences':effects['sequence_count'],
  'p06_additional_effect_calls':effects['call_count'],
  'p06_state_only_controls_rejected':sum(not x['replay']['valid'] for x in effects['state_only_controls']),
  'p01_candidate_successful_domain_cases':p01['successful_domain_case_count'],
  'p01_candidate_successful_domain_mismatches':p01['successful_domain_mismatch_count'],
  'p01_scalar_boundary_controls':p01['scalar_boundary_case_count'],
  'p01_scalar_boundary_differences':sum(not x['same'] for x in p01['scalar_boundary_controls']),
  'p08_equivalence_domain_cases':p08['bounded_case_count'],'p08_excluded_domain_controls':p08['excluded_domain_count'],
  'public_mutants':u['mutation_study']['mutant_count'],
  'public_mutation_candidate_slot_cap_per_mutant':u['mutation_study']['candidate_slot_cap_per_mutant'],
  'public_mutants_detected_developer':mutation['repeated-developer-indices']['detected'],
  'public_mutants_detected_random':mutation['seeded-random-with-replacement']['detected'],
  'public_mutants_detected_even_grid':mutation['evenly-spaced-enumeration-indices']['detected'],
  'public_mutation_actual_executions_developer':mutation['repeated-developer-indices']['actual_executions'],
  'public_mutation_actual_executions_random':mutation['seeded-random-with-replacement']['actual_executions'],
  'public_mutation_actual_executions_even_grid':mutation['evenly-spaced-enumeration-indices']['actual_executions'],
  'public_complete_source_adapters':u['admitted_count'],
  'bibliography_entries':r['bibliography_entries'],'bibliography_cited_keys':r['cited_keys'],
  'bibliography_doi_records':r['doi_records'],'bibliography_stable_url_only_records':r['stable_url_only_records'],
  'bibliography_verified_inventory_records':r['verified_inventory_records'],
  'bibliography_primary_record_checks':r['primary_record_checks'],
  'bibliography_citation_context_checks':r['citation_context_checks'],
  'bibliography_latest_inventory_check':r['latest_inventory_check'],
  'bibliography_latest_primary_record_check':r['latest_primary_record_check'],
  'bibliography_latest_citation_context_check':r['latest_citation_context_check'],
  'posthoc_robustness_seeds':len(v['seeds']),'posthoc_robustness_cases':v['case_count'],
  'posthoc_robustness_queries':v['query_count'],'posthoc_robustness_oracle_checks':v['oracle_checks'],
  'posthoc_robustness_replays':v['refutation_replays'],'posthoc_robustness_certificates':v['compact_certificates'],
  'interpretation':'Generated implementation diagnostics plus a fixed 12-commit public source-adapter study. Three commits are admitted and nine abstain. P01 successful-domain diagnostics are reported separately and are not adapter coverage. Admission is not upstream execution, workload representativeness, a comparative speed result, or a mechanized general proof.'}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,default=Path('results/current'));a.add_argument('--output',type=Path,default=Path('results/summary.json'));args=a.parse_args()
 result=summarize(args.directory);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
