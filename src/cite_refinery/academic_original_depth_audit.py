"""Bounded Europe PMC JATS structure check for frozen Academic source leads.

Original publishers' XML is read in memory and is NOT copied into map artifacts.
A verified section/table *exists*; no finding, method validity, replication,
peer review or intervention outcome is adjudicated by this check.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re

from .academic_evidence_atlas import SCHEMA as ACADEMIC_SCHEMA
from .fulltext_audit import fulltext_source, parse_article

SCHEMA = "cite_refinery.academic_original_jats_structure_audit.v1"
PMCID = re.compile(r"^PMC-PMC([0-9]{4,12})$")
DOMAIN = "https://europepmc.org/articles/"
MAX_XML = 2_500_000


def _normalize(title):
    return " ".join(re.findall(r"\w+",str(title).casefold()))


def _similar(a,b):
    return round(SequenceMatcher(None,_normalize(a),_normalize(b)).ratio(),4)


def audit_original_jats(atlas, *, fetcher=fulltext_source, limit=8):
    if (atlas.get("schema") != ACADEMIC_SCHEMA or
        not isinstance(limit,int) or not 1 <= limit <= 43):
        raise ValueError("Expected independent Academic Atlas and bounded source sample")
    rows = []
    candidates = [
        x for x in atlas["sources"].values()
        if x["origin_genre"] == "full_text_jats"]
    candidates.sort(key=lambda x: sha256(x["id"].encode()).hexdigest())
    for row in candidates[:limit]:
        match = PMCID.fullmatch(row["id"])
        if not match or row["url"] != DOMAIN + "PMC" + match.group(1):
            raise ValueError("Academic full-text ID cannot be verified against canonical accession")
        pmcid = "PMC" + match.group(1)
        result = {
            "source_id": row["id"], "original_source_url": row["url"],
            "original_extracted_text_sha256": row["text_sha256"],
            "upstream_pmcid": pmcid,
            "status": "unavailable_or_unreviewed",
            "scientific_findings_or_study_design_verified": False,
            "original_retrieved_text_digest_revalidated": False,
        }
        try:
            response = fetcher(pmcid)
            if not isinstance(response,tuple) or len(response)!=2:
                raise ValueError("Malformed bounded original publisher response")
            url,raw=response
            if url != (
                "https://www.ebi.ac.uk/europepmc/webservices/rest/"
                + pmcid + "/fullTextXML"
            ):
                raise ValueError("Original full-text endpoint identity mismatch")
            if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_XML:
                raise ValueError("Original full-text bytes missing or oversized")
            parsed=parse_article(raw,url)
            similarity=_similar(row["title"],parsed["title"])
            if similarity < 0.75:
                result.update(status="publisher_article_title_mismatch",
                              title_similarity=similarity)
            else:
                sections = parsed.get("sections") or []
                result.update(
                    status="original_jats_identity_and_structure_inspected",
                    publisher_title=parsed["title"],
                    publisher_doi=parsed["doi"],
                    title_similarity=similarity,
                    original_xml_sha256=sha256(raw).hexdigest(),
                    section_count=len(sections),
                    distinct_section_headings=len({s["title"].casefold() for s in sections}),
                    method_heading_candidates=sum(bool(re.search(
                        r"method|material|study design|protocol|sampling",
                        s["title"],re.I)) for s in sections),
                    result_heading_candidates=sum(bool(re.search(
                        r"result|finding|outcome",
                        s["title"],re.I)) for s in sections),
                    table_count=len(parsed.get("tables") or []),
                    supplementary_entry_count=len(parsed.get("supplementary_entries") or []),
                    author_report_not_independent_qualification=True,
                )
        except (ValueError,LookupError,TypeError,KeyError,TimeoutError,
                ConnectionError,OSError,UnicodeError,Exception) as exc:
            # Status is explicitly unavailable, and is never silently upgraded.
            # Do not expose provider exceptions (which may include URLs or payloads).
            result["status"]="publisher_source_unavailable_or_unparseable"
            result["error_type"]=type(exc).__name__
        rows.append(result)
    return {
        "schema":SCHEMA,
        "sample_selection":"stable_sha256_of_source_id_not_quality_ranked",
        "indexed_article_source_count":len(candidates),
        "sampled_count":len(rows),
        "original_structure_inspected":sum(
            r["status"]=="original_jats_identity_and_structure_inspected" for r in rows),
        "bibliographic_or_original_title_mismatch":sum(
            r["status"]=="publisher_article_title_mismatch" for r in rows),
        "independently_reviewed_scientific_findings":0,
        "original_snapshot_extracted_text_revalidated":0,
        "records":rows,
    }


def attach_original_jats_structure(atlas, report):
    """Only attach original identity checks; never convert source to accepted claim."""
    if atlas.get("schema") != ACADEMIC_SCHEMA or report.get("schema") != SCHEMA:
        raise ValueError("Incorrect original Academic source report schema")
    result=json.loads(json.dumps(atlas))
    inspected=set()
    counted=0
    for item in report.get("records",[]):
        sid=item.get("source_id")
        if sid in inspected or sid not in result["sources"]:
            raise ValueError("Duplicate or unknown original Academic XML identity")
        inspected.add(sid)
        src=result["sources"][sid]
        if (src["origin_genre"]!="full_text_jats" or
            item.get("original_source_url")!=src["url"] or
            item.get("original_extracted_text_sha256")!=src["text_sha256"] or
            item.get("scientific_findings_or_study_design_verified") is not False or
            item.get("original_retrieved_text_digest_revalidated") is not False):
            raise ValueError("JATS structure audit would promote or change source authority")
        ok=item.get("status")=="original_jats_identity_and_structure_inspected"
        if ok:
            for key in ("publisher_doi","publisher_title","original_xml_sha256",
                        "section_count","table_count"):
                if key not in item:
                    raise ValueError("Falsely asserted JATS publisher structure")
            digest=item["original_xml_sha256"]
            if not isinstance(digest,str) or not re.fullmatch(r"[a-f0-9]{64}",digest):
                raise ValueError("JATS original publisher digest invalid")
            if item["title_similarity"] < 0.75:
                raise ValueError("JATS title mismatch represented as match")
            counted+=1
        src["original_public_jats_structure_inspected"] = ok
        src["original_public_jats_status"] = item.get("status")
        src["source_xml_structure_receipt"] = ({
            key:item[key] for key in (
                "publisher_doi","section_count","distinct_section_headings",
                "method_heading_candidates","result_heading_candidates",
                "table_count","supplementary_entry_count","original_xml_sha256")
            if key in item
        } if ok else None)
    if (report.get("sampled_count") != len(inspected) or
        report.get("original_structure_inspected") != counted or
        report.get("independently_reviewed_scientific_findings") != 0 or
        report.get("original_snapshot_extracted_text_revalidated") != 0):
        raise ValueError("External JATS audit aggregate mismatch")
    result["coverage"]["original_public_jats_structure_inspected"]=counted
    result["coverage"]["original_jats_source_ids_sampled"]=len(inspected)
    result["coverage"]["independently_validated_scientific_findings"]=0
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--academic-atlas",type=Path,required=True)
    parser.add_argument("--max-docs",type=int,default=8)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(argv)
    if args.out.exists():
        raise ValueError("Refusing to overwrite original publisher audit")
    if args.academic_atlas.stat().st_size>12_000_000:
        raise ValueError("Original Academic map too large")
    report=audit_original_jats(
        json.loads(args.academic_atlas.read_text(encoding="utf-8")),
        limit=args.max_docs)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"schema":SCHEMA, "sampled_count":report["sampled_count"],
                      "original_structure_inspected":report["original_structure_inspected"],
                      "independently_reviewed_scientific_findings":0}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
