"""Second-wave public evidence acquisition for heterogeneous semantic benchmarks.

Independent material channels:
- Europe PMC public Open Access JATS full text (not abstracts-only).
- World Bank official project/report text (not just search snippets).
- Zenodo published open dataset record metadata, file listing *not data values*.

Only permitted fixed public APIs are fetched; no arbitrary user-provided URLs,
credentials, or account data. All publisher text remains local.
"""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlencode,urlparse
import xml.etree.ElementTree as ET

import requests

RESEARCH_STRATA={
 "s01":{"pmc":"urban heat cardiovascular exposure low income adaptation","wb":"urban heat action plan implementation evaluation","zenodo":"urban heat mortality dataset"},
 "s02":{"pmc":"electronic waste informal recycling workers exposure intervention","wb":"electronic waste recycling environmental health implementation","zenodo":"electronic waste pollution dataset"},
 "s03":{"pmc":"food redistribution food insecurity rescue intervention evaluation","wb":"food security distribution program evaluation","zenodo":"food rescue logistics dataset"},
 "s04":{"pmc":"free roaming dog rabies vaccination longitudinal study","wb":"rabies community dogs vaccination program","zenodo":"dog population survey dataset"},
 "s05":{"pmc":"urban flood adaptation community early warning health","wb":"flood early warning project implementation results","zenodo":"flood exposure remote sensing dataset"},
 "s06":{"pmc":"lithium ion battery fire recycling workplace hazard","wb":"battery recycling environment project evaluation","zenodo":"battery waste safety dataset"},
 "s07":{"pmc":"school classroom ventilation particulate asthma intervention","wb":"school ventilation indoor air pollution implementation","zenodo":"classroom indoor air quality dataset"},
 "s08":{"pmc":"delivery courier platform algorithmic management worker wellbeing","wb":"digital platform gig workers labour protection","zenodo":"platform work survey dataset"},
 "s09":{"pmc":"drinking water service disruptions rural contamination diarrheal illness","wb":"water sanitation implementation completion results","zenodo":"water quality monitoring dataset"},
 "s10":{"pmc":"urban housing evictions health rental affordability evaluation","wb":"housing social assistance implementation completion","zenodo":"housing displacement survey dataset"},
 "s11":{"pmc":"disability accessibility public transport barriers evaluation","wb":"public transportation accessibility project implementation","zenodo":"transport accessibility survey dataset"},
 "s12":{"pmc":"healthcare waste disposal occupational infectious hazard interventions","wb":"healthcare waste management implementation project","zenodo":"hospital waste management dataset"},
}
BASE="https://www.ebi.ac.uk/europepmc/webservices/rest"
WB="https://search.worldbank.org/api/v3/wds"
ZEN="https://zenodo.org/api/records"
SCHEMA="cite_refinery.richer_corpus.v1"

def _digest(s):return hashlib.sha256(s.encode("utf8")).hexdigest()
def _normalize(s):return " ".join(html.unescape(re.sub(r"<[^>]+>"," ",str(s or ""))).split())

def _get(url,params=None,*,expected=("www.ebi.ac.uk","search.worldbank.org","zenodo.org","documents.worldbank.org","documents1.worldbank.org"),max_bytes=2_500_000,timeout=22):
    target=urlparse(url)
    if target.scheme!="https" or target.hostname not in expected:
        raise ValueError("Rejected unlisted retrieval domain")
    response=requests.get(url,params=params,timeout=timeout,
        headers={"User-Agent":"CiteRefinery/0.2 (open scientific evidence audit)","Accept":"application/json,application/xml,text/plain,*/*"})
    response.raise_for_status()
    actual=urlparse(response.url)
    if actual.scheme!="https" or actual.hostname not in expected:
        raise ValueError("Redirect to unlisted evidence domain")
    if len(response.content)>max_bytes:raise ValueError("Document exceeds private collection bound")
    return response.content,response.url

def _title_text(parent):
    return " ".join(" ".join(parent.itertext()).split())

