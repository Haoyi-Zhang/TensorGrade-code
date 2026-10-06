"""Regression tests for the frozen public-source adapters."""
from __future__ import annotations

import csv
import inspect
import json
from pathlib import Path
import unittest

from semantic_contract.public_adapters import (
    ADAPTERS,
    SOURCE_PINS,
    EinsumBuildSpec,
    IfNode,
    _parent_render,
    _child_render_conditional,
    coord_after,
    coord_before,
    coord_mutant,
    mode_after,
    mode_before,
    mutation_study,
    node_kind_signature,
    p01_exhaustive_specs,
    p04_cases,
    p04_coverage_map,
    p06_cases,
    p08_cases,
    p08_excluded_cases,
    render_mutant,
    verify_adapter,
    verify_p01_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


class PublicAdapterStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (ROOT / "data/public-corpus.csv").open() as handle:
            cls.corpus = list(csv.DictReader(handle))
        cls.evidence = json.loads((ROOT / "data/public-adapter-evidence.json").read_text())
        cls.adapters = [verify_adapter(adapter_id) for adapter_id in ADAPTERS]
        cls.mutation = mutation_study(seed=20260915, candidate_slot_cap=64)

    def test_corpus_denominator_and_split_are_frozen(self) -> None:
        self.assertEqual(len(self.corpus), 12)
        self.assertEqual(sum(r["split"] == "development" for r in self.corpus), 4)
        self.assertEqual(sum(r["split"] == "held-out" for r in self.corpus), 8)
        self.assertEqual(sum(r["decision"] == "admitted" for r in self.corpus), 3)
        self.assertEqual(sum(r["decision"] == "abstained" for r in self.corpus), 9)
        self.assertEqual(
            sum(r["split"] == "development" and r["decision"] == "admitted" for r in self.corpus),
            1,
        )
        self.assertEqual(
            sum(r["split"] == "held-out" and r["decision"] == "admitted" for r in self.corpus),
            2,
        )
        self.assertEqual(
            sorted(r["adapter_id"] for r in self.corpus if r["decision"] == "admitted"),
            sorted(ADAPTERS),
        )


    def test_hunk_disposition_and_source_invariant_evidence_is_complete(self) -> None:
        records = self.evidence["records"]
        self.assertEqual(set(records), {"P01", "P04", "P06", "P08"})
        for adapter_id, record in records.items():
            self.assertEqual(record["parent_commit"], SOURCE_PINS[adapter_id]["parent"])
            self.assertEqual(record["child_commit"], SOURCE_PINS[adapter_id]["child"])
            self.assertEqual(record["parent_tree_sha"], SOURCE_PINS[adapter_id]["parent_tree"])
            self.assertEqual(record["child_tree_sha"], SOURCE_PINS[adapter_id]["child_tree"])
            self.assertTrue(record["hunk_disposition"])
            self.assertTrue(record["immutable_files"])
        self.assertEqual(records["P01"]["failed_gates"], ["G3", "G4", "G5"])
        self.assertEqual(records["P04"]["bounded_validation"]["states"], 30)
        self.assertFalse(records["P06"]["bounded_validation"]["label_only_comparison_used"])
        self.assertIn("post-call pending-coordinate map", records["P06"]["observable"])
        self.assertEqual(records["P06"]["bounded_validation"]["additional_calls"], 22)
        p08_inventory = records["P08"]["fixed_production_callsite_invariant"]
        self.assertEqual(len(p08_inventory["callsite_groups"]), 4)
        self.assertEqual(p08_inventory["inventory_summary"]["direct_tensorvar_call_expressions"], 20)
        self.assertTrue(p08_inventory["inventory_summary"]["all_direct_calls_supply_fmt"])
        self.assertEqual(records["P08"]["bounded_validation"]["excluded_domain_controls"], 4)
        self.assertIn("not used as evidence", records["P08"]["bounded_validation"]["partition_role"])
        aggregate = self.evidence["aggregate_after_repair"]
        self.assertEqual((aggregate["admitted_complete_adapters"], aggregate["abstentions"]), (3, 9))
        self.assertEqual(aggregate["admitted_bounded_states"], 526)

    def test_source_pins_have_fixed_parent_and_child(self) -> None:
        self.assertEqual(set(SOURCE_PINS), {"P01", "P04", "P06", "P08"})
        for pin in SOURCE_PINS.values():
            self.assertEqual(len(pin["parent"]), 40)
            self.assertEqual(len(pin["parent_tree"]), 40)
            self.assertEqual(len(pin["child"]), 40)
            self.assertEqual(len(pin["child_tree"]), 40)
            self.assertNotEqual(pin["parent"], pin["child"])
            self.assertNotEqual(pin["parent_tree"], pin["child_tree"])
        self.assertEqual(SOURCE_PINS["P01"]["decision"], "abstained")

    def test_all_admitted_adapters_match_on_retained_domain(self) -> None:
        # P04=30, P06=400, P08=96.  P01's 29,222 successful-domain
        # diagnostics are deliberately not included after its admission failure.
        self.assertEqual(sum(r["bounded_case_count"] for r in self.adapters), 526)
        self.assertTrue(all(r["mismatch_count"] == 0 for r in self.adapters))

    def test_p01_range_is_finite_boundary_not_source_invariant(self) -> None:
        specs = p01_exhaustive_specs()
        self.assertEqual(len(specs), 29222)
        self.assertEqual(len(specs), len(set(specs)))
        self.assertTrue(any(len(spec.operands) == 4 for spec in specs))
        self.assertTrue(all(isinstance(spec, EinsumBuildSpec) for spec in specs))
        result = verify_p01_candidate()
        self.assertEqual(result["decision"], "abstained")
        self.assertEqual(result["successful_domain_mismatch_count"], 0)
        self.assertEqual(result["scalar_boundary_case_count"], 4)
        # Three source-reachable mixed scalar/result-scalar controls differ.
        self.assertEqual(sum(not x["same"] for x in result["scalar_boundary_controls"]), 3)

    def test_p04_independent_conditional_paths_and_branch_coverage(self) -> None:
        self.assertEqual(len(p04_cases()), 30)
        coverage = p04_coverage_map()
        self.assertIn("Comment", coverage)
        self.assertIn("BlankLine", coverage)
        self.assertIn("ForLoop.init-none", coverage)
        self.assertIn("IfThenElse.make-last-case-else", coverage)
        # The parent monolith does not call the child's extracted conditional helper.
        self.assertNotIn("_child_render_conditional", inspect.getsource(_parent_render))
        self.assertNotEqual(_parent_render.__code__, _child_render_conditional.__code__)
        conditional_cases = [c for c in p04_cases() if isinstance(c.node, IfNode)]
        for mutant in (
            "conditional-change-condition",
            "conditional-drop-else",
            "conditional-drop-closing-brace",
        ):
            self.assertTrue(
                any(render_mutant(c, mutant) != _parent_render(c.node, c.indent_level, c.no_semicolon, c.no_comments)
                    for c in conditional_cases),
                mutant,
            )

    def test_p06_compares_complete_nodes_not_labels(self) -> None:
        self.assertEqual(len(p06_cases()), 400)
        self.assertTrue(all(coord_before(c) == coord_after(c) for c in p06_cases()))
        case = next(c for c in p06_cases() if any(it.coordinate and it.has_child for it in c.iterators))
        baseline = coord_after(case)
        mutant = coord_mutant(case, "coord-end-off-by-one")
        self.assertNotEqual(baseline, mutant)
        # The negative control preserves top-level node kinds while changing the
        # literal in the actual bound expression, so label equality cannot pass it.
        self.assertEqual(node_kind_signature(baseline.nodes), node_kind_signature(mutant.nodes))
        self.assertEqual(baseline.pending, mutant.pending)
        result = verify_adapter("P06")
        self.assertEqual(result["effect_replay_count"], 400)
        self.assertEqual(result["effect_replay_failures"], [])

    def test_p08_keeps_96_equivalence_cases_and_four_excluded_controls(self) -> None:
        self.assertEqual(len(p08_cases()), 96)
        self.assertEqual(len(p08_excluded_cases()), 4)
        self.assertTrue(all(mode_before(c) == mode_after(c) for c in p08_cases()))
        for case in p08_excluded_cases():
            with self.assertRaises(AttributeError):
                mode_before(case)
            self.assertIsNone(mode_after(case))
        result = verify_adapter("P08")
        self.assertEqual(result["bounded_case_count"], 96)
        self.assertEqual(result["excluded_domain_count"], 4)
        self.assertTrue(all(not row["same"] for row in result["excluded_domain_controls"]))

    def test_negative_controls_and_candidate_slot_accounting(self) -> None:
        self.assertEqual(self.mutation["mutant_count"], 18)
        expected = {
            "repeated-developer-indices": (14, 325),
            "seeded-random-with-replacement": (18, 121),
            "evenly-spaced-enumeration-indices": (18, 318),
        }
        for method, (detected, executions) in expected.items():
            self.assertEqual(self.mutation["summary"][method]["detected"], detected)
            self.assertEqual(self.mutation["summary"][method]["actual_executions"], executions)
        self.assertEqual(self.mutation["candidate_slot_cap_per_mutant"], 64)
        self.assertNotIn("stratified", self.mutation["interpretation"].lower())
        for row in self.mutation["rows"]:
            for method in expected:
                run = row[method]
                self.assertLessEqual(run["actual_executions"], 64)
                if run["detected"]:
                    self.assertEqual(run["actual_executions"], run["first_detection_slot"])
                else:
                    self.assertIsNone(run["first_detection_slot"])
                    self.assertEqual(run["actual_executions"], 64)


if __name__ == "__main__":
    unittest.main()
