"""Independently check published article identity and exact table anchors.

Fixed public Europe PMC full-text XML only. Reports source SHA, DOI, publication
identity and presence of limited original textual/numerical anchors. Does NOT
infer published claims from anchors, validate authored example excerpts, store
full text, run a model, or promote any Scientific Atlas edge.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import argparse
import json
import re
from xml.etree import ElementTree as ET

URL="https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML"
DOI="10.14202/vetworld.2026.2816-2849"
PMCID="PMC13500148"
SCHEMA="cite_refinery.original_article_anchor_receipt.v1"
MAX_BYTES=5_000_000
NUMERIC_ANCHORS=("1,368","484","0.55488235","0.835","0.038","0.0003")


def _require(ok,message):
    if not ok: raise ValueError(message)


def fetch_original():
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            raise ValueError("Original source redirected outside pinned endpoint")
    req=Request(URL,headers={"User-Agent":"CiteRefineryOriginalSourceAudit/0.1",
                              "Accept":"application/xml, text/xml"})
    with build_opener(NoRedirect()).open(req,timeout=18) as response:
        _require(response.status==200,"Original PMC XML not HTTP 200")
        body=response.read(MAX_BYTES+1)
    _require(len(body)<=MAX_BYTES,"Original PMC XML exceeded limit")
    return body


def audit_original(raw):
    _require(isinstance(raw,bytes) and 10_000<=len(raw)<=MAX_BYTES,
             "Original academic XML unavailable or outside bounds")
    _require(not raw.lstrip().lower().startswith(b"<!doctype"),
             "Original XML had unsafe DTD")
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError("Original source was not valid XML") from e
    _require(root.tag=="article","Original XML was not a JATS article")
    doi=[(x.text or "").strip().lower() for x in root.iter("article-id")
         if x.attrib.get("pub-id-type")=="doi"]
    pmcs=[(x.text or "").strip().upper() for x in root.iter("article-id")
          if x.attrib.get("pub-id-type") in {"pmcid","pmc"}]
    _require(DOI in doi and PMCID in pmcs,
             "Original article DOI / PMC identity disagreement")
    title_nodes=list(root.iter("article-title"))
    _require(title_nodes, "Article missing title")
    title=" ".join(" ".join(title_nodes[0].itertext()).split())
    _require("long-term evaluation of a zoned catch-neuter-vaccinate-release program" in title.lower(),
             "Original title/source mismatch")
    text=" ".join(" ".join(root.itertext()).split())
    hits={x:bool(x in text) for x in NUMERIC_ANCHORS}
    _require(all(hits.values()),"Original published table anchors missing")
    # No assumptions about the truth of model-supplied claim labels;
    # these booleans only indicate original publication text was observed.
    return {
        "schema":SCHEMA,
        "publisher": "Europe PMC public full text / original Veterinary World JATS article",
        "source_url":URL,
        "verified_doi":DOI,
        "verified_pmcid":PMCID,
        "original_xml_sha256":sha256(raw).hexdigest(),
        "original_xml_size_bytes":len(raw),
        "article_title":title,
        "numeric_table_anchor_presence":hits,
        "original_article_available":True,
        "archived_curated_excerpt_offsets_verified_against_this_xml":False,
        "nli_model_question_entailment_approved":False,
        "causal_conclusion_independently_established":False,
        "no_article_fulltext_rehosted":True,
        "no_frozen_academic_holdout_or_graph_mutation":True,
        "requires_exact_original_passage_quotation_for_each_claim":True,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args(argv)
    _require(not args.out.exists(),"Do not overwrite original-source audit")
    report=audit_original(fetch_original())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    print("ORIGINAL_ARTICLE_SOURCE_AUDIT",json.dumps({
        "source_url":report["source_url"],
        "verified_doi":report["verified_doi"],
        "verified_pmcid":report["verified_pmcid"],
        "original_xml_sha256":report["original_xml_sha256"],
        "numeric_table_anchor_presence":report["numeric_table_anchor_presence"],
        "model_claim_approved":False,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
