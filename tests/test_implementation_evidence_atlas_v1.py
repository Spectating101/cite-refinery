"""Original Implementation sources and synthetic trials are separate evidence tiers."""
from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha1,sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import base64
import json
import unittest

from cite_refinery.layer_foundations import build,review_backlog
from cite_refinery.implementation_evidence_atlas import (
    build_implementation_atlas,browse_implementation)
from cite_refinery.implementation_original_code_audit import (
    _blob_matches,audit_original_code)
from cite_refinery.layered_cli import main as cli

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/"research_materials/runtime_trials/open_corpus_20261020"
ATLAS=ROOT/"research_materials/opportunity_atlas"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def original_report(backlog):
    sample=backlog["entries"][0]
    rid=sample["repository_id"]
    commit="a"*40
    return {
        "schema":"cite_refinery.implementation_original_source_audit.v1",
        "selected_category_pairs":1,
        "original_repo_revision_and_root_checked_pairs":1,
        "records":[{
            "repository_id":rid,"category":sample["category"],
            "source_original_url":sample["original_repository_url"],
            "source_description_publisher_claim":sample["publisher_description"],
            "original_code_executed":False,
            "independent_capability_demonstrated":False,
            "observed_adoption_or_conversion_gap":False,
            "original_source_snapshot":{
                "status":"original_source_metadata_checked",
                "source_commit":commit,"functional_quality_or_adoption_verified":False,
                "license_entitlement_verified":False,"original_test_commands_executed":0,
                "root_test_directory_visible_not_executed":True,
            }
        }]
    }


def gitblob(content):
    return sha1(("blob "+str(len(content))+"\0").encode()+content).hexdigest()


def original_depth(audit,*,tamper=False,unavailable=False):
    rec=audit["records"][0]
    slug=rec["repository_id"].removeprefix("github:")
    commit=rec["original_source_snapshot"]["source_commit"]
    tree="b"*40
    source=b"def transform(value):\n    return value + 1\n"
    tests=b"def test_transform():\n    assert 2 == 2\n"
    ssha=gitblob(source)
    tsha=gitblob(tests)
    prefix="https://api.github.com/repos/"+slug+"/git/"
    def get(url,token=None):
        if unavailable:raise RuntimeError("unavailable")
        if url==prefix+"commits/"+commit:
            return {"sha":commit,"tree":{"sha":tree}}
        if url==prefix+"trees/"+tree+"?recursive=1":
            return {
                "sha":tree,"truncated":False,"tree":[
                    {"type":"blob","sha":ssha,"size":len(source),"path":"src/engine.py"},
                    {"type":"blob","sha":tsha,"size":len(tests),"path":"tests/test_engine.py"}
                ]}
        if url==prefix+"blobs/"+ssha:
            return {"sha":ssha,"encoding":"base64",
                    "content":base64.b64encode(source if not tamper else b"fake").decode()}
        if url==prefix+"blobs/"+tsha:
            return {"sha":tsha,"encoding":"base64",
                    "content":base64.b64encode(tests).decode()}
        raise AssertionError("Unexpected GitHub API target "+url)
    return audit_original_code(audit,fetcher=get,max_repositories=1)


class ImplementationAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=build(
            load(CORPUS/"source_manifest.json"),
            [load(p) for p in sorted((CORPUS/"source_readings").glob("shard-*.json"))],
            load(CORPUS/"global_atlas.json"),
            load(ATLAS/"github_repository_survey.json"),
            load(ATLAS/"github_frontier_repository_survey.json"),
            load(ATLAS/"atlas_network.json"),
            load(ATLAS/"ted_published_notice_context.json"))
        cls.probes=load(ATLAS/"functional_component_trials.json")
        cls.backlog=review_backlog(cls.base,per_category=2)

    def test_original_1287_leads_not_conflated_with_3_external_probes(self):
        report=build_implementation_atlas(self.base,functional_trials=self.probes)
        c=report["coverage"]
        self.assertEqual(c["survey_repository_leads"],1287)
        self.assertEqual(c["repository_category_memberships"],1360)
        self.assertEqual(c["metadata_reviewed_memberships"],220)
        self.assertEqual(c["historical_scoped_trial_assets"],3)
        self.assertEqual(c["historical_scoped_trial_assets_also_in_survey"],0)
        self.assertEqual(c["historical_scoped_trial_assets_outside_survey"],3)
        self.assertEqual(c["historic_synthetic_or_static_case_status_counts"],
                         {"pass":6,"fail":7,"blocked":1,"not_tested":3})
        self.assertEqual(c["technical_capabilities_independently_replayed_in_this_map"],0)
        self.assertEqual(c["live_operational_implementations_verified"],0)
        self.assertEqual(c["reuse_rights_independently_cleared"],0)
        self.assertEqual(c["underconverted_assets_proven"],0)
        self.assertEqual(report["cross_layer_edges_generated"],0)
        self.assertTrue(all(not row["bounded_component_probe_ids"]
                            for row in report["surveyed_repositories"].values()))
        self.assertEqual(browse_implementation(report,stage="historical_trial")[
            "matching_count"],3)
        self.assertEqual(browse_implementation(report,stage="source_sample")[
            "matching_count"],0)
        self.assertGreater(browse_implementation(report,category="finite_elements")[
            "matching_count"],0)

    def test_actual_three_trials_retain_specific_successes_defects_and_gaps(self):
        atlas=build_implementation_atlas(self.base,functional_trials=self.probes)
        flood=atlas["historical_scoped_component_trials"][
            "github:WeixuanZ/flood-warning-system"]
        self.assertEqual(flood["case_counts"]["fail"],2)
        self.assertIn("nonfinite_sensor_level_is_excluded",flood["experimental_blockers"])
        self.assertEqual(flood["cases"]["threshold_selection"]["status"],"pass")
        self.assertFalse(flood["independently_confirmed_operational_function"])
        self.assertFalse(flood["execution_receipt_cryptographically_signed"])
        self.assertNotIn("working_solution",str(atlas["coverage"]))

    def test_operator_cannot_fake_execution_attestation_or_case_counts(self):
        altered=deepcopy(self.probes)
        altered["technical_fit_confirmed"]=True
        with self.assertRaisesRegex(ValueError,"cautious"):
            build_implementation_atlas(self.base,functional_trials=altered)
        altered=deepcopy(self.probes)
        altered["probes"][0]["source"]["git_commit"]="different"
        with self.assertRaisesRegex(ValueError,"pinned"):
            build_implementation_atlas(self.base,functional_trials=altered)
        altered=deepcopy(self.probes)
        altered["test_case_counts"]["pass"]=7
        with self.assertRaisesRegex(ValueError,"count"):
            build_implementation_atlas(self.base,functional_trials=altered)
        altered=deepcopy(self.probes)
        altered["probes"][0]["cases"][0]["status"]="scientifically_validated"
        with self.assertRaisesRegex(ValueError,"falsely"):
            build_implementation_atlas(self.base,functional_trials=altered)

    def test_pinned_original_metadata_and_source_blob_are_not_live_capability(self):
        audit=original_report(self.backlog)
        depth=original_depth(audit)
        self.assertEqual(depth["source_file_inspection_successes"],1)
        self.assertEqual(depth["sampled_repositories"],1)
        self.assertEqual(depth["records"][0]["source_file_samples"][0][
            "structural_function_names_not_a_behavioral_test"][0]["name"],"transform")
        self.assertTrue(depth["records"][0]["source_file_samples"][0][
            "python_ast_syntax_parsed_only"])
        report=build_implementation_atlas(
            self.base,original_audit=audit,code_audit=depth,
            functional_trials=self.probes)
        c=report["coverage"]
        self.assertEqual(c["distinct_repositories_original_commit_root_checked"],1)
        self.assertEqual(c["original_source_file_samples_sha_checked"],1)
        self.assertEqual(c["technical_capabilities_independently_replayed_in_this_map"],0)
        self.assertEqual(browse_implementation(report,stage="source_sample")[
            "matching_count"],1)
        self.assertTrue(report["interpretation"]["source_file_sha_is_not_test_pass"])
        self.assertFalse(report["surveyed_repositories"][audit["records"][0][
            "repository_id"]]["scoped_capability_confirmed_in_live_deployment"])

    def test_blob_substitution_refuses_source_confirmation(self):
        audit=original_report(self.backlog)
        bad=original_depth(audit,tamper=True)
        self.assertEqual(bad["source_file_inspection_successes"],0)
        self.assertEqual(bad["records"][0]["status"],"unavailable_or_inconclusive")
        self.assertFalse(_blob_matches(b"not source",gitblob(b"actual source")))
        with self.assertRaisesRegex(ValueError,"structure"):
            build_implementation_atlas(self.base,code_audit=bad)
        unavailable=audit_original_code(audit,
            fetcher=lambda url,token=None: (_ for _ in ()).throw(
                ValueError("unknown")),max_repositories=1)
        self.assertEqual(unavailable["source_file_inspection_successes"],0)

    def test_forged_revision_or_approval_rejected(self):
        audit=original_report(self.backlog)
        depth=original_depth(audit)
        bad=deepcopy(depth)
        bad["records"][0]["functionality_demonstrated"]=True
        with self.assertRaisesRegex(ValueError,"cannot promote"):
            build_implementation_atlas(self.base,original_audit=audit,code_audit=bad)
        bad=deepcopy(depth)
        bad["records"][0]["pinned_commit"]="f"*40
        with self.assertRaisesRegex(ValueError,"pinned revision"):
            build_implementation_atlas(self.base,original_audit=audit,code_audit=bad)
        bad=deepcopy(audit)
        bad["records"][0]["original_source_snapshot"]["original_test_commands_executed"]=2
        with self.assertRaisesRegex(ValueError,"cannot qualify"):
            build_implementation_atlas(self.base,original_audit=bad)

    def test_cli_implementation_map_real_trial_fixtures_and_report(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            with redirect_stdout(StringIO()):
                result=cli([
                    "investigate","map-foundations",
                    "--implementation-component-trials",
                    str(ATLAS/"functional_component_trials.json"),
                    "--implementation-stage","historical_trial",
                    "--implementation-atlas-out",str(root/"implementation.json"),
                    "--json-out",str(root/"combined.json"),
                    "--markdown-out",str(root/"coverage.md"),
                ])
            self.assertIn(result,(None,0))
            a=load(root/"implementation.json")
            b=load(root/"combined.json")
            self.assertEqual(a["coverage"]["historical_scoped_trial_assets_outside_survey"],3)
            self.assertEqual(b["implementation"]["evidence_depth_browse"]["matching_count"],3)
            self.assertEqual(b["implementation"]["evidence_depth_atlas"]["coverage"][
                "live_operational_implementations_verified"],0)
            self.assertIn("Independent Implementation source",(
                root/"coverage.md").read_text())


if __name__=="__main__":
    unittest.main()
