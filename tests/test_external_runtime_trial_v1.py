"""Live experiment support must remain falsifiable and source-span bounded."""
import unittest
import asyncio
import json
from cite_refinery.external_engines import lightrag_propose
from cite_refinery.external_evidence_audit import (
    verify_source_span, detect_explicit_link_misread,
)
from scripts.external_grounding_trial_v1 import classify_yes_no


class SourceSpanIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.quote = "HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters"
        self.source = {
            "id": "WMO-HYDROSOS", "url": "https://wmo.int/activities/hydrosos",
            "text": "WMO informs countries.  " + self.quote + " and thus supports local resilience.",
        }

    def test_literal_source_quote_pins_and_never_asserts_entailment(self):
        got = verify_source_span(self.source, self.quote)
        self.assertTrue(got["literal_quote_found"])
        self.assertEqual(got["status"], "verbatim_span_present_not_entailment")
        self.assertTrue(got["source_passage_sha256"])
        self.assertIn("not semantic entailment", got["boundary"])

    def test_source_span_detection_rejects_quote_not_in_source(self):
        got = verify_source_span(self.source, "HydroSOS demonstrably saved twenty lives.")
        self.assertFalse(got["literal_quote_found"])
        self.assertEqual(got["status"], "quote_not_in_source")

    def test_explicit_link_flags_incorrect_negative_even_after_retrieval(self):
        negative = detect_explicit_link_misread(
            self.source, model_decision="no", exact_span=self.quote,
            subject="HydroSOS", object_name="Early Warnings for All")
        self.assertTrue(negative["potential_source_contradiction"])
        self.assertEqual(negative["status"], "manual_review_required")
        positive = detect_explicit_link_misread(
            self.source, model_decision="yes", exact_span=self.quote,
            subject="HydroSOS", object_name="Early Warnings for All")
        self.assertFalse(positive["potential_source_contradiction"])
        false_source = detect_explicit_link_misread(
            self.source, model_decision="no",
            exact_span="HydroSOS supports no relationship with other systems",
            subject="HydroSOS", object_name="Early Warnings for All")
        self.assertFalse(false_source["potential_source_contradiction"])

    def test_lightrag_candidate_requires_literal_source_quote_when_enabled(self):
        quote = self.quote
        ref = self.source["url"]
        class GraphEngine:
            async def ainsert(self, text):
                self.inserted = text
            async def aquery(self, prompt, param):
                return json.dumps({"proposals": [
                    {"source": "WA-06", "target": "DR-01", "relation": "CONTEXT_FOR",
                     "evidence_refs": [ref], "evidence_quotes": {ref: quote}},
                    {"source": "WA-06", "target": "DR-01", "relation": "CONTEXT_FOR",
                     "evidence_refs": [ref], "evidence_quotes": {ref: "This does not exist in the cited source"}},
                ]})
        result = asyncio.run(lightrag_propose(
            GraphEngine(), source_text=self.source["text"],
            module_ids={"WA-06", "DR-01"}, source_refs={ref}, query_param=object(),
            source_passages={ref: self.source["text"]}))
        self.assertEqual(len(result["proposals"]), 1)
        self.assertEqual(result["rejected_proposals"], 1)
        self.assertTrue(result["proposals"][0]["source_span_checks"][0]["literal_quote_found"])
        self.assertEqual(result["proposals"][0]["status"], "candidate")

    def test_response_labeler_not_a_groundedness_estimator(self):
        self.assertEqual(classify_yes_no("No. This does not establish field outcomes."), "no")
        self.assertEqual(classify_yes_no("Yes. Source explicitly says so."), "yes")
        self.assertEqual(classify_yes_no("Cannot determine from memory"), "unparseable")


if __name__ == "__main__":
    unittest.main()
