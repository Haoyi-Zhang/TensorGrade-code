# Frozen public-source study

## Selection and split

The denominator is the fixed twelve-row chronological production-commit corpus
in `data/public-corpus.csv`. The first four rows are the development segment and
the next eight form a later retrospective segment. The split is not
preregistered or blind. Unsupported records remain in the denominator as
abstentions. After source-invariant repair, three commits pass all seven gates
and nine abstain; development admits one of four and the later segment admits two
of eight. No upstream checkout, import, native build, generated kernel, or Scorch
test suite is run.

## Evidence and gates

`data/public-adapter-evidence.json` fixes the parent and child commit, immutable
file/blob locator, production-hunk disposition, source invariant, observable,
proof location, bounded cases, and negative controls for P01, P04, P06, and P08.
An admitted record requires:

1. fixed parent/child and complete changed production-file scope;
2. runtime/non-runtime disposition of every production hunk;
3. a source-derived invariant, not an adapter-only input filter;
4. a complete observable for the claimed execution;
5. a universal equality argument;
6. independently coded before/after models and target-sensitive controls; and
7. unchanged-downstream congruence to S, V, Z, M, and O.

## Records

- **P01 is abstained.** The source only asserts that some index variable exists.
  It does not require every operand or result access to be non-scalar. Three
  mixed scalar/indexed controls enter the changed region and differ. The 1--4
  operand range and finite access grammar are therefore only a validation
  boundary. The 29,222 equal successful-domain ASTs remain a candidate
  diagnostic and are not counted as admitted adapter states.
- **P04 is admitted.** Independent parent-monolith and child-helper renderers
  compare exact C++ text on 30 branch/constructor states. Coverage includes
  Comment, suppressed Comment, BlankLine, list dispatch, `ForLoop.init=None`,
  condition lists, explicit else, and `make_last_case_else=True`. Condition,
  else, and closing-brace mutants alter only the changed conditional path.
- **P06 is admitted.** Four hundred states compare complete ordered typed LLIR
  trees and persistent ordered post-maps. Fields include operands, addresses,
  calls, literals, loop bounds, updates, and bodies. Dense declarations are
  supplied as complete expressions/dependency lists, not generated from input
  readiness bits. The pre-map is read and extended by destination-name dedup;
  readiness is tested only after insertion, then ready entries are removed and
  unready entries retained in order. The post-map is threaded through calls.
  A separate ordered-list reference replays all 400 transitions and eight
  additional 22-call sequences. Three state-only controls leave returned nodes
  unchanged but fail replay. These extra diagnostics are excluded from the
  frozen 526-state and 18-mutant denominators. The original same-kind `+1`/`+2`
  node control still fails. Theorem I proves the full state transition and G7
  consumes both returned LLIR and lowerer state.
- **P08 is admitted only for the fixed production call graph.** Immutable
  child-tree call sites pass a format directly, or use `Workspace`, whose
  overridden format property is present. Ninety-six equivalence-domain cases
  match. Four absent-format controls are run separately and record parent
  `AttributeError` versus child `None`. Direct external calls in that excluded
  domain are not claimed equivalent.

## Negative controls and selection schedules

Eighteen mutants are retained across the three admitted adapters. Each mutant
has at most 64 **candidate input slots**. Execution stops at first detection and
records the actual number executed. The schedules are named literally:

- repeated developer indices;
- seeded random indices with replacement; and
- evenly spaced indices in the deterministic enumeration order.

The third schedule is not semantic-feature stratification. If a domain has fewer
than 64 cases, it is exhausted and repeated; otherwise the schedule depends on
the enumeration order. The repaired run detects 14/18, 18/18, and 18/18,
respectively, using 325, 121, and 318 actual executions. These mutants are
synthetic controls, not historical Scorch defects or a baseline for the
universal proof.

## Retrieval boundary

The artifact redistributes no upstream source. It retains immutable commit,
tree, and blob locators and clean-room adapters. The exact Scorch Apache license
is recorded in `external_resources.csv`. Reproduction of the paper's executable
models is network-free; reinspection of upstream source requires the immutable
public locators.
