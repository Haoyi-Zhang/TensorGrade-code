# Frozen public-commit selection and split

## Denominator

The fixed denominator is the twelve-row chronological sequence in
`data/public-corpus.csv`. Each row is a non-merge commit changing production
compiler, format, dispatch, or kernel source. Intervening documentation-only,
benchmark-only, or tests-only commits are excluded by file-scope rule rather
than adapter outcome. Every unsupported selected commit remains as an
abstention.

Rows P01--P04 are the development segment. P05--P12 are the later retrospective
segment; the CSV retains `held-out` for continuity, but the segment was not
preregistered, blinded, or statistically sampled.

## Admission gates

The seven gates are frozen in `data/public-adapter-evidence.json`: fixed source
pins, complete hunk disposition, source-derived invariant, complete observable,
universal argument, independent bounded paths with discriminating controls, and
unchanged-downstream congruence. A self-authored predicate cannot establish that
an upstream state is unreachable. Failure produces abstention, not a claim that
the upstream patch is wrong.

## Repaired outcome

P01 fails the source-invariant and complete-observable gates because scalar
operands/results are source-reachable and can change behavior. P04, P06, and P08
pass under their documented conditional scopes. The final descriptive result is
three admitted and nine abstained: one of four in development and two of eight
in the later segment.

The study does not execute Scorch. Physical sparse storage, object identity,
allocation/lifetime, heuristic scheduling, IEEE floating point, raw memory,
threading, and whole-runtime dispatch remain outside the source-adapter scope.
