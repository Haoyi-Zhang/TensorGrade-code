"""P06 multi-call source-map regressions; no symbolic backend is needed."""
from copy import deepcopy
from dataclasses import replace
import inspect
import unittest

from semantic_contract import dense_effects
from semantic_contract.certificates import source_effect_certificate, check_source_effect_certificate
from semantic_contract.public_adapters import (
    CoordState, CoordSequence, DenseIteratorState, PendingCoordinate, Literal,
    Var, VarInit, Cast, Comment, Blank, IteratorState, coord_before, coord_after,
    coord_mutant, coord_sequence, p06_effect_cases, verify_p06_effects,
)
from semantic_contract.replay import ReplayError, replay_source_effects


def names(entries):
    return tuple(e.statement.var.name for e in entries)


class DenseEffectsTest(unittest.TestCase):
    def test_all_sequences_compare_and_replay_full_effects(self):
        report = verify_p06_effects()
        self.assertEqual(report['sequence_count'], 8)
        self.assertEqual(report['call_count'], 22)
        self.assertEqual(report['errors'], [])
        for sequence in p06_effect_cases():
            original = deepcopy(sequence)
            parent = coord_sequence(sequence, coord_before)
            child = coord_sequence(sequence, coord_after)
            self.assertEqual(parent, child)
            self.assertEqual(sequence, original)  # input flags/trees/deps unchanged
            cert = source_effect_certificate(sequence, parent)
            self.assertTrue(check_source_effect_certificate(sequence, cert)['valid'])
            self.assertTrue(replay_source_effects(cert)['valid'])

    def test_ready_removal_and_retained_order(self):
        sequence = p06_effect_cases()[0]
        results = coord_sequence(sequence)
        self.assertEqual(results[0].dense.retained, (False, True, False))
        self.assertEqual(names(results[0].pending), ('b',))
        self.assertEqual(tuple(n.var.name for n in results[0].dense.emitted[1:]), ('a', 'c'))
        self.assertEqual(results[1].pending, ())
        self.assertEqual(results[2].dense.emitted, ())
        results = coord_sequence(p06_effect_cases()[6])
        self.assertEqual(names(results[0].dense.snapshot), ('b', 'a', 'c', 'd'))
        self.assertEqual(names(results[0].pending), ('b', 'd'))
        self.assertEqual(names(results[1].pending), ('d',))

    def test_name_dedup_keeps_original_expression_and_dependencies(self):
        results = coord_sequence(p06_effect_cases()[1])
        self.assertEqual(results[0].dense.inserted, (True, False))
        self.assertEqual(results[0].pending[0].statement.value, Literal('1'))
        self.assertEqual(results[0].pending[0].dependencies, ('j',))
        self.assertEqual(results[1].pending, ())
        self.assertEqual(results[2].dense.emitted[1].value, Literal('2'))
        ready_old = coord_sequence(p06_effect_cases()[2])
        self.assertEqual(ready_old[0].dense.inserted, (False,))
        self.assertEqual(ready_old[0].dense.emitted[1].value, Literal('1'))
        self.assertEqual(ready_old[1].dense.inserted, (True,))
        unready_old = coord_sequence(p06_effect_cases()[3])
        self.assertEqual(unready_old[0].dense.inserted, (False,))
        self.assertEqual(unready_old[0].dense.emitted, ())
        self.assertEqual(unready_old[1].pending, unready_old[0].pending)
        self.assertEqual(unready_old[2].pending, ())

    def test_absent_value_is_skipped_but_literal_zero_is_present(self):
        first = coord_sequence(p06_effect_cases()[4])[0]
        self.assertEqual(first.dense.inserted, (None, True))
        self.assertEqual(first.dense.emitted[1].var.name, 'zero')
        self.assertEqual(first.dense.emitted[1].value, Literal('0'))

    def test_emission_does_not_define_dependency_names(self):
        results = coord_sequence(p06_effect_cases()[5])
        self.assertEqual(names(results[0].pending), ('b',))
        self.assertEqual(results[1].dense.emitted, ())
        self.assertEqual(results[2].pending, ())

    def test_equal_output_does_not_imply_equal_post_map(self):
        sequence = p06_effect_cases()[7]
        baseline = coord_sequence(sequence)[0]
        reordered = coord_after(replace(sequence.calls[0], pending=tuple(reversed(sequence.initial_pending))))
        empty = coord_after(sequence.calls[0])
        self.assertEqual(baseline.nodes, reordered.nodes)
        self.assertEqual(baseline.nodes, empty.nodes)
        self.assertNotEqual(baseline.pending, reordered.pending)
        self.assertNotEqual(baseline.pending, empty.pending)
        cert = source_effect_certificate(sequence, coord_sequence(sequence))
        for post in ([], list(reversed(cert['calls'][0]['post']))):
            bad = deepcopy(cert)
            bad['calls'][0]['post'] = post
            self.assertEqual(bad['calls'][0]['emitted'], cert['calls'][0]['emitted'])
            self.assertFalse(check_source_effect_certificate(sequence, bad)['valid'])

    def test_retaining_ready_entries_fails_replay_without_changing_output(self):
        sequence = p06_effect_cases()[0]
        cert = source_effect_certificate(sequence, coord_sequence(sequence))
        bad = deepcopy(cert)
        bad['calls'][0]['post'] = bad['calls'][0]['snapshot']
        self.assertEqual(bad['calls'][0]['emitted'], cert['calls'][0]['emitted'])
        self.assertFalse(check_source_effect_certificate(sequence, bad)['valid'])

    def test_certificate_binding_links_and_flags_are_checked(self):
        sequence = p06_effect_cases()[1]
        cert = source_effect_certificate(sequence, coord_sequence(sequence))
        changes = [('case_id', 'other'), ('calls', [])]
        for key, value in changes:
            bad = deepcopy(cert); bad[key] = value
            self.assertFalse(check_source_effect_certificate(sequence, bad)['valid'])
        for field, value in [('pre', []), ('defined', ['other']), ('retained', [1]), ('inserted', [1, 0])]:
            bad = deepcopy(cert); bad['calls'][1 if field == 'pre' else 0][field] = value
            self.assertFalse(check_source_effect_certificate(sequence, bad)['valid'])
        bad = deepcopy(cert); bad['calls'][0]['offered'][0]['value']['fields']['value'] = '99'
        self.assertFalse(check_source_effect_certificate(sequence, bad)['valid'])

    def test_reference_does_not_call_changed_implementations(self):
        source = inspect.getsource(dense_effects)
        self.assertNotIn('import public_adapters', source)
        self.assertNotIn('coord_before(', source)
        self.assertNotIn('coord_after(', source)

    def test_supplied_full_expression_and_variable_flags_survive(self):
        var = Var('custom', 'int*', True)
        declaration = VarInit(var, Cast(var.typ, Literal('0')), '=', True)
        pending = (PendingCoordinate(declaration, ('i', 'i')),)
        call = CoordState((), False, False, False, False, (), ('i',))
        sequence = CoordSequence('supplied-flags', pending, (call,))
        parent = coord_sequence(sequence, coord_before)
        self.assertEqual(parent, coord_sequence(sequence, coord_after))
        self.assertEqual(parent[0].dense.emitted[1], declaration)
        self.assertTrue(check_source_effect_certificate(sequence, source_effect_certificate(sequence, parent))['valid'])


