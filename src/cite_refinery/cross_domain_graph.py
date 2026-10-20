"""Convert semantically reviewed 3-perspective evidence coverage into neutral graph.

No role model outcome is scientific acceptance. Institution-hosted statements
stay distinct from verified implementation, and missing roles produce gap nodes
rather than speculative cross-perspective causal edges.
"""
from __future__ import annotations

import hashlib
import json

from .semantic import SemanticGraph
from .app import CiteRefinery

def _key(prefix,value):
    return prefix+"-"+hashlib.sha256(value.encode()).hexdigest()[:16]

def coverage_packet(domain,review):
    if review.get("schema")!="cite_refinery.cross_domain_role_critique.v1" or not domain.get("modules"):
        raise ValueError("Must stage critic-reviewed source evidence roles")
    modules={m["id"]:m for m in domain["modules"]}
    if set(modules)!=set(review["coverage"]):raise ValueError("Module coverage mismatch")
    module_keys={}
    nodes=[];edges=[]
    for mid,m in modules.items():
        mk=_key("module",domain["id"]+mid);module_keys[mid]=mk
        nodes.append({"key":mk,"statement":m["title"]+": "+m["summary"],
                      "kind":"concept","layer":"neutral",
                      "tags":["semantic_problem_module",m["perspective"],domain["id"]],
                      "source_refs":[],"provenance":{
                         "perspective":m["perspective"],
                         "boundary":"Ontological question only; no field claim or coverage implied."}})
    for r in review["results"]:
        if r["fit"]=="off_topic":
            continue
        key=_key("source_evidence_role",domain["id"]+r["source_id"]+r["source_sha256"])
        nodes.append({"key":key,"statement":"Source text: "+r["quote"][:1200],
                      "kind":"source","layer":"neutral","source_refs":[r["url"]],
                      "tags":["semantic_source_role",r["role"],r["fit"]],
                      "provenance":{
                          "source_id":r["source_id"],"sha256":r["source_sha256"],
                          "quote":r["quote"],"model_role":r["role"],
                          "critic_action":r["critic_action"],
                          "limitation":r["limitations"],
                          "boundary":"Even after LLM critique, source entailment, policy implementation and outcomes are not independently established."}})
        for mid in r["module_ids"]:
            if mid not in modules:raise ValueError("Source attempts unknown module")
            edges.append({"source":key,"target":module_keys[mid],
                          "relation":"CONTEXT_FOR","status":"candidate" if r["fit"]=="direct" else "unresolved",
                          "evidence_refs":[r["url"]],
                          "provenance":{"fit":r["fit"],"role":r["role"],
                              "boundary":"Source context for module, not evidence that an intervention worked."}})
    for mid,cov in review["coverage"].items():
        needs=[]
        if cov["source_coverage_status"]!="role_specific_direct_source":
            needs.append("No direct source with the required "+cov["perspective"]+" evidence role")
        if cov["perspective"]=="program":
            if not cov["implementation_reported_in_source"]:
                needs.append("No documented real operation of the intervention in reviewed sources")
            if not cov["measured_outcome_reported_in_source"]:
                needs.append("No directly reported program-outcome evaluation in reviewed sources")
        for index,statement in enumerate(needs):
            qid=_key("coverage_gap",domain["id"]+mid+str(index)+statement)
            nodes.append({"key":qid,"statement":"Unresolved: "+statement+" for "+modules[mid]["title"],
                          "kind":"research_question","layer":"neutral",
                          "source_refs":[],"tags":["semantic_coverage_gap",domain["id"]],
                          "provenance":{"required_perspective":cov["perspective"],
                                        "boundary":"Absence in retrieved sample, not evidence no studies or programs exist."}})
            edges.append({"source":module_keys[mid],"target":qid,"relation":"REQUIRES",
                          "status":"unresolved","evidence_refs":[],
                          "provenance":{"boundary":"Gap in limited source sample; not asserted truth."}})
    return {
      "schema":"cite_refinery.semantic_graph.v1",
      "source_system":"cross_domain_source_role_probe_v1",
      "clusters":[],"nodes":nodes,"edges":edges,
      "conversion_metadata":{"domain":domain["id"],
         "source_review_status":"same_family_critic_neutral_candidates",
         "accepted_scientific_claims":0,
         "accepted_program_outcomes":0,
         "independent_field_validation":False},
    }

def stage_coverage(workspace,investigation_id,domain,review):
    root=CiteRefinery(__import__("pathlib").Path(workspace)/"refinery")
    graph=SemanticGraph(root.store)
    import json
    state=json.loads((__import__("pathlib").Path(workspace)/"investigations"/(investigation_id+".json")).read_text())
    if state.get("id")!=investigation_id or review.get("investigation_id")!=investigation_id:
        raise ValueError("Cross-domain role graph bound to another project")
    project_id=state["project_id"]
    pkt=coverage_packet(domain,review)
    current=root.store.load()
    original={k:v["status"] for k,v in current["semantic_edges"].items()}
    preview=graph.preview_packet(project_id,pkt)
    if preview["changed_existing_edge_statuses"]:raise ValueError("Cannot change existing relation authority")
    receipt=graph.ingest_packet(project_id,pkt)
    after=root.store.load()
    if any(after["semantic_edges"][k]["status"]!=v for k,v in original.items()):
        raise RuntimeError("Previous graph status changed")
    return {"packet":pkt,"receipt":receipt,"preview":preview}
