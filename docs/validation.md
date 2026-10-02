# Evidence interpretation and resource accounting

The raw current outputs are in `results/current/`; `results/summary.json`
reconciles their semantic counts. Assertions in tests and runners are finite
checks, not machine-checked universal proofs. General arguments are in
`proofs/core.md`.

## Independent paths, not independent researchers

The symbolic encoder uses typed SMT syntax. `replay.py` has a separate concrete
AST interpreter with exact `Fraction` arithmetic, independently validates the
case grammar, sorts, bounds, and witness schema, and does not import the encoder
or solver. `oracle.py` aggregates coefficient rows and enumerates bounded
occupancy masks. `certificates.py` reconstructs compact rational witnesses from
concrete rows rather than copying solver rational assignments. Public adapters implement independent before and after paths; 18 mutants are distributed across the three admitted adapters.

These paths can expose inconsistencies, but they were developed and audited in
one AI-assisted research process. They are not independent human replication or
proof-assistant verification.

## Retained units

- 28 pilot program pairs: 22 admitted, 3 invalid, 2 unsupported, 1 vacuous.
- 16 consumer descriptions: 6 proved, 5 refuted, 4 invalid, 1 unsupported.
- 64 frozen generated program pairs, all admitted.
- 729 coefficient-row pairs and 19,683 finite vector evaluations.
- 801 main-run SMT queries, excluding unit-test queries.
- 252 finite-shape oracle checks containing 3,259 finer obligations.
- 167 successful direct refutation replays.
- 162 compact finite-read certificates: 72 zero-cell, 83 one-cell, 7 two-cell.
- 12 public commits: 3 admitted complete adapters and 9 abstentions.
- 526 admitted bounded adapter states with zero mismatches.
- P01 candidate diagnostics: 29,222 matching successful-domain states and four
  scalar boundary controls, three of which differ.
- 18 synthetic mutants: repeated developer indices detect 14, seeded random with
  replacement 18, and an evenly spaced enumeration-index grid 18. Each mutant
  has at most 64 candidate slots; early stopping uses 325, 121, and 318 actual
  executions.
- 83 cited bibliography records match the frozen inventory: 77 DOI records and
  six stable official or DBLP locators; all 83 cited keys also have a dated
  primary-record metadata audit, and all 83 have citation-context records.
- Post-hoc seed sensitivity (excluded from main counts): eight additional seeds,
  256 admitted cases, 2,048 queries, 512 oracle checks, and 500 replayed compact
  certificates, with zero validation errors.

These counts describe different objects and must not be summed. Generated pairs,
row pairs, adapter states, and mutants are not public bug counts.

Observed maxima in the retained semantic runs are 64 read occurrences per pair,
2,016 conditional same-input occurrence pairs, and 258,746 encoded query bytes.
Syntax bounds are 32 terms per program, rank at most four, one to four shape
parameters and tensors, 512 expression characters, 128 expression nodes, source
integer literals below `2^31`, and normalized coefficient numerator/denominator
magnitudes below `2^16`. Shape variables remain unbounded integers.

## Negative controls

Omitting conditional address congruence produces a false apparent failure when
two reads collide at one shape; direct replay rejects it. Other tests cover
malformed or tampered certificates, stored-zero distinctions, late-shape
thresholds, admission abstentions, and an injected unknown result. A correlated
producer range refutes an overgeneralized necessity claim for the consumer
theorem. Mutants attack operand construction, renderer punctuation/order,
coordinate-resolution blocks/bounds, and initialization precedence.

## Resource closure

Scientific intake recorded four cgroup-quota CPU cores, 4 GiB memory, no swap,
and adequate writable space. Reproduction runs children sequentially with one
worker, 2 GiB address space, 105/110 CPU seconds, 115 wall seconds, and 1,500 ms
per SMT query. The retained repaired six-phase run used 13.706612 whole-child
process CPU seconds and a 130,424 KiB child peak-RSS upper bound.

Early exploratory local commands were not all individually metered. The resource
ledger conservatively charges the entire early wall interval at four CPU cores
rather than inventing utilization. Exact early fine-grained obligation counts and
provider-transfer byte totals were unavailable and are not claimed. No stress
test, GPU, swap, external model API, or large upstream archive was used.

## Reproduction boundary

A compatible host Z3 shared library is required and no solver binary is bundled
or pinned. Different installations can return different valid models or timing.
Semantic statuses, certificates, public decisions, and empty error lists are the
targets. Direct replay checks SAT witnesses but cannot certify UNSAT.

The bibliography audit is an offline consistency and completeness check against
a frozen manually verified inventory, a delivered complete dated primary-record
audit for all 83 cited keys, and a citation-context ledger. Reproduction does not
re-resolve remote records, and none of these files constitutes independent
literature review or source-content rereading. The public study does not reproduce Scorch execution. It validates three complete
clean-room source adapters conditional on source invariants, scope closure, and
unchanged downstream components. Original repository tests, native compilation,
floating-point behavior, physical sparse layout, memory ownership, and threading
remain unavailable baselines or out-of-scope semantics, not zero-valued results.

## Final clean-delivery check

The final project and standalone repository archives are extracted separately
into empty directories. All documented reproduction, summary, table-generation,
and CLI commands are rerun; semantic summaries and generated tables are compared
with the retained evidence. The paper and supplement are rebuilt from the clean
project. The retained PDFs are visually inspected page by page, and the clean
rebuilds are rendered and compared page by page with zero changed renders. The resulting record
is written to `results/delivery-check.json`.
The final clean artifact run used 9.258232 process CPU seconds and a 130,460
KiB child peak-RSS upper bound. Excluding those environment-dependent fields,
its reconciled semantic summary exactly matches the retained summary; all nine
generated TeX tables are byte-identical to the paper tables.

This check establishes packaging consistency in the same environment. It is not
independent review, cross-platform validation, or permission to submit.
