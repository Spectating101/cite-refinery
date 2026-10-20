"""Source-bounded TED notice XML reading for mapping, not tender discovery claims.

Provider API uses UBL roots to distinguish award / competition / prior notice.
Extract concise source excerpts; avoid treating titles as requirements.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

NOTICE_ID=re.compile(r"^[0-9]{4,8}-20[0-9]{2}$")
ROOT_TYPES={
    "ContractNotice":"competition_notice",
    "ContractAwardNotice":"award_notice",
    "PriorInformationNotice":"prior_information_notice",
    "VoluntaryExAnteTransparencyNotice":"voluntary_ex_ante_notice",
    "ContractModificationNotice":"contract_modification_notice",
}


def _local(tag: str)->str:
    return tag.rsplit("}",1)[-1]


def parse_notice(number: str, raw: bytes) -> dict[str,Any]:
    if not NOTICE_ID.fullmatch(number) or len(raw)>1_800_000:
        raise ValueError("invalid or oversized notice")
    root=ET.fromstring(raw)
    notice_type=ROOT_TYPES.get(_local(root.tag),"other_published_notice")
    # Only content suitable as document-level context. No automatic claim
    # that descriptions match a repository or define a currently open bid.
    details=[]
    seen=set()
    for element in root.iter():
        if _local(element.tag)!="Description":
            continue
        phrase=" ".join(" ".join(element.itertext()).split())
        if len(phrase)<55 or phrase in seen:
            continue
        seen.add(phrase)
        details.append(phrase[:750])
    details.sort(key=lambda x:-len(x))
    return {
        "id":"ted:"+number,
        "url":"https://ted.europa.eu/en/notice/-/detail/"+number,
        "xml_source":"https://ted.europa.eu/en/notice/"+number+"/xml",
        "ubl_type":_local(root.tag),
        "lifecycle_category":notice_type,
        "excerpts":details[:3],
        "excerpt_scope":"published UBL Description elements; may contain tender legal boilerplate",
        "is_verified_currently_open":False,
        "full_tender_document_reviewed":False,
        "buyer_spending_commitment_to_us":False,
        "publication_is_not_contract_opportunity":True,
    }


def _description(value: Any) -> str:
    if isinstance(value,str):
        return " ".join(value.split())[:850]
    if isinstance(value,list):
        return _description(value[0]) if value else ""
    if isinstance(value,dict):
        for k in ("eng","ENG","deu","fra"):
            if k in value:
                return _description(value[k])
        for v in value.values():
            text=_description(v)
            if text:
                return text
    return ""


def fetch_notice(number: str)->dict[str,Any]:
    """Use official TED v3 Search API; XML download links may be unavailable."""
    if not isinstance(number,str) or not NOTICE_ID.fullmatch(number):
        raise ValueError("invalid notice number")
    body={
        "query":"ND="+number,
        "fields":["publication-number","notice-type","notice-title","buyer-name",
                  "description-lot","description-proc","deadline-receipt-tender-date-lot"],
        "limit":1,"scope":"ALL","page":1,"paginationMode":"PAGE_NUMBER"
    }
    req=Request("https://api.ted.europa.eu/v3/notices/search",
                headers={"Content-Type":"application/json","Accept":"application/json",
                         "User-Agent":"CiteRefinerySourceAtlas/0.1"},
                data=json.dumps(body).encode("utf-8"),method="POST")
    with urlopen(req,timeout=16) as response:
        data=response.read(1_800_001)
    if len(data)>1_800_000:
        raise ValueError("oversized TED Search API response")
    packet=json.loads(data)
    notices=packet.get("notices")
    if not isinstance(notices,list) or len(notices)!=1 or notices[0].get("publication-number")!=number:
        raise ValueError("TED search notice identity mismatch or absent")
    source=notices[0]
    lifecycle={
        "cn-standard":"competition_notice",
        "can-standard":"award_notice",
        "can-modif":"award_modification_notice",
        "can-social":"award_notice",
        "pin-only":"prior_information_notice",
        "pin-cfc-standard":"prior_information_for_competition",
        "veat":"voluntary_ex_ante_notice",
    }.get(source.get("notice-type"),"other_published_notice")
    descriptions=[]
    for field in ("description-lot","description-proc"):
        text=_description(source.get(field))
        if len(text)>=40 and text not in descriptions:
            descriptions.append(text)
    return {
        "id":"ted:"+number,
        "url":"https://ted.europa.eu/en/notice/-/detail/"+number,
        "api_source":"https://api.ted.europa.eu/v3/notices/search",
        "notice_type_code":source.get("notice-type"),
        "lifecycle_category":lifecycle,
        "excerpts":descriptions[:2],
        "excerpt_scope":"official TED Search API notice-procedure and lot-description fields, truncated",
        "is_verified_currently_open":False,
        "full_tender_document_reviewed":False,
        "buyer_spending_commitment_to_us":False,
        "publication_is_not_contract_opportunity":True,
    }


def enrich(context: dict[str,Any], numbers: list[str], *,
           fetcher: Any=fetch_notice) -> dict[str,Any]:
    if context.get("schema")!="cite_refinery.ted_notice_context.v1":
        raise ValueError("source context required")
    known={r["publication_number"]:r for r in context.get("notices",[])}
    if not 1<=len(numbers)<=25 or len(set(numbers))!=len(numbers) or any(n not in known for n in numbers):
        raise ValueError("notice IDs must be unique source-observed context, bounded")
    results=[]
    failures={}
    for num in numbers:
        try:
            meta=known[num]
            x=fetcher(num)
            if x["id"]!="ted:"+num or x["is_verified_currently_open"] is not False:
                raise ValueError("bad notice identity or lifecycle claim")
            x.update({
                "published_title":meta["title"],
                "buyer":meta["buyer"],
                "publication_date":meta["publication_date"],
                "themes":meta["sampled_themes"],
                "notice_type_metadata":meta["notice_type"],
            })
            results.append(x)
            print(num,x["lifecycle_category"],"description_excerpts",len(x["excerpts"]),flush=True)
        except (OSError, ValueError, TypeError,ET.ParseError) as ex:
            failures[num]=type(ex).__name__
            print(num,"unavailable",type(ex).__name__,flush=True)
    return {
        "schema":"cite_refinery.ted_notice_enrichment.v1",
        "notices":results,"failures":failures,
        "lifecycle_counts":dict(Counter(n["lifecycle_category"] for n in results)),
        "evidence_boundary":"UBL work-description excerpts and notice lifecycles only; not tender spec, bidding rights, current procurement availability, or buyer contract.",
    }


def main(argv: list[str]|None=None)->int:
    import argparse
    parser=argparse.ArgumentParser(prog="cite-refinery-notice-details")
    parser.add_argument("notice_context",type=Path)
    parser.add_argument("--ids",required=True,help="comma-separated 1..25 source-listed notice IDs")
    parser.add_argument("--output",required=True,type=Path)
    x=parser.parse_args(argv)
    nums=x.ids.split(",")
    output=enrich(json.loads(x.notice_context.read_text(encoding="utf-8")),nums)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return int(bool(output["failures"]))


if __name__=="__main__":
    raise SystemExit(main())
