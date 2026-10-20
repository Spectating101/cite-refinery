"""Assemble an intentionally UNRANKED, source-bounded atlas across many fields.

The atlas distinguishes discoverable repositories from reviewed problem
evidence, technical suitability, actual buyers and legal conversion rights.
It cannot automatically nominate a "best" sector or claim underconversion.
"""
from __future__ import annotations

from collections import Counter,defaultdict
import json
from pathlib import Path
from typing import Any

GH = "cite_refinery.opportunity_atlas_github_snapshot.v1"
CHANNELS = "cite_refinery.opportunity_atlas_channels.v1"
BRIDGES = "cite_refinery.opportunity_atlas_mechanisms.v1"
SEMANTIC = "cite_refinery.opportunity_atlas_semantic_review.v1"


def combine_snapshots(primary: dict[str,Any], frontier: dict[str,Any]) -> dict[str,Any]:
    """Join separate sampling frames, never sum different query-population totals."""
    if primary.get("schema")!=GH or frontier.get("schema")!=GH:
        raise ValueError("not two provider snapshots")
    if primary.get("sample_segment", "primary")!="primary" or frontier.get("sample_segment")!="recent_lower_visibility":
        raise ValueError("distinct primary and frontier frames required")
    a={s["id"]:s for s in primary["strata"]}
    b={s["id"]:s for s in frontier["strata"]}
    if set(a)!=set(b):
        raise ValueError("sampling frames do not cover same strata")
    repos={r["full_name"]:dict(r) for r in primary["repositories"]}
    for r in frontier["repositories"]:
        name=r["full_name"]
        if name not in repos:
            repos[name]=dict(r)
        else:
            old=repos[name]
            old["found_in"]=sorted(set(old["found_in"]+r["found_in"]))
            old["sample_segments"]=sorted(set(old.get("sample_segments",["primary"])+r.get("sample_segments",["recent_lower_visibility"])))
    strata=[]
    for id in a:
        merged=dict(a[id])
        merged["frontier_sampling"]={
            "query":b[id]["query"],
            "source_url":b[id].get("source_url"),
            "frontier_matching_results_not_additive":b[id]["total_reported"],
            "sampled":b[id]["sampled"],
            "status":b[id]["status"],
        }
        merged["sampled"]=sum(id in r["found_in"] for r in repos.values())
        strata.append(merged)
    out=dict(primary)
    out["sample_segment"]="combined"
    out["query_count"]=primary["query_count"]+frontier["query_count"]
    out["strata"]=strata
    out["repositories"]=sorted(repos.values(), key=lambda r:r["full_name"].casefold())
    out["collection_errors"]={
        "primary":primary.get("collection_errors",{}),
        "frontier":frontier.get("collection_errors",{}),
    }
    out["observed_at"]=max(primary["observed_at"],frontier["observed_at"])
    out["boundary"]=primary["boundary"]+" Lower-visibility sampling uses activity and GitHub counters, neither of which proves underconversion."
    return out


