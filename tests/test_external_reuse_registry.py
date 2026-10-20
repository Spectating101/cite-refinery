"""Governance contract: reconnaissance cannot silently become authority or alter freeze scope."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "research_materials/external_landscape/reuse_registry_v1.json"


class ReuseRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_frozen_holdout_receipt_and_scope(self):
        frozen = self.data["freeze"]
        self.assertEqual(self.data["schema"], "cite_refinery.external_reuse_registry.v1")
        self.assertEqual(frozen["state"], "evaluation_first")
        self.assertEqual((frozen["corpus_unique_sources"], frozen["new_development_sources"],
                          frozen["holdout_sources"]), (232, 103, 66))
        self.assertEqual(frozen["holdout_sha256"],
            "282f2595728f970f29fc3c208d86a8992b96dcbb6f11a8f7d7e1b3e26de1ea00")
        self.assertTrue(frozen["no_new_corpus_collection"])
        self.assertTrue(frozen["no_new_unvalidated_feature_expansion"])

    def test_registry_unique_explicit_and_not_invented_connectors(self):
        rows = self.data["records"]
        self.assertGreaterEqual(len(rows), 25)
        names = [r["id"] for r in rows]
        self.assertEqual(len(names), len(set(names)))
        for record in rows:
            with self.subTest(id=record["id"]):
                self.assertTrue(record["url"].startswith("https://"))
                self.assertTrue(record["capability"])
                self.assertTrue(record["action"])
                self.assertTrue(record["reuse_for"])
                self.assertIn(record["status"], {
                    "reference_only", "adapter_available", "adapter_code_added_unverified_live",
                    "adapter_live_smoke", "existing_other_modules", "existing_optional_engine"})
        self.assertEqual(next(r["status"] for r in rows if r["id"] == "dpg-registry"),
                         "adapter_code_added_unverified_live")
        self.assertEqual(next(r["status"] for r in rows if r["id"] == "openaire"), "adapter_live_smoke")


if __name__ == "__main__":
    unittest.main()
