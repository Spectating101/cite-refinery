"""Acceptance case 02: free-roaming dogs, real sources, unsolved observability.

This is a bounded product case, not a general data ingester. It checks original
v0.13 pilot integrity, independently reviewed source documentation and the
epistemic distinction between a documented survey app and validated estimator.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from cite_refinery.hosted_store import WorkspaceDB
from cite_refinery.workspace import ProductWorkspace
from cite_refinery.hosted_store import _MemoryStore

CASE = "taiwan-free-roaming-dogs-survey-management"
PILOT_SHA256 = "c1188fc6265627cdbd9144c61839a4a1a3a5200db719b0170015906891ffb216"
REVIEW_SHA256 = "a3ff46144b1403226ea1431c2607da6fbf5db660e37260911817dea984750131"
APPROVED_SOURCES = {
    "taiwan-national-survey": "https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599",
    "taiwan-miaoli-local": "https://animal.moa.gov.tw/Frontend/News/Detail/N0000000002313",
    "population-estimation-review": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/",
    "shoushan-model": "https://www.sciencedirect.com/science/article/pii/S235198942400194X",
    "icam-talea-user-guide": "https://www.icam-coalition.org/talea-user-guide/",
    "taiwan-2026-program": "https://animal.moa.gov.tw/Frontend/News/Detail/N0000000002234",
}


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked_sources(path: str | Path) -> dict[str, dict]:
    raw = Path(path).read_bytes()
    if _sha_bytes(raw) != REVIEW_SHA256:
        raise ValueError("source review mutated after approval")
    doc = json.loads(raw)
    if doc.get("schema") != "cite_refinery.animal_welfare_acceptance_sources.v1" or doc.get("case") != CASE:
        raise ValueError("source review case identity invalid")
    rows = doc.get("sources")
    if not isinstance(rows, list) or len(rows) != len(APPROVED_SOURCES):
        raise ValueError("exact approved source review required")
    sources={s["key"]:s for s in rows}
    if set(sources) != set(APPROVED_SOURCES):
        raise ValueError("source review has missing or replaced primary document")
    if any(sources[k].get("url") != url for k, url in APPROVED_SOURCES.items()):
        raise ValueError("reviewed primary URL changed")
    return sources


def case_packet(original_path: str | Path, source_review: str | Path) -> dict:
    raw = Path(original_path).read_bytes()
    if _sha_bytes(raw) != PILOT_SHA256:
        raise ValueError("original free-roaming dog pilot revision changed")
    sources = checked_sources(source_review)
    packet = deepcopy(json.loads(raw))
    if packet.get("schema") != "cite_refinery.semantic_graph.v1" or len(packet["nodes"]) != 12 or len(packet["edges"]) != 12:
        raise ValueError("unexpected canonical animal-welfare pilot")
    packet["source_system"] = "public_animal_welfare_case_review"
    for cl in packet["clusters"]:
        cl["provenance"] = {
            "case":CASE,"original_pilot_sha256":PILOT_SHA256,
            "source_review_sha256":REVIEW_SHA256,
            "review_state":"source_summaries_checked_not_field_replayed",
            "boundary":"Source-backed cluster coverage does not establish deployed animal population control.",
        }
    node_by_key = {node["key"]:node for node in packet["nodes"]}
    # Source-scope receipts explicitly prevent software and policy nodes from
    # becoming a phantom verified working population estimator.
    node_by_key["talea"]["provenance"] = {
        "source_system":"icam_provider_guide",
        "source_document":sources["icam-talea-user-guide"]["url"],
        "verification_scope":"provider_documentation_only",
        "field_execution_tested":False,
        "individual_photo_capture":False,
        "population_estimator_executed":False,
        "boundary":"Documented survey capture and data download; NOT documented individual-photo recapture or live statistical estimator.",
    }
    node_by_key["tw_source_control_policy"]["provenance"].update({
        "verification_scope":"official_policy_intent_only",
        "intervention_effectiveness_verified":False,
        "boundary":"Ministry source describes 2026 program goals, not evaluated intervention outcomes.",
    })
    node_by_key["tw_periodic_estimate"]["provenance"].update({
        "reviewed_source_url":sources["taiwan-national-survey"]["url"],
        "statistically_significant_decline":False,
        "boundary":"National survey point estimate and cadence, not continuously observed local abundance or significant intervention benefit.",
    })
    node_by_key["shoushan_immigration"]["provenance"].update({
        "reviewed_source_url":sources["shoushan-model"]["url"],
        "inference_scope":"Shoushan local model and camera trap study",
        "causal_extrapolation_to_all_taiwan":False,
    })
    for node in packet["nodes"]:
        node.setdefault("tags",[]).append("case_02_source_review")
        node.setdefault("provenance",{}).setdefault(
            "acceptance_boundary",
            "Secondary record grounded in cited original; no independent field or source-code replay.",
        )
    # Re-review every original semantic inference. An omitted status previously
    # meant 'asserted'; under case acceptance none can silently claim real
    # intervention effects or general validated applicability.
    downgrade = {
        ("estimation_validity_claim","QUALIFIES","continuous_state_problem"): "qualified",
        ("talea","PARTIALLY_ADDRESSES","continuous_state_problem"): "candidate",
        ("shoushan_immigration","SUPPORTS","open_population_problem"): "qualified",
    }
    for edge in packet["edges"]:
        pair=edge["source"],edge["relation"],edge["target"]
        if pair in downgrade:
            edge["status"]=downgrade[pair]
        if not edge.get("status"):
            # All inherited implicit assertions must instead be reviewed.
            edge["status"]="candidate"
        edge.setdefault("provenance",{}).update({
            "acceptance_reviewed":True,
            "boundary":edge.get("provenance",{}).get("boundary") or
                "Topical or methodological relationship, not proof of individual intervention efficacy.",
        })
    # Add source-backed caveats absent from the original map.
    packet["nodes"].extend([
        {
            "key":"survey_decline_not_significant",
            "statement":"The Ministry of Agriculture cautioned that the 2024 national decline relative to 2022 was not statistically significant.",
            "kind":"observation","layer":"practical","clusters":["observability"],
            "source_refs":[sources["taiwan-national-survey"]["url"]],
            "tags":["official_uncertainty","not_evidence_of_program_effectiveness"],
            "provenance":{
                "source_locator":"national 2024 survey press release",
                "reviewed_on":"2026-10-19",
                "boundary":"The apparent decline does not prove a statistically established national reduction, much less attributable policy effects.",
            },
        },
        {
            "key":"talea_sighting_photo_limit",
            "statement":"ICAM's Talea guide says a sighting cannot include an animal photograph; the app can record textual notes.",
            "kind":"limitation","layer":"program","clusters":["observability"],
            "source_refs":[sources["icam-talea-user-guide"]["url"]],
            "tags":["documented_feature_limit","no_executed_software_test"],
            "provenance":{
                "source_locator":"Talea user guide FAQ 5.4",
                "review_state":"provider_documentation_checked",
                "independent_field_validation":False,
                "boundary":"A photo-based individual mark-recapture pipeline cannot be presumed from Talea survey records alone.",
            },
        },
        {
            "key":"source_review_tool_not_tested",
            "statement":"Neither Talea's field capture workflow nor a dog-identification and local population estimator was executed in this acceptance case.",
            "kind":"requirement","layer":"neutral","clusters":["observability","intervention"],
            "source_refs":[sources["icam-talea-user-guide"]["url"]],
            "tags":["explicit_product_gap","not_production_solution"],
            "provenance":{
                "review_state":"acceptance_gap",
                "boundary":"Provider documentation does not establish operational readiness, photo ID, statistical validity, or continuous estimates.",
            },
        },
    ])
    packet["edges"].extend([
        {
            "source":"survey_decline_not_significant","target":"tw_periodic_estimate",
            "relation":"QUALIFIES","status":"qualified",
            "evidence_refs":[sources["taiwan-national-survey"]["url"]],
            "provenance":{"review_state":"source_statement_checked",
                          "boundary":"Government itself says inter-year estimate difference not statistically significant."},
        },
        {
            "source":"talea","target":"talea_sighting_photo_limit",
            "relation":"LIMITED_BY","status":"qualified",
            "evidence_refs":[sources["icam-talea-user-guide"]["url"]],
            "provenance":{"review_state":"documented_provider_feature",
                          "boundary":"Provider user guide documents that sighting record has no animal photo."},
        },
        {
            "source":"talea_sighting_photo_limit","target":"identity_reconciliation_requirement",
            "relation":"MISSING_LINK","status":"unresolved",
            "evidence_refs":[sources["icam-talea-user-guide"]["url"],
                             sources["population-estimation-review"]["url"]],
            "provenance":{"review_state":"method_dependency_unresolved",
                          "boundary":"No individual-photo identity workflow tested or shown to be available through the provider app."},
        },
        {
            "source":"source_review_tool_not_tested","target":"local_estimation_requirement",
            "relation":"MISSING_LINK","status":"unresolved",
            "evidence_refs":[sources["icam-talea-user-guide"]["url"]],
            "provenance":{"review_state":"field_estimation_not_executed",
                          "boundary":"No local population estimator, repeated field survey or validated downstream program integration."},
        },
    ])
    packet["conversion_metadata"]={
        "case":CASE,
        "original_pilot_sha256":PILOT_SHA256,
        "source_review_sha256":REVIEW_SHA256,
        "reviewed_primary_sources":len(sources),
        "field_tested_programs":0,
        "locally_executed_statistical_estimators":0,
        "boundary":"Case 02 tests research map semantics and source fidelity, NOT validated intervention effectiveness.",
    }
    return packet


def evaluate_case(state: dict[str, Any], project: str) -> dict[str, Any]:
    """Machine-check researcher-facing claims and source-applicability gaps."""
    atlas=ProductWorkspace(_MemoryStore(state)).project_view(project)["atlas"]
    clusters={c["title"]:c for c in atlas["clusters"]}
    violations=[]
    expect=("Population observability",
            "Population replenishment and source control",
            "Intervention effectiveness and feedback")
    for title in expect:
        if title not in clusters:
            violations.append("Missing semantic module: "+title)
    members={n["external_key"].split(":",1)[-1]:n for n in state["semantic_nodes"].values()
             if n.get("project_id")==project and n.get("external_key")}
    required=(
        "tw_periodic_estimate","survey_decline_not_significant",
        "estimation_validity_claim","capture_recapture_method","talea",
        "talea_sighting_photo_limit","identity_reconciliation_requirement",
        "local_estimation_requirement","source_review_tool_not_tested",
        "shoushan_immigration","miaoli_persistence","tw_source_control_policy",
    )
    for key in required:
        if key not in members:
            violations.append("Missing source-backed evidence node: "+key)
    for key in ("tw_periodic_estimate","survey_decline_not_significant","talea",
                "talea_sighting_photo_limit","shoushan_immigration",
                "miaoli_persistence","tw_source_control_policy"):
        if key in members and not any(s.startswith("https://") for s in members[key]["source_refs"]):
            violations.append("Missing actual source citation: "+key)
    def receipts(key):
        return members.get(key,{}).get("provenance_receipts") or []
    if not any(r.get("statistically_significant_decline") is False
               for r in receipts("tw_periodic_estimate")):
        violations.append("Official non-significant survey distinction suppressed.")
    if not any(r.get("individual_photo_capture") is False
               and r.get("field_execution_tested") is False
               and r.get("population_estimator_executed") is False
               for r in receipts("talea")):
        violations.append("Provider-documented Talea limitation or test-scope missing.")
    if not any(r.get("intervention_effectiveness_verified") is False
               for r in receipts("tw_source_control_policy")):
        violations.append("Ministry program intent mistaken for verified outcome.")
    if not any(r.get("causal_extrapolation_to_all_taiwan") is False
               for r in receipts("shoushan_immigration")):
        violations.append("Shoushan model applicability limitation missing.")
    original=members.get("talea",{})
    app_id=original.get("id")
    photo_id=members.get("talea_sighting_photo_limit",{}).get("id")
    identity_id=members.get("identity_reconciliation_requirement",{}).get("id")
    requirements_id=members.get("local_estimation_requirement",{}).get("id")
    missing_id=members.get("source_review_tool_not_tested",{}).get("id")
    national_id=members.get("tw_periodic_estimate",{}).get("id")
    nonsig_id=members.get("survey_decline_not_significant",{}).get("id")
    edges=[e for e in state.get("semantic_edges",{}).values() if e.get("project_id")==project]
    def has(src,dst,relation,status):
        return any(e.get("source_id")==src and e.get("target_id")==dst
                   and e.get("relation")==relation and e.get("status")==status
                   for e in edges)
    if not has(app_id,photo_id,"LIMITED_BY","qualified"):
        violations.append("Provider's no-photo limitation is not explicitly linked.")
    if not has(photo_id,identity_id,"MISSING_LINK","unresolved"):
        violations.append("Missing link from no-photo feature to individual identity must remain unresolved.")
    if not has(missing_id,requirements_id,"MISSING_LINK","unresolved"):
        violations.append("Untested local estimator gap is hidden.")
    if not has(nonsig_id,national_id,"QUALIFIES","qualified"):
        violations.append("Non-significant national decline caveat not linked.")
    if any(e["status"]=="asserted" for e in edges):
        violations.append("Unreviewed asserted edge in real-world animal welfare map.")
    if any(e["relation"] in ("DEPLOYED_BY","CAUSES","SAME_AS")
           and e["status"] in ("qualified","asserted") for e in edges):
        violations.append("Map fabricates deployment or causal evidence.")
    for title in expect:
        if title in clusters:
            cl=clusters[title]
            if not all(cl["layer_presence"].get(k) for k in ("practical","academic","program")):
                violations.append("One expected problem module lacks three distinct evidence authority families.")
    # These task answers are machine-enforced audit pointers, NOT the result
    # of a human researcher usability trial.
    tasks=[
        {
            "question":"What did Taiwan report for 2024, and was its decrease statistically significant?",
            "required_evidence":["tw_periodic_estimate","survey_decline_not_significant"],
            "answer":"141584 dogs; an apparent decrease from 2022, explicitly not statistically significant",
            "status":"traceable_in_map",
        },
        {
            "question":"Can Talea alone provide photo-based individual dog matching and a validated local abundance estimate?",
            "required_evidence":["talea","talea_sighting_photo_limit","identity_reconciliation_requirement","local_estimation_requirement"],
            "answer":"No documented photo within a sighting and no validated local estimation pipeline demonstrated; identity reconciliation remains unresolved",
            "status":"traceable_in_map",
        },
        {
            "question":"Does Shoushan's model prove sterilization works nationally under immigration?",
            "required_evidence":["shoushan_immigration","miaoli_persistence"],
            "answer":"No: localized camera-trap/modelling evidence shows immigration can undermine control, without nationwide causal validation",
            "status":"traceable_in_map",
        },
        {
            "question":"Is the 2026 source-control policy a proven effective intervention?",
            "required_evidence":["tw_source_control_policy","longitudinal_feedback_requirement"],
            "answer":"No: policy intent is documented, but longitudinal population, welfare, and conflict outcomes remain unverified here",
            "status":"traceable_in_map",
        },
    ]
    for task in tasks:
        if any(k not in members for k in task["required_evidence"]):
            violations.append("Reader audit evidence missing for task: "+task["question"])
    report={
        "schema":"cite_refinery.animal_welfare_acceptance_report.v1",
        "case":CASE,
        "outcome":"ACCEPTED_WITH_OPEN_GAPS" if not violations else "REJECTED",
        "module_count":len(clusters),
        "structurally_three_layer_modules":atlas["summary"]["three_layer_clusters"],
        "practical_nodes":sum(n["layer"]=="practical" for n in members.values()),
        "academic_nodes":sum(n["layer"]=="academic" for n in members.values()),
        "program_nodes":sum(n["layer"]=="program" for n in members.values()),
        "total_edges":len(edges),
        "candidate_edges":sum(e["status"]=="candidate" for e in edges),
        "unresolved_edges":sum(e["status"]=="unresolved" for e in edges),
        "qualified_edges":sum(e["status"]=="qualified" for e in edges),
        "verified_field_survey_run":False,
        "verified_local_population_estimator":False,
        "verified_management_effectiveness":False,
        "human_researcher_usability_tested":False,
        "machine_audited_researcher_tasks":tasks,
        "blocked_claims":[
            "A national survey difference is not a statistically established reduction.",
            "Talea's documented survey functionality is not a verified photographic individual-matching or statistical estimator.",
            "Shoushan's local open-population model is not a nationally causal policy evaluation.",
            "An announced management program is not independently proven effective.",
            "Machine-checked citation navigation is not human-researcher comprehension testing.",
        ],
        "violations":violations,
    }
    return report


def run_case(pilot: str | Path, reviewed: str | Path, private_db: str | Path) -> dict[str, Any]:
    path=Path(private_db)
    if path.exists():
        raise ValueError("Refusing to write acceptance case into an existing private database")
    packet=case_packet(pilot, reviewed)
    db=WorkspaceDB(path)
    user=db.create_tenant("Dog population acceptance test", "source-reviewer")
    uid=user["owner_user_id"]
    project=db.create_project(uid,user["tenant_id"],
        "Free-roaming dog welfare and survey observability",
        "Can a research map connect source-specific population estimates, academic methods and documented tools without inventing operational effectiveness?")
    preview=db.preview(uid,project,packet)
    db.enqueue(uid,project,packet,preview["project_revision"],preview["packet_digest"])
    job=db.run_one_job()
    if job["status"]!="succeeded":
        raise RuntimeError("Case ingest transaction failed: "+str(job.get("error",""))[:200])
    state=db.project_state(uid,project)
    report=evaluate_case(state,project)
    report["packet_digest"]=preview["packet_digest"]
    report["private_project_revision"]=preview["project_revision"]+1
    if report["outcome"]!="ACCEPTED_WITH_OPEN_GAPS":
        raise RuntimeError("Acceptance rejected: "+json.dumps(report["violations"]))
    return report


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--pilot",default="examples/free_roaming_dog_semantic_pilot.json")
    p.add_argument("--review",default="examples/acceptance_free_roaming_dog_source_review_v1.json")
    p.add_argument("--db",required=True)
    args=p.parse_args(argv)
    result=run_case(args.pilot,args.review,args.db)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