def assemble(github: dict[str,Any], channels: dict[str,Any],
             crosswalk: dict[str,Any], judgments: list[dict[str,Any]] | None = None,
             ted: dict[str,Any] | None = None) -> dict[str,Any]:
    if github.get("schema")!=GH or channels.get("schema")!=CHANNELS or crosswalk.get("schema")!=BRIDGES:
        raise ValueError("incorrect atlas source schema")
    rows=github.get("strata")
    repos=github.get("repositories")
    if not isinstance(rows,list) or not isinstance(repos,list):
        raise ValueError("invalid repository survey")
    id_to_domain={r["id"]:r for r in rows}
    if len(id_to_domain)!=len(rows):
        raise ValueError("duplicate domain")
    refs={}
    for r in repos:
        name=r["full_name"]
        if name in refs:
            raise ValueError("duplicate repository")
        if any(domain not in id_to_domain for domain in r["found_in"]):
            raise ValueError("unknown repository domain")
        if r.get("evidence_level")!="public_repository_metadata_unverified":
            raise ValueError("attempt to import promoted external evidence")
        refs[name]=r
    mechanisms=crosswalk.get("bridges",[])
    modes=crosswalk.get("conversion_modes",[])
    if not isinstance(mechanisms,list) or not isinstance(modes,list):
        raise ValueError("invalid crosswalk")
    for b in mechanisms:
        if not set(b["domain_ids"]) <= set(id_to_domain):
            raise ValueError("mechanism references missing domain")
        if b["review_status"]!="curated_candidate_mechanism_not_validated_fit":
            raise ValueError("unverified bridge improperly promoted")
    semantic_reviews={}
    for audit in judgments or []:
        if audit.get("schema")!=SEMANTIC:
            raise ValueError("invalid semantic review")
        for j in audit["judgments"]:
            key=(j["domain_id"],j["repository_id"])
            if key in semantic_reviews or j["domain_id"] not in id_to_domain or j["repository_id"] not in refs:
                raise ValueError("duplicate/unknown semantic review subject")
            if j["domain_id"] not in refs[j["repository_id"]]["found_in"]:
                raise ValueError("model classification outside collected topic match")
            if j.get("review_state")!="model_metadata_judgment_not_code_verified":
                raise ValueError("model labels cannot be promoted to accepted technical claims")
            semantic_reviews[key]=j
    macros=defaultdict(list)
    area_rows=[]
    for s in rows:
        macro=s["macro"];id=s["id"]
        eligible=[r for r in repos if id in r["found_in"]]
        eligible.sort(key=lambda r:(-int(r.get("stars") or 0),r["full_name"]))
        nlabels=Counter(semantic_reviews[(id,r["full_name"])]["label"] for r in eligible
                        if (id,r["full_name"]) in semantic_reviews)
        sample=[
            {
                "repository":r["full_name"],"url":r["url"],"description":r["description"],
                "search_basis":"GitHub topic match, NOT a working solution",
                "semantic_review":semantic_reviews.get((id,r["full_name"]),{}).get("label","not_reviewed"),
                "semantic_review_reason":semantic_reviews.get((id,r["full_name"]),{}).get("reason"),
                "tech_fit":"not_evaluated", "market_demand":"not_evaluated",
            } for r in eligible
        ]
        relevant_mechanisms=sorted(b["id"] for b in mechanisms if id in b["domain_ids"])
        area_rows.append({
            "id":id, "macro":macro,"query":s["query"],"search_url":s.get("source_url"),
            "provider_reported_matching_repositories":s.get("total_reported"),
            "sampled_repo_count":s["sampled"], "sampled_repositories":sample,
            "candidate_mechanisms":relevant_mechanisms,
            "sampled_semantic_audit":dict(nlabels),
            "problem_evidence_status":"not_systematically_surveyed",
            "academic_evidence_status":"not_systematically_surveyed",
            "implementation_evidence_status":"github_metadata_only",
            "verified_buyer_demand":"none_collected_in_this_pass",
            "economic_capture":"not_assessed",
            "rights_clearance":"not_assessed",
            "readiness":"discovery_inventory_not_a_target",
        })
        macros[macro].append(id)
    audited=len(semantic_reviews)
    procurement_by_macro=defaultdict(list)
    procurement_status="not_collected"
    if ted is not None:
        if ted.get("schema")!="cite_refinery.ted_notice_context.v1" or ted.get("scope")!="ALL":
            raise ValueError("unexpected TED procurement evidence scope")
        themes={s["id"]:s for s in ted.get("query_strata",[])}
        for notice in ted.get("notices",[]):
            if notice.get("demand_evidence")!="published_notice_metadata_not_verified_currently_open" or notice.get("full_scope_reviewed") is not False:
                raise ValueError("tender context cannot be promoted to verified eligible contract")
            for theme in notice.get("sampled_themes",[]):
                if theme not in themes:
                    raise ValueError("unrecognized notice theme")
                macro=themes[theme]["macro"]
                if macro not in macros:
                    raise ValueError("notice references unknown macro area")
                if notice["id"] not in {r["id"] for r in procurement_by_macro[macro]}:
                    procurement_by_macro[macro].append(notice)
        procurement_status="published_notice_metadata_only_not_verified_active_or_eligible"
    network={
        "schema":"cite_refinery.opportunity_atlas_network.v1",
        "as_of":github["observed_at"][:10],
        "snapshot_observed_at":github["observed_at"],
        "macro_areas":[{"id":key,"domains":sorted(values)} for key,values in sorted(macros.items())],
        "domain_areas":area_rows,
        "mechanism_hypotheses":mechanisms,
        "published_procurement_context":[
            {"macro":m,"notices":rs,"evidence_status":"published_notice_metadata_only_not_eligible_bid"}
            for m,rs in sorted(procurement_by_macro.items())
        ],
        "source_channels":channels["channels"],
        "conversion_modes":modes,
        "coverage_integrity":{
            "survey_domains":len(rows),
            "github_queries_executed":github.get("query_count"),"unique_repository_leads":len(repos),
            "semantically_audited_repo_domain_pairs":audited,
            "semantically_unaudited_pairs":sum(len(r["found_in"]) for r in repos)-audited,
            "semantic_metadata_conflicts":[
                {"domain_id":a["id"],"labels":a["sampled_semantic_audit"]}
                for a in area_rows if a["sampled_semantic_audit"].get("different_meaning",0)>0
            ],
            "problem_evidence_survey":"existing curated case studies separate; broad cross-field primary problems not yet collected",
            "paid_buyer_survey":"not_collected",
            "procurement_survey":procurement_status,
            "published_notices_sampled":(len(ted["notices"]) if ted is not None else 0),
            "independent_reproducibility":"not_established",
            "commercial_underconversion":"not_established",
        },
        "evidence_boundaries":[
            "Repository metadata and topic labels are untrusted navigation candidates, not source-reviewed software capabilities.",
            "Semantic auditing of descriptions does not establish code quality or real deployment.",
            "Cross-domain mechanism links are explicit hypotheses, not independently demonstrated equivalences.",
            "Published procurement metadata does not establish an open, funded-for-us, bidder-eligible or awarded contract.",
            "A registered demand/procurement channel does not establish a currently open, funded, eligible contract.",
            "Popularity, low stars and issue counts are not economic underconversion or paying demand.",
            "The frozen PR #70 research corpus and its private holdout are not merged or changed.",
            "No targets are selected or scored; a later evaluation requires buyer/rights/technical evidence.",
        ],
    }
    return network


