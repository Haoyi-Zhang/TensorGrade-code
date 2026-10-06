# Semantic Contract Grading for Tensor-Compiler Patches

This standalone repository implements and validates the artifact for the paper of
the same name. It contains an exact-rational finite-read tensor checker, compact
counterexample construction and replay, a restricted linear-consumer support
criterion, and three clean-room source adapters for a fixed twelve-commit public
Scorch denominator.

The scope is intentionally narrow. Three commits admit complete production-diff
source adapters and nine remain explicit abstentions. P01 remains an abstained
candidate with separately reported finite successful-domain diagnostics. No upstream Scorch
checkout, native extension, generated kernel, or repository test suite is built
or executed. The public result is conditional source-observable equality under
stated invariants and unchanged downstream components—not whole-runtime patch
verification.

## Requirements

- Linux, Windows, or another environment exposing a compatible Z3 shared library;
- Python 3.10 or newer; and
- no Python package dependencies beyond the standard library.

The symbolic layer uses the standard Z3 C API. It accepts an explicitly selected
library through `Z3_LIBRARY_PATH`, discovers a system library with
`ctypes.util.find_library('z3')`, or locates the library in an installed official
`z3-solver` Python package. The optional package supplies the native library;
it is not imported by certificate replay. No external model API, GPU, network access, repository checkout,
private cache, or solver download is used by the retained workflow. Certificate
replay does not load Z3.

The repository does not pin or redistribute a native solver binary. Different
compatible installations may choose different models or timings. The semantic
reproduction targets are statuses, validated certificates, empty error lists,
public-adapter decisions, and aggregate counts—not byte-identical JSON model text
or performance.

## Complete reproduction

Run from this extracted repository root:

```sh
python reproduce.py --output results/reproduced
python summarize.py \
  --directory results/reproduced \
  --output results/reproduced-summary.json
python emit_tables.py \
  --directory results/reproduced \
  --output results/tex-tables
```

`reproduce.py` launches six sequential bounded phases:

1. 56 unit and adversarial tests, including 18 P06 state-effect and export-binding regressions;
2. an offline integrity audit of 83 cited scholarly records plus a complete 83-record primary-record audit;
3. 28 pilot program pairs and 16 consumer descriptions;
4. 64 frozen generated pairs plus the 729 coefficient-row-pair enumeration;
5. a separate post-hoc multi-seed robustness audit over 256 additional generated
   pairs, excluded from the frozen 801-query campaign; and
6. the frozen twelve-commit public source-adapter study.

Each child uses one worker and a 115-second wall timeout. On POSIX systems the
wrapper also applies a 2 GiB address-space cap and 105/110 CPU-second limits.
On Windows these POSIX caps and child RSS measurements are unavailable and are
recorded as unavailable, not as zero. Solver queries use a 1,500 ms timeout. A nonzero child exit,
wall timeout, or nonempty validation-error list is a failed reproduction.

`summarize.py` refuses to summarize failed phases. `emit_tables.py` generates all
nine paper/supplement tables from the selected results directory without needing
the paper source.

The retained current summary reports:

- all nine closed grades;
- 167 successful direct refutation replays;
- 162 compact finite-read certificates: 72 with zero stored cells, 85 with one,
  and five with two in the current run; the chosen solver witnesses may differ
  between compatible installations while preserving replay validity and the
  two-cell bound;
- five additional two-cell consumer refutations;
- 3 admitted public source adapters and 9 abstentions in 12 commits;
- 526 admitted bounded source-adapter states with zero mismatches;
- P06: 400 independent single-call state-effect replays, eight additional
  sequences containing 22 calls, and three rejected unchanged-output state
  controls, reported separately from frozen state/mutant and IR-certificate counts;
- P01 retained separately with 29,222 matching successful-domain states and
  three differing source-reachable scalar boundary controls;
- 18 synthetic adapter mutants: repeated developer indices detect 14/18,
  seeded random with replacement detects 18/18, and an evenly spaced
  enumeration-index grid detects 18/18 under a cap of 64 candidate slots per
  mutant, using 325, 121, and 318 actual executions; and
- 83 cited bibliography records matching the frozen inventory, including 77 DOI
  records and six stable official or DBLP locators, plus complete dated
  primary-record metadata reconciliation and citation-context records for all
  83 cited keys; and
- a post-hoc robustness audit over eight additional seeds (256 cases, 2,048
  queries, 512 oracle checks, and 500 independently replayed compact
  certificates) with no validation errors. These counts are kept separate from
  the frozen main campaign and do not constitute independent or statistical
  validation.

These units describe different objects and must not be summed into a nominal
workload or bug count.

## Individual CLI examples

```sh
PYTHONPATH=src python -m semantic_contract grade \
  data/examples/late-shape-threshold.json \
  --output results/example-grade.json

PYTHONPATH=src python -m semantic_contract replay \
  data/examples/storage-without-support.json \
  data/certificates/support-cancellation.json

PYTHONPATH=src python -m semantic_contract consumer \
  data/consumer-example.json \
  --output results/example-consumer.json
```

The grade command returns per-atom `proved`, `refuted`, or `unknown` in the
restricted supplied semantics. `complete_grade` is true only for admitted,
production-mode, conclusive five-atom runs. A zero exit can contain refuted atoms;
it is not an “all contracts correct” verdict.

