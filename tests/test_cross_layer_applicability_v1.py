"""Three-layer evidence entailment ≠ matched publisher quote ≠ field implementation."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.cross_layer_review import (
    preflight, critic_prompt, apply_critic, assess, SCHEMA, RESULT_SCHEMA,
)
from cite_refinery.investigation_controller import InvestigationController
from cite_refinery.layered_cli import main as canonical_main

SOURCE_TEXT={
 "practical":"The map initially centers thousands of miles away from the intended geographic region due to an outlier geocode in user data.",
 "academic":"Geocoding error distributions are not normal and often contain a number of very large positional error values.",
 "implementation":"calculateAngle = (angles) -> Math.min.apply(null,angles) + (Math.max.apply(null,angles) - Math.min.apply(null,angles)) / 2",
}
FAMILY={"practical":"P","academic":"A","implementation":"I"}

def sample():
    return {"schema":SCHEMA,"links":[{
        "id":"BR-01",
        "practical_problem":"An operator-reported map starts in an incorrect geographic region.",
        "academic_mechanism":"Large positional outliers can distort geographic data calculations.",
        "implementation_claim":"An upstream map center algorithm calculates midpoint using coordinate extremes.",
        "requested_outcome":"Evaluate whether a robust location policy can improve initial geographic map views.",
        "disconfirming_test":"Use a realistic country-wide map dataset with invalid and legitimate distant coordinates.",
        "source_anchors":{
            family:{"source_id":"USR-"+FAMILY[family]+"-01",
                    "quote":SOURCE_TEXT[family][:70]}
            for family in FAMILY
        },
    }]}

def state():
    sources=[]
    receipts=[]
    for family,text in SOURCE_TEXT.items():
        sid="USR-"+FAMILY[family]+"-01"
        digest=sha256(text.encode()).hexdigest()
        url=f"https://example.org/{sid}"
        sources.append({
            "id":sid,"source_family":family,"url":url,"text":text,
            "text_sha256":digest,"source_scope":"Unverified real-world outcomes, source matched only."
        })
        receipts.append({
            "id":sid,"family":family,"url":url,"text_sha256":digest,
            "status":"publisher_passage_matched_claim_unreviewed",
            "source_claim_verified":False,"authority":"NONE_ACCEPTED",
        })
    return {"id":"example-investigation","supplied_sources":sources,
            "source_authentication":receipts,"authority":"candidate_neutral_only",
            "stage":"plan"}

def verdict(*,relation="mechanistically_relevant",implementation="candidate_only",
            practical="entailed_as_source_statement",academic="partially_supported",
            implementation_fit="partially_supported",outcome=False):
    return {"schema":"cite_refinery.cross_layer_critic.v1",
            "reviews":[{
                "id":"BR-01","practical_fit":practical,
                "academic_fit":academic,"implementation_fit":implementation_fit,
                "cross_layer_relation":relation,"implementation_readiness":implementation,
                "outcome_supported":outcome,
                "rationale":"The source passages are relevant to a shared potential mechanism but do not establish field outcomes or a working fix.",
                "missing_tests":["Execute an outlier-resistant implementation against real user data and confirm geography."]
            }]}

class CrossLayerEntailmentTests(unittest.TestCase):
    def test_real_source_text_receipts_do_not_prove_implementation(self):
        base=preflight(state(),sample())
        self.assertEqual(base[0]["status"],"publisher_anchors_matched_semantics_unreviewed")
        self.assertFalse(base[0]["automatic_semantic_entailment"])
        self.assertFalse(base[0]["implementation_functional_fit_verified"])
        self.assertEqual(base[0]["bridge_authority"],"CANDIDATE_ONLY")
        prompt=critic_prompt(state(),sample(),base)
        self.assertIn("implementation",prompt)
        self.assertIn("mechanistic",prompt.lower())
        result=assess(state(),sample(),critic=lambda prompt:verdict(),
                      model_metadata={"provider":"test","model":"stub"})
        self.assertEqual(result["rows"][0]["status"],
                         "plausible_mechanism_not_established_solution")
        self.assertFalse(result["all_source_materials_external_facts_verified"])
        self.assertFalse(result["graph_write_performed"])
        self.assertFalse(result["scientific_claims_accepted"])
        self.assertFalse(result["independent_buyer_or_revenue_proven"])

    def test_unrelated_heat_paper_or_claim_is_criticized_as_mismatch(self):
        result=assess(state(),sample(),critic=lambda _:verdict(
            relation="mismatched",academic="unsupported"))
        self.assertEqual(result["rows"][0]["status"],
                         "reviewer_reports_mismatch_or_contradiction")
        self.assertEqual(result["rows"][0]["graph_authority"],"CANDIDATE_ONLY")

    def test_one_invalid_source_does_not_prevent_unrelated_matched_link_critique(self):
        p=deepcopy(sample())
        second=deepcopy(p["links"][0])
        second["id"]="BR-02"
        second["source_anchors"]["academic"]["quote"]="This fabricated article passage never appeared in any publisher original."
        p["links"].append(second)
        seen=[]
        def critic(prompt):
            payload=json.loads(prompt.split("INPUT:",1)[1].strip())
            seen.append([row["id"] for row in payload["links"]])
            return verdict()
        response=assess(state(),p,critic=critic)
        self.assertEqual(seen,[["BR-01"]])
        self.assertEqual(response["rows"][0]["status"],
                         "plausible_mechanism_not_established_solution")
        self.assertEqual(response["rows"][1]["status"],"evidence_preflight_blocked")
        self.assertFalse(response["graph_write_performed"])

    def test_malformed_model_verdict_is_preserved_as_rejected_digest(self):
        malformed=verdict(outcome=True)
        result=assess(state(),sample(),critic=lambda _:malformed,
                      model_metadata={"provider":"test","model":"rejected"})
        row=result["rows"][0]
        self.assertEqual(row["status"],"critic_output_invalid_untrusted")
        self.assertIn("unsupported acceptance",row["critic_contract_error"])
        self.assertEqual(len(row["critic_response_sha256"]),64)
        self.assertEqual(row["graph_authority"],"CANDIDATE_ONLY")
        self.assertFalse(result["graph_write_performed"])
        self.assertFalse(result["scientific_claims_accepted"])

    def test_model_cannot_self_assert_original_component_testing(self):
        result=assess(state(),sample(),critic=lambda _:verdict(
            implementation="demonstrated_outcome"))
        self.assertEqual(result["rows"][0]["status"],
                         "reviewer_claimed_unverified_implementation_testing")
        self.assertFalse(result["rows"][0]["implementation_functional_fit_verified"])
        self.assertFalse(result["graph_write_performed"])

    def test_missing_or_tampered_publisher_receipt_blocks_link(self):
        wrong=deepcopy(state())
        wrong["source_authentication"][1]["status"]="submitted_text_does_not_match_publisher"
        pre=preflight(wrong,sample())
        self.assertEqual(pre[0]["status"],"evidence_preflight_blocked")
        self.assertIn("academic:publisher_text_not_matched_or_authority_inflated",
                      pre[0]["failures"])
        called=[]
        result=assess(wrong,sample(),critic=lambda prompt:called.append(prompt))
        self.assertEqual(called,[])
        self.assertEqual(result["rows"][0]["status"],"evidence_preflight_blocked")
        wrong=deepcopy(state())
        wrong["supplied_sources"][2]["text"]="Supplied code changed without publisher review."
        result=preflight(wrong,sample())
        self.assertIn("implementation:quote_not_in_supplied_passage",
                      result[0]["failures"])
        self.assertIn("implementation:source_or_receipt_identity_mismatch",
                      result[0]["failures"])

    def test_critic_cannot_self_promote_outcome_or_replace_ids(self):
        pre=preflight(state(),sample())
        with self.assertRaisesRegex(ValueError,"unsupported acceptance"):
            apply_critic(pre,verdict(outcome=True))
        with self.assertRaisesRegex(ValueError,"identities"):
            forged=verdict()
            forged["reviews"][0]["id"]="BR-02"
            apply_critic(pre,forged)
        with self.assertRaisesRegex(ValueError,"Critic"):
            forged=verdict()
            forged["reviews"][0]["implementation_readiness"]="production_ready"
            apply_critic(pre,forged)
        with self.assertRaisesRegex(ValueError,"unauthenticated"):
            wrong=deepcopy(pre);wrong[0]["status"]="evidence_preflight_blocked"
            apply_critic(wrong,verdict())

    def test_untrusted_link_input_fails_without_acceptance(self):
        for modifier in (
            lambda x:x["links"][0]["source_anchors"]["practical"].update(
                quote="hallucinated location that appears nowhere"),
            lambda x:x["links"].append(deepcopy(x["links"][0])),
            lambda x:x.update(schema="accepted_causal_link.v4"),
            lambda x:x["links"][0].update(authority="qualified"),
        ):
            p=deepcopy(sample());modifier(p)
            if p["schema"]!=SCHEMA or "authority" in p["links"][0] or len(p["links"])!=1:
                with self.assertRaises(ValueError):
                    preflight(state(),p)
            else:
                pre=preflight(state(),p)
                self.assertEqual(pre[0]["status"],"evidence_preflight_blocked")

    def test_source_identity_reuse_is_rejected_at_schema_gate(self):
        p=deepcopy(sample())
        p["links"][0]["source_anchors"]["implementation"]["source_id"]="USR-A-01"
        with self.assertRaisesRegex(ValueError,"masquerade"):
            preflight(state(),p)

    def test_controller_persists_canonical_preflight_without_graph_write(self):
        with TemporaryDirectory() as td:
            c=InvestigationController(td,reasoner=lambda p:{})
            s=c.start("Can a map outlier problem be linked to a testable software intervention?",
                    [{"id":"RQ-01","title":"Geocode quality",
                      "summary":"Unverified need and unverified mechanisms"}])
            s["supplied_sources"]=state()["supplied_sources"]
            s["source_authentication"]=state()["source_authentication"]
            c.save(s)
            report=c.assess_cross_layer_links(s["id"],sample())
            self.assertEqual(report["schema"],RESULT_SCHEMA)
            self.assertEqual(report["rows"][0]["status"],
                             "publisher_anchors_matched_semantics_unreviewed")
            restored=c.load(s["id"])
            self.assertEqual(restored["authority"],"candidate_neutral_only")
            self.assertEqual(len(restored["cross_layer_assessments"]),1)
            self.assertEqual(len(restored["rounds"]),0)
            self.assertEqual(restored["stage"],"plan")

if __name__=="__main__":
    unittest.main()
