from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit
from cite_refinery.external_solution_sources import scan, lookup_repository, stage_landscape_packet
from cite_refinery.external_landscape_cli import main


class ExternalSolutionSourcesTest(unittest.TestCase):
    def test_openaire_is_metadata_only_and_source_bound(self):
        urls = []
        def fetch(url):
            urls.append(url)
            return {"results": [
                {"id": "doi_dedup___::abc", "mainTitle": "Heat in informal settlements", "type": "publication"},
                {"id": None, "mainTitle": "Bad"}, {"id": "unlabeled"}]}
        result = scan("heat & housing", fetch_json=fetch)
        self.assertEqual(result["status"], "complete_fetch")
        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["authority"], "navigation_candidate_only")
        self.assertIsNone(record["evidence_layer"])
        self.assertFalse(record["outcomes_verified"])
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(parse_qs(urlsplit(urls[0]).query)["search"], ["heat & housing"])
        self.assertIn("id%3Adoi_dedup___%3A%3Aabc", record["source_url"])

    def test_dpg_local_filter_and_no_outcome_promotion(self):
        def fetch(url):
            self.assertEqual(url, "https://api.digitalpublicgoods.net/dpgs/")
            return [
                {"id": "food-rescue", "name": "Food Rescue", "description": "Food waste coordination", "stage": "DPG"},
                {"id": "monitoring-app", "name": "Monitoring", "description": "Water sensor"},
                {"id": "invalid/redirect", "name": "Food waste", "description": "malicious"}]
        result = scan("food waste", sources=("dpg",), fetch_json=fetch)
        self.assertEqual([r["external_id"] for r in result["records"]], ["food-rescue"])
        self.assertEqual(result["records"][0]["candidate_kind"], "reviewed_public_good_listing")
        self.assertFalse(result["records"][0]["outcomes_verified"])

    def test_endpoint_failure_is_partial_not_empty_complete(self):
        def fetch(_):
            raise OSError("503")
        packet = scan("urban heat", sources=("openaire", "dpg"), fetch_json=fetch)
        self.assertEqual(packet["status"], "partial")
        self.assertEqual(len(packet["provider_errors"]), 2)

    def test_exact_repository_lookup_only(self):
        urls = []
        def fetch(url):
            urls.append(url)
            return {"full_name": "example/repo", "description": "Does a thing", "stargazers_count": 9000,
                    "forks_count": 12, "archived": False, "license": "MIT"}
        result = lookup_repository("https://github.com/example/repo", fetch_json=fetch)
        self.assertEqual(result["status"], "complete_fetch")
        self.assertIn("url=https%3A%2F%2Fgithub.com%2Fexample%2Frepo", urls[0])
        self.assertEqual(result["records"][0]["metadata"]["stars"], 9000)
        self.assertFalse(result["records"][0]["outcomes_verified"])
        self.assertIsNone(result["records"][0]["evidence_layer"])

    def test_repo_identity_mismatch_fails_closed(self):
        result = lookup_repository("alice/project", fetch_json=lambda _: {"full_name": "bob/other"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["records"], [])

    def test_untrusted_url_rejected(self):
        for value in ["https://127.0.0.1/private", "http://github.com/alice/repo",
                      "https://github.com/alice/repo?secret=1", "https://github.com@evil.com/a/b",
                      "alice/../private", "alice/repo/extra", "alice/.git"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                lookup_repository(value, fetch_json=lambda _: {})

    def test_queries_bounded_and_provider_allowlisted(self):
        for invalid in ("x", "z" * 121):
            with self.assertRaises(ValueError):
                scan(invalid)
        with self.assertRaises(ValueError):
            scan("food", sources=("localhost",))
        with self.assertRaises(ValueError):
            scan("food", limit=21)

    def test_staging_is_neutral_and_refuses_evidence_promotion(self):
        record = scan("urban flood", fetch_json=lambda _: {"results": [{"id": "abc", "mainTitle": "Flood risk"}]})["records"][0]
        packet = stage_landscape_packet("risk", "Flood risk", [record, record])
        self.assertEqual(len(packet["edges"]), 1)
        self.assertEqual(packet["edges"][0]["status"], "candidate")
        self.assertEqual(packet["edges"][0]["relation"], "DISCOVERED_FOR")
        self.assertTrue(all(n["layer"] == "neutral" for n in packet["nodes"]))
        self.assertEqual(packet["conversion_metadata"]["status"], "DISCOVERY_ONLY_NOT_ACCEPTED")
        bad = dict(record, promotion_authorized=True)
        with self.assertRaises(ValueError):
            stage_landscape_packet("risk", "Flood", [bad])

    def test_cli_rejects_unknown_provider_without_fetch(self):
        with self.assertRaises(SystemExit) as cm:
            main(["scan", "dogs", "--sources", "wikipedia,localhost"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