def _jats_excerpt(body):
    # Do not expand external entities. Stdlib ET ignores remote DTD and will
    # fail safely on unsafe/unresolved document entity usage.
    root=ET.fromstring(body)
    title=""
    t=root.find(".//article-title")
    if t is not None:title=_title_text(t)
    abstract=root.find(".//abstract")
    intro=_title_text(abstract) if abstract is not None else ""
    sections=[]
    for sect in root.findall(".//body/sec"):
        ttl=sect.find("./title")
        heading=_title_text(ttl) if ttl is not None else ""
        paras=[]
        for para in sect.findall("./p")[:9]:
            val=_title_text(para)
            if len(val)>70:paras.append(val[:2300])
        section=("SECTION: "+heading+"\n" if heading else "")+"\n".join(paras)
        if len(section)>130:sections.append(section)
        if len("\n".join(sections))>24000:break
    text=(title+"\nABSTRACT: "+intro+"\n"+"\n\n".join(sections)).strip()
    return title,text[:31000],len(sections)

def _pmc(q,limit):
    params={"query":q+" AND OPEN_ACCESS:y AND HAS_FT:y",
            "format":"json","pageSize":min(18,limit*2),"resultType":"core"}
    response,url=_get(BASE+"/search",params,max_bytes=1_900_000)
    search=json.loads(response)
    found=[];failures=[]
    for x in search.get("resultList",{}).get("result",[]):
        pmcid=x.get("pmcid")
        if not pmcid or not re.fullmatch(r"PMC[0-9]+",pmcid):continue
        try:
            content,actual=_get(BASE+"/"+pmcid+"/fullTextXML",max_bytes=2_500_000)
            title,sections,section_count=_jats_excerpt(content)
            if len(sections)<2200 or section_count<2:continue
            article_url="https://europepmc.org/articles/"+pmcid
            found.append({
                "id":"PMC-"+pmcid,
                "canonical_url":article_url,
                "title":title or x.get("title") or "Untitled full text",
                "text":sections,
                "type":"full_text_jats",
                "field":"open_access_scholarly_full_text",
                "source_location":article_url,
                "retrieval_url":actual,
                "source_scope":"Public open-access JATS text; peer review, clinical effects and study generalizability not independently verified.",
                "document_date":x.get("firstPublicationDate"),
                "article_id":pmcid,
                "doi":x.get("doi"),
                "license_observed":None,
                "section_count":section_count,
            })
        except Exception as exc:
            failures.append({"id":pmcid,"reason":type(exc).__name__})
        if len(found)>=limit:break
    return found,failures

def _worldbank(q,limit):
    params={"format":"json","qterm":q,"rows":min(15,limit*3),"fl":"abstracts,docty,docdt,pdfurl,txturl,display_title,url"}
    raw,_=_get(WB,params,max_bytes=2_500_000)
    data=json.loads(raw)
    items=list(data.get("documents",{}).values())
    found=[];failures=[]
    for x in items:
        txt=x.get("txturl")
        if not isinstance(txt,str) or not txt.startswith(("http://","https://")):continue
        # Transform publisher's http link to the same HTTPS host.
        txt="https://"+txt.split("://",1)[1]
        try:
            content,actual=_get(txt,max_bytes=2_500_000,timeout=24)
            text=" ".join(content.decode("utf-8","replace").split())
            if len(text)<3200:continue
            title=_normalize(x.get("display_title") or "World Bank document")
            if len(title)<10:continue
            # Strip boilerplate front pages when present, while retaining
            # report text and named sections, bounded for model token safety.
            doc=text[:28000]
            uri=str(x.get("url") or "")
            if uri.startswith("http://"):uri="https://"+uri.split("://",1)[1]
            if not uri.startswith("https://"):uri=actual
            found.append({
                "id":"WB-"+str(x["id"]),
                "canonical_url":uri,
                "title":title,"text":title+". "+doc,
                "type":"report_extracted_text","field":"institutional_report",
                "source_location":uri,"retrieval_url":actual,
                "source_scope":"World Bank published report; narrative, plans and reported operational claims are not independently validated outcomes.",
                "document_date":x.get("docdt"),
                "document_kind":x.get("docty"),
                "pdf_url":x.get("pdfurl"),
            })
        except Exception as exc:
            failures.append({"id":str(x.get("id")),"reason":type(exc).__name__})
        if len(found)>=limit:break
    return found,failures

