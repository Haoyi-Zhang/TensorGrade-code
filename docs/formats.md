# Input and result formats

The exact semantic schemas are enforced in `src/semantic_contract/ir.py`,
`coherence.py`, and `public_adapters.py`; retained JSON/CSV files are complete
usable inputs. No hidden configuration exists.

## Program pairs

Top-level scientific fields are `id`, `parameters`, `inputs`, `precondition`,
`before`, and `after`. Optional `family`, `provenance`, and `expected` fields
document generated diagnostics; expected labels are read by tests and never used
by the grader to decide an atom. Input names are `A` through `D`; shape parameters
are distinct `n0` through `n3`. Output indices are `i0` through `i3` up to the
output rank. Each program has `shape`, `terms`, and `storage`. A term has tensor,
index, coefficient, and guard. Coefficients are rational strings; expressions are
parsed as a restricted affine/Boolean AST, never Python `eval`. Storage is one of
`dense`, `union`, `compact`, or `empty`.

## Consumer descriptions

Fields are `id`, `parameters`, `precondition`, `input_extent`, `output_extent`,
`scales`, `weights`, and `compatible`; `family` and `expected` are optional.
Scales and weights are finite lists of `{guard, coefficient}`. Scales may use
`u0`; weights may use `u0` and `i0`; compatibility may use `u0` and `v0`.
Scale coefficients are nonzero. Admission checks total/disjoint partitions and
reflexive/symmetric compatibility. Legal masks are all cliques of the relation,
not an undocumented producer range.

## Counterexample certificates

A finite-read certificate contains `case_id`, `observation`, `coordinates`, and
`cells`. Each cell has a tensor name, integral index vector, rational-string
value, and `stored=true`. At most two cells are allowed; every unlisted cell is
absent zero. An explicit stored zero differs from an omitted cell. Coordinates
include every shape parameter and required output coordinate. Replay verifies a
finite witness; it does not establish all-shape admission or a source translation.

## Public corpus and adapter results

`data/public-corpus.csv` has one row per selected commit: neutral ID, split,
immutable SHA, title, decision, adapter ID if admitted, complete changed
production-file scope, disposition reason, and source URL. The stable split value
`held-out` means the later retrospective segment; it does not imply preregistration
or blinding.

`public-study.json` embeds the corpus, P01 candidate diagnostics, per-admitted-
adapter bounded case/mismatch counts, four P08 excluded-domain controls,
per-mutant first-detection slots and actual executions for three literal selection
schedules, aggregate coverage, and explicit interpretation text. A zero adapter mismatch is not an upstream test
or universal proof.

## Raw semantic evidence

Each SMT query records obligation, status, selected model values when SAT,
encoding bytes, CPU/wall duration, and unknown detail. A program grade records
admission, per-atom statuses, `complete_grade`, and production/defective mode.
Pilot and diagnostic entries embed exact cases, oracle results, direct replay,
and compact certificates. The algebra enumeration records its cardinalities and
any disagreements. `execution.json` records child commands, exits, timeouts,
whole-process CPU, and a peak-RSS upper bound.

No success field means publication acceptance, novelty, independent review, or
unrestricted public compiler correctness. Inspect the typed decision and boundary,
not only a process exit code.
