# Clean-extraction verification

This directory records a verification run performed from an extracted staging
archive after the final scientific, bibliographic, and writing repairs.

The extracted copy completed six sequential bounded phases: unit/adversarial
tests, the offline 83-record bibliography audit, the semantic pilot, the frozen
seed-1729 diagnostic campaign, a separately reported eight-seed post-hoc
sensitivity audit, and the public source-adapter study.  It then regenerated the
summary and all nine TeX tables, ran the three public CLI examples, rebuilt the
36-page article and 10-page supplement, checked fonts and Ghostscript rendering,
and compared both PDFs at 96 dpi.

The post-hoc audit is not added to the frozen 801-query main campaign.  It uses
the same generator family, checker, oracle, and replay code, so it is a
sensitivity check rather than independent replication or statistical evidence.
Runtime and peak RSS vary by host and are intentionally excluded from semantic
summary equality.
