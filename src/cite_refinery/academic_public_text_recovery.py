"""Rehydrate original Academic JATS extracts only if they equal frozen SHA-256.

The original development collection used _jats_excerpt from
richer_public_sources. Recreate exactly that extraction, compare against the
published 103-source development atlas; do not adapt/repair changed text.
This is a public publisher-retrieval tool, not semantic model execution.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json
import re

from .richer_public_sources import BASE,_get,_jats_excerpt
from .source_grounded_semantic_answer import _validate_map

SCHEMA="cite_refinery.academic_publisher_text_recovery.v1"
MAX_SELECTED=12
PMCID=re.compile(r"^PMC-PMC([0-9]{4,12})$")


def recover(atlas,*,source_ids,fetch=None):
    """Explicitly pin publisher bytes; only return text after digest check."""
    _validate_map(atlas)
    if not isinstance(source_ids,list) or not 1<=len(source_ids)<=MAX_SELECTED:
        raise ValueError("Select 1-12 explicit public Academic JATS source IDs")
    if len(set(source_ids))!=len(source_ids):
        raise ValueError("Repeated source IDs in publisher recovery request")
    fetch=fetch or (lambda url:_get(url,max_bytes=2_500_000))
    records=[]
    recovered={}
    for source_id in source_ids:
        if source_id not in atlas["sources"]:
            raise ValueError("Publisher recovery source not in 103-document frozen development inventory")
        source=atlas["sources"][source_id]
        pm=PMCID.fullmatch(source_id)
        if not pm or source["origin_genre"]!="full_text_jats":
            raise ValueError("Only the original Europe PMC JATS subset can be recovered")
        pmcid="PMC"+pm.group(1)
        expected_url="https://europepmc.org/articles/"+pmcid
        if source["url"]!=expected_url:
            raise ValueError("Academic publisher identity mismatches canonical PMCID")
        original_url=BASE+"/"+pmcid+"/fullTextXML"
        row={"source_id":source_id,"canonical_url":expected_url,
             "original_publisher_url":original_url,
             "frozen_extracted_text_sha256":source["text_sha256"],
             "status":"not_recovered","content_written":False,
             "scientific_claims_validated":False,
             "publisher_xml_is_not_frozen_original_file":True}
        try:
            raw,final_url=fetch(original_url)
            if final_url!=original_url:
                raise ValueError("Publisher JATS redirected away from original pinned accession")
            if not isinstance(raw,bytes) or not 200<=len(raw)<=2_500_000:
                raise ValueError("Publisher XML bytes missing or too large")
            title,text,sections=_jats_excerpt(raw)
            fingerprint=sha256(text.encode("utf-8")).hexdigest()
            row["retrieved_xml_sha256"]=sha256(raw).hexdigest()
            row["retrieved_extracted_text_sha256"]=fingerprint
            row["observed_section_count"]=sections
            row["actual_extracted_characters"]=len(text)
            if (fingerprint==source["text_sha256"] and
                len(text)>=100 and sections>=2):
                row["status"]="original_development_extraction_sha256_recovered"
                row["content_written"]=True
                recovered[source_id]=text
            else:
                row["status"]="publisher_source_version_or_extraction_digest_mismatch"
        except Exception as exc:
            # Never include untrusted publisher response/error bodies.
            row["status"]="publisher_source_unavailable_or_unparseable"
            row["error_type"]=type(exc).__name__[:100]
        records.append(row)
    return {
        "schema":SCHEMA,"requested":len(source_ids),"recovered":len(recovered),
        "digest_mismatches":sum(x["status"]==
             "publisher_source_version_or_extraction_digest_mismatch"
             for x in records),
        "unavailable_or_unparseable":sum(x["status"]==
             "publisher_source_unavailable_or_unparseable" for x in records),
        "records":records,
        "heldout_document_text_accessed":False,
        "original_extracted_source_fulltext_published":False,
        "model_called":False,
        "source_identity_or_methodological_findings_independently_validated":False,
        "exact_previous_dev_digest_is_required":True,
    },recovered


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--academic-atlas",required=True,type=Path)
    p.add_argument("--private-out-dir",required=True,type=Path)
    p.add_argument("--report-out",required=True,type=Path)
    p.add_argument("--source-id",action="append",default=[])
    p.add_argument("--max-sources",type=int,default=8)
    args=p.parse_args(argv)
    if (args.private_out_dir.exists() or args.report_out.exists() or
        args.private_out_dir.is_symlink() or args.report_out.is_symlink()):
        raise ValueError("Refuse overwrite or symlinked publisher recovery outputs")
    if not 1<=args.max_sources<=12:
        raise ValueError("Maximum 1-12 publisher source requests per run")
    original=json.loads(args.academic_atlas.read_text("utf-8"))
    _validate_map(original)
    ids=args.source_id or sorted(x for x,r in original["sources"].items()
                                 if r["origin_genre"]=="full_text_jats")[:args.max_sources]
    if len(ids)>args.max_sources:
        raise ValueError("Explicit source IDs exceed max-sources")
    receipt,texts=recover(original,source_ids=ids)
    args.private_out_dir.mkdir(parents=True,exist_ok=False)
    # Restricted permissions: original source text remains local and separate
    # from GitHub CI artifacts and the publicly shareable browser ZIP.
    for source_id,body in texts.items():
        dest=args.private_out_dir/(source_id+".txt")
        with dest.open("x",encoding="utf-8") as file:
            file.write(body)
        dest.chmod(0o600)
    args.report_out.parent.mkdir(parents=True,exist_ok=True)
    args.report_out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({"schema":SCHEMA,"requested":receipt["requested"],
                      "recovered":receipt["recovered"],
                      "digest_mismatches":receipt["digest_mismatches"],
                      "original_body_files_in_private_directory_only":len(texts)}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
