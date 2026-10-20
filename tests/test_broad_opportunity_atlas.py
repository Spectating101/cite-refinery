from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_atlas_collect import validate_manifest, normalize, collect
from cite_refinery.opportunity_atlas_semantic import create_batches, validate, prompt
from cite_refinery.opportunity_atlas import assemble, combine_snapshots, render_markdown
from cite_refinery.opportunity_atlas_ted import collect as collect_ted, validate as validate_ted

ROOT=Path(__file__).resolve().parents[1] / "research_materials/opportunity_atlas"


def source(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class WideAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=source("survey_manifest.json")
        cls.frontier_manifest=source("frontier_survey_manifest.json")
        cls.snapshot=source("github_repository_survey.json")
        cls.channels=source("source_channel_registry.json")
        cls.crosswalk=source("mechanism_crosswalk.json")
        cls.meanings=source("domain_meanings.json")

    def test_taxonomy_is_broad_and_frozen_unranked(self):
        self.assertEqual(len(validate_manifest(self.manifest)["domains"]),44)
        self.assertEqual(len(validate_manifest(self.frontier_manifest)["domains"]),44)
        self.assertGreaterEqual(len({r["macro"] for r in self.manifest["domains"]}),6)
        self.assertGreaterEqual(len(self.channels["channels"]),30)
        self.assertGreaterEqual(len(self.crosswalk["bridges"]),20)
        self.assertFalse(self.manifest["collection"]["commercial_inference"])

    def test_no_arbitrary_github_queries(self):
        bad=copy.deepcopy(self.manifest)
        bad["domains"][0]["query"]="topic:pcb user:somebody fork:true"
        self.assertRaises(ValueError,validate_manifest,bad)
        bad=copy.deepcopy(self.frontier_manifest)
        bad["domains"][0]["query"]="topic:pcb stars:0..1000000"
        self.assertRaises(ValueError,validate_manifest,bad)

    def test_public_metadata_only(self):
        manifest=copy.deepcopy(self.manifest)
        manifest["domains"]=manifest["domains"][:1]
        raw={
            "total_count":3,
            "items":[
                {"full_name":"author/repo-a","private":False,"fork":False,"archived":False,
                 "description":"Physical hardware","language":"Python","topics":["pcb"],
                 "license":{"spdx_id":"MIT"},"stargazers_count":8,"forks_count":2},
                {"full_name":"author/repo-b","private":True,"fork":False,"archived":False},
                {"full_name":"author/repo-c","private":False,"fork":False,"archived":True},
            ]}
        out=normalize(manifest,{manifest["domains"][0]["id"]:raw},observed_at="2026-10-21T00:00:00Z")
        self.assertEqual(len(out["repositories"]),1)
        row=out["repositories"][0]
        self.assertEqual(row["buyer_demand"],"unknown")
        self.assertEqual(row["commercial_status"],"unknown")
        self.assertFalse(row["license_review_complete"])

    def test_public_snapshot_bounded_counts_not_commercial_truth(self):
        snap=self.snapshot
        self.assertEqual(len(snap["strata"]),44)
        self.assertGreater(len(snap["repositories"]),400)
        self.assertFalse(snap["collection_errors"])
        self.assertTrue(all(r["commercial_status"]=="unknown" for r in snap["repositories"]))
        self.assertTrue(all(r["implementation_impact"]=="unknown" for r in snap["repositories"]))

    def test_semantic_review_requires_every_sample_and_exact_ids(self):
        batches=create_batches(self.snapshot,self.meanings,per_domain=2,domains_per_batch=2)
        first=batches[0]
        self.assertEqual(len(first["domain_groups"]),2)
        self.assertIn("polysemy",prompt(first).lower())
        self.assertRaises(ValueError,validate,first,{"judgments":[]})
        answer={"judgments":[]}
        for group in first["domain_groups"]:
            for r in group["sampled_repositories"]:
                answer["judgments"].append({
                    "domain_id":group["domain_id"],"repository_id":r["id"],
                    "label":"insufficient_metadata",
                    "reason":"Public repository description does not establish the intended mechanism.",
                })
        self.assertEqual(len(validate(first,answer)["judgments"]),4)
        wrong=copy.deepcopy(answer);wrong["judgments"][0]["repository_id"]="invented/fake"
        self.assertRaises(ValueError,validate,first,wrong)

    def test_two_sampling_frames_cannot_sum_provider_total_count(self):
        primary=copy.deepcopy(self.snapshot)
        secondary=copy.deepcopy(self.snapshot)
        secondary["sample_segment"]="recent_lower_visibility"
        secondary["observed_at"]="2026-10-21T01:01:01Z"
        secondary["strata"][0]["total_reported"]=123
        joined=combine_snapshots(primary,secondary)
        self.assertEqual(len(joined["repositories"]),len(primary["repositories"]))
        self.assertEqual(joined["strata"][0]["total_reported"],primary["strata"][0]["total_reported"])
        self.assertEqual(joined["strata"][0]["frontier_sampling"]["frontier_matching_results_not_additive"],123)
        self.assertEqual(joined["query_count"],88)

    def test_assemble_no_underconversion_and_review_source_boundary(self):
        aud=source("semantic_review_batch_1.json")
        net=assemble(self.snapshot,self.channels,self.crosswalk,[aud])
        self.assertEqual(len(net["domain_areas"]),44)
        self.assertEqual(net["coverage_integrity"]["semantically_audited_repo_domain_pairs"],55)
        self.assertEqual(net["coverage_integrity"]["commercial_underconversion"],"not_established")
        self.assertTrue(all(a["verified_buyer_demand"]=="none_collected_in_this_pass" for a in net["domain_areas"]))
        self.assertTrue(all(x["review_status"]=="curated_candidate_mechanism_not_validated_fit" for x in net["mechanism_hypotheses"]))
        self.assertIn("No sector is selected",render_markdown(net))
        self.assertNotIn("MatrixTM/MHDDoS",render_markdown(net))

    def test_live_combined_wide_snapshot_retains_independent_frames(self):
        low=source("github_frontier_repository_survey.json")
        both=combine_snapshots(self.snapshot,low)
        self.assertGreater(len(both["repositories"]),1000)
        self.assertEqual(both["query_count"],88)
        self.assertEqual(len(both["strata"]),44)
        self.assertEqual(len(set(x["full_name"] for x in both["repositories"])),len(both["repositories"]))
        self.assertTrue(all(r["buyer_demand"]=="unknown" for r in both["repositories"]))

    def test_ted_published_notice_metadata_is_not_a_contract(self):
        ted=source("ted_published_notice_context.json")
        self.assertEqual(ted["schema"],"cite_refinery.ted_notice_context.v1")
        self.assertEqual(ted["scope"],"ALL")
        self.assertGreater(len(ted["notices"]),20)
        for notice in ted["notices"]:
            self.assertEqual(notice["demand_evidence"],"published_notice_metadata_not_verified_currently_open")
            self.assertFalse(notice["full_scope_reviewed"])
            self.assertEqual(notice["bid_eligibility"],"unknown")
        combined=combine_snapshots(self.snapshot,source("github_frontier_repository_survey.json"))
        net=assemble(combined,self.channels,self.crosswalk,ted=ted)
        self.assertEqual(net["coverage_integrity"]["commercial_underconversion"],"not_established")
        self.assertEqual(net["coverage_integrity"]["published_notices_sampled"],len(ted["notices"]))
        self.assertTrue(all(a["economic_capture"]=="not_assessed" for a in net["domain_areas"]))
        doc=render_markdown(net)
        self.assertIn("published notices, not active contracts",doc)

    def test_ted_manifest_fail_closed_and_no_active_assumption(self):
        m=source("ted_survey_manifest.json")
        validate_ted(m)
        m["themes"][0]["keyword"]='"; private data'
        self.assertRaises(ValueError,validate_ted,m)
        m=source("ted_survey_manifest.json")
        m["themes"]=m["themes"][:1]
        out=collect_ted(m,request=lambda body:{
            "totalNoticeCount":1,
            "notices":[{
                "publication-number":"123456-2026","notice-title":{"eng":["Public infrastructure support"]},
                "buyer-name":{"eng":["Public Buyer"]},"publication-date":"2026-10-20+02:00",
                "notice-type":"cn-standard"}]},pause_seconds=0)
        self.assertEqual(len(out["notices"]),1)
        self.assertEqual(out["notices"][0]["title"],"Public infrastructure support")
        self.assertEqual(out["notices"][0]["demand_evidence"],
                         "published_notice_metadata_not_verified_currently_open")

    def test_ted_promotion_rejected(self):
        ted=source("ted_published_notice_context.json")
        bad=copy.deepcopy(ted)
        bad["notices"][0]["full_scope_reviewed"]=True
        self.assertRaises(ValueError,assemble,self.snapshot,self.channels,self.crosswalk,[],bad)

    def test_claim_promotion_or_missing_bridge_rejected(self):
        walk=copy.deepcopy(self.crosswalk)
        walk["bridges"][0]["review_status"]="confirmed_commercial_fit"
        self.assertRaises(ValueError,assemble,self.snapshot,self.channels,walk)
        walk=copy.deepcopy(self.crosswalk)
        walk["bridges"][0]["domain_ids"]=["imaginary_domain"]
        self.assertRaises(ValueError,assemble,self.snapshot,self.channels,walk)


if __name__=="__main__":
    unittest.main()
