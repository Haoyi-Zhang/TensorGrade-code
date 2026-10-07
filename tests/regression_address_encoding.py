"""Portable exact-encoding regressions; no native solver or historical code.

The independent address reference interprets the public affine syntax. Scripted
answers exercise control flow only, not SAT/UNSAT validity or solver performance.
snapshot() also supports private actual-before/current comparison without carrying
either implementation in this public test.
"""
import ast
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from semantic_contract import checker, ir
from semantic_contract.certificates import check_certificate
from semantic_contract.replay import evaluate
from semantic_contract.solver import Answer, SolverError


def literal_address(text):
    """Independent integer-only prefix notation for the admitted address grammar."""
    def render(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return str(node.value) if node.value >= 0 else '(- %d)' % -node.value
        if isinstance(node, ast.UnaryOp):
            value = render(node.operand)
            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.USub):
                return '(- ' + value + ')'
        if isinstance(node, ast.BinOp):
            symbols = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*'}
            if type(node.op) in symbols:
                return '(%s %s %s)' % (symbols[type(node.op)], render(node.left), render(node.right))
        raise AssertionError('address outside the test reference')
    return render(ast.parse(text, mode='eval').body)


def literal_congruences(raw):
    terms = raw['before']['terms'] + raw['after']['terms']
    result = []
    for right in range(len(terms)):
        for left in range(right):
            if terms[left]['tensor'] != terms[right]['tensor']:
                continue
            components = ['(= %s %s)' % (literal_address(x), literal_address(y))
                          for x, y in zip(terms[right]['index'], terms[left]['index'])]
            condition = ('true' if not components else components[0] if len(components) == 1
                         else '(and ' + ' '.join(components) + ')')
            result.append('(=> %s (and (= x%d x%d) (= b%d b%d)))' %
                          (condition, right, left, right, left))
    return result


def retained_cases():
    examples = [json.loads(path.read_text(encoding='utf-8'))
                for path in sorted((ROOT / 'data/examples').glob('*.json'))]
    generated = json.loads((ROOT / 'data/diagnostic-cases.json').read_text(encoding='utf-8'))
    assert len(examples) == 28 and len(generated) == 64
    return examples + generated


def boundary_cases():
    result = []
    for rank in range(5):
        shape = ['n0'] * rank
        # Deliberately include zero coefficients and inactive addresses.
        terms = [{'tensor': 'A', 'index': ['+i%d' % k if j % 2 else 'n0-1' for k in range(rank)],
                  'coefficient': str((j % 3) - 1), 'guard': 'False' if j % 4 == 0 else 'True'}
                 for j in range(32)]
        result.append({'id': 'envelope-rank-%d' % rank, 'parameters': ['n0'],
                       'inputs': {'A': shape}, 'precondition': 'n0 >= 0',
                       'before': {'shape': shape, 'terms': terms, 'storage': 'union'},
                       'after': {'shape': shape, 'terms': list(reversed(deepcopy(terms))), 'storage': 'compact'}})
    base = deepcopy(result[1])
    base['id'] = 'empty-inactive-oob'
    base['before']['shape'] = base['after']['shape'] = ['0']
    for program in (base['before'], base['after']):
        program['terms'] = [{'tensor': 'A', 'index': ['-1'], 'coefficient': '0', 'guard': 'False'}]
    result.append(base)
    base = deepcopy(result[2])
    base['id'] = 'different-input-and-coefficient'
    base['inputs']['B'] = ['n0', 'n0']
    for number, term in enumerate(base['after']['terms']):
        term['tensor'] = 'B' if number % 2 else 'A'
        term['coefficient'] = '2/3' if number % 3 else '-5/7'
        term['index'] = ['2*i0-n0+1', '(-3)*i1+4']
    result.append(base)
    return result


def encoding_record(raw, mode):
    declarations, assertions, definitions, bad, pairs = checker.encode(ir.load_case(raw), mode)
    # Lists of items preserve insertion order even through canonical JSON.
    return {'id': raw['id'], 'omit_congruence': mode, 'declarations': list(declarations.items()),
            'assertions': assertions, 'definitions': definitions, 'bad': list(bad.items()), 'pairs': pairs}


class ScriptedSolver:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    def check(self, declarations, assertions, definitions=None):
        index = len(self.calls)
        if index >= len(self.statuses):
            raise AssertionError('unexpected extra query')
        self.calls.append({'declarations': list(declarations.items()), 'assertions': list(assertions),
                           'definitions': None if definitions is None else list(definitions)})
        status = self.statuses[index]
        return Answer(status, {'n0': '1', 'i0': '0'} if status == 'sat' else {},
                      0., 0., 0, 'test-only scripted answer; no native solver')


