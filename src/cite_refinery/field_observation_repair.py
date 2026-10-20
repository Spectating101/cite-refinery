"""Connect critical field-methods review to a data contract and readiness report.

The protocol is intentionally NOT field-approved. Synthetic inputs show how the
requirements behave; cannot turn a model-designed protocol into expert signoff.
"""
from __future__ import annotations
import json
from pathlib import Path
from .field_observation_contract import assess, digest

FIXED_REVISIONS={
    "T1":{
        "data_contract_elements":["visit_id","animal_code","matching_confidence","fixed_route",
                                  "actual_effort_km","observer_independent","observer_blinding_documented"],
        "repair":"Repeated pseudonymous individual encounters and explicit double-observer match uncertainty; independently validate false-split/false-merge rates and geographic boundaries.",
        "outstanding":"Photo-ID audit dataset, mark-resight open-population/SECR assumptions and power simulations need qualified ecological methods review.",
    },
    "T2":{
        "data_contract_elements":["origin_class","evidence_kind","corroborated","age_class",
                                  "reproductive_sign","consent_confirmed"],
        "repair":"Use non-invasive repeat visual identities, observed offspring of resident mothers, coarse zone transition evidence, and explicitly consented deidentified voluntary reports; do not mandate collars, genetics or invasive household tracking.",
        "outstanding":"Origin labels alone do not establish immigration or abandonment; unobserved neonatal loss and co-occurrence remain. Genetic parentage or telemetry requires a separate welfare/ethics feasibility decision.",
    },
    "T3":{
        "data_contract_elements":["observed_a","observed_b","match_status","matching_confidence",
                                  "distance_m","weather_code","actual_effort_km","fixed_route",
                                  "observer_independent","observer_blinding_documented","reproductive_sign"],
        "repair":"Collect independent paired observer encounter histories, match confidence, distance and effort covariates, reproductive-state categories and repeat transect visits; do not assume g(0)=1.",
        "outstanding":"MRDS model family, conditional detection dependence, responsive movement, g(0), den availability and population closure require qualified simulation/calibration. No fitting or effect inference happens here.",
    },
}

def proposed_repair(original_plan,prior_critic,observations):
    if original_plan.get("schema")!="cite_refinery.mechanism_discrimination_plan.v1":
        raise ValueError("Requires source-grounded original field-study candidate")
    if prior_critic.get("schema")!="cite_refinery.discrimination_protocol_review.v1":
        raise ValueError("Requires stored skeptical critique")
    if prior_critic.get("original_plan_digest")!=original_plan.get("source_digest"):
        raise ValueError("Original critical review must match source-digest")
    verdicts={x["id"]:x["verdict"] for x in prior_critic["reviews"]}
    if set(verdicts)!={"T1","T2","T3"}:
        raise ValueError("Expected complete critical review of all three tests")
    if verdicts["T2"]!="not_discriminating" or verdicts["T3"]!="uncertain":
        raise ValueError("Unexpected input critique: do not silently assume repaired T2/T3")
    audit=assess(observations)
    covered={}
    for test_id,fix in FIXED_REVISIONS.items():
        covered[test_id]={
            "prior_verdict":verdicts[test_id],
            "candidate_revision":fix["repair"],
            "required_fields":fix["data_contract_elements"],
            "remaining_methodological_blocker":fix["outstanding"],
            "data_format_readiness":audit["test_status"].get(test_id,"not_assessed_in_format_audit"),
            "expert_signoff":False,
            "ready_for_field_use":False,
        }
    return {
        "schema":"cite_refinery.revised_field_observation_plan.v1",
        "source_plan_digest":original_plan["source_digest"],
        "observation_dataset_sha256":digest(observations),
        "synthetic":audit["synthetic"],
        "revised_tests":covered,
        "measurement_quality_report":audit,
        "status":"data_dictionary_and_pilot_quality_checks_only",
        "next_evidence_gate":"Independent ecology/animal-welfare and privacy protocol review, pilot double-observer matching and coverage calibration, then real anonymized repeated field data.",
        "causal_identification":"not_identified",
        "observed_field_outcome_validated":False,
        "approved_for_field_deployment":False,
        "scope":"Demonstration of minimum observable data and quality preconditions only; not the original data, author validation or a statistically tested MRDS model.",
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-field-repair")
    p.add_argument("--original-plan",type=Path,required=True)
    p.add_argument("--critic-review",type=Path,required=True)
    p.add_argument("--observations",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    source=json.loads(a.original_plan.read_text())
    critic=json.loads(a.critic_review.read_text())
    data=json.loads(a.observations.read_text())
    report=proposed_repair(source,critic,data)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"out":str(a.out),"status":report["status"],
                     "synthetic":report["synthetic"],
                     "T2":report["revised_tests"]["T2"]["data_format_readiness"],
                     "T3":report["revised_tests"]["T3"]["data_format_readiness"],
                     "field_approved":False,"causal_identification":"not_identified"},indent=2))


if __name__=="__main__":main()
