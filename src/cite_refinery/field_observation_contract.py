"""Minimal privacy-conscious field observation data contract for dog survey studies.

No original wildlife counts in this module. This validator accepts field records
only for quality review; it NEVER determines immigration, birth or detection
causality. No raw GPS, household address, personal IDs, names or contact details.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import math
import re

SCHEMA="cite_refinery.noninvasive_dog_observation.v1"
AGE={"adult","juvenile","puppy","unknown"}
REPRO={"lactating","pup_with_resident_dam","none_observed","unknown"}
WEATHER={"dry","rain","variable","unknown"}
MATCH={"confirmed","uncertain","not_applicable"}
ORIGIN={"cross_boundary_confirmed","resident_dam_observed",
        "owner_report_unverified","unresolved"}
PRIVACY_FORBIDDEN={
    "owner_name","person_name","name","address","street","household_id",
    "telephone","phone","email","lat","lon","lng","latitude","longitude",
    "gps","precise_location","raw_photo","photo_path","raw_video",
    "ip_address","personal_id","exact_home_address","owner_contact",
}

def _fieldnames(record,expected,where):
    if not isinstance(record,dict) or set(record)!=set(expected):
        raise ValueError(f"{where}: fields must exactly equal the approved schema")
    if set(record)&PRIVACY_FORBIDDEN:
        raise ValueError(f"{where}: personal or precise location data forbidden")

def _id(v,what):
    if not isinstance(v,str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,48}",v):
        raise ValueError(f"{what}: anonymous bounded token required")
    return v

def _enum(v,expected,what):
    if v not in expected: raise ValueError(f"{what}: unsupported categorical code")
    return v

def _decimal(v,what,minimum=0,maximum=100000):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not minimum<=v<=maximum:
        raise ValueError(f"{what}: finite numeric measurement required")
    return float(v)

def _boolean(v,what):
    if not isinstance(v,bool):raise ValueError(f"{what}: boolean required")
    return v

def _date(v):
    if not isinstance(v,str) or not re.fullmatch(r"\d{4}-\d\d-\d\d",v):
        raise ValueError("survey_day requires YYYY-MM-DD, no full time/coordinate")
    try: date.fromisoformat(v)
    except ValueError as e:raise ValueError("Invalid survey date") from e
    return v

VISIT_FIELDS=("visit_id","round_id","site_code","survey_day","planned_effort_km",
              "actual_effort_km","fixed_route","observer_independent",
              "observer_blinding_documented","weather_code")
DETECTION_FIELDS=("visit_id","event_code","observed_a","observed_b","match_status",
                  "matching_confidence","distance_m","animal_code",
                  "age_class","reproductive_sign")
ORIGIN_FIELDS=("event_code","origin_class","evidence_kind","corroborated",
               "consent_confirmed")
EVIDENCE_KIND={"direct_animal_observation","deidentified_voluntary_report","unverified_inference"}

def assess(data):
    if not isinstance(data,dict) or set(data)!={"schema","synthetic","species","visits","detections","origin_evidence"}:
        raise ValueError("Unknown field study data schema or personal fields")
    if data["schema"]!=SCHEMA or data["species"]!="free_roaming_dog":
        raise ValueError("Only the specific dog observation contract supported")
    synthetic=_boolean(data["synthetic"],"synthetic")
    if not all(isinstance(data[k],list) for k in ("visits","detections","origin_evidence")):
        raise ValueError("Observation collections must be lists")
    if not 1<=len(data["visits"])<=100000 or len(data["detections"])>500000 or len(data["origin_evidence"])>500000:
        raise ValueError("Record counts outside bounds")
    visits={};site_rounds=defaultdict(set);warnings=[]
    for i,v in enumerate(data["visits"]):
        _fieldnames(v,VISIT_FIELDS,f"visit[{i}]")
        vid=_id(v["visit_id"],"visit_id")
        if vid in visits:raise ValueError("Duplicate visit ID")
        site=_id(v["site_code"],"site_code")
        rnd=_id(v["round_id"],"round_id")
        _date(v["survey_day"])
        planned=_decimal(v["planned_effort_km"],"planned_effort_km",0.00001,10000)
        actual=_decimal(v["actual_effort_km"],"actual_effort_km",0,10000)
        if actual>planned*1.5:raise ValueError("Actual effort significantly exceeds planned route; inspect protocol")
        for flag in ("fixed_route","observer_independent","observer_blinding_documented"):
            _boolean(v[flag],flag)
        _enum(v["weather_code"],WEATHER,"weather_code")
        if not actual:
            warnings.append("zero_effort_visit:"+vid)
        visits[vid]=v
        site_rounds[site].add(rnd)
    seen={};matched=0;ambiguous=0;solo_a=0;solo_b=0;both=0;unknown_age=0
    detections_per_visit=Counter()
    for i,e in enumerate(data["detections"]):
        _fieldnames(e,DETECTION_FIELDS,f"detection[{i}]")
        vid=_id(e["visit_id"],"detection.visit_id")
        if vid not in visits:raise ValueError("Detection refers to missing visit")
        ident=_id(e["event_code"],"event_code")
        if ident in seen:raise ValueError("Duplicate detection event code")
        seen[ident]=e
        a=_boolean(e["observed_a"],"observed_a")
        b=_boolean(e["observed_b"],"observed_b")
        if not(a or b):raise ValueError("Undetected animals are not observable event records")
        _enum(e["match_status"],MATCH,"match_status")
        confidence=_decimal(e["matching_confidence"],"matching_confidence",0,1)
        _decimal(e["distance_m"],"distance_m",0,500)
        _id(e["animal_code"],"animal_code")
        _enum(e["age_class"],AGE,"age_class")
        _enum(e["reproductive_sign"],REPRO,"reproductive_sign")
        if a and b:
            both+=1
            if e["match_status"]=="not_applicable":
                raise ValueError("Double detection needs an explicit matching assessment")
            if e["match_status"]=="uncertain" or confidence<0.95:ambiguous+=1
            else:matched+=1
        else:
            if e["match_status"]!="not_applicable":
                raise ValueError("Single observer detection cannot claim cross-observer matching")
            solo_a+=int(a);solo_b+=int(b)
        unknown_age+=e["age_class"]=="unknown"
        detections_per_visit[vid]+=1
        if visits[vid]["actual_effort_km"]==0:raise ValueError("Positive detections during zero survey effort")
    evidence=Counter();uncorroborated=[];consent_missing=[];seen_origin_events=set()
    for i,o in enumerate(data["origin_evidence"]):
        _fieldnames(o,ORIGIN_FIELDS,f"origin_evidence[{i}]")
        key=_id(o["event_code"],"origin event_code")
        if key not in seen:raise ValueError("Origin claim not linked to a captured event")
        if key in seen_origin_events:raise ValueError("Contradictory or duplicate origin evidence for same event")
        seen_origin_events.add(key)
        _enum(o["origin_class"],ORIGIN,"origin_class")
        _enum(o["evidence_kind"],EVIDENCE_KIND,"evidence_kind")
        _boolean(o["corroborated"],"corroborated")
        _boolean(o["consent_confirmed"],"consent_confirmed")
        if o["evidence_kind"]=="deidentified_voluntary_report" and not o["consent_confirmed"]:
            consent_missing.append(key)
        if o["origin_class"]!="unresolved" and not o["corroborated"]:
            uncorroborated.append(key)
        evidence[o["origin_class"]]+=1
    if consent_missing:raise ValueError("Voluntary human reports require explicit consent and deidentification")
    all_independent=all(v["observer_independent"] and v["observer_blinding_documented"] for v in visits.values())
    same_routes=all(v["fixed_route"] for v in visits.values())
    effort_complete=all(v["actual_effort_km"]>0 for v in visits.values())
    rounds_adequate=bool(site_rounds) and all(len(x)>=2 for x in site_rounds.values())
    duplicate_quality=bool(both) and ambiguous/max(1,both)<=0.10
    # These are transparent *format/readiness* thresholds, NOT field-validated
    # or statistical-power-approved rules.
    t3_ready=(
        len(visits)>=4 and rounds_adequate and all_independent and same_routes and
        effort_complete and both>=4 and duplicate_quality
    )
    corroborated_immigration=evidence["cross_boundary_confirmed"] and not uncorroborated
    corroborated_births=evidence["resident_dam_observed"] and not uncorroborated
    # Strong field identification needs specific design, oversight and
    # validated detection correction; this records availability only.
    t2_partial=bool(corroborated_immigration and corroborated_births)
    if not all_independent:warnings.append("observer_independence_or_blinding_not_verified")
    if not same_routes:warnings.append("transect_route_not_fixed")
    if not rounds_adequate:warnings.append("insufficient_repeated_rounds_per_site")
    if ambiguous:warnings.append("uncertain_or_low_confidence_double_detection_match")
    if not both:warnings.append("no_cross_observer_overlap")
    if uncorroborated:warnings.append("uncorroborated_origin_labels")
    if not t2_partial:warnings.append("missing_corroborated_origin_or_resident_maternity_contrast")
    if unknown_age:warnings.append("age_classification_unknown_present")
    statuses={
        "T2":"data_elements_available_requires_external_design_review" if t2_partial else "unresolved_data_gap",
        "T3":"conditional_data_quality_review_only" if t3_ready else "not_ready_for_detection_model",
    }
    return {
        "schema":"cite_refinery.field_observation_readiness.v1",
        "synthetic":synthetic,
        "visit_count":len(visits),
        "site_count":len(site_rounds),
        "rounds_per_site":{key:len(val) for key,val in sorted(site_rounds.items())},
        "detection_event_count":len(seen),
        "independent_observer_counts":{"a_only":solo_a,"b_only":solo_b,"both":both,
                                       "confirmed_pairs":matched,"uncertain_or_low_confidence_pairs":ambiguous},
        "source_evidence_counts":dict(evidence),
        "warnings":sorted(set(warnings)),
        "test_status":statuses,
        "detection_overlap_fraction_of_recorded_events":round(both/max(1,len(seen)),5),
        "human_privacy_fields_present":False,
        "statistically_identified_mechanism":False,
        "g_zero_estimated":False,
        "field_protocol_approved":False,
        "boundaries":[
            "Counts are source records only and do not estimate latent abundance.",
            "Observer overlap is descriptive; its ratio is NOT g(0) or a capture-recapture estimate.",
            "A double-observer setup alone does not establish observer independence, detection at zero or model validity.",
            "Both arrivals and local births can co-occur; event labels never estimate contribution to population change.",
            "Original dog photo/personal owner data and precise GPS are forbidden in this interchange.",
            "Thresholds are pilot format heuristics, not calibrated power criteria or animal-welfare approval.",
            "No original dog-level field data are implied when synthetic=true.",
        ],
    }

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
