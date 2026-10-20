"""Bounded, permissionless TED published-notice *context* scan.

A published notice is a procurement-demand SIGNAL, not a verified open
tender, accessible contract, budget available to us or won customer.
"""
from __future__ import annotations

from datetime import datetime,timezone
import json
from pathlib import Path
import re
import time
from typing import Any
import urllib.request

URL="https://api.ted.europa.eu/v3/notices/search"
SCHEMA="cite_refinery.ted_broad_demand_survey.v1"


def _name(obj: Any) -> str:
    if isinstance(obj,str):
        return " ".join(obj.split())[:500]
    if isinstance(obj,list):
        return _name(obj[0]) if obj else ""
    if isinstance(obj,dict):
        for k in ("eng","ENG","deu","fra"):
            if k in obj:
                return _name(obj[k])
        for v in obj.values():
            result=_name(v)
            if result:
                return result
    return ""


def validate(manifest: dict[str,Any]) -> dict[str,Any]:
    if not isinstance(manifest,dict) or manifest.get("schema")!=SCHEMA or manifest.get("provider")!="EU TED v3 public notice search":
        raise ValueError("unsupported TED manifest")
    if manifest.get("scope") not in {"ALL","ACTIVE"} or manifest.get("since")!="2026-01-01":
        raise ValueError("TED query scope must be explicit")
    if not isinstance(manifest.get("limit_per_query"),int) or not 1 <= manifest["limit_per_query"] <= 10:
        raise ValueError("bounded sampling")
    rows=manifest.get("themes")
    if not isinstance(rows,list) or not 1<=len(rows)<=20:
        raise ValueError("bounded thematic survey")
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or not all(isinstance(r.get(k),str) for k in ("id","macro","keyword")):
            raise ValueError("theme identity required")
        if not re.fullmatch("[a-z][a-z0-9_]{2,60}",r["id"]) or r["id"] in seen:
            raise ValueError("duplicate/unsafe theme")
        seen.add(r["id"])
        if not re.fullmatch("[a-z ]{4,45}",r["keyword"]):
            raise ValueError("allowlisted plain topic phrases only")
    return manifest


def _provider(body: dict[str,Any]) -> Any:
    req=urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),method="POST",
        headers={"Accept":"application/json","Content-Type":"application/json",
                 "User-Agent":"CiteRefineryAtlasResearch/0.1"})
    with urllib.request.urlopen(req,timeout=23) as resp:
        if "json" not in resp.headers.get("Content-Type","").lower():
            raise ValueError("TED did not return JSON")
        raw=resp.read(1_800_001)
        if len(raw)>1_800_000:
            raise ValueError("oversize TED response")
    return json.loads(raw)


def collect(manifest: dict[str,Any],*,request: Any = _provider,
            pause_seconds: float = 1.0) -> dict[str,Any]:
    validate(manifest)
    if not 0<=pause_seconds<=15:
        raise ValueError("pacing bound")
    notices={}
    strata=[]
    for index,theme in enumerate(manifest["themes"]):
        phrase=theme["keyword"]
        expr='FT~"'+phrase+'" AND PD>=20260101 SORT BY publication-date DESC'
        payload={
            "query":expr,
            "fields":["publication-number","notice-title","buyer-name","buyer-country",
                      "publication-date","deadline","notice-type","total-value","total-value-cur"],
            "limit":manifest["limit_per_query"],"scope":manifest["scope"],
            "page":1,"paginationMode":"PAGE_NUMBER",
        }
        status="available";count=None;sample=0;err=None
        try:
            result=request(payload)
            if not isinstance(result,dict) or not isinstance(result.get("notices"),list):
                raise ValueError("invalid TED response")
            count=result.get("totalNoticeCount")
            if not isinstance(count,int) or count<0:
                raise ValueError("invalid provider total")
            for entry in result["notices"][:manifest["limit_per_query"]]:
                if not isinstance(entry,dict):
                    continue
                number=entry.get("publication-number")
                if not isinstance(number,str) or not re.fullmatch(r"[0-9]{4,8}-20[0-9]{2}",number):
                    continue
                sample+=1
                if number not in notices:
                    notices[number]={
                        "id":"ted:"+number,"publication_number":number,
                        "url":"https://ted.europa.eu/en/notice/-/detail/"+number,
                        "title":_name(entry.get("notice-title")),
                        "buyer":_name(entry.get("buyer-name")),
                        "buyer_country":entry.get("buyer-country"),
                        "publication_date":str(entry.get("publication-date") or "")[:10],
                        "deadline":str(entry.get("deadline") or "")[:10] or None,
                        "notice_type":str(entry.get("notice-type") or "")[:60],
                        "sampled_themes":[],
                        "demand_evidence":"published_notice_metadata_not_verified_currently_open",
                        "bid_eligibility":"unknown","full_scope_reviewed":False,
                        "financial_claim":"no_budget_or_award_inferred",
                    }
                if theme["id"] not in notices[number]["sampled_themes"]:
                    notices[number]["sampled_themes"].append(theme["id"])
        except (ValueError,TypeError,OSError,json.JSONDecodeError) as exc:
            status="unavailable";err=type(exc).__name__
        strata.append({"id":theme["id"],"macro":theme["macro"],"keyword":phrase,
                        "status":status,"error_class":err,
                        "total_matching_reported":count,"sampled":sample,
                        "selection":"recent published notices, not current eligibility or demand estimate"})
        print(f"{index+1}/{len(manifest['themes'])} {theme['id']} {status} sample={sample}",flush=True)
        if index+1<len(manifest["themes"]):
            time.sleep(pause_seconds)
    return {
        "schema":"cite_refinery.ted_notice_context.v1",
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "scope":manifest["scope"],
        "query_strata":strata,
        "notices":sorted(notices.values(),key=lambda x:x["publication_number"]),
        "source":"EU TED published notices v3",
        "boundary":"This is cross-sector published procurement context. 'ALL' may include expired/awarded notices; no tender is claimed currently active, eligible, funded for our work or commercially captured.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    a=argparse.ArgumentParser(prog="cite-refinery-ted-context")
    a.add_argument("manifest",type=Path)
    a.add_argument("--output",type=Path,required=True)
    x=a.parse_args(argv)
    obj=collect(json.loads(x.manifest.read_text(encoding="utf-8")))
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("TED scope",obj["scope"],"notices",len(obj["notices"]),flush=True)
    return 0 if all(r["status"]=="available" for r in obj["query_strata"]) else 1


if __name__=="__main__":
    raise SystemExit(main())
