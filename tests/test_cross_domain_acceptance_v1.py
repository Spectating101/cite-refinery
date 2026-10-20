"""Independent non-model sanity and spoofing checks over saved cross-domain outputs."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

from cite_refinery.cross_domain_acceptance import audit,scope_outcome,run

ROOT=Path(__file__).resolve().parents[1]/"research_materials/runtime_trials/cross_domain_20261020"
SEEDS={d["id"]:d for d in json.loads((ROOT/"seeds.json").read_text())["domains"]}

def read(domain,post=True):
    return json.loads((ROOT/(domain+".critique.recovery.json" if post else domain+".critique.json")).read_text())

class CrossDomainAcceptanceTests(unittest.TestCase):
    def test_heat_recovery_fills_practical_but_not_verified_impact(self):
        x=audit("urban_heat",SEEDS["urban_heat"],read("urban_heat",False),read("urban_heat"))
        self.assertEqual(x["coverage_improved_in"],["practical"])
        self.assertEqual(x["remaining_missing_role"],[])
        self.assertFalse(x["broad_accuracy_estimated"])
        self.assertFalse(x["independent_source_entailment_validation"])
        self.assertFalse(x["before_and_after"]["recovered"]["per_perspective"]["program"]["measured_outcome_reported"])
    def test_ewaste_injury_not_metal_biomarker(self):
        x=audit("ewaste_exposure",SEEDS["ewaste_exposure"],read("ewaste_exposure",False),read("ewaste_exposure"))
        self.assertEqual(x["coverage_improved_in"],["program"])
        self.assertEqual(x["remaining_missing_role"],["practical"])
        outcomes=x["before_and_after"]["recovered"]["reported_outcome_endpoints"]
        self.assertEqual(len(outcomes),1)
        self.assertEqual(outcomes[0]["reported_outcome_type"],"self_reported_workplace_injury")
        self.assertFalse(outcomes[0]["toxicity_biomarker_reduction_verified"])
    def test_no_critical_review_scope_spoofing(self):
        pre=read("urban_heat",False);post=read("urban_heat")
        f=deepcopy(post)
        f["coverage"]["HT-01"]["independent_field_replication"]=True
        with self.assertRaises(ValueError):audit("urban_heat",SEEDS["urban_heat"],pre,f)
        f=deepcopy(post)
        f["coverage"]["HT-01"]["source_coverage_status"]="role_specific_direct_source"
        f["coverage"]["HT-01"]["direct_source_ids"]=[]
        with self.assertRaises(ValueError):audit("urban_heat",SEEDS["urban_heat"],pre,f)
        f=deepcopy(post)
        f["results"][0]["source_id"]=f["results"][1]["source_id"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):audit("urban_heat",SEEDS["urban_heat"],pre,f)
    def test_outcome_classification_unknown_is_not_assumed_valid(self):
        x=scope_outcome("urban_heat",[{"source_id":"S1","fit":"direct","role":"measured_program_outcome",
                                       "quote":"The intervention improved conditions in unknown ways."}])
        self.assertEqual(x[0]["reported_outcome_type"],"unclassified_requires_human_scope_review")
        self.assertFalse(x[0]["toxicity_biomarker_reduction_verified"])
    def test_reanalysis_is_deterministic(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            a=run(ROOT,Path(td)/"a.json")
            b=run(ROOT,Path(td)/"b.json")
            self.assertEqual(a,b)
            self.assertEqual((Path(td)/"a.json").read_bytes(),(Path(td)/"b.json").read_bytes())

if __name__=="__main__":unittest.main()
