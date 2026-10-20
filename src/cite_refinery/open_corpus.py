"""Breadth-first primary-material dump: retrieve excerpts, preserve source IDs/hashes.

Search strata are ingestion quotas, NOT ontology nodes. Retrieved text stays
in an explicit local data folder. Public Git artifacts publish only metadata,
provenance, sha256 and sanitized labels, not reproduced publisher abstracts.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .investigation_sources import search_europe_pmc,search_official

SCHEMA="cite_refinery.open_corpus.v1"
SOURCE_LIMIT=96
# Broad *collection queries*, deliberately not domain modules/labels for the mapper.
QUERY_STRATA={
    "h01":{"academic":"heatwave urban cooling access health vulnerability","official":"urban heat heat health action community cooling WHO"},
    "h02":{"academic":"informal electronics waste recycling toxic occupational exposure","official":"e-waste informal recycling children workers WHO"},
    "h03":{"academic":"food surplus redistribution food insecurity waste rescue","official":"food loss redistribution food banks sustainable cities FAO"},
    "h04":{"academic":"free roaming dogs population vaccination sterilization rabies","official":"dog population management rabies community WOAH"},
    "h05":{"academic":"flood adaptation urban displacement risk early warning","official":"urban flood displacement risk disaster response UN"},
    "h06":{"academic":"lithium ion battery recycling safety fire waste","official":"battery recycling fires circular economy OECD"},
    "h07":{"academic":"school indoor air quality ventilation asthma children","official":"school indoor air quality ventilation respiratory health WHO"},
    "h08":{"academic":"platform gig work algorithmic management occupational health","official":"digital platform workers algorithm management labour policy OECD"},
}

def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _request(url,timeout=20):
    req=Request(url,headers={"User-Agent":"CiteRefinery/0.1 (research provenance and audit)",
                              "Accept":"application/json"})
    with urlopen(req,timeout=timeout) as r:
        raw=r.read(850_000)
    return json.loads(raw)

def _abstract(inverted):
    if not isinstance(inverted,dict): return ""
    positions={}
    for word,items in inverted.items():
        for ix in items[:20]:
            if isinstance(ix,int) and 0<=ix<=3000:
                positions[ix]=word
    return " ".join(positions[i] for i in sorted(positions))[:7000]

def search_openalex(query,limit=4,fetch=_request):
    url="https://api.openalex.org/works?"+urlencode({
        "search":query,"per-page":min(limit,10),
        "filter":"has_abstract:true","select":"id,doi,display_name,abstract_inverted_index,publication_year,type,primary_location",
    })
    data=fetch(url)
    result=[]
    for work in data.get("results",[])[:limit]:
        title=" ".join(str(work.get("display_name") or "").split())
        abstract=_abstract(work.get("abstract_inverted_index"))
        if len(abstract)<110 or len(title)<8:continue
        uri=work.get("doi") or work.get("id")
        if not uri or not uri.startswith("https://"):continue
        body=title+". "+abstract
        result.append({
            "id":"OA-"+h(str(work["id"]))[:14],
            "url":uri,"title":title,"text":body[:7000],
            "origin_type":"openalex_bibliographic_abstract_lead",
            "retrieval_url":url,
            "source_record":work["id"],
            "source_scope":"OpenAlex metadata/abstract; not verified full text, causal study or actual program",
            "publication_year":work.get("publication_year"),
        })
    return result

def normalize(source):
    content=" ".join(str(source.get("text") or "").split())
    title=" ".join(str(source.get("title") or "").split())
    uri=str(source.get("url") or "")
    if len(content)<100 or len(uri)<12 or not title:return None
    origin=source.get("origin_type")
    if not isinstance(origin,str) or not origin:return None
    return {
        "id":str(source["id"]),"url":uri,"title":title[:350],
        "text":content[:6500],"origin_type":origin,
        "source_scope":str(source.get("source_scope") or "")[:500],
        "retrieval_url":str(source.get("retrieval_url") or "")[:600],
        "source_record":str(source.get("source_record") or "")[:300],
        "year":source.get("publication_year"),
        "sha256":h(content[:6500]),
    }

def public_entry(src):
    return {k:src[k] for k in ("id","url","title","origin_type","source_scope",
                             "retrieval_url","source_record","year","sha256")}

def collect(directory,*,queries=None,europe=2,openalex=4,official=2,
            efunc=search_europe_pmc,afunc=search_openalex,ofunc=search_official):
    root=Path(directory)
    root.mkdir(parents=True,exist_ok=True)
    q=queries or QUERY_STRATA
    if len(q)>16:raise ValueError("Too many collection query groups")
    sources={};urlhash=set();failures=[];ledger=[]
    for code,spec in q.items():
        if set(spec)!={"academic","official"}:raise ValueError("Malformed collection quota")
        for lane,fn,query,limit in (
            ("academic_europe_pmc",efunc,spec["academic"],europe),
            ("academic_openalex",afunc,spec["academic"],openalex),
            ("institutional",ofunc,spec["official"],official),
        ):
            try:
                found=fn(query,limit=limit)
                if not isinstance(found,list):raise ValueError("Source discovery not a list")
            except Exception as exc:
                failures.append({"quota_code":code,"lane":lane,
                                 "error_class":type(exc).__name__,
                                 "boundary":"Retrieval failure: no fabricated replacement"})
                found=[]
            saved=0
            for item in found:
                x=normalize(item)
                if x is None:continue
                unique=x["url"].lower().split("?",1)[0]
                if (unique,x["sha256"]) in urlhash or len(sources)>=SOURCE_LIMIT:
                    continue
                # Same DOI abstract in both indexes is one publication;
                # never count different abstract passages as independent replication.
                if unique in {v["url"].lower().split("?",1)[0] for v in sources.values()}:
                    continue
                if x["id"] in sources and sources[x["id"]]["sha256"]!=x["sha256"]:
                    raise ValueError("Same source id has conflicting evidence")
                if x["id"] in sources:continue
                sources[x["id"]]=x
                urlhash.add((unique,x["sha256"]))
                saved+=1
            ledger.append({"quota_code":code,"retrieval_lane":lane,
                           "query":query,"returned":len(found),"accepted_new":saved})
    material=sorted(sources.values(),key=lambda s:s["id"])
    primary={
        "schema":SCHEMA,"material_type":"unclassified_source_records",
        "source_count":len(material),"sources":material,
        "collection_not_a_map":True,
        "collection_queries":ledger,"retrieval_errors":failures,
        "note":"Original extracted public excerpts retained locally as inputs, not scientific truth.",
    }
    (root/"private_corpus.json").write_text(json.dumps(primary,indent=2,ensure_ascii=False)+"\n")
    manifest={
        "schema":"cite_refinery.open_corpus_manifest.v1",
        "count":len(material),"source_records":[public_entry(x) for x in material],
        "collection_queries":ledger,"retrieval_errors":failures,
        "all_perspectives_preassigned":False,
        "ontology_preassigned":False,
        "mapping_status":"not_yet_interpreted",
        "publication_policy":"Extracted copyrighted abstracts/publisher text remain on authorized local machine; this manifest excludes verbatim source passages.",
    }
    (root/"public_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    return primary,manifest
