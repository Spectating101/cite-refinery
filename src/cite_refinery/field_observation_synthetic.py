"""Entirely synthetic animal-encounter fixtures to exercise the field contract.

No raw field observations, owner records, GPS, exact properties or photographs.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

from .field_observation_contract import SCHEMA,assess

def synthetic_pilot():
    visits=[]
    detections=[]
    day=0
    for round_id in ("pre","post"):
        for visit_no in range(2):
            day+=1
            vid=f"survey_{round_id}_{visit_no}"
            visits.append({
                "visit_id":vid,"round_id":round_id,"site_code":"district_A",
                "survey_day":f"2026-10-{day:02d}",
                "planned_effort_km":2.0,"actual_effort_km":2.0,
                "fixed_route":True,"observer_independent":True,
                "observer_blinding_documented":True,"weather_code":"dry",
            })
            for i in range(6):
                both=i in (0,1,2)
                ea={
                    "visit_id":vid,"event_code":f"event_{round_id}_{visit_no}_{i}",
                    "observed_a":i!=4,"observed_b":both or i==4,
                    "match_status":"confirmed" if both else "not_applicable",
                    "matching_confidence":0.99 if both else 0.0,
                    "distance_m":float(8+i*5),
                    "animal_code":f"dog_{i:03d}",
                    "age_class":"puppy" if i==5 else "adult",
                    "reproductive_sign":"pup_with_resident_dam" if i==5 else "none_observed",
                }
                detections.append(ea)
    return {
        "schema":SCHEMA,"synthetic":True,"species":"free_roaming_dog",
        "visits":visits,"detections":detections,
        "origin_evidence":[
            {"event_code":"event_post_0_0","origin_class":"cross_boundary_confirmed",
             "evidence_kind":"direct_animal_observation","corroborated":True,"consent_confirmed":False},
            {"event_code":"event_post_0_5","origin_class":"resident_dam_observed",
             "evidence_kind":"direct_animal_observation","corroborated":True,"consent_confirmed":False},
        ],
    }

def incomplete_pilot():
    records=deepcopy(synthetic_pilot())
    records["origin_evidence"]=[]
    records["visits"][0]["observer_independent"]=False
    records["detections"][0]["match_status"]="uncertain"
    records["detections"][0]["matching_confidence"]=0.3
    return records

def build_examples(directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"cite_refinery.synthetic_field_contract_demo.v1"}
    for name,records in (
        ("synthetic_observations.json",synthetic_pilot()),
        ("synthetic_missing_quality.json",incomplete_pilot()),
    ):
        assessment=assess(records)
        (root/name).write_text(json.dumps(records,indent=2)+"\n")
        (root/name.replace(".json","_readiness.json")).write_text(
            json.dumps(assessment,indent=2)+"\n")
        manifest[name]={"status":assessment["test_status"],
                        "warnings":assessment["warnings"],
                        "synthetic":assessment["synthetic"]}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest
