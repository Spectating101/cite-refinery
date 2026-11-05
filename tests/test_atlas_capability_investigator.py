"""Atlas objective-driven discovery: original Git blobs, not README faith."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest

from cite_refinery.atlas_capability_investigator import (
    GOAL,SCHEMA,blob_text,build_plan,github_api,inspect_repo,
    literal_code_indicator,render,run,validate_goal,validate_snapshot,file_priority,
)

ROOT=Path(__file__).resolve().parents[1]
GOAL_FILE=ROOT/"examples/discovery/hardware_splicer_capability_goal_20261105.json"


def original_blob(data:bytes):
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    return sha,{"encoding":"base64","size":len(data),
                 "content":base64.b64encode(data).decode()}


def robot_spec():
    return json.loads(GOAL_FILE.read_text())["requirements"][0]


class AtlasAutonomousEngineeringTests(unittest.TestCase):
    def test_configuration_uses_existing_discovery_and_does_not_supply_winning_repositories(self):
        data=json.loads(GOAL_FILE.read_text())
        self.assertTrue(validate_goal(data))
        queries,rules=build_plan(data)
        self.assertEqual(len(queries["sources"]),5)
        self.assertEqual(len(rules["requirements"]),5)
        self.assertTrue(all(x["provider"]=="github_search" for x in queries["sources"]))
        self.assertTrue(all(x["ranking"]=="relevance" for x in queries["sources"]))
        self.assertTrue(all(x["allow_source_types"]==["software"] for x in rules["requirements"]))
        for q in queries["sources"]:
            self.assertNotIn("CadQuery/",q["query"])
            self.assertNotIn("Unity-Technologies/",q["query"])
        bogus=copy.deepcopy(data);bogus["evidence_policy"]="trust_readme"
        with self.assertRaisesRegex(ValueError,"relax"):validate_goal(bogus)
        bogus=copy.deepcopy(data);bogus["requirements"][0]["query"]="x\nrm -rf /"
        with self.assertRaisesRegex(ValueError,"query"):validate_goal(bogus)
        bogus=copy.deepcopy(data);bogus["requirements"][0]["evidence_text_tokens"]=["__import__('os')"]
        with self.assertRaisesRegex(ValueError,"evidence"):validate_goal(bogus)

    def test_exact_original_sha_pinned_code_file_witness_never_proves_integration(self):
        payload=b"def import_urdf(path):\n    robot = urdf_loader(path)\n    return robot\n"
        sha,original=original_blob(payload)
        commit="a"*40
        def api(route,**kwargs):
            if route=="repos/Example/RealURDF":
                return {"full_name":"Example/RealURDF","private":False,"archived":False,
                        "default_branch":"main","license":{"spdx_id":"MIT"},
                        "stargazers_count":11,"pushed_at":"2026-11-01T00:00:00Z"}
            if route.endswith("/commits/main"):return {"sha":commit}
            if "/git/trees/" in route:
                self.assertIsNotNone(kwargs.get("jq"))
                return {"truncated":False,"files":[
                    {"path":"robot/urdf_loader.py","sha":sha,"size":len(payload)}]}
            if "/git/blobs/" in route:return original
            self.fail("unexpected original-source read: "+route)
        got=inspect_repo("Example/RealURDF",robot_spec(),api=api)
        self.assertEqual(got["review_status"],"CODE_LITERAL_OBSERVED_NOT_TESTED")
        self.assertEqual(got["source_sha"],commit)
        self.assertEqual(got["original_source_code_files"][0]["git_blob_sha"],sha)
        self.assertEqual(got["original_source_code_files"][0]["literal_indicator"],"urdf")
        self.assertEqual(got["license_api_spdx"],"MIT")
        self.assertFalse(got["license_clearance_complete"])
        self.assertFalse(got["runtime_integration_verified"])
        self.assertFalse(got["external_code_executed"])
        self.assertFalse(got["safe_to_auto_merge"])

    def test_malicious_or_mismatched_source_blob_never_accepted(self):
        original=b"def import_urdf(model):\n    return model + 'robot'\n"
        sha,body=original_blob(original)
        wrong=copy.deepcopy(body)
        wrong["content"]=base64.b64encode(b"def import_urdf(x):\n    return 'other robot'\n").decode()
        with self.assertRaisesRegex(ValueError,"Git original source blob SHA"):
            blob_text(wrong,sha)
        self.assertEqual(blob_text(body,sha),original.decode())
        self.assertEqual(literal_code_indicator("## urdf importer\n# robot\n",["urdf"]),(None,None))
        self.assertEqual(file_priority({"path":"README.md","sha":sha},["urdf"]),0)
        self.assertEqual(file_priority({"path":"docs/urdf.py","sha":sha},["urdf"]),0)
        self.assertEqual(file_priority({"path":"../robot/urdf.py","sha":sha},["urdf"]),0)
        self.assertGreater(file_priority({"path":"robot/urdf.py","sha":sha},["urdf"]),0)

    def test_real_live_source_snapshot_cannot_claim_autonomy_or_adoption(self):
        frozen=ROOT/"examples/discovery/hs_atlas_source_investigation_20261105.json"
        report_path=ROOT/"reports/hs_atlas_source_investigation_20261105.md"
        if not frozen.exists():self.skipTest("development fixture not yet committed")
        data=json.loads(frozen.read_text())
        profile=json.loads(GOAL_FILE.read_text())
        self.assertTrue(validate_snapshot(data,profile))
        self.assertEqual(data["project"],"hardware_splicer")
        self.assertEqual(data["target_repository"],"Spectating101/hardware-splicer")
        self.assertEqual(data["provider_discovery_candidates"],43)
        self.assertEqual(data["total_code_repository_probes"],13)
        self.assertEqual(data["capability_questions"],5)
        self.assertEqual(data["capabilities_with_some_source_indicator"],5)
        self.assertEqual(data["plain_github_first_result_code_indicators"],5)
        self.assertEqual(data["atlas_top_original_code_indicators"],5)
        self.assertEqual(data["categories_with_possible_existing_target_code_indicators"],5)
        self.assertEqual(sum(g["top_evidence_tied_not_unique_winner"]
                             for g in data["requirements"]),4)
        self.assertTrue(data["target_default_branch_only_not_open_prs"])
        self.assertFalse(data["economic_opportunity_verified"])
        self.assertEqual(data["tested_integrations"],0)
        self.assertEqual(data["independent_analyst_reviews"],0)
        self.assertEqual(data["automatically_merged_repositories"],0)
        self.assertEqual(data["automatic_device_actions"],0)
        self.assertEqual(report_path.read_text(),render(data))
        self.assertIn("same",data["comparison_note"].lower())

    def test_api_disallows_arbitrary_endpoints_before_network_use(self):
        for endpoint in (
            "https://evil.com/anything","user","repos/Example/X/issues",
            "repos/Example/X/git/blobs/../../etc/passwd",
            "repos/Example/X/commits/main;echo secret",
        ):
            with self.assertRaisesRegex(ValueError,"unsafe"):
                github_api(endpoint)

    def test_provider_metadata_first_result_and_atlas_source_evidence_compared_fairly(self):
        data=json.loads(GOAL_FILE.read_text())
        data["requirements"]=data["requirements"][:1]
        desc="URDF robot import simulation and physics"
        rows=[
          {"id":"robot_urdf_search:one","title":"Example/DocsOnly",
           "description":desc,"observation_type":"software",
           "source_url":"https://github.com/Example/DocsOnly",
           "discovery_provider":"github_search","entity_key":"github:example/docsonly"},
          {"id":"robot_urdf_search:two","title":"Example/RealURDF",
           "description":desc,"observation_type":"software",
           "source_url":"https://github.com/Example/RealURDF",
           "discovery_provider":"github_search","entity_key":"github:example/realurdf"},
        ]
        def collector(manifest):
            self.assertEqual(manifest["sources"][0]["query"],data["requirements"][0]["query"])
            return {"schema":"cite_refinery.multisource_discovery.v1",
                "records":rows,
                "source_results":[{"source":"robot_urdf_search","state":"ok","count":2}]}
        code=b"def import_urdf(path):\n    robot = load_urdf(path)\n    return robot\n"
        blob_sha,blob=original_blob(code)
        commit="b"*40
        def api(route,**kwargs):
            slug=route.split("/")[1]+"/"+route.split("/")[2]
            if route=="repos/"+slug:
                return {"full_name":slug,"private":False,"archived":False,
                        "default_branch":"main","license":None,
                        "stargazers_count":1,"pushed_at":"2026-11-01T00:00:00Z"}
            if route.endswith("/commits/main"):return {"sha":commit}
            if "/git/trees/" in route:
                return {"truncated":False,"files":[] if slug.endswith("DocsOnly") else [
                  {"path":"robot/urdf.py","sha":blob_sha,"size":len(code)}]}
            if "/git/blobs/" in route:return blob
            self.fail(route)
        out=run(data,collector=collector,api=api,probes_per_capability=2)
        self.assertEqual(out["schema"],SCHEMA)
        self.assertEqual(out["provider_discovery_candidates"],2)
        self.assertEqual(out["total_code_repository_probes"],2)
        self.assertEqual(out["capabilities_with_some_source_indicator"],1)
        self.assertEqual(out["plain_github_first_result_code_indicators"],0)
        self.assertEqual(out["atlas_top_original_code_indicators"],1)
        self.assertEqual(out["requirements"][0]["atlas_top_source_review_repo"],"Example/RealURDF")
        self.assertFalse(out["requirements"][0]["top_evidence_tied_not_unique_winner"])
        self.assertEqual(out["requirements"][0]["provider_search_baseline_repo"],"Example/DocsOnly")
        self.assertEqual(out["tested_integrations"],0)
        self.assertEqual(out["automatically_merged_repositories"],0)
        self.assertEqual(out["automatic_device_actions"],0)
        self.assertTrue(validate_snapshot(out,data))
        self.assertEqual(out["categories_with_possible_existing_target_code_indicators"],1)
        self.assertEqual(out["requirements"][0]["decision"],
                         "REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION")
        forged=copy.deepcopy(out)
        forged["requirements"][0]["ranked_original_source_witnesses"][0]["original_source_code_files"][0]["pinned_url"]="https://evil.org/fake"
        with self.assertRaisesRegex(ValueError,"URL/hash mismatch"):
            validate_snapshot(forged)
        forged=copy.deepcopy(out)
        forged["tested_integrations"]=1
        with self.assertRaisesRegex(ValueError,"improperly claims authority"):
            validate_snapshot(forged)
        forged=copy.deepcopy(out)
        forged["requirements"][0]["target_default_branch_source_overlap_status"]="NOT_CHECKED"
        with self.assertRaisesRegex(ValueError,"overlap assessment"):
            validate_snapshot(forged)
        md=render(out)
        self.assertIn("Example/RealURDF",md)
        self.assertIn("Plain first-result code indicators: 0/1",md)
        self.assertIn("not executed",md)
        self.assertIn("Git blob",md)

    def test_import_statements_are_not_an_implementation_indication(self):
        text="from robot_urdf_library import URDFParser\nusing URDFImporter;\n# parse URDF\n"
        self.assertEqual(literal_code_indicator(text,["urdf","robot"]),(None,None))
        text2="class URDFImporter:\n    def load_urdf(self,source):\n        return source\n"
        self.assertEqual(literal_code_indicator(text2,["urdf"]),("urdf",1))


if __name__=="__main__":
    unittest.main()
