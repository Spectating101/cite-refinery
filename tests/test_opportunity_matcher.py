from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_matcher import validate_input, matching_prompt, inspect_matches

PATH = Path(__file__).resolve().parents[1] / "research_materials/opportunity_conversion/semantic_match_input.json"


def material():
    return json.loads(PATH.read_text(encoding="utf-8"))


def answer():
    return {
        "matches": [{
            "problem_id": "food_pickup", "repository_id": "repo_food_rescue",
            "fit": "adaptation_hypothesis",
            "mechanism": "Pickup listings could address an identified temporal coordination problem.",
            "limitation": "The README is not an independently tested local deployment or a buyer commitment.",
            "next_test": "Verify that organization role claims and pickup eligibility survive adversarial tests.",
        }, {
            "problem_id": "dog_identity", "repository_id": "repo_foodsoft",
            "fit": "not_fit",
            "mechanism": "Food cooperative ordering functions do not identify individual animals.",
            "limitation": "A generic record system is not a photographic capture-recapture workflow.",
            "next_test": "Reject this candidate unless a separate identity capability is independently shown.",
        }],
        "boundary": "No buying, license or outcome authority derived from this proposal.",
    }


class OpportunityMatcherTests(unittest.TestCase):
    def test_meaningful_positive_and_negative_pairings(self):
        r = inspect_matches(material(), answer())
        self.assertEqual(len(r["matches"]), 2)
        self.assertEqual(r["matches"][0]["fit"], "adaptation_hypothesis")
        self.assertEqual(r["matches"][1]["fit"], "not_fit")
        self.assertFalse(r["matches"][0]["buyer_validated"])
        self.assertFalse(r["matches"][0]["rights_clearance"])
        self.assertIn("not commercial proof", r["authority"].replace("_", " "))
        self.assertIn("not topical co-occurrence", matching_prompt(material()).lower())

    def test_cannot_hallucinate_assets_or_claim_revenue(self):
        bad = answer()
        bad["matches"][0]["repository_id"] = "repo_fake"
        r = inspect_matches(material(), bad)
        self.assertEqual(len(r["rejected_candidates"]), 1)
        self.assertEqual(len(r["matches"]), 1)
        bad = answer()
        bad["matches"][0]["mechanism"] = "This proves a paid contract confirmed with the maintainer."
        r = inspect_matches(material(), bad)
        self.assertEqual(len(r["matches"]), 1)

    def test_untrusted_provider_is_not_a_credential(self):
        input_data = material()
        input_data["repositories"][0]["source_url"] = "file:///etc/passwd"
        self.assertRaises(ValueError, validate_input, input_data)
        input_data = material()
        input_data["problems"][0]["evidence_status"] = "independently_verified_effectiveness"
        self.assertRaises(ValueError, matching_prompt, input_data)

    def test_duplicate_and_oversized_are_rejected(self):
        input_data = material()
        input_data["repositories"][0]["id"] = input_data["problems"][0]["id"]
        self.assertRaises(ValueError, validate_input, input_data)
        too_long = answer()
        too_long["matches"] *= 5
        self.assertRaises(ValueError, inspect_matches, material(), too_long)

    def test_zero_matches_explicitly_allowed(self):
        r = inspect_matches(material(), {"matches": [], "boundary": "No justified match"})
        self.assertEqual(r["matches"], [])
        self.assertEqual(r["rejected_candidates"], [])


if __name__ == "__main__":
    unittest.main()
