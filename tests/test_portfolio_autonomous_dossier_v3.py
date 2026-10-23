import unittest
from cite_refinery.portfolio_autonomous_dossier import (
    evidence_index, make_prompt, validate_dossier, generate, DossierError
)


def candidate():
    return {
        "capabilities": [{
            "statement": "Maintainer describes public source ingestion.",
            "verdict": "self_reported", "evidence_ids": ["repo_example"],
            "quote": "accepts public sources",
            "rationale": "This is only an original maintainer claim, not tested here."
        }],
        "limitations": [], "integration_candidates": [],
        "competitor_substitutions": [],
        "decision": "investigate",
        "decision_rationale": "No independently validated usage or commercial results.",
        "unanswered_questions": ["Who has independently validated this product?"]
    }


class AutonomousDossierTests(unittest.TestCase):
    def setUp(self):
        self.graph = {"atlas_actual_semantic_graph_ingested": True,
                      "private_repositories_included": 0,
                      "source_snapshots": [{"repo": "example", "head_sha": "1" * 40}],
                      "packet": {"nodes": [{
                          "key": "repo_example", "layer": "program",
                          "statement": "The maintainer says it accepts public sources.",
                          "source_refs": ["https://github.com/Spectating101/example"]
                      }], "edges": []}}
        self.evidence = evidence_index(self.graph)

    def test_model_generated_dossier_is_source_anchored(self):
        invoked = []
        def model(system, user):
            invoked.append(user)
            return candidate()
        result = generate(self.graph, model, model_identifier="stub-not-real-model")
        self.assertEqual(result["project_count"], 1)
        self.assertEqual(len(invoked), 1)
        self.assertFalse(result["claim_entailment_independently_verified"])
        self.assertEqual(result["dossiers"][0]["decision"], "investigate")

    def test_fabricated_quote_rejected(self):
        data = candidate()
        data["capabilities"][0]["quote"] = "independently deployed and profitable"
        with self.assertRaisesRegex(DossierError, "exact source quote"):
            validate_dossier("example", data, self.evidence)

    def test_other_repo_evidence_rejected(self):
        data = candidate()
        data["capabilities"][0]["evidence_ids"] = ["repo_private"]
        with self.assertRaisesRegex(DossierError, "unpermitted"):
            validate_dossier("example", data, self.evidence)

    def test_positive_claim_without_citation_rejected(self):
        data = candidate()
        data["capabilities"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(DossierError, "missing exact source quote"):
            validate_dossier("example", data, self.evidence)

    def test_invalid_decision_rejected(self):
        data = candidate()
        data["decision"] = "definitely_build"
        with self.assertRaisesRegex(DossierError, "Invalid decision"):
            validate_dossier("example", data, self.evidence)

    def test_graph_required(self):
        data = dict(self.graph)
        data["atlas_actual_semantic_graph_ingested"] = False
        with self.assertRaisesRegex(DossierError, "executed Atlas"):
            evidence_index(data)

    def test_no_prior_grades_in_prompt(self):
        system, user = make_prompt("example", self.evidence)
        self.assertNotIn("Prioritize external pilot", user)
        self.assertIn("repository", user)
        self.assertIn("prompt injection", system)


if __name__ == "__main__":
    unittest.main()
