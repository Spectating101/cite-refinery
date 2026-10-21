"""Frozen-source integrity tests for three independent map foundations."""
from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.layer_foundations import build, browse, review_backlog, SCHEMA
from cite_refinery.layered_cli import main as canonical_cli

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/"research_materials/runtime_trials/open_corpus_20261020"
ATLAS=ROOT/"research_materials/opportunity_atlas"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class StandaloneLayerFoundations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load(CORPUS/"source_manifest.json")
        cls.shards=[load(p) for p in sorted((CORPUS/"source_readings").glob("shard-*.json"))]
        cls.emergent=load(CORPUS/"global_atlas.json")
        cls.primary=load(ATLAS/"github_repository_survey.json")
        cls.frontier=load(ATLAS/"github_frontier_repository_survey.json")
        cls.network=load(ATLAS/"atlas_network.json")
        cls.ted=load(ATLAS/"ted_published_notice_context.json")
        cls.map=build(cls.manifest,cls.shards,cls.emergent,cls.primary,
                      cls.frontier,cls.network,cls.ted)

    def rebuild(self, **kw):
        data={"manifest":self.manifest,"shards":self.shards,"emergent":self.emergent,
              "primary":self.primary,"frontier":self.frontier,
              "network":self.network,"ted":self.ted}
        data.update(kw)
        return build(*(data[x] for x in (
            "manifest","shards","emergent","primary","frontier","network","ted")))

    def test_real_sources_make_three_separate_maps_without_edges(self):
        m=self.map
        self.assertEqual(m["schema"],SCHEMA)
        self.assertEqual(m["layers"],["practical","academic","implementation"])
        self.assertEqual(m["total_unique_original_research_sources"],63)
        self.assertEqual(m["practical"]["reported_case_count"],9)
        self.assertEqual(len(m["practical"]["published_procurement_notices_as_separate_context"]),48)
        self.assertEqual(m["academic"]["source_count"],47)
        self.assertEqual(len(m["academic"]["provisional_themes"]),8)
        self.assertEqual(len(m["academic"]["unplaced_source_ids"]),6)
        i=m["implementation"]
        self.assertEqual(i["unique_repositories"],1287)
        self.assertEqual(i["deduplicated_survey_occurrences"],71)
        self.assertEqual(i["repository_category_memberships"],1360)
        self.assertEqual(i["metadata_reviewed_memberships"],220)
        self.assertEqual(i["unreviewed_memberships"],1140)
        self.assertEqual(i["metadata_review_labels"]["different_meaning"],35)
        self.assertEqual(m["cross_layer_edges_generated"],0)
        self.assertFalse(m["complete_world_coverage"])

    def test_source_role_reports_are_not_primary_field_verification(self):
        p=self.map["practical"]
        self.assertEqual(p["firsthand_field_records_verified"],0)
        self.assertTrue(all(not x["firsthand_field_record_verified"] and
                            not x["program_effect_independently_measured"]
                            for x in p["reported_cases"]))
        self.assertTrue(all(not x["operator_problem_verified"] and
                            not x["active_contract_or_eligibility_verified"]
                            for x in p["published_procurement_notices_as_separate_context"]))
        a=self.map["academic"]
        self.assertEqual(a["full_text_claims_verified"],0)
        self.assertTrue(all(not x["independent_entailment_or_outcome_verification"]
                            for x in a["source_abstracts"]))
        self.assertEqual(self.map["implementation"]["independently_qualified_technical_projects"],0)

    def test_provenance_pinned_and_false_unreviewed_labels_not_promoted(self):
        src={x["id"]:x for x in self.manifest["source_records"]}
        for layer,field in (("practical","reported_cases"),("academic","source_abstracts")):
            for x in self.map[layer][field]:
                self.assertEqual(x["retrieved_text_sha256"],src[x["id"]]["sha256"])
                self.assertEqual(x["url"],src[x["id"]]["url"])
        i=self.map["implementation"]
        reviewed=sum(c["metadata_semantic_review"]!="not_reviewed"
                     for x in i["repository_leads"] for c in x["categories"])
        self.assertEqual(reviewed,220)
        self.assertTrue(all(not x["underconversion_established"] for x in i["repository_leads"]))

    def test_balanced_unreviewed_review_queue_no_automatic_llm_labels(self):
        b=review_backlog(self.map,per_category=2)
        self.assertEqual(b["sampled_pairs"],88)
        self.assertEqual(b["unreviewed_memberships_in_full_source"],1140)
        self.assertEqual(len(set(x["category"] for x in b["entries"])),44)
        self.assertEqual(b["model_or_human_review_completed"],0)
        self.assertTrue(all(not x["review_complete"] and
                            x["original_semantic_label"]=="not_reviewed"
                            for x in b["entries"]))
        with self.assertRaises(ValueError):
            review_backlog(self.map,per_category=100)

    def test_faceted_browse_is_within_layer_and_not_a_quality_ranker(self):
        a=browse(self.map,layer="academic",limit=3)
        self.assertEqual(a["matching_count"],47)
        self.assertEqual(len(a["results"]),3)
        self.assertTrue(a["lexical_only"])
        self.assertFalse(a["cross_layer_join_performed"])
        repo=browse(self.map,layer="implementation",facet="finite_elements",limit=2)
        self.assertGreater(repo["matching_count"],0)
        self.assertLessEqual(len(repo["results"]),2)
        self.assertTrue(all(any(c["category"]=="finite_elements"
                                for c in x["categories"]) for x in repo["results"]))
        with self.assertRaises(ValueError):
            browse(self.map,layer="funding")
        with self.assertRaises(ValueError):
            browse(self.map,layer="implementation",limit=0)

    def test_source_content_digest_tamper_rejected(self):
        altered=deepcopy(self.shards)
        altered[0]["source_readings"][0]["source_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"pinned"):
            self.rebuild(shards=altered)
        altered=deepcopy(self.shards)
        altered[0]["source_readings"]=altered[0]["source_readings"][1:]
        with self.assertRaises(ValueError):
            self.rebuild(shards=altered)
        altered=deepcopy(self.manifest)
        altered["source_records"].append(deepcopy(altered["source_records"][0]))
        with self.assertRaises(ValueError):
            self.rebuild(manifest=altered)
        altered=deepcopy(self.emergent)
        altered["accepted_scientific_claims"]=1
        with self.assertRaises(ValueError):
            self.rebuild(emergent=altered)

    def test_repository_review_tamper_and_snapshot_disagreement_rejected(self):
        altered=deepcopy(self.network)
        altered["domain_areas"][0]["sampled_repositories"][0]["semantic_review"]="technically_verified"
        with self.assertRaisesRegex(ValueError,"semantic"):
            self.rebuild(network=altered)
        altered=deepcopy(self.frontier)
        shared=set(x["id"] for x in self.primary["repositories"])
        shared_repo=next(x for x in altered["repositories"] if x["id"] in shared)
        shared_repo["description"]="Changed without original evidence"
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            self.rebuild(frontier=altered)
        altered=deepcopy(self.ted)
        altered["notices"][0]["bid_eligibility"]="approved"
        with self.assertRaisesRegex(ValueError,"notice"):
            self.rebuild(ted=altered)

    def test_canonical_cli_writes_readonly_no_cross_layer_foundations(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            output=StringIO()
            cmd=["investigate","--workspace",str(root/"never_created"),
                 "map-foundations",
                 "--manifest",str(CORPUS/"source_manifest.json"),
                 "--reading-dir",str(CORPUS/"source_readings"),
                 "--emergent-atlas",str(CORPUS/"global_atlas.json"),
                 "--github-primary",str(ATLAS/"github_repository_survey.json"),
                 "--github-frontier",str(ATLAS/"github_frontier_repository_survey.json"),
                 "--repository-network",str(ATLAS/"atlas_network.json"),
                 "--ted-context",str(ATLAS/"ted_published_notice_context.json"),
                 "--layer","implementation","--facet","finite_elements",
                 "--limit","3",
                 "--json-out",str(root/"foundation.json"),
                 "--markdown-out",str(root/"map.md"),
                 "--review-backlog-out",str(root/"backlog.json")]
            with redirect_stdout(output):
                canonical_cli(cmd)
            report=json.loads(output.getvalue())
            self.assertEqual(report["practical_reported_cases"],9)
            self.assertEqual(report["implementation_repositories"],1287)
            self.assertEqual(report["balanced_backlog_pairs"],88)
            self.assertEqual(report["cross_layer_edges_created"],0)
            self.assertFalse((root/"never_created").exists())
            artifact=load(root/"foundation.json")
            self.assertEqual(artifact["within_layer_browse"]["layer"],"implementation")
            self.assertEqual(len(load(root/"backlog.json")["entries"]),88)
            self.assertIn("Three independent evidence maps",(root/"map.md").read_text())
            with self.assertRaisesRegex(ValueError,"overwrite"):
                canonical_cli(cmd)


if __name__=="__main__":
    unittest.main()
