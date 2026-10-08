"""Regression and adversarial tests for bibliography integrity."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from audit_references import audit, parse_bibtex

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "data/references.bib"
INVENTORY = ROOT / "data/reference-audit.csv"
CITATIONS = ROOT / "data/cited-reference-keys.txt"
PRIMARY_RECORDS = ROOT / "data/reference-primary-record-audit.csv"
CONTEXT_AUDIT = ROOT / "data/reference-context-audit.csv"


class ReferenceAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit(BIB, INVENTORY, CITATIONS, PRIMARY_RECORDS, CONTEXT_AUDIT)

    def test_frozen_inventory_is_consistent(self):
        self.assertTrue(self.report["passed"], self.report["errors"])
        self.assertEqual(self.report["bibliography_entries"], 83)
        self.assertEqual(self.report["inventory_rows"], 83)
        self.assertEqual(self.report["cited_keys"], 83)
        self.assertEqual(self.report["verified_inventory_records"], 83)

    def test_every_record_has_a_stable_locator(self):
        self.assertEqual(self.report["doi_records"], 77)
        self.assertEqual(self.report["stable_url_only_records"], 6)

    def test_complete_primary_record_audit_is_delivered(self):
        self.assertEqual(self.report["primary_record_checks"], 83)
        self.assertEqual(self.report["latest_primary_record_check"], "2026-10-08")
        self.assertEqual(self.report["citation_context_checks"], 83)
        self.assertEqual(self.report["latest_citation_context_check"], "2026-09-29")

    def test_current_nearest_tensor_superoptimizers_are_cited(self):
        entries = {entry["key"] for entry in parse_bibtex(BIB.read_text())}
        cited = set(CITATIONS.read_text().split())
        for key in ("wu2025mirage", "wu2026prism", "zhan2026eqiforge"):
            self.assertIn(key, entries)
            self.assertIn(key, cited)

    def test_bad_inventory_status_is_rejected(self):
        with INVENTORY.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = reader.fieldnames
        self.assertIsNotNone(fields)
        rows[0]["status"] = "unchecked"
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "reference-audit.csv"
            with bad.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            report = audit(BIB, bad, CITATIONS, PRIMARY_RECORDS)
        self.assertFalse(report["passed"])
        self.assertTrue(any("status" in error for error in report["errors"]))

    def test_unapproved_stable_host_is_rejected(self):
        with INVENTORY.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = reader.fieldnames
        target = next(row for row in rows if row["key"] == "wu2025mirage")
        target["identifier"] = "https://mirror.invalid/mirage"
        target["record_url"] = target["identifier"]
        with tempfile.TemporaryDirectory() as tmp:
            bad_inventory = Path(tmp) / "reference-audit.csv"
            bad_bib = Path(tmp) / "references.bib"
            with bad_inventory.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            bad_bib.write_text(
                BIB.read_text().replace(
                    "https://www.usenix.org/conference/osdi25/presentation/wu-mengdi",
                    "https://mirror.invalid/mirage",
                )
            )
            report = audit(bad_bib, bad_inventory, CITATIONS, PRIMARY_RECORDS)
        self.assertFalse(report["passed"])
        self.assertTrue(any("approved primary-record" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