The replay command independently revalidates the finite-read schema, grammar,
sorts, bounds, and witness before exact concrete execution. It is not a source-
mapping proof or a check of an UNSAT result. The consumer command checks the stated free-value/clique-mask
criterion.

Exit codes:

- `0`: conclusive admitted grading (possibly with refutations), valid replay, or
  conclusive consumer result;
- `2`: unsupported, invalid, vacuous, or unknown complete result;
- `3`: invalid replay; and
- `1`: input or runtime error.

## Semantic scope

The finite-read language has affine integer shape preconditions, affine output
shapes and read addresses, constant exact rational coefficients, value-independent
guards, ranks at most four, and at most 32 reads per program. Logical storage is
dense, empty, compact, or union. Potential-contribution order is syntactic active
term order; it is not floating-point reduction order.

The checker does not model physical sparse index arrays, duplicate-coordinate
assembly, aliasing, mutation, exceptions, allocation or lifetime, machine integer
overflow, floating point, NaNs, threading, atomics, undefined behavior, or general
value-dependent/variable-length reductions. The separate consumer schema covers
a restricted unbounded-size linear relation, not arbitrary consumer equivalence.

## Public source-adapter study

`data/public-corpus.csv` is the fixed denominator. The first four chronological
records are the development segment; the next eight form a later retrospective
segment. Repository scouting preceded the split, so it is not preregistered or
blind. Every nonadmitted commit remains in the denominator.

An admitted adapter records a complete production-file scope, runtime disposition
of every changed statement, source-state invariant, before/after observable,
universal equality argument, independently coded bounded models with mutants,
and an unchanged-downstream lifting premise.

- **P01 (abstained candidate)**: generated-string versus direct CIN
  construction. The 29,222 successful-domain AST comparisons are retained, but
  source-reachable scalar boundary controls invalidate the proposed complete
  invariant.
- **P04 (admitted)**: monolithic versus extracted LLIR rendering; exact generated
  C++ text, with independently implemented conditional paths.
- **P06 (admitted)**: monolithic versus extracted coordinate resolution; complete
  ordered typed LLIR node trees, including operands, addresses, literals, bounds,
  updates, and bodies, jointly with the persistent ordered pending-coordinate
  map. Explicit dependency lists drive readiness; pre-map reads, append/name
  dedup, snapshot scanning, ready removal, and unready retention are preserved
  across calls. `dense_effects.py` independently replays transition certificates
  without importing changed adapter logic or a solver.
- **P08 (admitted)**: two mode-order initialization cascades under the immutable
  fixed-production call-site invariant; initialized sequence or exception class.

P01 and the other eight abstained commits change or expose accepted inputs,
object/exception or ownership semantics, physical sparse representation,
scheduler choices, floating-point/raw-memory behavior, or whole-runtime
dispatch beyond a closed adapter domain. The artifact abstains rather than
projecting them onto a convenient rational expression.

The adapters are original semantic models written from attributed public diffs.
No upstream source file or patch is redistributed. Commit URLs and file scopes are
retained in the CSV and source ledger.

## Repository layout

- `src/semantic_contract/`: schema, admission, SMT adapter, checker, concrete
  interpreter, finite oracle, certificate constructor/replayer, consumer checker,
  public adapters, and CLI.
- `proofs/core.md`: definitions and prose proof ledger.
- `tests/`: semantic, replay, oracle, consumer, and source-adapter regressions.
- `audit_references.py`, `run_pilot.py`, `run_diagnostics.py`,
  `run_robustness_audit.py`, `run_public_study.py`: retained integrity check and campaigns.
- `data/`: exact program/consumer inputs, generated cases, certificates, public
  commit denominator, frozen bibliography, primary-record audit, citation-context
  ledger, citation keys, and metadata inventory.
- `results/current/`: raw outputs used by the paper.
- `results/summary.json`: reconciled retained counts.
- `docs/`: protocols, source selection, literature scope, formats, and evidence
  interpretation.
- `claim_evidence_ledger.csv`: claim-to-proof/check/raw-evidence boundaries.
- `external_resources.csv`: externally consulted primary resources and public
  commit locators.
- `licenses/`: notice for the unbundled Z3 dependency.

## Trust and interpretation

The all-shapes theorems are prose proofs, not proof-assistant certificates. Z3 is
trusted for UNSAT; the separate interpreter only validates concrete SAT
witnesses. The symbolic checker, oracle, replay path, source adapters, proofs,
and self-audit were produced in one research process, so they are not independent
human validation.

Synthetic mutants are not historical Scorch bugs. Bounded adapter agreement is
not the universal proof. Universal adapter proofs do not establish omitted source
behavior. Successful commands do not imply external submission readiness or
permission to submit.


## Licensing

Original implementation, generated inputs, proof text, and result records are
provided under the MIT license in `LICENSE`. Z3 is an unmodified external runtime
dependency; its notice is retained in `licenses/Z3-NOTICE.txt`, and no solver
binary is bundled. Public upstream source is linked and described but not
redistributed. Scholarly sources are cited rather than relicensed here.
