# Literature and source-reading scope

Final calibration date: 2026-09-29. Bibliographic details used by the manuscript
are in `paper/references.bib` in the full project; the standalone artifact retains
primary workflow/source locators in `external_resources.csv`. The main paper has
83 distinct cited references.

## Anchor and closest technical work

The motivating source was verified as *TensorBench: Benchmarking Coding Agents on
a Compiler-Based Tensor Framework* by Bobby Yan and Fredrik Kjolstad, public on
2026-06-04. Its repository-task and test-based grading role motivates the
distinction between passing examples and universal semantic contracts. No
TensorBench task archive or model-generated patch set is redistributed or run.

Closest technical comparisons cover:

- SMT-based translation validation for machine-learning compilers;
- verified high-level tensor scheduling rewrites;
- Tenspiler's verified lifting for tensor operations;
- TensorRight's tensor-graph rewrite verification;
- Prism's symbolic tensor-program optimization;
- Mirage's multi-level tensor-program superoptimization;
- EquiForge's equality-saturation tensor-program superoptimization; and
- classic translation validation, Alive/Alive2, CompCert, abstract
  interpretation, symbolic execution, and solver foundations.

The comparison is claim-specific. Mirage and EquiForge search for profitable
fully equivalent implementations, whereas this work classifies which declared
observations remain universally equal when a supplied pair may fail full
equivalence. The paper does not attribute mechanization, floating-point coverage,
end-to-end runtime proofs, or synthesis results from those systems to this
artifact.

## TOSEM structural calibration

Twelve full TOSEM research articles were used to calibrate problem framing,
method/evidence separation, RQ presentation, threats, artifact reporting, and use
of tables/figures:

1. Offutt, software-testing coupling effect (1992).
2. Jackson, Alloy (2002).
3. Durante, Sisto, and Valenzano, testing-equivalence verification (2003).
4. Gao et al., crash-constraint program repair (2021).
5. Sun et al., feedback-directed metamorphic testing (2023).
6. Xu et al., MR-Scout (2024).
7. Liu et al., generation-based differential fuzzing for DL libraries (2024).
8. Xia et al., bounded valid-program enumeration (2024).
9. Harzevili et al., history-driven DL-library fuzzing (2025).
10. Wu et al., attribute-guided compiler testing (2026).
11. Lee et al., feature-sensitive conformance coverage (2026).
12. Li et al., multi-configuration compiler fault isolation (2026).

Five influential foundations—symbolic execution, abstract interpretation, KLEE,
CSmith, and Alive2—and at least five adjacent tensor/compiler-verification papers
were also calibrated. The compact pattern matrix and full source list are in
`research-plan.md`. No award status, citation-count threshold, or acceptance
prediction is asserted.

Available full text or publisher HTML was inspected for substantive method,
evaluation, and threat structure. Metadata-only pages were not used for
content-specific scientific claims. The manuscript favors original papers and
formal records over blogs or search snippets. A complete 2026-09-29 primary-record metadata audit covers all 83 cited keys,
including Mirage and EquiForge; it is retained as
`data/reference-primary-record-audit.csv`;
`data/reference-context-audit.csv` separately maps every key to its main-paper
use. The offline reproduction checks both frozen files but does not present them
as independent review or source-content rereading.

## Public source reading

The complete twelve-row Scorch denominator, decisions, changed production files,
and URLs are in `data/public-corpus.csv`. Three admitted diffs received complete
source-region reasoning; the nine abstentions were inspected far enough to
identify the unresolved semantic boundary. Long machine/runtime diffs were not
pretended to be fully modeled. No upstream source is bundled or executed.

The official TOSEM author guide and ACM submission pages returned HTTP 403 at the
2026-09-29 final recheck. This accessibility failure affects submission-readiness
verification, not the scholarly claims. The supplied current ACM template remains
the internal layout basis.
