"""Evidence-repair frontier: source-audit anomalies -> neutral graph -> new inquiry.

This is an *audit issue* workflow, not a contradiction proof or an authority
promotion. Source numbers are structurally verified against their article
table; interpretation and the reason for discrepancies remain unverified.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .external_llm_packets import _key
from .investigation_controller import InvestigationController

DOI="10.14202/vetworld.2026.2816-2849"
JATS="https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML"

def _validate_inputs(table,replication,investigation,fulltext_audit):
    if (fulltext_audit.get("schema")!="cite_refinery.fulltext_claim_audit.v1" or
        fulltext_audit.get("doi")!=DOI or
        fulltext_audit.get("source_sha256")!=table.get("source_sha256")):
        raise ValueError("Full-text article digest/DOI does not match program table")
    if table.get("schema")!="cite_refinery.published_program_table.v1":
        raise ValueError("Expected exact published-program source schema")
    if replication.get("schema")!="cite_refinery.published_table_replication_assessment.v1":
        raise ValueError("Expected checked regression replication assessment")
    if table.get("source_doi")!=DOI or replication.get("published_study_doi")!=DOI:
        raise ValueError("Audit source DOI does not match target study")
    if table["source_sha256"]!=replication.get("source_sha256",table["source_sha256"]):
        raise ValueError("Mismatched article digests")
    if table["row_count"]!=replication["program_rows"] or table["positive_effort_rows"]!=replication["positive_effort_rows"]:
        raise ValueError("Inconsistent source row counts")
    if table["row_count"]<20 or table["source_subtotals_checked"]<10:
        raise ValueError("Insufficient verified table coverage")
    if not isinstance(investigation,dict) or investigation.get("schema")!="cite_refinery.investigation.v1":
        raise ValueError("Requires prior persisted investigation")
    if not any(r.get("state")=="staged_candidates" for r in investigation["rounds"]):
        raise ValueError("Requires original source-backed staged candidates")
    found={}
    for r in reversed(investigation["rounds"]):
        for p in r.get("inspected",{}).get("propositions",[]):
            if any(q.get("source_url")==f"https://doi.org/{DOI}" for q in p.get("support",[])):
                found[f"R{r['number']}:{p['id']}"]=p
    if not found:raise ValueError("Original investigation lacks source-linked proposition for DOI")
    return found

def build_repair_cases(table,replication,investigation,fulltext_audit):
    """Priorities are deterministic audit-triage rules, not calibrated impact."""
    originals=_validate_inputs(table,replication,investigation,fulltext_audit)
    count_id=next((key for key,claim in originals.items()
                 if "requiring sterilization" in claim["statement"] and "2021" in claim["statement"]),None)
    buffer_id=next((key for key,claim in originals.items()
                  if "buffer" in claim["statement"].lower() and "male" in claim["statement"].lower() and "female" not in claim["statement"].lower()),None)
    zone3_id=next((key for key,claim in originals.items()
                  if "buffer" in claim["statement"].lower() and "female" in claim["statement"].lower()),None)
    cases=[]
    for idx,row in enumerate(replication["within_row_sex_total_mismatches"]):
        if row["type"]!="within_row_sex_total_mismatch":
            raise ValueError("Unexpected arithmetic anomaly type")
        if row["total"]==row["male"]+row["female"]:
            raise ValueError("Mismatch record does not have actual arithmetic conflict")
        issue_key=f"table2-sex-total-{row['year']}-{row['zone']}-{row['program']}"
        cases.append({
            "key":issue_key,"issue_type":"published_row_arithmetic_discrepancy",
            "priority":"P1","resolution_channel":"author_records_or_publisher_correction",
            "statement":f"Published Table 2 {row['year']}, zone {row['zone']}, program {row['program']}: total {row['total']} but male {row['male']} plus female {row['female']} equals {row['sex_sum']}.",
            "why_unresolved":"An internal published table count discrepancy is present; the underlying row definition and raw data have not been independently obtained.",
            "question":f"What original record, sex-classification convention or publication correction explains the Table 2 {row['year']} zone {row['zone']} program {row['program']} total/sex-count discrepancy?",
            "required_evidence":"Original program row, verified sex-total definition and dated analysis extract or publisher correction",
            "claim_ids":[],
            "table_ref":"T2","source_row":row["table_row"],
            "value_receipt":row,
        })
    variants=replication["model_sensitivity_cases"]
    if len(variants)<4:raise ValueError("Expected multiple sensitivity model definitions")
    matches=replication["close_IRR_and_p_reproductions_at_preregistered_tolerances"]
    if matches!=sum(bool(x.get("matches_published_T3_within_set_tolerances")) for x in variants):
        raise ValueError("Refit-match counts do not agree with model receipts")
    if matches==0:
        cases.append({
            "key":"table3-reproduction-definition-gap",
            "issue_type":"published_model_reproduction_gap",
            "priority":"P0","resolution_channel":"author_analysis_data_required",
            "statement":f"None of {len(variants)} specified published-Table-2 negative-binomial sensitivity fits jointly reproduces the Table 3 IRR and p-value within both 0.005 tolerances.",
            "why_unresolved":"The author's exact model-ready inputs, exclusions, offset definition and R script are unavailable; this does not identify a model or publication error.",
            "question":"Which exact analysis dataset, year/effort coding, inclusion rules and R glm.nb specification produced the published Table 3 annual incidence rate ratios and p-values?",
            "required_evidence":"Author-approved T3 input frame, R code, package versions, model diagnostics, and count/effort data dictionary",
            "claim_ids":[],
            "table_ref":"T3","source_row":None,
            "value_receipt":{"candidate_variants":len(variants),"close_joint_reproductions":0,
                            "published_total_IRR":1.03,"published_total_p":0.55488235},
        })
    cases.append({
        "key":"table6-buffer-exposure-design-gap",
        "issue_type":"missing_model_design_matrix",
        "priority":"P0","resolution_channel":"author_analysis_data_required",
        "statement":"The exact contemporaneous, program-aligned buffer exposure matrix behind Table T6C is not published with the accessible Table 2 summaries.",
        "why_unresolved":"Published T2 rows and T6C estimates do not establish the author's program alignment, regressors and confounder controls. Absence from the public paper is not proof original data do not exist.",
        "question":"What program alignment, buffer-operation timing and Zone × Period × Buffer Total regression design matrix generated the reported zone 1 male and zone 3 female buffer estimates?",
        "required_evidence":"Author-approved program dates, buffer_total join, zone/sex/program frame, code and CI method",
        "claim_ids":[q for q in (buffer_id,zone3_id) if q],
        "table_ref":"T6C","source_row":None,"value_receipt":{"data_access":"corresponding_author_on_request"},
    })
    cases.append({
        "key":"external-population-outcome-gap",
        "issue_type":"missing_independent_outcome_measurement",
        "priority":"P1","resolution_channel":"public_independent_source_discovery",
        "statement":"Published program catch counts do not independently measure total free-roaming dog abundance or district-specific human rabies incidence.",
        "why_unresolved":"The article reports resource limits on community-wide surveys and incomplete locally matched bite/PEP/rabies outcome series.",
        "question":"Which independent, geographically matched dog-abundance survey and bite/PEP/rabies records could test whether program catch-rate changes correspond to population and human-health changes?",
        "required_evidence":"Comparable effort- or detection-adjusted community survey plus deidentified geographically and temporally matched public-health indicators",
        "claim_ids":[q for q in (count_id,buffer_id,zone3_id) if q],
        "table_ref":"study_limitations","source_row":None,"value_receipt":{"impact_verified":False},
    })
    if len({x["key"] for x in cases})!=len(cases):
        raise ValueError("Repair case keys must be unique")
    return {"schema":"cite_refinery.evidence_repair_frontier.v1",
            "source_doi":DOI,"source_sha256":table["source_sha256"],
            "investigation_id":investigation["id"],"project_id":investigation["project_id"],
            "cases":cases,
            "limitations":["All entries are review questions, not established causal mistakes.",
                           "A derived Table T2 CSV is not the author's original operational dataset.",
                           "No author data request has been sent and no correction is asserted."],
            "authority":"neutral_unresolved_needs_primary_data",
           }

def repair_packet(frontier,investigation,graph_nodes):
    """Create standalone candidate issue/source nodes and link *only* DOI-backed claims."""
    if frontier.get("schema")!="cite_refinery.evidence_repair_frontier.v1" or frontier.get("investigation_id")!=investigation.get("id"):
        raise ValueError("Invalid repair frontier")
    index={}
    for rnd in investigation["rounds"]:
        for claim in rnd.get("inspected",{}).get("propositions",[]):
            claim_id=f"R{rnd['number']}:{claim['id']}"
            index[claim_id]=claim
    persisted={x.get("external_key"):x for x in graph_nodes}
    by_claim={}
    for ident,c in index.items():
        if not any(s.get("source_url")==f"https://doi.org/{DOI}" for s in c["support"]):
            continue
        tag="external_llm_reasoner_v1:"+_key("proposition",c["id"]+c["statement"])
        if tag in persisted:
            by_claim[ident]=persisted[tag]["id"]
    paperkey=_key("source_primary_article",DOI+frontier["source_sha256"])
    nodes=[{
        "key":paperkey,"statement":"Peer-reviewed deposited primary study underlying the Table T2/T3/T6 source audit: "+DOI,
        "kind":"source","layer":"neutral","source_refs":[JATS],
        "tags":["published_primary_source","not_independent_replication"],
        "provenance":{"doi":DOI,"jats_sha256":frontier["source_sha256"],
                      "boundary":"Author publication is source of figures, not independent verification."},
    }]
    edges=[]
    for issue in frontier["cases"]:
        key=_key("evidence_issue",issue["key"]+frontier["source_sha256"])
        qkey=_key("evidence_question",issue["key"]+issue["question"])
        nodes.extend([
            {"key":key,"statement":issue["statement"],"kind":"limitation",
             "layer":"neutral","source_refs":[JATS],"tags":["evidence_quality_review",issue["issue_type"],issue["priority"]],
             "provenance":{"key":issue["key"],"priority":issue["priority"],
                           "source_row":issue["source_row"],"source_table":issue["table_ref"],
                           "value_receipt":issue["value_receipt"],
                           "why_unresolved":issue["why_unresolved"],
                           "boundary":"Audit issue, NOT a proven error in authors' underlying dataset."}},
            {"key":qkey,"statement":issue["question"],"kind":"research_question",
             "layer":"neutral","source_refs":[JATS],
             "tags":["requires_primary_evidence","cannot_answer_with_model_confidence_alone"],
             "provenance":{"required_evidence":issue["required_evidence"],
                           "priority":issue["priority"],
                           "boundary":"Unresolved research question; no implied truth or causal effect."}},
        ])
        edges.extend([
            {"source":paperkey,"target":key,"relation":"CONTEXT_FOR","status":"candidate",
             "evidence_refs":[JATS],"provenance":{"table":issue["table_ref"],"row":issue["source_row"],
                   "boundary":"Paper contains auditable source values; interpretation pending."}},
            {"source":key,"target":qkey,"relation":"REQUIRES","status":"unresolved",
             "evidence_refs":[JATS],"provenance":{"required_evidence":issue["required_evidence"],
                   "boundary":"Resolution depends on new data, not a model verdict."}},
        ])
        for cid in issue["claim_ids"]:
            if cid not in by_claim:
                raise ValueError("Claim mapping lacks a verified existing DOI-backed node: "+cid)
            edges.append({
                "source":key,"target":by_claim[cid],"relation":"CONTEXT_FOR","status":"unresolved",
                "evidence_refs":[JATS],"provenance":{"target_claim":cid,
                     "boundary":"Relevant methodological/source limitation only, not a contradiction or refutation."},
            })
    return {
        "schema":"cite_refinery.semantic_graph.v1","source_system":"published_evidence_repair_v1",
        "clusters":[],"nodes":nodes,"edges":edges,
        "conversion_metadata":{"authority":"neutral_questions_only",
                               "issue_count":len(frontier["cases"]),
                               "accepted_scientific_claims":0,
                               "limitation":"All source-analysis flags are provisional; no original graph status is changed."},
    }

def stage_frontier(workspace,investigation_id,frontier):
    """Idempotent review graph import; never mutate source investigation state."""
    controller=InvestigationController(workspace,reasoner=None)
    session=controller.load(investigation_id)
    state_before=controller.app.store.load()
    nodes=[n for n in state_before["semantic_nodes"].values()
           if n["project_id"]==session["project_id"]]
    packet=repair_packet(frontier,session,nodes)
    preview=controller.graph.preview_packet(session["project_id"],packet)
    if preview["changed_existing_edge_statuses"]:
        raise ValueError("An existing edge would be changed")
    receipt=controller.graph.ingest_packet(session["project_id"],packet,
            packet_ref=f"evidence-repair:{frontier['source_sha256'][:16]}")
    state_after=controller.app.store.load()
    if any(state_after["semantic_edges"][eid]["status"]!=edge["status"]
           for eid,edge in state_before["semantic_edges"].items()):
        raise RuntimeError("Original relation status changed")
    return {"receipt":receipt,"preview":preview,"packet":packet}

def new_repair_investigation(workspace,original_id,frontier,*,max_rounds=2):
    """Fork a fresh investigation; original completed 2/2 session stays untouched."""
    ctrl=InvestigationController(workspace,reasoner=None)
    original=ctrl.load(original_id)
    if frontier.get("investigation_id")!=original_id or not frontier.get("cases"):
        raise ValueError("Repair frontier unrelated to parent investigation")
    ordered=sorted(frontier["cases"],key=lambda x:(x["priority"]!="P0",x["key"]))
    searchable=[q for q in ordered if q.get("resolution_channel")=="public_independent_source_discovery"]
    waiting=[q for q in ordered if q.get("resolution_channel")!="public_independent_source_discovery"]
    if not searchable:
        raise ValueError("All audit issues require author/publisher data; no independent web search target")
    focus=searchable[0]["question"]
    session=ctrl.start(focus,original["modules"],max_rounds=max_rounds,fulltext_enrichment=True)
    session["lineage"]={"parent_investigation":original_id,"source_audit_digest":frontier["source_sha256"],
                        "issue_keys":[q["key"] for q in ordered],
                        "researchable_now":[q["key"] for q in searchable],
                        "requires_external_author_data":[q["key"] for q in waiting]}
    session["dependency_queue"]=[{"key":q["key"],"priority":q["priority"],
                                  "question":q["question"],"required_evidence":q["required_evidence"],
                                  "resolution_channel":q["resolution_channel"]} for q in waiting]
    session["frontier"]=[{"question":q["question"],
                         "module_ids":[m["id"] for m in original["modules"]][:5],
                         "why_unresolved":q["why_unresolved"]} for q in searchable[1:]]
    ctrl.save(session)
    return session