class SourceEffectBindingTest(unittest.TestCase):
    def setUp(self):
        self.entry = PendingCoordinate(VarInit(Var('a'), Literal('1')), ('j',))
        self.call = CoordState((), False, False, False, False)
        self.sequence = CoordSequence('independent-binding', (self.entry,), (self.call,))

    def test_final_export_only_mutation_is_rejected(self):
        good = coord_sequence(self.sequence)
        cert = source_effect_certificate(self.sequence, good)
        checked = check_source_effect_certificate(self.sequence, cert)
        self.assertTrue(checked['valid'])
        self.assertEqual(checked['remaining_entries'], 1)
        wrong = (replace(good[0], pending=()),)
        self.assertEqual(wrong[0].nodes, good[0].nodes)
        self.assertEqual(wrong[0].dense, good[0].dense)
        later = replace(self.call, defined_index_vars=('j',))
        self.assertNotEqual(
            coord_after(replace(later, pending=good[0].pending)).nodes,
            coord_after(replace(later, pending=wrong[0].pending)).nodes,
        )
        with self.assertRaisesRegex(ReplayError, 'call 0: source exported pending binding'):
            source_effect_certificate(self.sequence, wrong)

    def test_supplied_step_export_only_mutation_is_rejected(self):
        def wrong_step(state):
            return replace(coord_after(state), pending=())

        for calls in ((self.call,), (self.call, replace(self.call, defined_index_vars=('j',)))):
            with self.subTest(call_count=len(calls)):
                sequence = replace(self.sequence, calls=calls)
                wrong = coord_sequence(sequence, wrong_step)
                self.assertEqual(wrong[0].pending, ())
                self.assertEqual(wrong[0].dense.post, (self.entry,))
                with self.assertRaisesRegex(ReplayError, 'call 0: source exported pending binding'):
                    source_effect_certificate(sequence, wrong)

    def test_only_last_export_in_multicall_sequence_is_bound(self):
        sequence = replace(self.sequence, calls=(self.call,) * 3)
        good = coord_sequence(sequence)
        wrong = (*good[:-1], replace(good[-1], pending=()))
        self.assertEqual(wrong[:-1], good[:-1])
        self.assertEqual(wrong[-1].nodes, good[-1].nodes)
        self.assertEqual(wrong[-1].dense, good[-1].dense)
        with self.assertRaisesRegex(ReplayError, 'call 2: source exported pending binding'):
            source_effect_certificate(sequence, wrong)

    def test_exported_pending_order_and_payload_are_bound(self):
        second = PendingCoordinate(VarInit(Var('b'), Literal('2')), ('k',))
        sequence = replace(self.sequence, initial_pending=(self.entry, second))
        good = coord_sequence(sequence)
        mutations = (
            (second, self.entry),
            (replace(self.entry, dependencies=('k',)), second),
            (replace(self.entry, statement=replace(self.entry.statement, value=Literal('2'))), second),
        )
        for pending in mutations:
            with self.subTest(pending=pending):
                wrong = (replace(good[0], pending=pending),)
                self.assertEqual(wrong[0].nodes, good[0].nodes)
                self.assertEqual(wrong[0].dense, good[0].dense)
                with self.assertRaisesRegex(ReplayError, 'source exported pending binding'):
                    source_effect_certificate(sequence, wrong)

    def test_template_pending_grammar_matches_executor(self):
        sequence = replace(self.sequence, calls=(self.call, self.call))
        good = coord_sequence(sequence)
        cert = source_effect_certificate(sequence, good)
        self.assertTrue(check_source_effect_certificate(sequence, cert)['valid'])
        reason = 'sequence pre-map belongs to previous call, not call template'
        for index in range(len(sequence.calls)):
            calls = list(sequence.calls)
            calls[index] = replace(calls[index], pending=(self.entry,))
            supplied = replace(sequence, calls=tuple(calls))
            with self.subTest(index=index):
                with self.assertRaisesRegex(ValueError, reason):
                    coord_sequence(supplied)
                with self.assertRaisesRegex(ReplayError, reason):
                    source_effect_certificate(supplied, good)
                checked = check_source_effect_certificate(supplied, cert)
                self.assertFalse(checked['valid'])
                self.assertEqual(checked['reason'], reason)

    def test_dense_emission_is_bound_to_final_comment_delimited_block(self):
        second = PendingCoordinate(VarInit(Var('b'), Literal('2')), ())
        call = replace(self.call, iterators=(IteratorState('X', True, True),),
                       defined_index_vars=('j',))
        sequence = replace(self.sequence, initial_pending=(self.entry, second), calls=(call,))
        good = coord_sequence(sequence)[0]
        emitted = good.dense.emitted
        self.assertEqual(len(emitted), 3)
        prefix = good.nodes[:-len(emitted)]
        self.assertTrue(prefix)
        self.assertTrue(check_source_effect_certificate(
            sequence, source_effect_certificate(sequence, (good,)))['valid'])
        mutations = {
            'missing-comment': prefix + emitted[1:],
            'dropped-declaration': good.nodes[:-1],
            'changed-value': prefix + emitted[:-1] + (replace(emitted[-1], value=Literal('99')),),
            'reordered-declarations': prefix + (emitted[0], emitted[2], emitted[1]),
            'trailing-node': good.nodes + (Blank(),),
            'duplicate-dense-block': emitted + good.nodes,
        }
        for label, nodes in mutations.items():
            with self.subTest(label=label):
                wrong = replace(good, nodes=nodes)
                self.assertEqual(wrong.pending, good.pending)
                self.assertEqual(wrong.dense, good.dense)
                with self.assertRaisesRegex(ReplayError, 'call 0: source dense emission binding'):
                    source_effect_certificate(sequence, (wrong,))
        wrong = replace(good, dense=replace(good.dense, emitted=()))
        with self.assertRaisesRegex(ReplayError, 'source dense emission binding'):
            source_effect_certificate(sequence, (wrong,))

    def test_empty_dense_emission_allows_prefix_but_not_spurious_dense_block(self):
        for iterators in ((), (IteratorState('X', True, True),)):
            with self.subTest(iterators=iterators):
                call = replace(self.call, iterators=iterators)
                sequence = replace(self.sequence, calls=(call,))
                good = coord_sequence(sequence)[0]
                self.assertEqual(good.dense.emitted, ())
                self.assertEqual(bool(good.nodes), bool(iterators))
                self.assertTrue(check_source_effect_certificate(
                    sequence, source_effect_certificate(sequence, (good,)))['valid'])
                for block in ((Comment('Resolve dense coordinates'),),
                              (Comment('Resolve dense coordinates'), self.entry.statement)):
                    wrong = replace(good, nodes=good.nodes + block)
                    with self.assertRaisesRegex(ReplayError, 'source dense emission binding'):
                        source_effect_certificate(sequence, (wrong,))

    def test_non_dense_node_mutation_remains_outside_certificate_scope(self):
        call = replace(self.call, iterators=(IteratorState('X', True, True),),
                       defined_index_vars=('j',))
        sequence = replace(self.sequence, calls=(call,))
        good = coord_sequence(sequence)[0]
        mutant = coord_mutant(replace(call, pending=sequence.initial_pending), 'coord-end-off-by-one')
        self.assertNotEqual(good.nodes, mutant.nodes)
        self.assertEqual(good.pending, mutant.pending)
        self.assertEqual(good.dense, mutant.dense)
        cert = source_effect_certificate(sequence, (good,))
        self.assertEqual(cert, source_effect_certificate(sequence, (mutant,)))
        self.assertTrue(check_source_effect_certificate(sequence, cert)['valid'])


if __name__ == '__main__':
    unittest.main()
