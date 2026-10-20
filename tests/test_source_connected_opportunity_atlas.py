from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_atlas_notice_details import parse_notice, enrich
from cite_refinery.opportunity_atlas_source_input import build_inputs
from cite_refinery.opportunity_atlas_bridge import prompt, validate
from cite_refinery.opportunity_atlas_connected import assemble as assemble_connected, markdown

ROOT=Path(__file__).resolve().parents[1] / "research_materials/opportunity_atlas"
RESEARCH=ROOT.parent / "runtime_trials/open_corpus_20261020/provisional_map.json"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class ConnectedAtlasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network=load("atlas_network.json")
        cls.notices=load("ted_notice_source_details.json")
        cls.readings=json.loads(RESEARCH.read_text(encoding="utf-8"))
        cls.six=build_inputs(cls.network,cls.notices,cls.readings)

    def test_six_domains_and_bounded_grounding(self):
        self.assertEqual(len(self.six),6)
        for x in self.six:
            self.assertTrue(1<=len(x["needs"])<=4)
            self.assertTrue(1<=len(x["repo_assets"])<=19)
            self.assertTrue(x["research"])
            self.assertTrue(all(n["evidence_status"]=="published_notice_excerpt_not_active_or_eligible_tender" for n in x["needs"]))
            self.assertTrue(all(r["evidence_status"]=="github_description_claim_not_code_verified" for r in x["repo_assets"]))
            self.assertTrue(all(r["evidence_status"]=="unverified_model_source_reading_not_original_article" for r in x["research"]))

    def test_ubl_lifecycle_claim_is_only_published_notice(self):
        raw=b'<ContractAwardNotice xmlns="urn:oasis:names:specification:ubl:schema:xsd:ContractAwardNotice-2"><Description>Work already subject to an awarded procurement notice and publicly published.</Description></ContractAwardNotice>'
        result=parse_notice("123456-2026",raw)
        self.assertEqual(result["lifecycle_category"],"award_notice")
        self.assertFalse(result["is_verified_currently_open"])
        self.assertTrue(result["publication_is_not_contract_opportunity"])

    def test_ted_details_supplier_invariants(self):
        self.assertFalse(self.notices["failures"])
        self.assertGreaterEqual(len(self.notices["notices"]),12)
        for n in self.notices["notices"]:
            self.assertTrue(n["excerpts"])
            self.assertFalse(n["is_verified_currently_open"])
            self.assertFalse(n["buyer_spending_commitment_to_us"])
            self.assertIn(n["lifecycle_category"],{
                "award_notice","competition_notice","prior_information_notice",
                "voluntary_ex_ante_notice","prior_information_for_competition"})
        self.assertTrue(any(n["lifecycle_category"]=="voluntary_ex_ante_notice" for n in self.notices["notices"]))

    def test_authority_boundary_on_enrichment(self):
        snapshot=load("ted_published_notice_context.json")
        number=snapshot["notices"][0]["publication_number"]
        enriched=enrich(snapshot,[number],fetcher=lambda n:{
            "id":"ted:"+n,"url":"https://ted.europa.eu/en/notice/-/detail/"+n,
            "lifecycle_category":"competition_notice",
            "excerpts":["The supplier shall install and maintain the environmental monitoring instruments."],
            "is_verified_currently_open":False,
            "buyer_spending_commitment_to_us":False})
        self.assertEqual(len(enriched["notices"]),1)
        self.assertFalse(enriched["notices"][0]["is_verified_currently_open"])
        bad=lambda n:{
            "id":"ted:"+n,"lifecycle_category":"competition_notice",
            "excerpts":["Monitoring instruments"],"is_verified_currently_open":True}
        r=enrich(snapshot,[number],fetcher=bad)
        self.assertFalse(r["notices"])
        self.assertIn(number,r["failures"])

    def _answer(self):
        x=next(i for i in self.six if i["macro"]=="knowledge_data")
        n=x["needs"][0]
        repo=x["repo_assets"][0]
        return x,{
            "links":[{
                "need_id":n["id"],"repo_id":repo["id"],
                "relation":"implementation_category_only",
                "need_anchor":n["description"][:60],
                "asset_anchor":repo["description"][:60],
                "research_id":None,"research_anchor":None,
                "mechanism":"Both descriptions mention software or data operations but no demonstrated functional interchangeability.",
                "limitation":"The repository metadata cannot establish procurement compliance, operations support, or a contractual relationship.",
                "next_check":"Read complete contract scope and corresponding repository documentation and attempt a minimal requirement trace.",
            }]}

    def test_zero_links_and_exact_anchor_validation(self):
        x,a=self._answer()
        zero=validate(x,{"links":[]})
        self.assertFalse(zero["links"])
        out=validate(x,a)
        self.assertEqual(len(out["links"]),1)
        self.assertEqual(out["links"][0]["relation"],"implementation_category_only")
        self.assertFalse(out["links"][0]["buyer_contract_established"])
        self.assertFalse(out["links"][0]["repository_rights_or_deployment_verified"])
        self.assertIn("Return ZERO",prompt(x))

    def test_fabricated_link_and_research_rejected(self):
        x,a=self._answer()
        variants=[("need_anchor","An invented requirement phrase that is nowhere in source"),
                  ("asset_anchor","An invented software capability not found in repository source"),
                  ("research_id","OA-does-not-exist"),
                  ("repo_id","github:madeup/fake")]
        for key,value in variants:
            with self.subTest(key=key):
                bad=deepcopy(a)
                bad["links"][0][key]=value
                result=validate(x,bad)
                self.assertFalse(result["links"])
                self.assertTrue(result["rejected_candidates"])

    def test_causal_sales_claim_not_accepted(self):
        x,a=self._answer()
        a["links"][0]["mechanism"]="This proves the buyer will pay us an annual recurring license fee."
        out=validate(x,a)
        self.assertFalse(out["links"])

    def test_connected_atlas_is_still_unranked_and_not_commercial_proof(self):
        batches=[json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "source_connection_results").glob("*_source_connections.json"))]
        reviews=load("repository_documentation_checks.json")
        out=assemble_connected(self.network,self.six,batches,reviews)
        self.assertEqual(out["counts"]["assessed_macros"],6)
        self.assertEqual(out["counts"]["research_attachments"],0)
        self.assertEqual(out["counts"]["candidate_components"],3)
        self.assertEqual(out["counts"]["wrong_fits"],11)
        self.assertEqual(out["counts"]["repo_readmes_inspected_for_component_leads"],3)
        self.assertEqual(out["counts"]["validated_technical_integrations"],0)
        self.assertEqual(out["counts"]["verified_buyer_commitments"],0)
        self.assertTrue(all(x["reasoning_authority"]==
            "llm_proposed_source_anchored_relation_requires_human_review" for x in out["links"]))
        self.assertTrue(all(x["buyer_contract_established"] is False for x in out["links"]))
        doc=markdown(out)
        self.assertIn("not a current tender",doc)
        self.assertIn("Caution:",doc)
        self.assertTrue(out["edges"])

    def test_connected_atlas_rejects_false_evidence_promotion(self):
        batches=[json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted((ROOT / "source_connection_results").glob("*_source_connections.json"))]
        bad=deepcopy(batches)
        bad[0]["links"][0]["buyer_contract_established"]=True
        with self.assertRaisesRegex(ValueError,"improperly promoted"):
            assemble_connected(self.network,self.six,bad)
        invalid=load("repository_documentation_checks.json")
        invalid["reviews"][0]["review_state"]="code_and_performance_verified"
        with self.assertRaisesRegex(ValueError,"documentation"):
            assemble_connected(self.network,self.six,batches,invalid)

    def test_no_unauthorized_evidence_promotion(self):
        x,a=self._answer()
        out=validate(x,a)
        link=out["links"][0]
        self.assertEqual(link["reasoning_authority"],"llm_proposed_source_anchored_relation_requires_human_review")
        self.assertTrue(link["published_notice_is_not_confirmed_active_tender"])
        self.assertFalse(link["scientific_causality_verified"])
        self.assertTrue(link["source_quote_existence_checked"])


if __name__=="__main__":
    unittest.main()