def grading_fixtures():
    cases = {c['id']: c for c in retained_cases()}
    fixtures = []
    for name, statuses, admission in (
        ('vacuous', ['unsat'], 'vacuous'), ('unknown-precondition', ['unknown'], 'unknown'),
        ('invalid-dimension', ['sat', 'sat'], 'invalid'),
        ('unknown-dimension', ['sat', 'unknown'], 'unknown'),
        ('invalid-bounds', ['sat', 'unsat', 'sat'], 'invalid'),
        ('unknown-bounds', ['sat', 'unsat', 'unknown'], 'unknown')):
        fixtures.append((name, cases['identity'], statuses, False, admission, False))
    atoms = ('shape', 'value', 'zero-support', 'stored-support', 'term-order')
    letters = ('S', 'V', 'Z', 'M', 'O')
    for grade in ('', 'S', 'SM', 'SZ', 'SZM', 'SZV', 'SZVM', 'SZVO', 'SZVOM'):
        statuses = ['sat', 'unsat', 'unsat'] + ['unsat' if letter in grade else 'sat' for letter in letters]
        fixtures.append(('closed-' + grade, cases['identity'], statuses, False, 'admitted', True))
    for index, atom in enumerate(atoms):
        statuses = ['sat', 'unsat', 'unsat'] + ['unsat'] * 5
        statuses[3 + index] = 'unknown'
        fixtures.append(('unknown-' + atom, cases['identity'], statuses, False, 'admitted', False))
    for status in ('sat', 'unknown', 'unsat'):
        statuses = ['sat', 'unsat', 'unsat', status] + (['unsat'] * 5 if status == 'unsat' else [])
        fixtures.append(('empty-storage-' + status, cases['cancellation-to-empty'], statuses,
                         False, 'admitted' if status == 'unsat' else 'invalid' if status == 'sat' else 'unknown', status == 'unsat'))
    fixtures.append(('ablation', cases['identity'], ['sat', 'unsat', 'unsat'] + ['unsat'] * 5,
                     True, 'admitted', False))
    for identifier in ('nonaffine-index', 'alias-outside-fragment'):
        fixtures.append((identifier, cases[identifier], [], False, 'unsupported', False))
    fixtures.append(('closure-value-support', cases['identity'],
                     ['sat', 'unsat', 'unsat', 'unsat', 'unsat', 'sat', 'unsat', 'unsat'],
                     False, 'error', False))
    fixtures.append(('closure-order-value', cases['identity'],
                     ['sat', 'unsat', 'unsat', 'unsat', 'sat', 'unsat', 'unsat', 'unsat'],
                     False, 'error', False))
    return fixtures


def grading_records():
    records = []
    for name, raw, statuses, mode, admission, complete in grading_fixtures():
        solver = ScriptedSolver(statuses)
        try:
            result = checker.grade(raw, solver, mode)
        except SolverError as exc:
            result = {'error': str(exc)}
        assert len(solver.calls) == len(statuses)
        assert ('error' in result) if admission == 'error' else result['admission'] == admission
        assert bool(result.get('complete_grade')) is complete
        records.append({'name': name, 'result': result, 'calls': solver.calls})
    return records


def certificate_records():
    choices = []
    for name in ('pilot', 'diagnostics'):
        archived = json.loads((ROOT / 'results/current' / (name + '.json')).read_text(encoding='utf-8'))
        for record in archived['records']:
            for entry in record.get('small_certificates', {}).values():
                choices.append((record['case'], entry['certificate']))
    selected, keys = [], set()
    for raw, certificate in choices:
        key = (certificate['observation'], len(certificate['cells']))
        if key not in keys:
            selected.append((raw, certificate))
            keys.add(key)
    for choice in choices:
        if len(selected) >= 12:
            break
        if choice not in selected:
            selected.append(choice)
    assert len(selected) == 12
    results = [{'certificate': cert, 'result': check_certificate(raw, cert)} for raw, cert in selected]
    assert all(r['result']['valid'] for r in results)
    assert {len(cert['cells']) for _, cert in selected} == {0, 1, 2}
    raw, cert = next(choice for choice in selected if len(choice[1]['cells']) == 2)
    for name in ('identifier', 'erase-values', 'cell-cap', 'noninteger-index'):
        bad = deepcopy(cert)
        if name == 'identifier':
            bad['case_id'] = 'different-case'
        elif name == 'erase-values':
            for cell in bad['cells']:
                cell['value'] = '0'
        elif name == 'cell-cap':
            bad['cells'] *= 2
        else:
            bad['cells'][0]['index'][0] = 0.5
        result = check_certificate(raw, bad)
        assert not result['valid']
        results.append({'mutation': name, 'certificate': bad, 'result': result})
    return results


