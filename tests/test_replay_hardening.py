"""Adversarial tests for the independent replay and certificate boundary."""
from __future__ import annotations

from copy import deepcopy
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from semantic_contract.cases import generated_cases, pilot_cases
from semantic_contract.certificates import check_certificate, small_certificate
from semantic_contract.checker import grade
from semantic_contract.ir import Unsupported, expression, load_case
from semantic_contract.replay import (
    ReplayError,
    integer_expression,
    replay,
    validate_replay_case,
)
from semantic_contract.solver import Solver


class ReplayHardeningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = Solver(1500)
        cls.cases = {case["id"]: case for case in pilot_cases()}

    @classmethod
    def tearDownClass(cls):
        cls.solver.close()

    def test_independent_parser_rejects_nonaffine_and_sort_errors(self):
        env = {"n0": 5, "i0": 2}
        for text, expected_bool in (
            ("n0*i0", False),
            ("n0//2", False),
            ("n0**2", False),
            ("f(n0)", False),
            ("n0+1", True),
            ("True", False),
            ("n1+1", False),
        ):
            with self.subTest(text=text):
                with self.assertRaises(ReplayError):
                    integer_expression(text, env, expected_bool)
        with self.assertRaises(ReplayError):
            integer_expression("n0+1", {"n0": True}, False)

    def test_independent_parser_matches_symbolic_front_end_on_generated_affine_terms(self):
        rng = random.Random(20260919)
        names = {"n0", "n1", "i0"}
        for _ in range(300):
            a, b, c = (rng.randint(-9, 9) for _ in range(3))
            x, y = rng.sample(sorted(names), 2)
            text = f"{a}*{x}+{b}*{y}+{c}"
            env = {name: rng.randint(-12, 12) for name in names}
            self.assertEqual(
                integer_expression(text, env, False),
                expression(text, names).concrete(env),
            )
            bound = rng.randint(-20, 20)
            boolean = f"({text} <= {bound}) and not ({x} == {y})"
            self.assertEqual(
                integer_expression(boolean, env, True),
                expression(boolean, names, True).concrete(env),
            )

    def test_replay_validator_matches_front_end_admission_on_retained_cases(self):
        for case in [*pilot_cases(), *generated_cases(64, 1729)]:
            with self.subTest(case=case["id"]):
                try:
                    load_case(case)
                    front_end_accepts = True
                except Unsupported:
                    front_end_accepts = False
                try:
                    validate_replay_case(case)
                    replay_accepts = True
                except ReplayError:
                    replay_accepts = False
                self.assertEqual(replay_accepts, front_end_accepts)

    def test_replay_rejects_malformed_case_before_interpretation(self):
        base = self.cases["identity"]
        malformed = []
        case = deepcopy(base)
        case["before"]["terms"][0]["index"][0] = "n0*i0"
        malformed.append(case)
        case = deepcopy(base)
        case["before"]["terms"][0]["guard"] = "1"
        malformed.append(case)
        case = deepcopy(base)
        case["before"]["extra"] = 1
        malformed.append(case)
        case = deepcopy(base)
        case["inputs"]["E"] = ["n0"]
        malformed.append(case)
        for case in malformed:
            with self.subTest(case=case):
                result = replay(case, "value", {"n0": 2, "i0": 0})
                self.assertFalse(result["valid"])

    def test_replay_rejects_inexact_or_wrongly_typed_witness_values(self):
        case = self.cases["late-shape-threshold"]
        result = grade(case, self.solver)
        witness = deepcopy(result["contracts"]["value"]["witness"])
        witness["n0"] = 65.0
        self.assertFalse(replay(case, "value", witness)["valid"])
        witness = deepcopy(result["contracts"]["value"]["witness"])
        first_occupancy = next(key for key in witness if key.startswith("b"))
        witness[first_occupancy] = 1
        self.assertFalse(replay(case, "value", witness)["valid"])

    def test_certificate_rejects_schema_and_case_tampering(self):
        case = self.cases["storage-without-support"]
        result = grade(case, self.solver)
        certificate = small_certificate(
            case,
            "zero-support",
            result["contracts"]["zero-support"]["witness"],
        )
        self.assertTrue(check_certificate(case, certificate)["valid"])

        bad = deepcopy(certificate)
        bad["unexpected"] = 1
        self.assertFalse(check_certificate(case, bad)["valid"])
        bad = deepcopy(certificate)
        bad["coordinates"]["j9"] = 0
        self.assertFalse(check_certificate(case, bad)["valid"])
        bad = deepcopy(certificate)
        bad["cells"][0]["unexpected"] = 1
        self.assertFalse(check_certificate(case, bad)["valid"])
        malformed_case = deepcopy(case)
        malformed_case["after"]["terms"][0]["guard"] = "i0"
        self.assertFalse(check_certificate(malformed_case, certificate)["valid"])

    def test_certificate_rejects_binary_float_values(self):
        case = self.cases["storage-without-support"]
        result = grade(case, self.solver)
        certificate = small_certificate(
            case,
            "zero-support",
            result["contracts"]["zero-support"]["witness"],
        )
        bad = deepcopy(certificate)
        bad["cells"][0]["value"] = 0.5
        self.assertFalse(check_certificate(case, bad)["valid"])


if __name__ == "__main__":
    unittest.main()
