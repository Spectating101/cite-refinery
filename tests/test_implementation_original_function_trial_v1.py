"""Frozen upstream source module trial contracts, not fake claims of deployment."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter
import base64
import unittest

from cite_refinery.implementation_original_function_trial import (
    SCHEMA, SOURCE_REPO, SOURCE_SHA256, SOURCE_BLOB, SOURCE_PATH, PINNED_COMMIT,
    _fixture_hash, _source_row, _check_code, FIXTURES, fetch_frozen_source,
)
from cite_refinery.implementation_evidence_atlas import attach_original_function_replay
from test_implementation_evidence_atlas_v1 import ImplementationAtlasTests, original_report


def original_inspection():
    return {
        "schema":"cite_refinery.implementation_original_code_structure_audit.v1",
        "records":[{
            "repository_id":SOURCE_REPO,
            "status":"source_files_sha_verified",
            "pinned_commit":PINNED_COMMIT,
            "source_code_executed":False,
            "functionality_demonstrated":False,
            "source_file_samples":[{
                "path":SOURCE_PATH,"blob_sha":SOURCE_BLOB,
                "body_sha256":SOURCE_SHA256,"code_executed":False
            }]
        }],
    }


def fully_anchored_map():
    from cite_refinery.implementation_evidence_atlas import build_implementation_atlas
    base=ImplementationAtlasTests.base
    # Populate single original audit row already in the 1,287 sample.
    repo=next(x for x in base["implementation"]["repository_leads"]
              if x["id"]==SOURCE_REPO)
    cat=repo["categories"][0]["category"]
    original={
        "schema":"cite_refinery.implementation_original_source_audit.v1",
        "selected_category_pairs":1,
        "original_repo_revision_and_root_checked_pairs":1,
        "records":[{
            "repository_id":SOURCE_REPO,"category":cat,
            "source_original_url":repo["url"],
            "original_code_executed":False,
            "independent_capability_demonstrated":False,
            "observed_adoption_or_conversion_gap":False,
            "original_source_snapshot":{
                "status":"original_source_metadata_checked",
                "source_commit":PINNED_COMMIT,
                "root_test_directory_visible_not_executed":True,
                "original_test_commands_executed":0,
                "functional_quality_or_adoption_verified":False,
                "license_entitlement_verified":False
            }
        }]
    }
    depth=original_inspection()
    depth.update(sampled_repositories=1,source_file_inspection_successes=1)
    return build_implementation_atlas(base,original_audit=original,code_audit=depth)


def simulated_receipt(*, status="pass"):
    cases=[{"id":row["id"],"status":status,
            "expected":row["expected"],
            "actual":row["expected"] if status=="pass" else "different"}
           for row in FIXTURES]
    counts=dict(Counter(x["status"] for x in cases))
    return {
        "schema":SCHEMA,"trial_subject":SOURCE_REPO,
        "upstream_revision":PINNED_COMMIT,"source_path":SOURCE_PATH,
        "original_git_blob_sha1":SOURCE_BLOB,
        "source_bytes_sha256":SOURCE_SHA256,
        "predeclared_fixture_sha256":_fixture_hash(),
        "source_checked_at_full_file_and_git_blob":True,
        "original_upstream_python_executed":True,
        "independent_inputs_and_expected_outputs":True,
        "approved_general_reuse_or_promotion":False,
        "upstream_software_is_secure_or_safe":False,
        "demonstrated_field_effect_or_real_user_benefit":False,
        "license_reuse_rights_cleared":False,
        "broad_repository_quality_or_adoption_verified":False,
        "network_sandbox_isolation_proven":False,
        "case_count":len(cases),"case_status_counts":counts,
        "all_preregistered_fixtures_pass":status=="pass",
        "cases":cases
    }


class OriginalFunctionFixtureSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ImplementationAtlasTests.setUpClass()

    def test_genuinely_preregistered_synthetic_requirements(self):
        self.assertEqual(len(FIXTURES),16)
        self.assertEqual(len({r["id"] for r in FIXTURES}),16)
        self.assertTrue(all(len(str(r["expected"]))<400 for r in FIXTURES))
        self.assertEqual(len(_fixture_hash()),64)
        self.assertIn("region_repeated_pattern",{r["id"] for r in FIXTURES})

    def test_source_audit_provenance_is_exact_and_nonpromoting(self):
        row=_source_row(original_inspection())
        self.assertEqual(row["pinned_commit"],PINNED_COMMIT)
        forged=deepcopy(original_inspection())
        forged["records"][0]["source_file_samples"][0]["body_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            _source_row(forged)
        forged=deepcopy(original_inspection())
        forged["records"][0]["functionality_demonstrated"]=True
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            _source_row(forged)

    def test_fabricated_upstream_blob_cannot_enter_replay(self):
        def fake_fetch(url,token=None):
            self.assertEqual(url,"https://api.github.com/repos/blisspixel/recon/git/blobs/"+SOURCE_BLOB)
            return {"sha":SOURCE_BLOB,"encoding":"base64",
                    "content":base64.b64encode(
                        b"def classify_subdomains(x,y):return {}").decode()}
        with self.assertRaisesRegex(ValueError,"do not match reviewed pinned module"):
            fetch_frozen_source(original_inspection(),fetcher=fake_fetch)
        with self.assertRaisesRegex(ValueError,"match reviewed pinned module"):
            _check_code(b"import subprocess\nsubprocess.run(['echo'])")

    def test_example_runner_receipts_do_not_elevate_field_or_general_software(self):
        result=attach_original_function_replay(fully_anchored_map(),simulated_receipt())
        cov=result["coverage"]
        self.assertEqual(cov["original_pinned_modules_with_executed_fixture_receipts"],1)
        self.assertEqual(cov["actual_original_function_fixtures_recorded"],16)
        self.assertEqual(cov["actual_original_function_fixtures_passing"],16)
        self.assertEqual(cov["live_operational_implementations_verified"],0)
        self.assertEqual(cov["underconverted_assets_proven"],0)
        self.assertFalse(result["surveyed_repositories"][SOURCE_REPO][
            "bounded_independent_original_module_replay"][
            "general_upstream_project_correctness_proven"])
        self.assertFalse(result["surveyed_repositories"][SOURCE_REPO][
            "bounded_independent_original_module_replay"][
            "live_domain_effectiveness_proven"])
        self.assertEqual(result["cross_layer_edges_generated"],0)

    def test_forged_fixtures_wrong_revision_and_false_pass_rejected(self):
        a=fully_anchored_map()
        for field,value in [("source_bytes_sha256","f"*64),
                            ("upstream_revision","0"*40),
                            ("network_sandbox_isolation_proven",True)]:
            bad=simulated_receipt();bad[field]=value
            with self.assertRaisesRegex(ValueError,"pinned bounded authority"):
                attach_original_function_replay(a,bad)
        bad=simulated_receipt()
        bad["cases"][0]["actual"]="incorrect output"
        with self.assertRaisesRegex(ValueError,"Recorded pass"):
            attach_original_function_replay(a,bad)
        bad=simulated_receipt()
        bad["cases"].pop()
        with self.assertRaisesRegex(ValueError,"incomplete"):
            attach_original_function_replay(a,bad)
        bad=simulated_receipt()
        bad["predeclared_fixture_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"pinned bounded authority"):
            attach_original_function_replay(a,bad)

    def test_negative_upstream_case_is_preserved_not_erased(self):
        a=fully_anchored_map()
        receipt=simulated_receipt(status="fail")
        result=attach_original_function_replay(a,receipt)
        self.assertEqual(result["coverage"]["actual_original_function_fixtures_passing"],0)
        self.assertEqual(result["original_source_function_replay_receipts"][SOURCE_REPO][
            "case_status_counts"]["fail"],16)
        self.assertFalse(result["surveyed_repositories"][SOURCE_REPO][
            "bounded_independent_original_module_replay"][
            "general_upstream_project_correctness_proven"])


if __name__=="__main__":
    unittest.main()
