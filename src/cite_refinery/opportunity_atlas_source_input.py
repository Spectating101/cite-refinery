"""Cross-evidence input construction: published requirements, source-scoped
development research statements and *metadata-level* OSS capability claims.

Connection generation is read-only. No proof of applicability or economics.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

AUDITED={"relevant","adjacent"}
RESEARCH_IDS={
    "energy_environment":["EPMC-0715c73feecf","EPMC-871d10af9889",
        "EPMC-fb93375cb76d","OA-f84a08fcbd0caa","OFFICIAL-dbee83ba8137"],
    "engineering":["EPMC-1d4b60c85f48","OA-2c8a36e510bc7f",
        "OA-4a59c468fd7941","OA-8d5107d133682c","OA-53d2760b3abab4"],
    "physical_operations":["EPMC-7deb988ae2ab","EPMC-826342b4eec2",
        "OA-da5bbdb0bf0dd0","OA-8e75d5d1b1f35b","OA-dbc0b8d397869b"],
    "public_services":["OA-1139840a6d83ac","OA-4f0f6d04561a0f",
        "OFFICIAL-6d6012da212a","OFFICIAL-31e8ca003c74","EPMC-15ee874ecc38"],
    "knowledge_data":["OFFICIAL-6d6012da212a","OFFICIAL-a6feb7e72ecd"],
    "investigation_finance":["OA-6642b2dc88be44","OA-79031782b475fb",
        "OA-e29dc4e0a782ec","EPMC-83a764d60470"],
}
CROSS_REPOS={
    "energy_environment":["DOI-USGS/EGRET","apache/airflow","CesiumGS/cesium","ckan/ckan"],
    "engineering":["FreeCAD/FreeCAD","DOI-USGS/EGRET","apache/airflow","materialsproject/pymatgen"],
    "physical_operations":["apache/airflow","ckan/ckan","farmOS/farmOS","civicrm/civicrm-core"],
    "public_services":["ckan/ckan","walt-id/waltid-identity","apache/airflow","Graphify-Labs/graphify"],
    "knowledge_data":["walt-id/waltid-identity","scipy/scipy","civicrm/civicrm-core","opendataloader-project/opendataloader-pdf"],
    "investigation_finance":["apache/airflow","ckan/ckan","Graphify-Labs/graphify","walt-id/waltid-identity"],
}


def build_inputs(atlas: dict[str,Any], details: dict[str,Any],
                 provisional: dict[str,Any])->list[dict[str,Any]]:
    if atlas.get("schema")!="cite_refinery.opportunity_atlas_network.v1" or \
       details.get("schema")!="cite_refinery.ted_notice_enrichment.v1" or \
       provisional.get("schema")!="cite_refinery.open_corpus_provisional_map.v1":
        raise ValueError("source atlas, TED description, source readings required")
    repos={}
    for area in atlas["domain_areas"]:
        for r in area["sampled_repositories"]:
            if r["repository"] not in repos:
                repos[r["repository"]]=r
    readings={r["source_id"]:r for r in provisional["readings"]}
    if any(x not in readings for ids in RESEARCH_IDS.values() for x in ids):
        raise ValueError("unresolved research source reference")
    output=[]
    for macro in sorted(atlas["macro_areas"],key=lambda x:x["id"]):
        name=macro["id"]
        domain_repos=[]
        for domain in macro["domains"]:
            area=next(a for a in atlas["domain_areas"] if a["id"]==domain)
            for item in area["sampled_repositories"]:
                if item["semantic_review"]=="relevant" and item["repository"] not in domain_repos:
                    domain_repos.append(item["repository"])
                if len(domain_repos)>=14:break
        for extra in CROSS_REPOS[name]:
            if extra in repos and extra not in domain_repos:
                domain_repos.append(extra)
        repo_list=[]
        for name_id in domain_repos[:19]:
            r=repos[name_id]
            if not r["description"] or len(r["description"])<15:continue
            repo_list.append({
                "id":"github:"+name_id,"url":r["url"],
                "description":r["description"][:390],
                "evidence_status":"github_description_claim_not_code_verified",
                "domain_relevance":"model_metadata_review" if r["semantic_review"] in AUDITED else
                                   "unreviewed_cross_domain_asset",
                "no_license_rights_granted":True,
            })
        notice_list=[]
        for n in details["notices"]:
            # map the selected TED theme from source context's joined notice groups:
            known=next((m for m in atlas["published_procurement_context"]
                        if m["macro"]==name and any(z["id"]==n["id"] for z in m["notices"])),None)
            if known is None:continue
            if not n["excerpts"]:continue
            notice_list.append({
                "id":n["id"],"source_url":n["url"],
                "title":n["published_title"][:250],
                "description":n["excerpts"][0][:650],
                "buyer":n["buyer"][:120],
                "lifecycle_category":n["lifecycle_category"],
                "evidence_status":"published_notice_excerpt_not_active_or_eligible_tender",
            })
        if not notice_list:continue
        research=[]
        for id in RESEARCH_IDS[name]:
            r=readings[id]
            research.append({
                "id":id,"source_url":r["source_url"],
                "statement":r["statement"][:450],
                "caveat":r["caveat"][:280],
                "role":r["role"],
                "evidence_status":"unverified_model_source_reading_not_original_article",
            })
        output.append({
            "schema":"cite_refinery.source_connected_input.v1",
            "macro":name,"needs":notice_list[:4],
            "repo_assets":repo_list,"research":research,
            "scope":"Published institutional requirement excerpts and repository descriptions, not evidence of open commercial demand or actual product compatibility.",
        })
    return output


def main(argv:list[str]|None=None)->int:
    import argparse
    x=argparse.ArgumentParser(prog="cite-refinery-source-bridge-input")
    for arg in ("atlas","ted","research"):
        x.add_argument("--"+arg,required=True,type=Path)
    x.add_argument("--outdir",required=True,type=Path)
    options=x.parse_args(argv)
    def load(p):return json.loads(p.read_text(encoding="utf-8"))
    rows=build_inputs(load(options.atlas),load(options.ted),load(options.research))
    options.outdir.mkdir(parents=True,exist_ok=True)
    for row in rows:
        p=options.outdir/(row["macro"]+".json")
        p.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n")
        print(row["macro"],"needs",len(row["needs"]),"repos",len(row["repo_assets"]),
              "research",len(row["research"]),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
