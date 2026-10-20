"""Candidate atlas cannot silently omit or create sources or approve outcomes."""
from __future__ import annotations
import copy
import unittest
import json
from pathlib import Path
from cite_refinery.open_corpus_atlas import validate_synthesis,synthesis_prompt

def fixture():
    readings=[{
        "source_id":f"S{i}","role":"academic_finding","statement":"Source reports a bounded observation about local context.",
        "scope":"Within the sampled place and time","caveat":"No universal intervention effect."
    } for i in range(12)]
    provisional={"readings":readings,"emergent_clusters":[]}
    ids=[r["source_id"] for r in readings]
    groups=[]
    for k in range(6):
        groups.append({
            "label":f"Coherent problem area {k}",
            "problem_node":"An observed problem requires locally grounded definition and measurement.",
            "source_ids":ids[k*2:k*2+2],
            "measurement_node":"Study measures a contextual outcome but has a limited sample.",
            "intervention_node":"No observed intervention implementation was independently verified.",
            "evidence_limit":"Small source collection and uncertain causal attribution.",
            "questions":["Which longitudinal source could independently validate this context?"],
        })
    return provisional,{"domains":groups,"cross_domain_links":[],"unplaced_source_ids":[],
                        "map_limit":"Only a bounded source collection was read; other topics and contrary evidence may be absent."}

class AtlasContractTests(unittest.TestCase):
    def test_full_map_from_emergent_source_proposals(self):
        x,raw=fixture()
        map_=validate_synthesis(raw,x)
        self.assertEqual(map_["mapped_source_count"],12)
        self.assertEqual(len(map_["domains"]),6)
        self.assertFalse(map_["blind_human_validation"])
        self.assertEqual(map_["accepted_scientific_claims"],0)
        self.assertIn("no predefined ontology",synthesis_prompt(x).lower().replace("no predefined ontology modules","no predefined ontology"))
    def test_missing_and_invented_source_rejected(self):
        p,base=fixture()
        x=copy.deepcopy(base);x["domains"][0]["source_ids"]=["S0","S100"]
        with self.assertRaisesRegex(ValueError,"Unanchored"):validate_synthesis(x,p)
        x=copy.deepcopy(base);x["domains"][0]["source_ids"]=["S0","S2"]
        with self.assertRaisesRegex(ValueError,"over-assigned|omitted"):validate_synthesis(x,p)
        x=copy.deepcopy(base);x["domains"][0]["source_ids"]=["S0","S1"]
        x["domains"][1]["source_ids"]=["S0","S1"]
        x["domains"][2]["source_ids"]=["S0","S1"]
        with self.assertRaisesRegex(ValueError,"over-assigned"):validate_synthesis(x,p)
    def test_absolute_negative_intervention_claim_rejected_from_incomplete_sample(self):
        p,base=fixture()
        x=copy.deepcopy(base)
        x["domains"][0]["intervention_node"] = (
            "There is NO verified deployed intervention or measured outcome demonstrating mortality reduction.")
        with self.assertRaisesRegex(ValueError,"Unscoped absence"):
            validate_synthesis(x,p)
        x["domains"][0]["intervention_node"] = (
            "No verified deployment was identified within these retrieved sources; further investigation is needed.")
        self.assertEqual(len(validate_synthesis(x,p)["domains"]), 6)
        prompt=synthesis_prompt(p)
        self.assertIn("NOT FOUND IN THESE RETRIEVED SOURCES",prompt)

    def test_original_atlas_global_absence_overclaim_is_flagged(self):
        from cite_refinery.open_corpus_atlas import reject_unscoped_absence
        path=Path(__file__).resolve().parents[1] / "research_materials/runtime_trials/open_corpus_20261020/global_atlas.json"
        atlas=json.loads(path.read_text(encoding="utf-8"))
        heat=next(x for x in atlas["domains"] if "Heat" in x["label"])
        with self.assertRaisesRegex(ValueError,"Unscoped absence"):
            reject_unscoped_absence(heat["intervention_node"])

    def test_cross_area_relation_must_be_from_accepted_domain_labels(self):
        p,base=fixture()
        x=copy.deepcopy(base);x["cross_domain_links"]=[{
            "from_label":"Coherent problem area 0","to_label":"Imaginary domain",
            "relation":"methodological_analogy","rationale":"Claimed relationship is not backed by any source."
        }]
        with self.assertRaisesRegex(ValueError,"cross-domain"):validate_synthesis(x,p)
if __name__=="__main__":unittest.main()
