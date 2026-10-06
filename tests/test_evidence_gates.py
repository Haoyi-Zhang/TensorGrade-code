"""Regressions for conclusive evidence and the documented portable CLI."""
from copy import deepcopy
import builtins
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from semantic_contract.checker import ATOMS
from semantic_contract.cases import pilot_cases
import run_diagnostics
import run_pilot
import run_robustness_audit
from summarize import summarize


class EvidenceGatesTest(unittest.TestCase):
    def incomplete(self, case):
        return {'id': case['id'], 'admission': 'admitted', 'complete_grade': False,
                'mode': 'production', 'queries': [],
                'contracts': {a: {'status': 'unknown', 'witness': None} for a in ATOMS}}

    def test_summary_rejects_unknown_even_with_empty_error_lists(self):
        names = ('pilot', 'diagnostics', 'execution', 'public-study',
                 'reference-audit', 'robustness-audit')
        originals = {name: json.loads((ROOT / 'results/current' / (name + '.json')).read_text())
                     for name in names}
        for source in ('pilot', 'diagnostics'):
            for flag in (False, True):
                with self.subTest(source=source, complete_grade=flag), tempfile.TemporaryDirectory() as temp:
                    records = deepcopy(originals)
                    grade = next(r['grade'] for r in records[source]['records']
                                 if r['grade']['admission'] == 'admitted')
                    grade['complete_grade'] = flag
                    grade['contracts']['value'].update(status='unknown', witness=None)
                    for name, record in records.items():
                        (Path(temp) / (name + '.json')).write_text(json.dumps(record), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'incomplete semantic grade'):
                        summarize(Path(temp))

    def test_summary_rejects_inconclusive_consumer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('pilot', 'diagnostics', 'execution', 'public-study',
                         'reference-audit', 'robustness-audit'):
                record = json.loads((ROOT / 'results/current' / (name + '.json')).read_text())
                if name == 'pilot':
                    record['consumer_records'][0]['grade']['status'] = 'unknown'
                (root / (name + '.json')).write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'inconclusive consumer'):
                summarize(root)

    def runner_unknown(self, module, arguments):
        class FakeSolver:
            queries = 0
            total_cpu = 0.
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'result.json'
            with patch.object(module, 'Solver', FakeSolver), \
                 patch.object(module, 'grade', side_effect=lambda case, *_a, **_k: self.incomplete(case)), \
                 patch.object(sys, 'argv', ['runner', '--output', str(output), *arguments]), \
                 contextlib.redirect_stdout(io.StringIO()):
                failed = module.main()
            report = json.loads(output.read_text())
            self.assertTrue(failed)
            self.assertTrue(any('incomplete semantic grade' in e for e in report['errors']))

    def test_diagnostic_runner_rejects_unknown_atoms(self):
        self.runner_unknown(run_diagnostics, [])

    def test_robustness_runner_rejects_unknown_atoms(self):
        self.runner_unknown(run_robustness_audit, ['--seeds', '7', '--cases-per-seed', '1'])

    def test_pilot_runner_rejects_incomplete_grade_without_expected_atoms(self):
        case = deepcopy(pilot_cases()[0])
        case['expected'] = {'admission': 'admitted'}
        with patch.object(run_pilot, 'pilot_cases', return_value=[case]), \
             patch.object(run_pilot, 'consumer_cases', return_value=[]), \
             patch.object(run_pilot, 'next', return_value=case, create=True):
            self.runner_unknown(run_pilot, [])


class PortableCLITest(unittest.TestCase):
    def cli(self, *arguments):
        env = os.environ.copy()
        env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        return subprocess.run([sys.executable, '-B', '-m', 'semantic_contract', *arguments],
                              cwd=ROOT, env=env, text=True, encoding='utf-8',
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    def test_cli_help_does_not_require_posix_resource(self):
        result = self.cli('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('consumer', result.stdout)
        original_import = builtins.__import__
        def without_resource(name, *args, **kwargs):
            if name == 'resource':
                raise ImportError('emulated non-POSIX host')
            return original_import(name, *args, **kwargs)
        # Exercise the fallback on Linux too, without changing host limits.
        with patch('builtins.__import__', side_effect=without_resource), \
             patch.object(sys, 'argv', ['semantic_contract', '--help']), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exited:
                runpy.run_module('semantic_contract', run_name='__main__')
        self.assertEqual(exited.exception.code, 0)

    def test_cli_replay_is_solver_free_and_preserves_failure_exit(self):
        example = ROOT / 'data/examples/storage-without-support.json'
        certificate = ROOT / 'data/certificates/support-cancellation.json'
        with patch.dict(os.environ, {'Z3_LIBRARY_PATH': 'deliberately-absent-library'}):
            result = self.cli('replay', str(example), str(certificate))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            with tempfile.TemporaryDirectory() as temp:
                bad = json.loads(certificate.read_text())
                bad['case_id'] = 'different-case'
                path = Path(temp) / 'tampered.json'
                path.write_text(json.dumps(bad), encoding='utf-8')
                result = self.cli('replay', str(example), str(path))
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertFalse(json.loads(result.stdout)['valid'])


if __name__ == '__main__':
    unittest.main()
