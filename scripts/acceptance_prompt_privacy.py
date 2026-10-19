"""Acceptance case 01: scholarly prompt sanitization vs bounded CloakPipe evidence.

NOT a generic literature adapter, general-purpose source browser, or promotion
algorithm. Runs only with the exact source-reviewed case and pinned evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from cite_refinery.refinery_execution_bridge import case_to_packet, load_case
from cite_refinery.hosted_store import WorkspaceDB

BASELINE = "798a312958f593c6f773a433b8e1f76e18572283"
REFINERY_PIN = "2b03ad20f8ab3d55462adb38852855b940194c94"
CASE_CLUSTER = "refinery-cloakpipe-recorded-privacy-problem"
CASE_TITLE = "LLM sensitive-data exposure and bounded redaction components"
SOURCE_SCHEMA = "cite_refinery.acceptance_academic_sources.v1"
APPROVED_SOURCE_REVIEW_DIGEST = "376dc589a7fac5005ed8ac076c8902060923a1db1d0f09dcaea12d3303e51494"
PAPERS = {
    "casper-arxiv-2408-07004": {
        "title": "Casper: Prompt Sanitization for Protecting User Privacy in Web-Based Large Language Models",
        "url": "https://arxiv.org/abs/2408.07004",
        "quote": "Casper runs entirely on the user's device as a browser extension",
        "status": "arxiv_preprint", "year": 2024,
    },
    "alsa-kdd-2025": {
        "title": "ALSA: Context-Sensitive Prompt Privacy Preservation in Large Language Models",
        "url": "https://doi.org/10.1145/3711896.3736840",
        "quote": "text anonymization is considered an effective approach to preventing privacy leakage in prompts through text substitution",
        "status": "peer_reviewed_conference_abstract", "year": 2025,
    },
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _node(state: dict[str, Any], project: str, external: str, layer: str) -> dict:
    matches = [
        n for n in state.get("semantic_nodes", {}).values()
        if n.get("project_id") == project
        and n.get("external_key") == external and n.get("layer") == layer
    ]
    if len(matches) != 1:
        raise ValueError(f"one exact prior {layer} evidence node required: {external}")
    return matches[0]


def academic_packet(sources: dict[str, Any], state: dict[str, Any],
                    project: str) -> dict[str, Any]:
    """Operator-curated, primary-page excerpt pinned Academic representation."""
    if (sources.get("schema") != SOURCE_SCHEMA
            or sources.get("case") != "llm-prompt-sensitive-data-local-redaction"):
        raise ValueError("approved case-specific scholarly source review required")
    reviewed = sources.get("papers")
    if not isinstance(reviewed, list) or len(reviewed) != len(PAPERS):
        raise ValueError("exact two manually reviewed academic sources required")
    if project not in state.get("projects", {}):
        raise ValueError("private project does not exist")
    matched = [
        c for c in state.get("semantic_clusters", {}).values()
        if c.get("project_id") == project and c.get("external_key") == CASE_CLUSTER
    ]
    if len(matched) != 1 or matched[0].get("title") != CASE_TITLE:
        raise ValueError("the actual pinned Refinery privacy cluster must exist")
    practical = _node(state, project, "refinery:problem-source-statement", "practical")
    limitation = _node(state, project, "refinery:program-limitation-probes", "program")
    decision = _node(state, project, "refinery:program-reuse-review", "program")
    report = practical.get("provenance_receipts") or []
    constraints = limitation.get("provenance_receipts") or []
    decisions = decision.get("provenance_receipts") or []
    if not any(r.get("source_system") == "refinery" and r.get("refinery_commit") == REFINERY_PIN
               and r.get("review_state") == "accepted_as_source_statement" for r in report):
        raise ValueError("practical self-report is not review-attributed to pinned source")
    if not any(r.get("source_system") == "refinery" and r.get("refinery_commit") == REFINERY_PIN
               and r.get("limitation_probes") == 4 and r.get("limitation_probe_leaks") == 4
               for r in constraints):
        raise ValueError("all four known broader failures must remain recorded")
    if not any(r.get("source_system") == "refinery" and r.get("refinery_commit") == REFINERY_PIN
               and r.get("decision_code") == "REUSE_CANDIDATE"
               and r.get("execution_ready") is False for r in decisions):
        raise ValueError("component execution must remain unapproved")
    keys = [v.get("key") for v in reviewed]
    if set(keys) != set(PAPERS) or len(set(keys)) != 2:
        raise ValueError("academic paper identity substitution detected")
    nodes=[];edges=[]
    for item in reviewed:
        key=item["key"]
        anchor=PAPERS[key]
        for field,expected in (
            ("title",anchor["title"]),("source_url",anchor["url"]),
            ("citation_quote",anchor["quote"]),("publication_status",anchor["status"]),
            ("year",anchor["year"]),
        ):
            if item.get(field)!=expected:
                raise ValueError(f"reviewed academic metadata/quote mismatch: {key}/{field}")
        claim=item.get("claim")
        if not isinstance(claim,str) or len(claim)<45 or len(claim)>700:
            raise ValueError("bounded scholarly claim statement required")
        if not isinstance(item.get("source_boundary"),str) or len(item["source_boundary"])<45:
            raise ValueError("academic source applicability limitation required")
        source_key=f"primary-source-{key}"
        claim_key=f"reviewed-finding-{key}"
        provenance = {
            "academic_source_key":key,"publication_status":anchor["status"],
            "year":anchor["year"],"source_locator":item.get("source_locator"),
            "short_primary_source_quote":anchor["quote"],
            "quote_sha256":_sha(anchor["quote"]),
            "source_scope":item["source_boundary"],
            "review_state":"analyst_curated_excerpt_not_independent_fulltext_verification",
            "cross_layer_authorization":"review_of_research_scope_only",
            "fulltext_replication":False,
            "boundary":"Primary source excerpt reviewed for topical relevance; no replication or matched test against CloakPipe.",
        }
        nodes.extend([
            {
                "key":source_key,"layer":"academic","kind":"source",
                "statement":f"Scholarly source: {anchor['title']} ({anchor['year']}, {anchor['status']})",
                "clusters":[CASE_CLUSTER],"source_refs":[anchor["url"]],
                "tags":["primary_source_review","review_limited_to_public_source_excerpt"],
                "provenance":provenance,
            },
            {
                "key":claim_key,"layer":"academic","kind":"academic_claim",
                "statement":claim,"clusters":[CASE_CLUSTER],
                "source_refs":[anchor["url"]],
                "tags":["source_excerpt_reviewed","not_tested_against_cloakpipe"],
                "provenance":provenance,
            },
        ])
        edges.extend([
            {
                "source":claim_key,"target":source_key,
                "relation":"DERIVED_FROM","status":"qualified",
                "evidence_refs":[anchor["url"]],
                "provenance":{
                    **provenance,
                    "relation_scope":"quote-attributed paper finding only; not independent empirical corroboration",
                },
            },
            {
                "source":claim_key,"target":practical["id"],
                "relation":"RELATED_TO","status":"candidate",
                "evidence_refs":[anchor["url"],*practical.get("source_refs",[])],
                "provenance":{
                    "source_scope":item["source_boundary"],
                    "review_state":"related_risk_context_not_case_validated",
                    "boundary":"Paper does not verify whether this public reporter's incident happened.",
                },
            },
        ])
        if key=="casper-arxiv-2408-07004":
            # Qualified only for relative scope of mechanisms/limitations:
            # no claim Casper would pass the same test or replace CloakPipe.
            edges.append({
                "source":claim_key,"target":limitation["id"],
                "relation":"QUALIFIES","status":"qualified",
                "evidence_refs":[anchor["url"],*limitation.get("source_refs",[])],
                "provenance":{
                    "review_state":"source_scope_compared_not_head_to_head_validated",
                    "methodological_note":"Casper describes multi-stage detection; pinned regex-oriented CloakPipe evidence exposes broader leakage failures.",
                    "boundary":"Methodological scope comparison only; not a matched empirical test, superiority claim or integration.",
                },
            })
        else:
            edges.append({
                "source":claim_key,"target":limitation["id"],
                "relation":"RELATED_TO","status":"candidate",
                "evidence_refs":[anchor["url"],*limitation.get("source_refs",[])],
                "provenance":{
                    "review_state":"research_direction_only",
                    "boundary":"ALSA studies contextual anonymization; it has not been tested as a CloakPipe replacement.",
                },
            })
    # Frozen case review includes the exact curated claims, applicability
    # qualifications and publication-status labels, not just paper titles.
    # Any change requires an explicit new reviewed case revision.
    reviewed_digest = _sha(json.dumps(sources, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    if reviewed_digest != APPROVED_SOURCE_REVIEW_DIGEST:
        raise ValueError("approved scholarly source review digest mismatch")
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"academic_acceptance",
        "clusters":[{
            "key":CASE_CLUSTER,"title":CASE_TITLE,
            "provenance":{
                "acceptance_case":"prompt_privacy_01",
                "source_review_count":2,
                "boundary":"Adding scholarly source representation; not claiming that academic findings validate the specific user report.",
            },
        }],
        "nodes":nodes,"edges":edges,
        "conversion_metadata":{
            "academic_sources":2,
            "abstract_scope_claims":2,
            "cross_layer_candidate_links":3,
            "cross_layer_qualified_scope_links":1,
            "verified_user_leak_reports":0,
            "verified_production_privacy_interventions":0,
            "boundary":"Three layers represented, but problem-specific causal support and program effectiveness remain open.",
        },
    }


def evaluate_acceptance(state: dict[str, Any], project: str) -> dict[str, Any]:
    """Inspect graph facts and fail closed when coverage hides unresolved risk."""
    from cite_refinery.hosted_store import _MemoryStore
    from cite_refinery.workspace import ProductWorkspace

    view=ProductWorkspace(_MemoryStore(state)).project_view(project)
    relevant=[
        c for c in view["atlas"]["clusters"]
        if c.get("external_key")==CASE_CLUSTER
    ]
    if len(relevant)!=1:
        raise ValueError("one pinned three-layer privacy module required")
    cluster=relevant[0]
    covered=cluster["layer_counts"]
    members=set(cluster["node_ids"])
    nodes=[n for n in state.get("semantic_nodes",{}).values()
           if n.get("project_id")==project and n["id"] in members]
    member_map={n["id"]:n for n in nodes}
    edges=[e for e in state.get("semantic_edges",{}).values()
           if e.get("project_id")==project and
           (e.get("source_id") in members or e.get("target_id") in members)]
    violations=[]
    if any(covered.get(layer,0)==0 for layer in ("practical","academic","program")):
        violations.append("All three layers must contain genuine source-backed records.")
    if not any(n["layer"]=="practical" and n["kind"]=="observation" and
               any(r.get("review_state")=="accepted_as_source_statement" for r in n.get("provenance_receipts",[]))
               for n in nodes):
        violations.append("Practical source report not review-attributed.")
    if sum(n["kind"]=="source" and n["layer"]=="academic" for n in nodes)!=2:
        violations.append("Both academically reviewed source records required.")
    if sum(n["kind"]=="academic_claim" and n["layer"]=="academic" for n in nodes)!=2:
        violations.append("Two source-limited academic findings required.")
    if not all(n.get("source_refs") for n in nodes):
        violations.append("All evidence nodes must have linkable sources.")
    for academic in [n for n in nodes if n["layer"]=="academic" and n["kind"]=="academic_claim"]:
        if not any(e["source_id"]==academic["id"] and e["relation"]=="DERIVED_FROM"
                   and e["status"]=="qualified"
                   and member_map.get(e["target_id"],{}).get("kind")=="source"
                   for e in edges):
            violations.append("Academic finding lacks qualified source attribution.")
    leaks=[
        n for n in nodes if n.get("external_key")=="refinery:program-limitation-probes"
    ]
    if len(leaks)!=1 or not any(r.get("limitation_probe_leaks")==4 for r in leaks[0].get("provenance_receipts",[])):
        violations.append("Four failed broad limitation probes must remain explicit.")
    decisions=[
        n for n in nodes if n.get("external_key")=="refinery:program-reuse-review"
    ]
    if len(decisions)!=1 or not any(
        r.get("decision_code")=="REUSE_CANDIDATE" and r.get("execution_ready") is False
        for r in decisions[0].get("provenance_receipts",[])
    ):
        violations.append("No execution-approved implementation may be inferred.")
    cross=[]
    for e in edges:
        src=member_map.get(e.get("source_id"))
        dst=member_map.get(e.get("target_id"))
        if src and dst and src["layer"]!=dst["layer"] and src["layer"]!="neutral" and dst["layer"]!="neutral":
            cross.append(e)
            if e["status"]=="asserted" or e["relation"] in ("ADDRESSES","CAUSES","DEPLOYED_BY","SAME_AS"):
                violations.append("Cross-layer truth claim or production implication is not supported.")
    if len(cross)<4:
        violations.append("Insufficient explicit reviewed inter-layer relations.")
    if not any(e["status"]=="candidate" for e in cross):
        violations.append("Unresolved applicability must remain clearly identified.")
    return {
        "schema":"cite_refinery.case_acceptance_report.v1",
        "case":"llm-prompt-sensitive-data-local-redaction",
        "infrastructure_baseline":BASELINE,
        "outcome":"ACCEPTED_WITH_OPEN_GAPS" if not violations else "REJECTED",
        "structural_three_layer":all(covered.get(k,0)>0 for k in ("practical","academic","program")),
        "layer_counts":covered,
        "cluster_node_count":cluster["node_count"],
        "cross_layer_links":len(cross),
        "cross_layer_candidate_links":sum(e["status"]=="candidate" for e in cross),
        "cross_layer_qualified_scope_links":sum(e["status"]=="qualified" for e in cross),
        "production_ready":False,
        "user_report_independently_verified":False,
        "fulltext_academic_replication":False,
        "blocked_claims":[
            "No proof that the public self-report occurred as described.",
            "No independent reproduction of the pinned CloakPipe binary test.",
            "Four failed broader probes remain a recorded limitation.",
            "Neither academic method was compared to this CloakPipe run on matched test cases.",
            "No deployed privacy protection, causal effect, or broad solution demonstrated.",
        ],
        "violations":violations,
    }


def run_private_case(refinery: str | Path, sources: str | Path, dbfile: str | Path) -> dict[str, Any]:
    """Create a disposable local acceptance project; no existing user graph changed."""
    db=WorkspaceDB(dbfile)
    tenant=db.create_tenant("Three-layer acceptance laboratory","acceptance-reviewer")
    uid=tenant["owner_user_id"]
    project=db.create_project(uid,tenant["tenant_id"],
        "Protecting sensitive LLM prompts",
        "Compare real source-reported privacy risks with academic prompt sanitization and pinned bounded software evidence")
    def reviewed_import(packet: dict):
        pre=db.preview(uid,project,packet)
        db.enqueue(uid,project,packet,pre["project_revision"],pre["packet_digest"])
        result=db.run_one_job()
        if result.get("status")!="succeeded":
            raise RuntimeError("reviewed acceptance queue failed: "+str(result.get("error",""))[:120])
        return pre
    core,identity=load_case(refinery,REFINERY_PIN)
    original=case_to_packet(core,identity)
    reviewed_import(original)
    paper=json.loads(Path(sources).read_text(encoding="utf-8"))
    academic=academic_packet(paper,db.project_state(uid,project),project)
    preview=reviewed_import(academic)
    result=evaluate_acceptance(db.project_state(uid,project),project)
    result["reviewed_academic_packet_digest"]=preview["packet_digest"]
    result["project_revision"]=preview["project_revision"]+1
    if result["outcome"]!="ACCEPTED_WITH_OPEN_GAPS":
        raise RuntimeError("full case acceptance gates failed: "+json.dumps(result["violations"]))
    return result


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--refinery-repo",required=True)
    p.add_argument("--sources",default="examples/acceptance_prompt_privacy_academic_v1.json")
    p.add_argument("--db",required=True,help="New disposable local private DB, never production")
    args=p.parse_args(argv)
    path=Path(args.db)
    if path.exists():
        p.error("acceptance must use a NEW isolated SQLite file, not a live private workspace")
    report=run_private_case(args.refinery_repo,args.sources,path)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
