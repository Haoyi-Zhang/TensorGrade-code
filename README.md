# Semantic Contract Grading for Tensor-Compiler Patches

This standalone artifact provides an exact-rational finite-read tensor checker,
counterexample construction and solver-free replay, a restricted linear-consumer
support criterion, and clean-room source adapters for a fixed twelve-commit
Scorch study. No upstream checkout, native extension, generated kernel, or
Scorch test suite is built or executed.

## Environment

Use Python 3.10 or newer on Linux, Windows, or another host with a compatible Z3
shared library. The Python implementation uses the standard library and the Z3
C API. The solver loader checks `Z3_LIBRARY_PATH`, a system Z3 library, then
the native library in an installed official `z3-solver` package. For example:

```sh
python -m pip install z3-solver==4.13.4.0
```

This is an optional way to obtain the external library, not a bundled binary or
a requirement that all compatible hosts use this version. The recorded Windows
run used Z3 4.13.4 and CPython 3.12.14. An explicit `Z3_LIBRARY_PATH` must name
a compatible shared-library file. Certificate replay does not load Z3.

The retained workflow is network-free once the runtime is installed. It needs
no external model API, GPU, downloaded benchmark, or private cache. Keep Python
assertions enabled; do not use `-O`.

## Reproduce and generate tables

Run from this directory. Choose an output directory that does not already exist,
inside the artifact but separate from retained `results/current/`:

```sh
python -B reproduce.py --output results/reproduced
python -B summarize.py --directory results/reproduced --output results/reproduced-summary.json
python -B emit_tables.py --directory results/reproduced --output results/tex-tables
```

The six sequential phases are the discovered unit tests, offline reference
audit, pilot, frozen diagnostics, separate post-hoc robustness audit, and public
source-adapter study. Each child has a 115-second wall timeout; Z3 queries use
1,500 ms. POSIX children also receive a 2 GiB address-space cap and 105/110
CPU-second limits. Windows records unavailable POSIX caps and child CPU/RSS as
unavailable, not zero.

A failed child, timeout, validation error, or inconclusive admitted grade fails
reproduction. The summary gate rejects failed/incomplete evidence.
`emit_tables.py` generates nine TeX tables without the paper directory.
To summarize existing evidence without rerunning experiments, substitute
`results/current` for the input directory and select new output paths.

Compatible Z3 versions may choose different valid witnesses or timings.
Reproduction targets semantic statuses, validated certificates, empty error
lists, public-adapter decisions, and counts, not byte-identical model JSON or
performance. The distinct workload units and retained counts are documented in
[docs/validation.md](docs/validation.md); do not sum them into a bug count.

## Individual commands

Set the source path in the current shell first:

```sh
# POSIX shell
export PYTHONPATH=src
```

```powershell
# PowerShell
$env:PYTHONPATH = 'src'
```

Then use the same Python commands on either platform:

```sh
python -B -m semantic_contract grade data/examples/late-shape-threshold.json --output results/example-grade.json
python -B -m semantic_contract replay data/examples/storage-without-support.json data/certificates/support-cancellation.json
python -B -m semantic_contract consumer data/consumer-example.json --output results/example-consumer.json
python -B tests/regression_address_encoding.py -v
```

The last command checks the finite encoder without loading a native solver;
scripted answers exercise control flow, not solver validity. Per-call address
rendering reuse preserves formulas and modeled counts and is not a measured
speedup.

Exit `0` means a conclusive admitted grade (possibly with refuted atoms), valid
replay, or conclusive consumer result. Exit `2` means unsupported, invalid,
vacuous, or unknown complete results; `3` means invalid replay; `1` means an
input/runtime error. A zero grade exit is not an all-contracts-correct verdict.
Replay validates a finite SAT witness, not UNSAT or a source-mapping proof.

## Inputs, results, and supporting material

- `data/`: complete program/consumer inputs, generated cases, certificates,
  the frozen public-commit denominator and source pins, bibliography inventory,
  primary-record audit, and citation contexts.
- `src/semantic_contract/`: schema/admission, SMT checker, exact interpreter,
  oracle, certificate replay, consumer criterion, source adapters, and CLI.
- `results/current/` and `results/summary.json`: retained raw evidence and
  reconciled counts. Other retained runs have their own provenance.
- `proofs/core.md` and `claim_evidence_ledger.csv`: arguments and evidence map.
- `tests/`: semantic, replay, oracle, consumer, and source-adapter regressions.
- [docs/formats.md](docs/formats.md): schemas and certificate/result boundaries.
- [docs/public-study.md](docs/public-study.md) and the other `docs/` protocols:
  source selection, adapter evidence, diagnostics, and interpretation.
- `external_resources.csv`, `LICENSE`, and `licenses/Z3-NOTICE.txt`:
  source provenance and licensing.

## Conditions and interpretation

The language has affine integer shapes/addresses, exact rational coefficients,
value-independent guards, rank at most four, and at most 32 reads per program.
It does not model physical sparse layout, aliasing, mutation, exceptions,
allocation, integer overflow, floating point, threading, or general
value-dependent reductions. The consumer schema covers its stated free-value
and clique-mask criterion, not arbitrary consumer equivalence.

The public denominator retains three admitted adapters and nine abstentions.
P01 remains abstained; its successful-domain diagnostics do not enlarge admitted
coverage. Admitted results are conditional source-observable equality under
source-derived invariants and unchanged downstream components, not whole-runtime
patch verification. The retrospective temporal split is not preregistered or
blind. Synthetic mutants are not historical Scorch bugs. Immutable commit/file
locators remain in the source ledger; no upstream source or patch is
redistributed.

General theorems are prose proofs. Z3 is trusted for UNSAT; the separate
interpreter checks concrete SAT witnesses. The code, adapters, proofs, and
self-audit arose in one research process, not independent human validation.
Successful commands do not confer submission permission.

Original implementation, generated inputs, proof text, and result records are
MIT-licensed under `LICENSE`. Z3 remains an unmodified, unbundled external
dependency with its retained notice. Linked upstream and scholarly sources are
not relicensed by this artifact.
