"""Review all broad discovery links, reject fabricated sources and avoid
promoting partial toy simulation tests into claimed conversion value."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest

from cite_refinery.open_corpus_atlas import (
    conversion_qualification_queue,render_qualification_queue,
    screen_emergent_batch,prepare_conversion_universe,
)
from cite_refinery.layered_cli import main as cli

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"research_materials/opportunity_atlas"
SCRATCH=DATA

def load(path):
    return json.loads(path.read_text())

class QualificationSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.slices=[load(DATA/f"emergent_conversion_slice_{i}_v1.json") for i in (0,1)]
        cls.slices.extend(load(DATA/f"emergent_conversion_slice_{i}_v1.json") for i in (2,3))
        cls.audits=[load(DATA/"original_repo_conversion_audit_first_14_v1.json"),
                    load(DATA/"original_repo_conversion_audit_additional_11_v1.json")]
        cls.tests=load(DATA/"original_source_component_test_receipts_v1.json")

    def test_full_four_slice_coverage_is_not_a_false_value_or_adoption_claim(self):
        j=conversion_qualification_queue(self.slices,self.audits,self.tests)
        self.assertEqual(j["source_slices_inspected"],4)
        self.assertEqual(j["implementation_listings_sampled_across_slices"],142)
        self.assertEqual(j["candidate_links_accepted_for_review"],21)
        self.assertEqual(j["candidate_links_rejected_for_invalid_source_or_schema"],1)
        self.assertEqual(j["original_repo_metadata_checked"],25)
        self.assertEqual(j["unique_referenced_asset_repositories"],25)
        self.assertEqual(j["scoped_original_test_passes_total"],15)
        self.assertEqual(j["confirmed_underconverted_assets"],0)
        self.assertEqual(j["independently_qualified_high_quality_assets"],0)
        self.assertEqual(j["accepted_new_recombinations"],0)
        self.assertEqual(j["realized_value"],0)
        self.assertFalse(j["funding_or_customers_required_to_enter_atlas"])
        self.assertEqual(len(j["rows"]),21)
        self.assertIn("not independent deployment evidence",render_qualification_queue(j).lower())

    def test_partial_toy_original_tests_are_not_partner_integration(self):
        j=conversion_qualification_queue(self.slices,self.audits,self.tests)
        item=next(x for x in j["rows"] if x["candidate_id"]=="slice-0:CV-03")
        grid=next(x for x in item["asset_provenance"]
                  if x["asset_id"]=="github:Krishita17/GridShadow")
        jackery=next(x for x in item["asset_provenance"]
                     if x["asset_id"]=="github:Bigdaddy1990/jackery_solarvault")
        self.assertEqual(grid["original_component_test_passes"],15)
        self.assertIn("simulation_tests_passed",grid["quality_status"])
        self.assertIsNone(jackery["test_source_commit"])
        self.assertEqual(jackery["original_component_test_passes"],0)
        self.assertFalse(item["proposed_recombination_tested"])
        self.assertFalse(item["technical_quality_complete_for_all_required_assets"])
        self.assertFalse(item["new_value_realized"])

    def test_fabricated_repo_candidate_remains_rejected_and_not_in_queue(self):
        j=conversion_qualification_queue(self.slices,self.audits,self.tests)
        self.assertEqual(j["rejected_model_candidates"][0]["slice_offset"],2)
        self.assertEqual(j["rejected_model_candidates"][0]["id"],"CV-02")
        self.assertFalse(any(row["candidate_id"]=="slice-2:CV-02" for row in j["rows"]))

    def test_missing_repo_spdx_labels_are_reuse_review_flags_not_proof_of_illegality(self):
        j=conversion_qualification_queue(self.slices,self.audits,self.tests)
        for repo in ("github:nadar71/FreddyFridge",
                     "github:Syracuse3DPrintingOrg/PantryRaider",
                     "github:lindbrook/cholera"):
            a=[x for row in j["rows"] for x in row["asset_provenance"]
               if x["asset_id"]==repo]
            self.assertGreater(len(a),0)
            self.assertTrue(all(x["reuse_license_review_required"] for x in a))
            self.assertTrue(all(not x["commercial_or_social_impact_measured"] for x in a))

    def test_unsupported_original_execution_claim_rejected(self):
        failed=deepcopy(self.tests)
        failed["test_runs"][0]["source_code_modified_for_test"]=True
        with self.assertRaisesRegex(ValueError,"modified/failed"):
            conversion_qualification_queue(self.slices,self.audits,failed)
        failed=deepcopy(self.tests)
        failed["test_runs"][0]["full_integration_to_any_partner_tested"]=True
        with self.assertRaisesRegex(ValueError,"modified/failed"):
            conversion_qualification_queue(self.slices,self.audits,failed)

    def test_unverified_promoted_model_graph_edge_is_not_qualifiable(self):
        fake=deepcopy(self.slices)
        fake[0]["new_graph_edges_accepted"]=1
        with self.assertRaisesRegex(ValueError,"unpromoted"):
            conversion_qualification_queue(fake,self.audits,self.tests)
        fake=deepcopy(self.slices)
        fake[1]["source_universe"]["stratified_offset"]=0
        with self.assertRaisesRegex(ValueError,"same source slice"):
            conversion_qualification_queue(fake,self.audits,self.tests)

    def test_cli_replay_and_no_new_installed_script_or_state_directory(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            args=["investigate","--workspace",str(root/"phantom"),
                  "qualify-conversions"]
            for i in (0,1):
                args.extend(["--discovery",str(DATA/f"emergent_conversion_slice_{i}_v1.json")])
            for i in (2,3):
                args.extend(["--discovery",str(DATA/f"emergent_conversion_slice_{i}_v1.json")])
            for path in (DATA/"original_repo_conversion_audit_first_14_v1.json",
                         DATA/"original_repo_conversion_audit_additional_11_v1.json"):
                args.extend(["--repository-audit",str(path)])
            args.extend(["--component-tests",str(DATA/"original_source_component_test_receipts_v1.json"),
                        "--json-out",str(root/"result.json"),
                        "--markdown-out",str(root/"result.md")])
            output=StringIO()
            with redirect_stdout(output):
                cli(args)
            receipt=json.loads(output.getvalue())
            self.assertEqual(receipt["candidate_links_for_review"],21)
            self.assertEqual(receipt["invalid_model_links_rejected"],1)
            self.assertEqual(receipt["original_upstream_test_passes"],15)
            self.assertFalse((root/"phantom").exists())
            self.assertTrue((root/"result.md").is_file())
            self.assertEqual(len(load(root/"result.json")["rows"]),21)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                cli(args)
            with (ROOT/"pyproject.toml").open("rb") as f:
                scripts=tomllib.load(f)["project"]["scripts"]
            self.assertNotIn("cite-refinery-qualify-conversions",scripts)
            self.assertEqual(len(scripts),50)

if __name__=="__main__":
    unittest.main()
