"""Reproduce the pinned WHO/WOAH/PLOS passages for semantic demonstration.

Only fetches three explicitly supplied public HTML pages. It requires exact
institutional text anchors and records HTML hash as provenance; on a website
change, fail rather than silently substitute a source.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SOURCES = [
    {
        "id": "WHO-RABIES-2024",
        "url": "https://www.who.int/en/news-room/fact-sheets/detail/rabies",
        "source_scope": "WHO global rabies fact sheet; not local service coverage data",
        "origin_type": "official_institutional_public_health",
        "anchors": [
            "Dog bites and scratches cause 99%",
            "However, rabies deaths are preventable with prompt post exposure prophylaxis",
            "WHO and its global partners aim to end human deaths",
            "Vaccinating dogs, including puppies, through mass dog vaccination programs",
        ],
    },
    {
        "id": "WOAH-DPM-2024",
        "url": "https://www.woah.org/fileadmin/Home/eng/Health_standards/tahc/2024/en_chapitre_aw_stray_dog.htm",
        "source_scope": "WOAH 2024 Terrestrial Code chapter 7.7; normative recommendations, not observed local outcomes",
        "origin_type": "official_program_guidance",
        "anchors": [
            "DPM supports effective and sustainable rabies control programmes",
            "Development of DPM programmes should include an initial assessment",
            "Estimation of dog population size and demography.",
            "For evaluation of DPM programme effectiveness, monitoring changes in population trends",
            "Acknowledging that the owned dog population",
        ],
    },
    {
        "id": "BELO-2015",
        "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144830",
        "source_scope": "2015 systematic methodological review, 26 studies; not a 2026 dog population census",
        "origin_type": "peer_reviewed_academic_article",
        "anchors": [
            "Seven [ 33 , 36 , 44",
        ],
    },
]


def build_sources():
    import requests
    from bs4 import BeautifulSoup
    sources, manifests = [], []
    for cfg in SOURCES:
        page=requests.get(cfg["url"],timeout=20,headers={"User-Agent":"Mozilla/5.0"})
        page.raise_for_status()
        soup=BeautifulSoup(page.content,"html.parser")
        paragraph_candidates=[]
        for elt in soup.find_all(["p","li"]):
            text=" ".join(elt.get_text(" ",strip=True).split())
            if 30<len(text)<1600 and text not in paragraph_candidates:
                paragraph_candidates.append(text)
        captured=[]
        for anchor in cfg["anchors"]:
            found=[p for p in paragraph_candidates if anchor.casefold() in p.casefold()]
            if len(found)!=1:
                raise RuntimeError(f"source {cfg['id']} anchor {anchor!r} matches {len(found)} paragraphs")
            captured.append(found[0])
        text="\n\n".join(captured)
        if len(text)>9000:
            raise RuntimeError("Too much source text for a bounded investigation")
        source={k:cfg[k] for k in ("id","url","source_scope","origin_type")}
        source["text"]=text
        sources.append(source)
        manifests.append({
            "id":cfg["id"],"url":cfg["url"],
            "retrieval_status":page.status_code,
            "raw_page_sha256":hashlib.sha256(page.content).hexdigest(),
            "selected_excerpts_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "selected_paragraph_count":len(captured),
            "selection_anchors":cfg["anchors"],
            "source_warning":"Fetched excerpts only, not verified original empirical data or reviewed complete source.",
        })
    return sources,manifests


def main():
    dest=Path("research_materials/runtime_trials/llm_multisource_20261020")
    dest.mkdir(parents=True,exist_ok=True)
    sources,manifests=build_sources()
    (dest/"sources.json").write_text(json.dumps(sources,indent=2,ensure_ascii=False)+"\n")
    (dest/"source_manifest.json").write_text(json.dumps(manifests,indent=2,ensure_ascii=False)+"\n")
    for s in sources:
        print("SOURCE",s["id"],len(s["text"]),"chars",s["source_scope"])
    print("SOURCE_INPUT",dest/"sources.json")


if __name__=="__main__":
    main()