def render_markdown(network: dict[str,Any]) -> str:
    if network.get("schema")!="cite_refinery.opportunity_atlas_network.v1":
        raise ValueError("not an opportunity atlas")
    audit=network["coverage_integrity"]
    out=[
        "# Broad Opportunity Atlas — mapping before targeting",
        "",
        "## What is mapped and what remains unproven",
        "",
        "This is a **source-bounded landscape**, not a revenue opportunity leaderboard. "
        "It inventories software-capability leads across independent fields; identifies "
        "plausible *mechanism bridges*; and tracks which evidence layers are still missing.",
        "",
        f"GitHub topical search covered {audit['survey_domains']} domain strata and retained "
        f"{audit['unique_repository_leads']} distinct public repository discovery leads. "
        "These entries are **not** evaluated product candidates or commercial targets.",
        "",
        f"An AI metadata audit labeled {audit['semantically_audited_repo_domain_pairs']} sampled "
        "repo/domain combinations; the rest remain unreviewed. "
        "Even a 'relevant' metadata label is **not a tested capability**.",
        "",
        "**Missing:** systematic problem evidence outside the existing limited case studies, "
        "actual tender/buyer validation, source-code functional checks, legal clearance, "
        "and conversion margins. No sector is selected.", "",
        "## Field coverage (implementation inventory only)", "",
        "| Field | Included questions / areas | Example unverified software leads |",
        "|---|---|---|",
    ]
    for macro in network["macro_areas"]:
        ids=set(macro["domains"])
        names=[]
        for a in network["domain_areas"]:
            if a["id"] in ids:
                names.append(a["id"].replace("_"," "))
        repo_candidates=[]
        for a in network["domain_areas"]:
            if a["id"] not in ids: continue
            # Prefer semantically relevant metadata samples if any, else first listed.
            chosen=[r for r in a["sampled_repositories"]
                    if r["semantic_review"] == "relevant"]
            if chosen:
                repo=chosen[0]
                if repo["repository"] not in repo_candidates:
                    repo_candidates.append(repo["repository"])
        out.append("| "+macro["id"].replace("_"," ").title()+" | "
            +", ".join(names)+" | "+
            (", ".join(repo_candidates[:6]) if repo_candidates else "No metadata-reviewed relevant lead yet")+
            " (AI metadata labels only) |")
    out.extend(["","## Cross-domain mechanism hypotheses", "",
        "Each row is an **investigation bridge**. It does not mean the technologies have "
        "already been integrated or that a paying buyer exists.",
        "",
        "| Mechanism | Where to investigate | What must be established |",
        "|---|---|---|",
    ])
    for b in network["mechanism_hypotheses"]:
        out.append("| "+b["title"]+" | "+", ".join(b["domain_ids"])+" | "+b["economic_question"]+" |")
    out.extend(["","## Institutional requirements — sampled published notices, not active contracts", "",
        "These are real publication metadata in the EU TED database. The ALL scope includes "
        "possibly expired or awarded notices. We have not inspected tender documents, verified "
        "budgets, checked bidder eligibility, or attached notices to specific repositories.", "",
        "| Area | Example published notice context |",
        "|---|---|",
    ])
    if network["published_procurement_context"]:
        for macro in network["published_procurement_context"]:
            examples=[]
            for n in sorted(macro["notices"],key=lambda x:x["publication_date"],reverse=True)[:3]:
                examples.append("["+n["publication_number"]+"]("+n["url"]+") "
                                +n["title"][:95].replace("|","/"))
            out.append("| "+macro["macro"].replace("_"," ")+" | "+"; ".join(examples)+" |")
    else:
        out.append("| No procurement notices sampled | No public requirements verified |")
    out.extend(["","## Reuse and conversion routes (no target selected)", "",
        "| Route | Economic hypothesis | Evidence needed / stopping rule |",
        "|---|---|---|"])
    for mode in network["conversion_modes"]:
        out.append("| "+mode["id"].replace("_"," ")+" ("+mode["route"]+") | "
                   +mode["possible_value"]+" | "+mode["evidence_required"]+"; stop if: "
                   +mode["stopping_condition"]+" |")
    out.extend(["","## Distinguishing evidence streams", "",
                "| Evidence stream | Sources indexed | What they do NOT prove |",
                "|---|---|---|"])
    grouped=defaultdict(list)
    for c in network["source_channels"]:
        grouped[c["family"]].append(c)
    for family in ("practical","academic","implementation","demand","market_context"):
        names=", ".join(c["name"] for c in grouped[family])
        limits={
            "practical":"Paid demand or causality",
            "academic":"Deployed solution effectiveness",
            "implementation":"Buyer need or usable licensed code",
            "demand":"Contract eligibility or confirmed award",
            "market_context":"Durable revenue and functionality",
        }
        out.append("| "+family.replace("_"," ")+" | "+names+" | "+limits[family]+" |")
    out.extend(["","## Critical semantic and market blind spots", "",
        "A keyword/topic match is often false: flood can mean a DDoS attack; "
        "repair can mean JSON correction; battery can mean a desktop status utility. "
        "The mapping pipeline tracks and labels these rather than silently asserting technical fit.",
        "",
        "The public repositories are just a biased first-page cross-section of GitHub's tagged projects: "
        "other forges, industrial repositories, project websites, non-English documentation, "
        "hardware prototypes, institutional implementations, and low-profile systems need further sampling.",
        "",
        "The next **mapping** pass, before any target selection, should add real practical incident/cost "
        "evidence, official procurement requirements, maintainer funding/constraints, cross-forge "
        "software inventory, and semantic source-level review. Project or field selection remains separate.",
        "",
        "## Safety and inference boundaries",""])
    out.extend("- "+x for x in network["evidence_boundaries"])
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    import argparse
    a=argparse.ArgumentParser(prog="cite-refinery-opportunity-atlas")
    a.add_argument("--survey",type=Path,required=True)
    a.add_argument("--frontier",type=Path,help="Optional low-visibility, recently active GitHub sampling frame")
    a.add_argument("--channels",type=Path,required=True)
    a.add_argument("--ted",type=Path,help="Optional ALL-scope published procurement metadata context")
    a.add_argument("--mechanisms",type=Path,required=True)
    a.add_argument("--review",type=Path,action="append",default=[])
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--markdown",type=Path,required=True)
    x=a.parse_args(argv)
    def read(p:Path): return json.loads(p.read_text(encoding="utf-8"))
    survey=read(x.survey)
    if x.frontier:
        survey=combine_snapshots(survey,read(x.frontier))
    net=assemble(survey,read(x.channels),read(x.mechanisms),[read(p) for p in x.review],
                 read(x.ted) if x.ted else None)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.markdown.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(net,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    x.markdown.write_text(render_markdown(net),encoding="utf-8")
    print("Atlas assembled",len(net["macro_areas"]),"macro areas,",
          len(net["domain_areas"]),"domain areas,",
          len(net["mechanism_hypotheses"]),"cross-domain mechanisms",
          "no target selection",flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
