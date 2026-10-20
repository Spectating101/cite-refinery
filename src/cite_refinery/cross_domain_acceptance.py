"""Independent read-only release gates for three-perspective cross-domain probes.

No ground-truth accuracy is inferred from same-family model classifications.
Separates *which outcome* was measured from the mere presence of an outcome.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

EXPECTED_PERSPECTIVES={"practical","academic","program"}
DOMAINS={"urban_heat","ewaste_exposure"}

def scope_outcome(domain,results):
    found=[]
    for row in results:
        if row["fit"]!="direct" or row["role"]!="measured_program_outcome":continue
        q=row["quote"].lower()
        # Conservative self-contained outcome labels; unknown requires reviewer.
        if "injur" in q and any(w in q for w in ("reduced","reduction","decrease")):
            label="self_reported_workplace_injury" if "self-report" in q else "reported_workplace_injury"
        elif any(w in q for w in ("blood lead","blood-lead","blood pb")):
            label="blood_lead_measurement"
        elif "mortality" in q or "death" in q:
            label="mortality_related_outcome"
        else:label="unclassified_requires_human_scope_review"
        found.append({"source_id":row["source_id"],"domain":domain,
                      "reported_outcome_type":label,
                      "evidence_quote":row["quote"],
                      "is_independent_replication":False,
                      "toxicity_biomarker_reduction_verified":False if label!="blood_lead_measurement" else None})
    return found

def audit(domain,seed,initial,recovered):
    if domain not in DOMAINS or seed["id"]!=domain:raise ValueError("Unknown domain")
    mids={m["id"]:m["perspective"] for m in seed["modules"]}
    if set(mids.values())!=EXPECTED_PERSPECTIVES:raise ValueError("Incomplete three-perspective modules")
    progress={}
    for stage,review in (("initial",initial),("recovered",recovered)):
        if review.get("schema")!="cite_refinery.cross_domain_role_critique.v1":
            raise ValueError("Only critically reviewed source roles supported")
        if set(review["coverage"])!=set(mids):raise ValueError("Coverage matrix mismatch")
        if len({r["source_id"] for r in review["results"]})!=len(review["results"]):
            raise ValueError("Duplicate source ID")
        rows={r["source_id"]:r for r in review["results"]}
        for mid,c in review["coverage"].items():
            if c["perspective"]!=mids[mid]:raise ValueError("Perspective spoofing")
            actual={r["source_id"] for r in review["results"]
                    if mid in r["module_ids"] and r["fit"]=="direct"}
            if actual!=set(c["direct_source_ids"]):
                raise ValueError("Direct source list disagrees with rows")
            if c["measured_outcome_reported_in_source"]:
                if mids[mid]!="program" or not any(
                    rows[s]["role"]=="measured_program_outcome" for s in c["direct_source_ids"]
                ):raise ValueError("Unwarranted measured outcome coverage")
            if c["implementation_independently_verified"] or c["independent_field_replication"]:
                raise ValueError("This same-family probe cannot independently validate implementation")
        progress[stage]={
            "source_count":len(rows),
            "role_counts":dict(Counter(r["role"] for r in review["results"])),
            "per_perspective":{mids[mid]:{
                "module":mid,
                "coverage":review["coverage"][mid]["source_coverage_status"],
                "direct_role_matching_count":len(review["coverage"][mid]["role_matching_source_ids"]),
                "measured_outcome_reported":review["coverage"][mid]["measured_outcome_reported_in_source"],
                "independent_replication":False,
            } for mid in mids},
            "reported_outcome_endpoints":scope_outcome(domain,review["results"]),
        }
    initial_status=progress["initial"]["per_perspective"]
    recovered_status=progress["recovered"]["per_perspective"]
    improvements=[perspective for perspective in EXPECTED_PERSPECTIVES
                  if recovered_status[perspective]["coverage"]=="role_specific_direct_source"
                  and initial_status[perspective]["coverage"]!="role_specific_direct_source"]
    remaining=[perspective for perspective in EXPECTED_PERSPECTIVES
               if recovered_status[perspective]["coverage"]!="role_specific_direct_source"]
    return {
        "schema":"cite_refinery.cross_domain_acceptance_audit.v1",
        "domain":domain,"before_and_after":progress,
        "coverage_improved_in":sorted(improvements),
        "remaining_missing_role":sorted(remaining),
        "independent_source_entailment_validation":False,
        "measured_outcome_endpoint_scope_checked":True,
        "authority":"neutral_cross_domain_diagnostic",
        "generalized_across_distinct_problems":True,
        "broad_accuracy_estimated":False,
        "limitations":[
            "Publisher identity does not establish intervention implementation or effects.",
            "Role agreement from Gemini Medium/High is not independent validation.",
            "Study-specific outcome evidence cannot silently transfer to another biomarker or population.",
            "Improved retrieval coverage is not evidence that a module has comprehensive field coverage.",
        ],
    }

def run(directory,out):
    root=Path(directory);seeds=json.loads((root/"seeds.json").read_text())
    results={}
    for seed in seeds["domains"]:
        key=seed["id"]
        initial=json.loads((root/(key+".critique.json")).read_text())
        recovered=json.loads((root/(key+".critique.recovery.json")).read_text())
        results[key]=audit(key,seed,initial,recovered)
    target=Path(out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n")
    return results
