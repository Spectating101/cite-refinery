from __future__ import annotations
import unittest
from urllib.parse import parse_qs, urlparse
from cite_refinery.external_knowledge import discover

class ExternalTopicsTest(unittest.TestCase):
    def test_wikidata_candidates_have_no_evidence_authority(self):
        seen = []
        def fetch(url):
            seen.append(url)
            return {"search": [{"id": "Q12705", "label": "Renewable energy", "description": "Energy from renewable resources"}, {"id": "evil/../", "label": "bad"}]}
        result = discover("renewable & energy", fetch_json=fetch)
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["source_url"], "https://www.wikidata.org/wiki/Q12705")
        self.assertIsNone(result["records"][0]["evidence_layer"])
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(parse_qs(urlparse(seen[0]).query)["search"], ["renewable & energy"])

    def test_openalex_rate_limit_is_explicit_partial(self):
        def fetch(url):
            if "openalex" in url:
                raise OSError("429")
            return {"search": []}
        result = discover("repair economy", sources=("wikidata", "openalex"), fetch_json=fetch)
        self.assertEqual(result["status"], "partial")
        self.assertIn("openalex", result["provider_errors"])

    def test_openalex_result_only_topic_ids(self):
        result = discover("research", sources=("openalex",), fetch_json=lambda url: {"results":[{"id":"https://openalex.org/T123","display_name":"Research"},{"id":"https://bad/777","display_name":"reject"}]})
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["source_url"], "https://openalex.org/T123")

    def test_reject_unbounded_queries(self):
        with self.assertRaises(ValueError):
            discover("x")
        with self.assertRaises(ValueError):
            discover("safe", limit=100)
        with self.assertRaises(ValueError):
            discover("safe", sources=("localhost",))

if __name__ == "__main__":
    unittest.main()