def tiny_observations():
    raw = next(c for c in retained_cases() if c['id'] == 'storage-without-support')
    records = []
    for x, y, stored_a, stored_b in product((-1, 0, 1), (-1, 0, 1), (False, True), (False, True)):
        if (x and not stored_a) or (y and not stored_b):
            continue
        cells = {('A', (0,)): (Fraction(x), stored_a), ('B', (0,)): (Fraction(y), stored_b)}
        results = []
        for program, expected in ((raw['before'], x + y), (raw['after'], x + 2*y)):
            value, stored, order = evaluate(program, {'n0': 1, 'i0': 0}, cells)
            assert value == expected and stored == (stored_a or stored_b)
            results.append({'value': str(value), 'stored': stored,
                            'order': [[key[0], list(key[1]), str(coefficient)] for key, coefficient in order]})
        records.append({'input': [x, y, stored_a, stored_b], 'observations': results})
    return records


def snapshot():
    encodings, rejected = [], []
    for raw in retained_cases() + boundary_cases():
        try:
            ir.load_case(raw)
        except ir.Unsupported as exc:
            rejected.append({'id': raw['id'], 'reason': str(exc)})
            continue
        for mode in (False, True):
            encodings.append(encoding_record(raw, mode))
    caps = []
    base = deepcopy(boundary_cases()[4])
    for field in ('terms', 'rank'):
        bad = deepcopy(base)
        if field == 'terms':
            bad['before']['terms'].append(deepcopy(bad['before']['terms'][0]))
        else:
            bad['before']['shape'].append('n0')
        try:
            ir.load_case(bad)
        except ir.Unsupported as exc:
            caps.append({'field': field, 'reason': str(exc)})
        else:
            raise AssertionError('encoding cap accepted')
    return {'encodings': encodings, 'rejected': rejected, 'caps': caps,
            'grades': grading_records(), 'certificates': certificate_records(), 'tiny': tiny_observations()}


class AddressEncodingTest(unittest.TestCase):
    def test_independent_addresses_and_once_per_occurrence(self):
        for raw in retained_cases() + boundary_cases():
            try:
                case = ir.load_case(raw)
            except ir.Unsupported:
                continue
            expected = literal_congruences(raw)
            for mode in (False, True):
                record = encoding_record(raw, mode)
                count = len(case.before.terms) + len(case.after.terms)
                self.assertEqual(record['assertions'][count:], [] if mode else expected)
                self.assertEqual(record['pairs'], 0 if mode else len(expected))
        case = ir.load_case(boundary_cases()[4])
        targets = {id(x): 0 for t in case.before.terms + case.after.terms for x in t.index}
        original = ir.Expr.smt
        def counted(expr):
            if id(expr) in targets:
                targets[id(expr)] += 1
            return original(expr)
        with patch.object(ir.Expr, 'smt', counted):
            checker.encode(case)
        self.assertEqual(len(targets), 256)
        self.assertEqual(set(targets.values()), {1})
        scalar = encoding_record(boundary_cases()[0], False)
        self.assertEqual(scalar['pairs'], 2016)
        self.assertIn('(=> (and g0 g63 (= ppos0 qpos31)) true)', dict(scalar['bad'])['term-order'])
        inactive = encoding_record(boundary_cases()[5], False)
        # Inactive zero-coefficient occurrences still appear in potential order.
        self.assertIn('(=> (and g0 g1 (= ppos0 qpos0)) (= (- 1) (- 1)))',
                      dict(inactive['bad'])['term-order'])
        self.assertIn('(define-fun vp () Real (ite g0 (* 0 x0) 0))', inactive['definitions'])

    def test_admission_queries_and_complete_grade_controls(self):
        records = grading_records()
        self.assertEqual(len(records), 28)
        self.assertEqual(next(r for r in records if r['name'] == 'ablation')['result']['congruence_pairs'], 0)
        self.assertTrue(all(not r['result'].get('complete_grade') for r in records if r['name'].startswith('unknown-')))

    def test_tiny_observations_certificates_and_encoding_caps(self):
        record = snapshot()
        self.assertEqual(len(record['encodings']), 194)
        self.assertEqual(len(record['rejected']), 2)
        self.assertEqual(len(record['caps']), 2)
        self.assertEqual(len(record['certificates']), 16)
        self.assertEqual(len(record['tiny']), 16)


if __name__ == '__main__':
    unittest.main()