def _zenodo(q,limit):
    raw,_=_get(ZEN,{"q":q,"size":min(15,limit*3)},max_bytes=2_500_000)
    data=json.loads(raw)
    found=[];failures=[]
    for record in data.get("hits",{}).get("hits",[]):
        m=record.get("metadata",{})
        if m.get("access_right","open")!="open":continue
        docid=record.get("id")
        if not docid:continue
        title=_normalize(m.get("title"))
        summary=_normalize(m.get("description"))
        files=[]
        for f in record.get("files",[]):
            files.append({"key":str(f.get("key") or f.get("filename") or "")[:180],
                          "size_bytes":f.get("size") or f.get("filesize"),
                          "checksum":str(f.get("checksum") or "")[:120]})
        if len(title)<10 or len(summary)<200:continue
        uri="https://zenodo.org/records/"+str(docid)
        metadata_text=(
            title+".\nSUMMARY: "+summary[:10000]+
            "\nPUBLIC DATASET FILE INVENTORY: "+json.dumps(files[:25],ensure_ascii=False)+
            "\nNOTE: file contents, observations and numerical values not downloaded."
        )
        found.append({
            "id":"ZEN-"+str(docid),"canonical_url":uri,
            "title":title,"text":metadata_text[:15500],
            "type":"dataset_metadata","field":"public_repository_dataset_description",
            "source_location":uri,
            "retrieval_url":"https://zenodo.org/api/records/"+str(docid),
            "source_scope":"Public dataset landing-page metadata and file names only; not downloaded/verified underlying measurements.",
            "document_date":m.get("publication_date"),
            "license_observed":(m.get("license") or {}).get("id") if isinstance(m.get("license"),dict) else str(m.get("license") or ""),
            "file_count":len(files),
        })
        if len(found)>=limit:break
    return found,failures

def acquire(workspace,*,strata=None,limits=None,provider_overrides=None):
    target=Path(workspace);target.mkdir(parents=True,exist_ok=True)
    selected=strata if strata is not None else RESEARCH_STRATA
    caps=limits or {"pmc":6,"wb":4,"zenodo":4}
    tasks=[(code,lane,query) for code,spec in selected.items() for lane,query in spec.items()]
    engines={"pmc":_pmc,"wb":_worldbank,"zenodo":_zenodo}
    if provider_overrides:engines.update(provider_overrides)
    batch=[];errors=[];ledger=[]
    # Bounded concurrency; no automatic retries, sources remain genuine
    # even when services rate-limit or fail.
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending={pool.submit(engines[lane],query,caps[lane]):(code,lane,query)
                 for code,lane,query in tasks}
        for future in as_completed(pending):
            code,lane,query=pending[future]
            try:
                records,bad=future.result()
            except Exception as exc:
                records=[];bad=[{"reason":type(exc).__name__}]
            for source in records:
                source["collection_quota"]=code
                source["discovery_lane"]=lane
                source["text_sha256"]=_digest(source["text"])
                source["word_count"]=len(source["text"].split())
                batch.append(source)
            errors += [{"quota":code,"lane":lane,**x} for x in bad]
            ledger.append({"quota":code,"lane":lane,"query":query,
                           "accepted":len(records),"failed":len(bad)})
    old={};duplicates=[]
    for source in sorted(batch,key=lambda x:x["id"]):
        canonical=source["canonical_url"].split("?",1)[0].rstrip("/").lower()
        if canonical in old:
            duplicates.append({"id":source["id"],"collision_with":old[canonical]["id"]})
            continue
        old[canonical]=source
    records=sorted(old.values(),key=lambda x:x["id"])
    corpus={"schema":SCHEMA,"sources":records,"source_count":len(records),
            "acquisition_queries":sorted(ledger,key=lambda x:(x["quota"],x["lane"])),
            "retrieval_failures":errors,
            "same_url_deduplications":duplicates,
            "authority":"unverified_public_material_only"}
    (target/"new_private_materials.json").write_text(json.dumps(corpus,indent=2,ensure_ascii=False)+"\n")
    return corpus
