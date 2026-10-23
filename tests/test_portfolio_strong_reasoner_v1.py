"""Provider-injected tests: no credentials, quota or network required."""
import unittest
from cite_refinery.external_llm_runtime import _parse_response, LLMUnavailable
from cite_refinery.portfolio_strong_reasoner import run_evaluation


def fixture():
    return {
        "private_repositories_included": 0,
        "atlas_actual_semantic_graph_ingested": True,
        "source_snapshots": [
            {"repo": "alpha", "head_sha": "1"*40},
            {"repo": "beta", "head_sha": "2"*40},
        ],
        "packet": {"nodes": [
            {"key": "repo_alpha", "layer": "program",
             "statement": "Alpha maintains research provenance records and evidence receipts.",
             "source_refs": ["https://github.com/Spectating101/alpha/blob/pin/README.md"]},
            {"key": "repo_beta", "layer": "program",
             "statement": "Beta maintains reproducible dataset exports and research records.",
             "source_refs": ["https://github.com/Spectating101/beta/blob/pin/README.md"]},
        ], "edges": []},
    }


def answer(repo):
    node = "repo_" + repo
    quote = ("Alpha maintains research provenance records"
             if repo == "alpha"
             else "Beta maintains reproducible dataset exports")
    return {
        "capabilities": [{
            "statement": "The source claims an evidence handling capability.",
            "verdict": "self_reported", "evidence_ids": [node],
            "quote": quote,
            "rationale": "This is a repository description, not verified field deployment."
        }],
        "limitations": [{
            "statement": "Independent institutional adoption is not established.",
            "verdict": "insufficient", "evidence_ids": [],
            "quote": "",
            "rationale": "No independent outside evidence was provided in this graph."
        }],
        "integration_candidates": [],
        "competitor_substitutions": [],
        "decision": "investigate",
        "decision_rationale": "Inspect code and independent evidence before a release decision.",
        "unanswered_questions": ["Are there verified deployments outside the lab?"],
    }


class StrongReasonerTests(unittest.TestCase):
    def test_existing_parser_accepts_portfolio_shapes(self):
        self.assertEqual(_parse_response(answer("alpha"))["decision"], "investigate")
        self.assertEqual(_parse_response({"opportunities":[]}), {"opportunities":[]})

    def test_authenticated_provider_adapter_invoked_for_each_project(self):
        used = []
        def invoke(prompt, **kwargs):
            used.append((prompt, kwargs))
            repo = "alpha" if "repo_alpha" in prompt else "beta"
            return {"raw": answer(repo)}
        report = run_evaluation(fixture(), provider="antigravity",
                                model="gemini-4-argon-medium", invoke=invoke)
        self.assertEqual(report["model_invocation_attempts"], 2)
        self.assertEqual(report["schema_valid_count"], 2)
        self.assertEqual(report["substantive_candidate_count"], 2)
        self.assertFalse(report["no_independent_claim_entailment_validation"] is False)
        self.assertEqual(used[0][1]["provider"], "antigravity")
        self.assertEqual(used[0][1]["model"], "gemini-4-argon-medium")

    def test_partial_failure_kept_as_failure_without_fallback(self):
        calls = []
        def invoke(prompt, **kwargs):
            calls.append(prompt)
            if "repo_beta" in prompt:
                raise LLMUnavailable("quota")
            return {"raw": answer("alpha")}
        report = run_evaluation(fixture(), provider="antigravity",
                                model="claude-opus-5-5-medium",
                                invoke=invoke, cross_project=True)
        self.assertEqual(report["schema_valid_count"], 1)
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["cross_project"]["status"], "not_attempted")
        self.assertEqual(len(calls), 2)

    def test_cross_project_stays_candidate_only(self):
        def invoke(prompt, **kwargs):
            if "at most 24" in prompt:
                return {"raw": {"opportunities": []}}
            return {"raw": answer("alpha" if "repo_alpha" in prompt else "beta")}
        report = run_evaluation(fixture(), provider="antigravity",
                                model="gemini-4-argon-medium",
                                invoke=invoke, cross_project=True)
        self.assertEqual(report["cross_project"]["status"], "candidate_only")
        self.assertEqual(report["cross_project"]["candidate_count"], 0)

    def test_private_receipts_rejected_before_model_calls(self):
        data = fixture()
        data["private_repositories_included"] = 1
        with self.assertRaisesRegex(ValueError, "PUBLIC"):
            run_evaluation(data, provider="antigravity",
                           model="gemini-4-argon-medium",
                           invoke=lambda *_a,**_k: self.fail("should not call"))

    def test_model_is_explicit_not_weak_fallback(self):
        with self.assertRaisesRegex(ValueError, "explicit model"):
            run_evaluation(fixture(),provider="antigravity",model="",
                           invoke=lambda *_a,**_k: self.fail("should not call"))


if __name__ == "__main__":
    unittest.main()
