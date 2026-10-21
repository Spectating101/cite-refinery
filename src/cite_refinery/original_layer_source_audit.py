"""Read-only independent publisher and original-repository identity audit.

Runs against an explicitly frozen prior source universe. Bibliographic identity
and root-tree presence are not peer review, scientific entailment, functionality,
source license clearance, adoption, or evidence of underconversion.

No network calls at import time. Tests inject fake HTTP fetchers.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import argparse
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

CROSSREF = "https://api.crossref.org/works/"
OPENALEX = "https://api.openalex.org/works/"
GITHUB = "https://api.github.com/repos/"
SCHEMA = "cite_refinery.original_source_layer_audit.v1"
DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
SHA = re.compile(r"^[a-f0-9]{40}$")
MAX_BYTES = 1_500_000


class FetchError(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _bounded_get(url, *, token=None, timeout=16):
    if not url.startswith((CROSSREF, GITHUB, OPENALEX)):
        raise ValueError("Audit accepts only explicit Crossref/GitHub API routes")
    headers = {"Accept":"application/vnd.github+json" if url.startswith(GITHUB)
               else "application/json", "User-Agent":"CiteRefinery-MapFoundations/1.0"}
    if token and url.startswith(GITHUB):
        headers["Authorization"]="Bearer "+token
        headers["X-GitHub-Api-Version"]="2022-11-28"
    req=Request(url,headers=headers)
    try:
        with urlopen(req,timeout=timeout) as response:
            final=response.geturl()
            if not final.startswith((CROSSREF,GITHUB,OPENALEX)):
                raise FetchError("unexpected_redirect")
            data=response.read(MAX_BYTES+1)
    except HTTPError as exc:
        raise FetchError("http_"+str(exc.code)) from exc
    except (URLError,TimeoutError) as exc:
        raise FetchError("transport_unavailable") from exc
    if len(data)>MAX_BYTES:
        raise FetchError("response_too_large")
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError,UnicodeError) as exc:
        raise FetchError("invalid_json") from exc


def _clean_title(value):
    return re.sub(r"[^\w]+"," ",value.casefold()).strip() if isinstance(value,str) else ""


def _canonical_doistr(value):
    return value.strip().lower() if isinstance(value,str) else ""


def _checked_doi(row):
    value=row.get("source_record","")
    if isinstance(value,str) and DOI.fullmatch(value):
        return value
    url=row.get("url","")
    if isinstance(url,str) and url.startswith("https://doi.org/"):
        doi=url[len("https://doi.org/"):]
        if DOI.fullmatch(doi):
            return doi
    return None


def academic_source_audit(manifest, *, fetcher=_bounded_get, max_records=47,
                          pause_seconds=0):
    """Publisher identity and year support, NOT claims within a publication."""
    if (manifest.get("schema")!="cite_refinery.open_corpus_manifest.v1"
        or not 1<=max_records<=300 or pause_seconds<0):
        raise ValueError("Expected bounded original source manifest")
    origins={"scholarly_abstract_lead","openalex_bibliographic_abstract_lead"}
    sources=sorted((x for x in manifest["source_records"]
                    if x["origin_type"] in origins),key=lambda x:x["id"])
    rows=[]
    for source in sources[:max_records]:
        doi=_checked_doi(source)
        record={"source_id":source["id"],"original_title":source["title"],
                "original_url":source["url"],"original_text_sha256":source["sha256"],
                "doi":doi,"snapshot_year":source.get("year"),
                "publisher_metadata_checked":False,"original_paper_fulltext_checked":False,
                "claims_or_methods_verified":False,"independent_peer_review_proven":False}
        if doi is None:
            record["metadata_status"]="no_valid_doi_in_source"
        else:
            try:
                response=fetcher(CROSSREF+quote(doi,safe=""))
                data=response["message"]
                external=_canonical_doistr(data["DOI"])
                if external!=_canonical_doistr(doi):
                    raise FetchError("doi_identity_mismatch")
                title=str((data.get("title") or [""])[0])
                ratio=SequenceMatcher(None,_clean_title(source["title"]),
                                      _clean_title(title)).ratio()
                dates=data.get("published") or data.get("issued") or {}
                year=None
                try:
                    year=int(dates["date-parts"][0][0])
                except (KeyError,IndexError,ValueError,TypeError):
                    pass
                record.update(
                    metadata_status="crossref_doi_identity_confirmed",
                    publisher_metadata_checked=True,
                    publisher_title=title,
                    title_similarity=round(ratio,4),
                    publisher_title_matches_loosely=ratio>=0.75,
                    crossref_publication_year=year,
                    crossref_record_type=data.get("type"),
                    publisher_doi=external,
                    bibliographic_disagreement_flag=ratio<0.75 or (
                        year is not None and source.get("year") is not None
                        and int(source["year"])!=year),
                    original_source_quote_still_unverified=True,
                )
            except (FetchError,KeyError,TypeError,IndexError) as exc:
                record["metadata_status"]="not_confirmed"
                record["check_issue"]=exc.reason if isinstance(exc,FetchError) else "unexpected_publisher_schema"
        rows.append(record)
        if pause_seconds:
            time.sleep(pause_seconds)
    return {
        "schema":"cite_refinery.academic_bibliographic_identity_audit.v1",
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "original_scholarly_leads_total":len(sources),
        "sampled":len(rows),
        "doi_confirmed":sum(x["publisher_metadata_checked"] for x in rows),
        "publication_year_added_from_crossref":sum(x.get("crossref_publication_year") is not None and
            x["snapshot_year"] is None for x in rows),
        "bibliographic_disagreements":sum(x.get("bibliographic_disagreement_flag",False) for x in rows),
        "peer_review_or_method_findings_confirmed":0,
        "crossref_metadata_is_not_full_text_verification":True,
        "records":rows,
    }


def recover_openalex_bibliography(manifest, first_pass, *, fetcher=_bounded_get,
                                  pause_seconds=0):
    """Use a separate public index for records left unconfirmed by Crossref.

    Work-id / DOI identity is not article content verification. Never merge
    conflicting publication years into a single silently corrected date.
    """
    if (first_pass.get("schema")!="cite_refinery.academic_bibliographic_identity_audit.v1"
        or manifest.get("schema")!="cite_refinery.open_corpus_manifest.v1"
        or pause_seconds<0):
        raise ValueError("Original research manifest and Crossref audit required")
    indexed={x["id"]:x for x in manifest["source_records"]}
    if len(indexed)!=len(manifest["source_records"]):
        raise ValueError("Duplicate original research source")
    visited=set()
    added=0
    years=0
    for row in first_pass["records"]:
        sid=row["source_id"]
        if sid in visited or sid not in indexed:
            raise ValueError("Unknown/duplicate source in academic recovery")
        visited.add(sid)
        if row.get("publisher_metadata_checked"):
            row["openalex_second_index_needed"]=False
            continue
        source=indexed[sid]
        doi=_checked_doi(source)
        external_id=source.get("url","")
        if (isinstance(external_id,str)
            and re.fullmatch(r"https://openalex.org/W[0-9]+",external_id)):
            endpoint=OPENALEX+external_id.rsplit("/",1)[-1]
            identity_type="openalex_work_id"
        elif doi is not None:
            endpoint=OPENALEX+"https://doi.org/"+doi
            identity_type="doi"
        else:
            row["openalex_lookup_status"]="no_supported_identity"
            continue
        try:
            work=fetcher(endpoint)
            work_id=work["id"]
            if (not isinstance(work_id,str)
                or not re.fullmatch(r"https://openalex.org/W[0-9]+",work_id)):
                raise FetchError("bad_openalex_work_id")
            if identity_type=="openalex_work_id":
                if work_id!=external_id:
                    raise FetchError("openalex_original_identity_mismatch")
            else:
                found=work.get("doi","")
                if not isinstance(found,str) or _canonical_doistr(
                        found.removeprefix("https://doi.org/"))!=_canonical_doistr(doi):
                    raise FetchError("openalex_doi_identity_mismatch")
            title=work.get("display_name") or work.get("title") or ""
            similarity=round(SequenceMatcher(None,
                _clean_title(source["title"]),_clean_title(title)).ratio(),4)
            year=work.get("publication_year")
            if not isinstance(year,int) or not 1800<=year<=2100:
                year=None
            row.update(
                metadata_status="openalex_work_identity_confirmed",
                openalex_index_identity_checked=True,
                openalex_work_id=work_id,
                openalex_index_title=title,
                openalex_title_similarity=similarity,
                openalex_publication_year=year,
                openalex_metadata_not_peer_review_or_fulltext=True,
                bibliographic_disagreement_flag=similarity<0.75 or (
                    year is not None and row.get("snapshot_year") is not None
                    and int(row["snapshot_year"])!=year),
            )
            added+=1
            years+=int(year is not None and row.get("snapshot_year") is None)
        except (FetchError,KeyError,ValueError,TypeError) as exc:
            row["openalex_lookup_status"]="not_confirmed"
            row["openalex_lookup_issue"]=(exc.reason if isinstance(exc,FetchError)
                                         else "unexpected_index_schema")
        if pause_seconds:
            time.sleep(pause_seconds)
    first_pass["openalex_identity_confirmed"]=added
    first_pass["publication_year_added_from_openalex"]=years
    first_pass["bibliographic_disagreements"]=sum(
        bool(x.get("bibliographic_disagreement_flag")) for x in first_pass["records"])
    first_pass["crossref_and_openalex_are_different_metadata_providers"]=True
    return first_pass


def _verify_repo_slug(slug):
    if not isinstance(slug,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",slug):
        raise ValueError("Unsafe repo URL component")
    return slug


def _repo_api_snapshot(slug, *, fetcher, token=None):
    try:
        info=fetcher(GITHUB+slug,token=token)
        if info.get("full_name")!=slug:
            raise FetchError("repository_canonical_identity_changed")
        default=info["default_branch"]
        if not isinstance(default,str) or len(default)>128:
            raise FetchError("missing_default_branch")
        commit=fetcher(GITHUB+slug+"/commits/"+quote(default,safe=""),token=token)
        pinned=commit.get("sha")
        if not isinstance(pinned,str) or not SHA.fullmatch(pinned):
            raise FetchError("missing_pinned_commit")
        root=fetcher(GITHUB+slug+"/contents?ref="+pinned,token=token)
        if not isinstance(root,list):
            raise FetchError("root_contents_not_directory")
        names={x["name"] for x in root if isinstance(x,dict)
               and isinstance(x.get("name"),str)}
        return {
            "status":"original_source_metadata_checked",
            "source_commit":pinned,
            "public_repository_url":info.get("html_url"),
            "default_branch":default,
            "source_pushed_at":info.get("pushed_at"),
            "archived":bool(info.get("archived")),
            "disabled":bool(info.get("disabled")),
            "api_license_spdx_not_reuse_permission":(info.get("license") or {}).get("spdx_id"),
            "root_test_directory_visible_not_executed":bool(names & {"test","tests","spec","specs"}),
            "root_readme_visible_not_read":any(n.lower().startswith("readme") for n in names),
            "root_license_file_visible_not_rights_review":any(n.lower().startswith(("license","copying")) for n in names),
            "root_ci_directory_visible_not_test_pass":".github" in names,
            "root_top_level_file_names":sorted(names)[:70],
            "original_test_commands_executed":0,
            "functional_quality_or_adoption_verified":False,
            "license_entitlement_verified":False
        }
    except (FetchError,KeyError,TypeError,ValueError) as exc:
        return {"status":"unavailable_or_inconclusive",
                "issue":exc.reason if isinstance(exc,FetchError) else "unexpected_original_api_schema",
                "source_commit":None,"original_test_commands_executed":0,
                "functional_quality_or_adoption_verified":False,
                "license_entitlement_verified":False}


def implementation_source_audit(backlog, *, fetcher=_bounded_get, max_pairs=44,
                                token=None, pause_seconds=0):
    """Balanced category-level sampling; reuses API results for repeated repo IDs."""
    if (backlog.get("schema")!="cite_refinery.standalone_metadata_review_backlog.v1"
        or not 1<=max_pairs<=200 or pause_seconds<0):
        raise ValueError("Original unreviewed review backlog required")
    candidates=backlog["entries"]
    if len(candidates)!=backlog["sampled_pairs"]:
        raise ValueError("Backlog item count tampering")
    by_category={}
    for item in candidates:
        slug=item["repository_id"]
        if not slug.startswith("github:") or item["original_repository_url"]!=(
            "https://github.com/"+slug[len("github:"):]):
            raise ValueError("Original repository identity changed")
        _verify_repo_slug(slug[len("github:"):])
        if item.get("original_semantic_label")!="not_reviewed" or item.get("review_complete") is not False:
            raise ValueError("Review backlog falsely pre-approved")
        by_category.setdefault(item["category"],[]).append(item)
    # Breadth-first: one unreviewed pair from every collection category before
    # second pass; don't choose by popularity or ability to get success.
    selected=[]
    for index in range(max(len(x) for x in by_category.values())):
        for category in sorted(by_category):
            options=by_category[category]
            if index<len(options) and len(selected)<max_pairs:
                selected.append(options[index])
    cache={}
    records=[]
    for entry in selected:
        rid=entry["repository_id"]
        slug=rid[len("github:"):]
        if rid not in cache:
            cache[rid]=_repo_api_snapshot(slug,fetcher=fetcher,token=token)
            if pause_seconds:
                time.sleep(pause_seconds)
        records.append({
            "repository_id":rid,"category":entry["category"],
            "source_original_url":entry["original_repository_url"],
            "source_description_publisher_claim":entry["publisher_description"],
            "category_fit_metadata_review":"not_reviewed",
            "original_source_snapshot":cache[rid],
            "original_code_executed":False,
            "independent_capability_demonstrated":False,
            "observed_adoption_or_conversion_gap":False,
        })
    ok=[x for x in records if x["original_source_snapshot"]["status"]=="original_source_metadata_checked"]
    return {
        "schema":"cite_refinery.implementation_original_source_audit.v1",
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "total_backlog_category_pairs":len(candidates),
        "selected_category_pairs":len(selected),
        "distinct_source_categories_sampled":len({x["category"] for x in selected}),
        "distinct_repositories_queried":len(cache),
        "original_repo_revision_and_root_checked_pairs":len(ok),
        "root_test_dir_visible_pairs":sum(x["original_source_snapshot"].get(
            "root_test_directory_visible_not_executed",False) for x in ok),
        "root_license_file_visible_pairs":sum(x["original_source_snapshot"].get(
            "root_license_file_visible_not_rights_review",False) for x in ok),
        "publisher_identity_and_metadata_not_executable_test":True,
        "original_functions_independently_executed":0,
        "underconverted_assets_established":0,
        "records":records
    }


def run_cli():
    p=argparse.ArgumentParser(description="Public original-source checks, NOT proof of claims")
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--backlog",type=Path,required=True)
    p.add_argument("--academic-out",type=Path,required=True)
    p.add_argument("--implementation-out",type=Path,required=True)
    p.add_argument("--max-academic",type=int,default=47)
    p.add_argument("--max-repo-pairs",type=int,default=44)
    args=p.parse_args()
    if len({args.academic_out.resolve(),args.implementation_out.resolve()})!=2:
        raise ValueError("Separate output files required")
    if any(x.exists() for x in (args.academic_out,args.implementation_out)):
        raise ValueError("Refusing to overwrite independent audit receipts")
    def load(file):
        if file.stat().st_size>12_000_000:
            raise ValueError("Audit input too large")
        return json.loads(file.read_text(encoding="utf-8"))
    original_manifest=load(args.manifest)
    academic=academic_source_audit(original_manifest,max_records=args.max_academic)
    academic=recover_openalex_bibliography(original_manifest,academic)
    technical=implementation_source_audit(load(args.backlog),max_pairs=args.max_repo_pairs,
                                          token=os.environ.get("GITHUB_TOKEN"))
    for path,record in ((args.academic_out,academic),
                        (args.implementation_out,technical)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "academic_original_doi_confirmed":academic["doi_confirmed"],
        "academic_years_recovered":academic["publication_year_added_from_crossref"]+
                                   academic["publication_year_added_from_openalex"],
        "openalex_identity_confirmed":academic["openalex_identity_confirmed"],
        "implementation_categories_sampled":technical["distinct_source_categories_sampled"],
        "original_repo_revision_checks":technical["original_repo_revision_and_root_checked_pairs"],
        "actual_field_or_source_code_quality_verified":0},indent=2))


if __name__=="__main__":
    run_cli()
