"""Second pinned original function replay: synthetic LEF/DEF source parser cases."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import base64
import unittest

from cite_refinery.implementation_original_lef_def_trial import (
    SCHEMA,REPO,REVISION,PATH,BLOB,DIGEST,URL,FIXTURES,
    fixture_sha256,audit_row,check_reviewed_source,fetch_original)
from cite_refinery.implementation_evidence_atlas import (
    build_implementation_atlas,attach_original_lef_def_replay,
    attach_original_function_replay)
from test_implementation_original_function_trial_v1 import (
    original_inspection as lexical_source_inspection, simulated_receipt)
from test_implementation_evidence_atlas_v1 import ImplementationAtlasTests


def fake_eda_audit():
    return {
        "schema":"cite_refinery.implementation_original_code_structure_audit.v1",
        "records":[{
            "repository_id":REPO,"status":"source_files_sha_verified",
            "pinned_commit":REVISION,"source_code_executed":False,
            "functionality_demonstrated":False,"tree_sha":"c"*40,
            "license_reuse_rights_cleared":False,
            "observed_end_user_adoption":False,
            "source_file_samples":[{
                "path":PATH,"blob_sha":BLOB,"body_sha256":DIGEST,
                "code_executed":False
            }]
        }]
    }


def source_bound_map():
    base=ImplementationAtlasTests.base
    rlex=next(x for x in base["implementation"]["repository_leads"]
              if x["id"]=="github:blisspixel/recon")
    reda=next(x for x in base["implementation"]["repository_leads"]
              if x["id"]==REPO)
    pinned=[]
    for rid,commit,row in (("github:blisspixel/recon",
                           "aad9746c29b5427263d7f7788373fcc85e7d4261",rlex),
                          (REPO,REVISION,reda)):
        pinned.append({
            "repository_id":rid,"category":row["categories"][0]["category"],
            "source_original_url":row["url"],
            "original_code_executed":False,
            "independent_capability_demonstrated":False,
            "observed_adoption_or_conversion_gap":False,
            "original_source_snapshot":{
                "status":"original_source_metadata_checked","source_commit":commit,
                "root_test_directory_visible_not_executed":False,
                "original_test_commands_executed":0,
                "functional_quality_or_adoption_verified":False,
                "license_entitlement_verified":False
            }
        })
    original={
        "schema":"cite_refinery.implementation_original_source_audit.v1",
        "selected_category_pairs":2,
        "original_repo_revision_and_root_checked_pairs":2,
        "records":pinned
    }
    two=[
        {**lexical_source_inspection()["records"][0]},
        {**fake_eda_audit()["records"][0]}
    ]
    depth={
        "schema":"cite_refinery.implementation_original_code_structure_audit.v1",
        "sampled_repositories":2,"source_file_inspection_successes":2,
        "records":two
    }
    atlas=build_implementation_atlas(base,original_audit=original,code_audit=depth)
    return attach_original_function_replay(atlas,simulated_receipt())


def synthetic_eda_receipt():
    cases=[{
        "id":f["id"],"status":"pass","expected":f["expected"],"actual":f["expected"]
    } for f in FIXTURES]
    case=next(x for x in cases if x["id"]=="design_comment_is_not_real_layer")
    case["status"]="fail"
    case["actual"]=["M1","PHANTOM"]
    counts=dict(Counter(x["status"] for x in cases))
    return {
        "schema":SCHEMA,"original_repository":REPO,
        "original_commit":REVISION,"original_path":PATH,
        "original_blob_sha1":BLOB,"original_full_source_sha256":DIGEST,
        "preregistered_fixture_sha256":fixture_sha256(),
        "original_program_functions_executed":True,
        "case_count":len(cases),"case_status_counts":counts,"cases":cases,
        "no_field_chip_design_verified":True,
        "no_real_foundry_or_PDK_validation":True,
        "real_automation_safety_not_established":True,
        "license_reuse_rights_not_cleared":True,
        "cross_layer_effectiveness_not_established":True,
        "operational_reuse_approved":False
    }


class OriginalLefDefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ImplementationAtlasTests.setUpClass()

    def test_fixture_count_and_adverse_comment_contract(self):
        self.assertEqual(len(FIXTURES),16)
        self.assertEqual(len({x["id"] for x in FIXTURES}),16)
        comment=next(x for x in FIXTURES if x["id"]=="design_comment_is_not_real_layer")
        self.assertEqual(comment["expected"],["M1"])
        self.assertEqual(len(fixture_sha256()),64)

    def test_upstream_original_source_and_false_approval_rejected(self):
        self.assertEqual(audit_row(fake_eda_audit())["pinned_commit"],REVISION)
        bad=deepcopy(fake_eda_audit())
        bad["records"][0]["source_file_samples"][0]["blob_sha"]="f"*40
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            audit_row(bad)
        bad=deepcopy(fake_eda_audit())
        bad["records"][0]["functionality_demonstrated"]=True
        with self.assertRaisesRegex(ValueError,"pinned original"):
            audit_row(bad)

    def test_replaced_source_file_fails_even_with_matching_forged_git_metadata(self):
        def bogus(url,token=None):
            self.assertEqual(url,URL)
            return {"sha":BLOB,"encoding":"base64",
                    "content":base64.b64encode(b"print('fake')").decode()}
        with self.assertRaisesRegex(ValueError,"differ from"):
            fetch_original(fake_eda_audit(),fetcher=bogus)
        with self.assertRaisesRegex(ValueError,"differ from"):
            check_reviewed_source(b"LAYER FAKE")

    def test_two_real_original_module_evidence_profiles_are_separate(self):
        atlas=attach_original_lef_def_replay(source_bound_map(),synthetic_eda_receipt())
        cov=atlas["coverage"]
        self.assertEqual(cov["original_pinned_modules_with_executed_fixture_receipts"],2)
        self.assertEqual(cov["actual_original_function_fixtures_recorded"],32)
        self.assertEqual(cov["actual_original_function_fixtures_passing"],31)
        self.assertEqual(cov["actual_original_function_fixtures_failing"],1)
        self.assertEqual(cov["live_operational_implementations_verified"],0)
        self.assertEqual(cov["underconverted_assets_proven"],0)
        self.assertEqual(atlas["cross_layer_edges_generated"],0)
        self.assertEqual(atlas["original_source_function_replay_receipts"][REPO][
            "case_status_counts"]["fail"],1)

    def test_implementation_original_failures_cannot_be_hidden_by_override(self):
        base=source_bound_map()
        r=synthetic_eda_receipt()
        r["cases"][13]["status"]="pass"
        with self.assertRaisesRegex(ValueError,"Falsely reported"):
            attach_original_lef_def_replay(base,r)
        r=synthetic_eda_receipt()
        r["cases"]=r["cases"][:-1]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            attach_original_lef_def_replay(base,r)
        r=synthetic_eda_receipt()
        r["operational_reuse_approved"]=True
        with self.assertRaisesRegex(ValueError,"falsely claims"):
            attach_original_lef_def_replay(base,r)
        r=synthetic_eda_receipt()
        r["preregistered_fixture_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"falsely claims"):
            attach_original_lef_def_replay(base,r)


if __name__=="__main__":
    unittest.main()
