"""No-premature-authority test suite for external OSS source consolidation."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from copy import deepcopy
import json

from cite_refinery.external_reuse_bridge import (
    SCIENCE, ORKG, science_software, orkg_papers, ftm_preview,
    consolidate_discovery,
)
from cite_refinery.external_landscape_cli import main


SCIENCE_ROW = {
    "projects": [
        {"project_id": 31, "repository_url": "https://github.com/earthlab/gauge",
         "name": "River Gauge", "description": "Source-derived river sensor toolkit",
         "science_score": 87, "matches": [{"field": "name", "value": "River Gauge"}]},
        {"project_id": 32, "repository_url": "https://github.com/other/river", "name": "Flood Index"}
    ], "next_after_id": 32,
}
ORKG_ROW = {"content": [
    {"id": "R42", "title": "Flood event methods", "verified": True,
     "identifiers": {"doi": ["10.1000/example.42"]},
     "publication_info": {"published_year": 2020},
     "extraction_method": "MANUAL"},
    {"id": "oops", "title": "Untrusted"},
]}


class ReuseBridgeTests(TestCase):
    def test_science_search_is_literal_and_not_semantic_promotion(self):
        called = []
        p = science_software("river level", limit=2,
                             fetch_json=lambda url: called.append(url) or SCIENCE_ROW)
        qs = parse_qs(urlsplit(called[0]).query)
        self.assertEqual(urlsplit(called[0]).netloc, "science.ecosyste.ms")
        self.assertEqual(urlsplit(called[0]).path, "/api/v1/software/search")
        self.assertEqual(qs["q"], ["river level"])
        self.assertEqual(qs["limit"], ["2"])
        self.assertEqual(qs["after_id"], ["0"])
        self.assertEqual(len(p["records"]), 2)
        self.assertEqual(p["next_after_id"], 32)
        self.assertFalse(p["is_semantic_search"])
        self.assertFalse(p["promotion_authorized"])
        item = p["records"][0]
        self.assertEqual(item["authority"], "navigation_candidate_only")
        self.assertEqual(item["candidate_kind"], "scientific_software_metadata")
        self.assertEqual(item["metadata"]["candidate_repository_url"], "https://github.com/earthlab/gauge")
        self.assertEqual(item["source_url"], SCIENCE + "/projects/31/search_context")
        self.assertEqual(item["metadata"]["reported_science_score"], 87)
        self.assertEqual(item["metadata"]["search_type"], "literal_substring")
        self.assertFalse(item["outcomes_verified"])
        self.assertIsNone(item["evidence_layer"])

    def test_science_exact_lookup_and_deduplicated_cursor(self):
        urls = []
        def fetch(url):
            urls.append(url)
            return {"projects": [{"project_id": 31, "name": "River"}],
                    "next_after_id": None}
        p = science_software("https://github.com/earthlab/gauge", exact_kind="repository_url",
                             after_id=31, fetch_json=fetch)
        self.assertIn("software/lookup", urls[0])
        self.assertEqual(parse_qs(urlsplit(urls[0]).query)["kind"], ["repository_url"])
        self.assertIsNone(p["next_after_id"])
        self.assertEqual(p["records"][0]["metadata"]["search_type"], "exact_identifier")

    def test_science_strict_identity_and_pagination_fail_closed(self):
        for response in [
            {"projects": [{"project_id": "31"}], "next_after_id": None},
            {"projects": [{"project_id": True}], "next_after_id": None},
            {"projects": [{"project_id": 1}, {"project_id": 2}, {"project_id": 3}], "next_after_id": None},
            {"projects": [{"project_id": 1}], "next_after_id": 0},
            {"items": []},
        ]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                science_software("river", limit=2, fetch_json=lambda _: response)
        with self.assertRaises(ValueError):
            science_software("river", limit=50, fetch_json=lambda _: SCIENCE_ROW)
        with self.assertRaises(ValueError):
            science_software("river", exact_kind="bad", fetch_json=lambda _: SCIENCE_ROW)
        with self.assertRaises(ValueError):
            science_software("river", after_id=-1, fetch_json=lambda _: SCIENCE_ROW)

    def test_orkg_is_unverified_even_when_provider_flag_is_true(self):
        urls = []
        p = orkg_papers("flood event", limit=3,
                        fetch_json=lambda u: urls.append(u) or ORKG_ROW)
        self.assertEqual(urlsplit(urls[0]).netloc, "orkg.org")
        qs = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(qs["title"], ["flood event"])
        self.assertEqual(qs["size"], ["3"])
        self.assertEqual(len(p["records"]), 1)
        a = p["records"][0]
        self.assertEqual(a["source_url"], "https://orkg.org/paper/R42")
        self.assertEqual(a["metadata"]["doi"], "10.1000/example.42")
        self.assertTrue(a["metadata"]["orkg_verified_flag"])
        self.assertFalse(a["metadata"]["semantic_finding_independently_verified"])
        self.assertFalse(a["promotion_authorized"])
        self.assertEqual(a["candidate_kind"], "structured_research_paper_metadata")

    def test_invalid_orkg_response_does_not_fake_zero_papers(self):
        with self.assertRaises(ValueError):
            orkg_papers("science", fetch_json=lambda _: {"unexpected": []})
        with self.assertRaises(ValueError):
            orkg_papers("science", limit=1, fetch_json=lambda _: ORKG_ROW)

    def test_partial_fails_closed_but_does_not_lose_other_providers(self):
        def fetch(url):
            if url.startswith(SCIENCE):
                return SCIENCE_ROW
            raise OSError("Provider not reachable")
        result = consolidate_discovery("river", limit=3, fetch_json=fetch)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["provider_errors"], {"orkg": "OSError"})
        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["accepted_claim_edges"], 0)
        self.assertFalse(result["promotion_authorized"])
        self.assertFalse(result["external_software_verified_operational"])

    def test_two_provider_staging_keeps_everything_neutral(self):
        def fetch(url):
            return SCIENCE_ROW if url.startswith(SCIENCE) else ORKG_ROW
        out = consolidate_discovery("flood", limit=3, fetch_json=fetch,
                                    module_id="gauge-mechanism",
                                    module_title="Flood station reliability")
        self.assertEqual(out["status"], "retrieval_complete_not_verified")
        self.assertEqual(len(out["records"]), 3)
        graph = out["candidate_packet"]
        self.assertEqual(len(graph["edges"]), 3)
        self.assertTrue(all(n["layer"] == "neutral" for n in graph["nodes"]))
        self.assertTrue(all(e["relation"] == "DISCOVERED_FOR" and
                            e["status"] == "candidate" for e in graph["edges"]))
        self.assertEqual(graph["conversion_metadata"]["status"],
                         "DISCOVERY_ONLY_NOT_ACCEPTED")
        self.assertFalse(out["promotion_authorized"])
        self.assertTrue(out["no_frozen_holdout_access_or_graph_mutation"])

    def test_default_provider_fetchers_respect_orkg_vendor_v2(self):
        # The production orchestrator must NOT force Science's generic-JSON
        # transport onto the versioned ORKG paper controller.
        calls = []
        def science_fetch(url):
            calls.append(("science", url))
            return SCIENCE_ROW
        def paper_v2_fetch(url):
            calls.append(("orkg_v2", url))
            return ORKG_ROW
        with patch("cite_refinery.external_reuse_bridge._fetch_json", science_fetch):
            with patch("cite_refinery.external_reuse_bridge._fetch_orkg_v2", paper_v2_fetch):
                result = consolidate_discovery("flood", limit=3)
        self.assertEqual(result["status"], "retrieval_complete_not_verified")
        self.assertEqual(len(result["records"]), 3)
        self.assertEqual([name for name, _ in calls], ["science", "orkg_v2"])
        self.assertEqual(result["provider_errors"], {})
        self.assertEqual(result["accepted_claim_edges"], 0)

    def test_ftm_local_preview_never_exports_names_or_properties(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "case.json"
            raw = {"entities": [
                {"id": "private-person-01", "schema": "Person",
                 "properties": {"name": ["Local individual"], "address": ["Sensitive"]}},
                {"id": "org-01", "schema": "Company",
                 "properties": {"name": ["Organization"]}},
                {"id": "legal-1", "schema": "LegalEntity", "properties": {}},
            ]}
            path.write_text(json.dumps(raw))
            result = ftm_preview(path, dataset_id="public_case_1")
            self.assertEqual(result["entity_count"], 3)
            self.assertEqual(result["entity_schema_counts"],
                             {"Company": 1, "LegalEntity": 1, "Person": 1})
            self.assertNotIn("Local individual", json.dumps(result))
            self.assertNotIn("private-person-01", json.dumps(result))
            self.assertEqual(result["records_imported"], 0)
            self.assertTrue(result["requires_dedicated_nocturnal_authorization"])
            self.assertFalse(result["promotion_authorized"])
            self.assertEqual(main(["ftm-preview", str(path),
                                   "--dataset-id", "public_case_1"]), 0)

    def test_ftm_missing_or_malformed_dataset_fails(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text(json.dumps([{"id": "a", "schema": "Person"}]))
            with self.assertRaises(ValueError):
                ftm_preview(path, dataset_id="..")
            with self.assertRaises(ValueError):
                ftm_preview(path, dataset_id="good_dataset", max_entities=0)
            path.write_text(json.dumps([{"schema": "Person", "properties": {}}]))
            with self.assertRaisesRegex(ValueError, "identity"):
                ftm_preview(path, dataset_id="good_dataset")

    def test_cli_rejects_invalid_source_and_partial_module_input(self):
        with self.assertRaises(SystemExit) as x:
            main(["reuse", "flood", "--sources", "localhost"])
        self.assertEqual(x.exception.code, 2)
        with self.assertRaises(SystemExit) as x:
            main(["reuse", "flood", "--module-id", "one"])
        self.assertEqual(x.exception.code, 2)
        with self.assertRaises(SystemExit) as x:
            main(["reuse", "flood", "--limit", "30"])
        self.assertEqual(x.exception.code, 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
