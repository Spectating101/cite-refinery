"""Operator delivery links only exact source-checked, bounded runtime receipts.

One canonical CLI command, no additional CLI scripts or evidence authority.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest
import tomllib

from cite_refinery.operator_delivery import build, render_markdown, SCHEMA
from cite_refinery.investigation_controller import InvestigationController
from cite_refinery.layered_cli import main as canonical_main

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=json.loads((ROOT/"research_materials/opportunity_atlas/framework_scoped_integration.json").read_text())
PINS=FRAMEWORK["source_checks"]

def make_state():
    cases=[]
    src=[]
    auth=[]
    fixtures=(
        ("openfoodnetwork","openfoodfoundation/openfoodnetwork",
         "app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee",
         "1167aa7b7585c1794199e032fc15c0e9c1c74104","USR-I-01","BR-01",
         "semantic_fit_uncertain"),
        ("foodsoft","foodcoops/foodsoft","app/helpers/orders_helper.rb",
         "f594be8e64f4d3748d0e418df05fbb554ccce71b","USR-I-02","BR-02",
         "reviewer_reports_mismatch_or_contradiction")
    )
    for key,repo,path,commit,sid,bridge,status in fixtures:
        url=f"https://github.com/{repo}/blob/{commit}/{path}"
        text="Pinned source fragment with a bounded test that cannot prove the original full application works."
        digest=hashlib.sha256(text.encode()).hexdigest()
        src.append({"id":sid,"source_family":"implementation","url":url,"text":text,
                    "text_sha256":digest,"source_scope":"Publisher matched source not working product"})
        auth.append({"id":sid,"url":url,"family":"implementation","text_sha256":digest,
                     "status":"publisher_passage_matched_claim_unreviewed",
                     "publisher_git_blob_sha":PINS[key]["blob"],
                     "authority":"NONE_ACCEPTED","source_claim_verified":False})
        cases.append({
            "id":bridge,"status":status,
            "family_receipts":{
                "implementation":{"source_id":sid,"publisher_text_verified":True},
                "practical":{"source_id":"P-"+key,"publisher_text_verified":True},
                "academic":{"source_id":"A-"+key,"publisher_text_verified":True}
            },
            "critic":{
                "cross_layer_relation":"mismatched" if key=="foodsoft" else "uncertain",
                "academic_fit":"unsupported" if key=="foodsoft" else "partially_supported",
                "missing_tests":["Run the complete original application suite and inspect a real operational dataset."]
            }
        })
    return {
        "id":"test-session","question":"Can the observed software defects be reproduced and corrected?",
        "supplied_sources":src,"source_authentication":auth,
        "cross_layer_assessments":[{
            "schema":"cite_refinery.cross_layer_applicability_review.v1",
            "graph_write_performed":False,"rows":cases
        }]
    }

class OperatorDeliveryTests(unittest.TestCase):
    def test_both_exact_git_blob_matches_attach_scope_not_commercialization(self):
        report=build(make_state(),repo_root=ROOT)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(len(report["case_decisions"]),2)
        first,second=report["case_decisions"]
        self.assertEqual(first["bounded_component_executable_receipt"]["project"],
                         "openfoodfoundation/openfoodnetwork")
        self.assertEqual(second["bounded_component_executable_receipt"]["project"],
                         "foodcoops/foodsoft")
        self.assertEqual((first["bounded_component_executable_receipt"]["original_tests"],
                          first["bounded_component_executable_receipt"]["original_failures"],
                          first["bounded_component_executable_receipt"]["experimental_candidate_failures"]),
                         (14,4,0))
        self.assertEqual((second["bounded_component_executable_receipt"]["original_tests"],
                          second["bounded_component_executable_receipt"]["original_failures"],
                          second["bounded_component_executable_receipt"]["experimental_candidate_failures"]),
                         (9,3,0))
        self.assertNotEqual(second["bounded_component_executable_receipt"]["publisher_source_commit"],
                            second["bounded_component_executable_receipt"]["curated_original_source_commit"])
        self.assertTrue(second["bounded_component_executable_receipt"]["same_source_bytes_proven"])
        self.assertIn("VALIDATE next",first["delivery_action"])
        self.assertIn("REJECT",second["delivery_action"])
        self.assertFalse(report["buyer_interest_verified"])
        self.assertEqual(report["pilot_sales_and_revenue"],0)
        self.assertEqual(report["total_full_application_approvals"],0)
        self.assertFalse(report["legal_and_licensing_cleared"])
        text=render_markdown(report)
        self.assertIn("10/14",text)
        self.assertIn("9/9",text)
        self.assertIn("NOT complete application",text)
        self.assertIn("Not a paid result",text)

    def test_source_attestation_prevents_false_runtime_merge(self):
        base=make_state()
        mutators=[
            lambda s:s["source_authentication"][0].update(publisher_git_blob_sha="0"*40),
            lambda s:s["source_authentication"][0].update(status="submitted_text_does_not_match_publisher"),
            lambda s:s["source_authentication"][0].update(source_claim_verified=True),
            lambda s:s["supplied_sources"][0].update(url="https://github.com/another/repo/blob/"+PINS["openfoodnetwork"]["commit"]+"/"+PINS["openfoodnetwork"].get("path","any")),
            lambda s:s["source_authentication"][0].update(text_sha256="f"*64),
            lambda s:s["source_authentication"][0].update(authority="VERIFIED"),
        ]
        for mutate in mutators:
            edited=deepcopy(base)
            mutate(edited)
            rows=build(edited,repo_root=ROOT)["case_decisions"]
            self.assertIsNone(rows[0]["bounded_component_executable_receipt"])
            self.assertIsNotNone(rows[1]["bounded_component_executable_receipt"])
            self.assertIn("INSUFFICIENT",rows[0]["delivery_action"])

    def test_explicit_curated_artifact_supports_wheel_without_source_checkout(self):
        with TemporaryDirectory() as td:
            input_path=ROOT/"research_materials/opportunity_atlas/framework_scoped_integration.json"
            file=Path(td)/"scoped_artifact.json"
            file.write_bytes(input_path.read_bytes())
            data=build(make_state(),repo_root=Path(td),framework_artifact=file)
            self.assertEqual(len(data["case_decisions"]),2)
            self.assertTrue(data["case_decisions"][0]["bounded_component_executable_receipt"])

    def test_artifact_digest_mismatch_fails_closed_without_output(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            dst=root/"research_materials/opportunity_atlas"
            dst.mkdir(parents=True)
            contents=(ROOT/"research_materials/opportunity_atlas/framework_scoped_integration.json").read_bytes()
            (dst/"framework_scoped_integration.json").write_bytes(contents+b" ")
            with self.assertRaisesRegex(ValueError,"fingerprint"):
                build(make_state(),repo_root=root)

    def test_rejected_candidate_cannot_be_made_positive_by_runtime_only(self):
        state=make_state()
        report=build(state,repo_root=ROOT)
        self.assertIn("REJECT",report["case_decisions"][1]["delivery_action"])
        state["cross_layer_assessments"][-1]["rows"][0]["status"]="evidence_preflight_blocked"
        report=build(state,repo_root=ROOT)
        self.assertIn("REJECT until valid",report["case_decisions"][0]["delivery_action"])

    def test_absence_of_semantic_assessment_is_not_a_delivery(self):
        s=make_state()
        s.pop("cross_layer_assessments")
        with self.assertRaisesRegex(ValueError,"assess-links"):
            build(s,repo_root=ROOT)
        s=make_state()
        s["cross_layer_assessments"][0]["graph_write_performed"]=True
        with self.assertRaisesRegex(ValueError,"candidate-only"):
            build(s,repo_root=ROOT)

    def test_canonical_operator_brief_outputs_two_inspectable_files_without_new_cli(self):
        with TemporaryDirectory() as td:
            base=Path(td)
            ctrl=InvestigationController(base,reasoner=lambda _:None)
            session=ctrl.start("Can validated source tests help an operator?",
                [{"id":"RQ-01","title":"Original source scope",
                "summary":"Source text and runtime are separate evidence types"}])
            modified=ctrl.load(session["id"])
            fixture=make_state()
            modified["supplied_sources"]=fixture["supplied_sources"]
            modified["source_authentication"]=fixture["source_authentication"]
            modified["cross_layer_assessments"]=fixture["cross_layer_assessments"]
            ctrl.save(modified)
            args=["investigate","--workspace",td,"operator-brief","--id",session["id"],
                  "--markdown-out",str(base/"deliver.md"),
                  "--json-out",str(base/"deliver.json")]
            stdout=StringIO()
            with redirect_stdout(stdout):
                canonical_main(args)
            result=json.loads(stdout.getvalue())
            self.assertEqual(result["cases"],2)
            self.assertEqual(result["attached_scoped_runtime_receipts"],2)
            self.assertTrue((base/"deliver.md").is_file())
            self.assertEqual(json.loads((base/"deliver.json").read_text())["schema"],SCHEMA)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                canonical_main(args)
            with (ROOT/"pyproject.toml").open("rb") as handle:
                scripts=tomllib.load(handle)["project"]["scripts"]
            self.assertEqual(len(scripts),50)
            self.assertNotIn("cite-refinery-operator-brief",scripts)

if __name__=="__main__":
    unittest.main()
