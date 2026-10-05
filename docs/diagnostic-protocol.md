# Frozen diagnostic and public-adapter protocols

## Semantic diagnostics

The 64-case diagnostic input set was frozen on 2026-09-14 with seed 1729.
Every case is admitted, refuted, or abstained without retry tuning. The retained
main counts remain 801 symbolic queries including admission checks, 167 independently replayed finite
refutations, and 162 compact certificates. The fixed-shape oracle is not an
all-shapes decision.

A separate post-hoc sensitivity audit uses eight additional seeds and 32 cases
per seed. Its 256 cases, 2,048 queries, 512 oracle checks, and 500 replayed
compact certificates are never added to the frozen main counts. The audit reuses
the same generator family, checker, oracle, and replay paths; it probes dependence
on one seed but is not independent replication or statistical evidence.

## Public source adapters

The twelve-row denominator and development/later split remain fixed. Source
repair changes the decision for P01 but does not remove it from the denominator.
Three complete adapters remain: P04, P06, and P08. Their bounded state counts are
30, 400, and 96. P01's 29,222 successful-domain states are retained separately
as candidate diagnostics after three source-reachable scalar boundary controls
invalidate full admission.

Each of 18 admitted-adapter mutants receives at most 64 candidate input slots.
Selection stops at first detection and records actual executions. The schedules
are repeated developer indices, seeded random indices with replacement, and an
even grid over deterministic enumeration indices. The even grid is not semantic
feature stratification; small domains are exhausted and then repeated, and large
domains inherit enumeration-order dependence.

## Resource and retention rules

Use one worker. Each reproduction child has a 2 GiB address-space limit,
105/110 CPU-second soft/hard limits, and a 115-second wall timeout. SMT queries
use 1,500 ms. Retain exact inputs, rejected controls, raw decisions, replay
outcomes, public abstentions, candidate-slot schedules, first detection slots,
actual executions, and process measurements. After repairs, rerun all six
phases from a clean extraction.
