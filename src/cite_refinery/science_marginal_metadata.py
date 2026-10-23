"""Assess incremental metadata utility of an external science catalog on frozen repos.

This is source-identity-matched catalogue enrichment, NOT software correctness,
semantic match accuracy, article entailment or an adoption/market estimate.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError
import argparse
import json
import re

from .science_reuse_census import frozen_repositories, _digest

SCHEMA="cite_refinery.science_marginal_metadata_utility.v1"
SAMPLE="cite_refinery.science_marginal_context_preregistered_sample.v1"
SEED="refinery-science-incremental-context-v1"
SOURCE_SHA="b8bb8c733801c04e8c6f07f0c9a99f4016edd8e677343c93ffe13612aea450d2"
SCIENCE="https://science.ecosyste.ms/api/v1/projects/"
MAX_BYTES=350_000


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _read(path: Path, limit: int=3_000_000):
    _require(path.is_file() and not path.is_symlink()
             and path.stat().st_size < limit,"Input file not original/bounded")
    return json.loads(path.read_text("utf-8"))


def _hash_order(url):
    return sha256((SEED+"|"+url.lower()).encode("utf-8")).hexdigest()


def validate_sample(fixture, census, primary, frontier):
    original=frozen_repositories(primary,frontier)
    _require(fixture.get("schema")==SAMPLE and
             fixture.get("seed")==SEED and
             fixture.get("census_source_sha256")==SOURCE_SHA and
             census.get("schema")=="cite_refinery.science_reuse_census.v1" and
             census.get("cohort_size")==1287 and
             census.get("status")=="complete_metadata_identity_census_no_semantic_quality_claim" and
             census.get("survey_fingerprint_sha256")==SOURCE_SHA and
             _digest(original)==SOURCE_SHA and
             census.get("accepted_scientific_or_implementation_relations")==0,
             "Historical frozen source census, sample and provenance mismatch")
    match=census["exact_matches"]
    absent=census["reported_nonmatches"]
    _require(len(match)==398 and len(absent)==889 and
             not census["ambiguous_matches"] and
             not census["unaccounted"] and
             not census["failed_batches"],"Expected original complete identity census")
    expected_match=sorted(match,key=lambda x:(_hash_order(x["repository"]),x["repository"]))[:20]
    expected_absent=sorted(absent,key=lambda x:(_hash_order(x),x))[:20]
    from_fixture=fixture.get("matched")
    _require(isinstance(from_fixture,list) and
             all(isinstance(x,dict) for x in from_fixture) and
             [(x.get("repository"),x.get("science_project_id")) for x in from_fixture] ==
             [(x["repository"],x["science_project_id"]) for x in expected_match] and
             fixture.get("unmatched")==expected_absent,
             "Sample identities differ from preregistered SHA256 selection")
    original_by_url={x["url"].casefold():x for x in original}
    for url in expected_absent+[x["repository"] for x in expected_match]:
        _require(url.casefold() in original_by_url,"Sample absent from frozen original")
    raw_sources={}
    for snapshot in (primary,frontier):
        for x in snapshot["repositories"]:
            key=x["url"].casefold()
            if key not in raw_sources:
                raw_sources[key]=x
    return expected_match,expected_absent,raw_sources


def fetch_science_context(project_id: int) -> dict:
    """No redirects or arbitrary URLs. 20 bounded read-only project contexts."""
    _require(type(project_id) is int and project_id > 0, "Invalid Science project ID")
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("External science context redirect blocked")
    url=SCIENCE+str(project_id)+"/search_context"
    req=Request(url,headers={"Accept":"application/json",
                            "User-Agent":"CiteRefineryScienceReuseValidation/0.1"})
    with build_opener(NoRedirect()).open(req, timeout=12) as response:
        _require(response.status==200 and
                 "json" in response.headers.get("Content-Type","").lower(),
                 "Science context is not JSON HTTP 200")
        raw=response.read(MAX_BYTES+1)
    _require(len(raw)<=MAX_BYTES,"Science context response oversized")
    obj=json.loads(raw)
    _require(isinstance(obj,dict) and obj.get("project_id")==project_id and
             all(isinstance(obj.get(k),list)
                 for k in ("descriptions","languages","packages","direct_dependencies")),
             "Science project context response has unexpected schema/identity")
    return obj


def _safe_count(value):
    return len(value) if isinstance(value,list) else 0


def benchmark(sample, census, primary, frontier, *,
              fetch: Callable[[int],dict]=fetch_science_context,
              workers: int=4):
    matched,absent,original=validate_sample(sample,census,primary,frontier)
    # Grouped coverage measures overlapping memberships, not 44 disjoint
    # samples. Source metadata counts are not technical-quality scores.
    full=frozen_repositories(primary,frontier)
    known={x["repository"].casefold() for x in census["exact_matches"]}
    by_category={}
    for r in full:
        for cat in r["categories"]:
            row=by_category.setdefault(cat,{"category":cat,
                "source_repository_memberships":0,
                "science_exact_identity_memberships":0})
            row["source_repository_memberships"]+=1
            row["science_exact_identity_memberships"]+=int(r["url"].casefold() in known)
    _require(len(by_category)==44
             and sum(x["source_repository_memberships"] for x in by_category.values())==1360,
             "44 original source categories or 1,360 memberships not intact")
    category_review=[]
    for name,row in sorted(by_category.items()):
        category_review.append({
            **row,
            "metadata_identity_coverage_fraction":round(
                row["science_exact_identity_memberships"]/row["source_repository_memberships"],4),
            "does_not_measure_true_domain_relevance":True,
        })
    _require(type(workers) is int and 1 <= workers <= 6,
             "Science concurrent source fetch must be limited")
    fetched={}
    errors={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(fetch,x["science_project_id"]):x for x in matched}
        for future in as_completed(tasks):
            x=tasks[future]
            try:
                result=future.result()
                _require(isinstance(result,dict) and
                         result.get("project_id")==x["science_project_id"] and
                         all(isinstance(result.get(k),list) for k in (
                            "descriptions","languages","packages","direct_dependencies")),
                         "Wrong Science identity or context shape")
                fetched[x["repository"]]=result
            except Exception as exc:
                errors[x["repository"]]=(
                    "HTTP_"+str(exc.code) if isinstance(exc,HTTPError)
                    else type(exc).__name__)
    rows=[]
    counts=Counter()
    for x in matched:
        url=x["repository"]
        github=original[url.casefold()]
        obj=fetched.get(url)
        if obj is None:
            counts["unavailable"]+=1
            rows.append({"repository":url,"science_project_id":x["science_project_id"],
                         "state":"provider_unavailable_or_invalid_response",
                         "source_metadata_not_checked":True})
            continue
        # Additional fields are *not* evidence the provider measured quality.
        descriptions=_safe_count(obj.get("descriptions"))
        languages=_safe_count(obj.get("languages"))
        packages=_safe_count(obj.get("packages"))
        deps=_safe_count(obj.get("direct_dependencies"))
        has_package=packages>0
        has_deps=deps>0 and obj.get("dependencies_indexed_at") is not None
        has_extra_description=descriptions>1
        counts["contexts_read"]+=1
        counts["with_package_relationships"]+=int(has_package)
        counts["with_indexed_direct_dependencies"]+=int(has_deps)
        counts["with_multiple_description_records"]+=int(has_extra_description)
        counts["with_language_context"]+=int(languages>0)
        rows.append({
            "repository":url,"science_project_id":x["science_project_id"],
            "state":"original_project_metadata_read_not_independently_verified",
            "github_frozen_snapshot_has_description":bool(github.get("description")),
            "github_frozen_snapshot_has_language":bool(github.get("language")),
            "github_frozen_snapshot_topic_count":_safe_count(github.get("topics")),
            "science_description_record_count":descriptions,
            "science_language_record_count":languages,
            "science_package_record_count":packages,
            "science_direct_dependency_record_count":deps,
            "science_dependencies_indexed_timestamp_reported":bool(
                obj.get("dependencies_indexed_at")),
            "package_relationship_metadata_not_in_original_github_survey":has_package,
            "indexed_dependency_metadata_not_in_original_github_survey":has_deps,
            "multiple_description_records_not_in_original_github_survey":has_extra_description,
            "science_project_repo_identity_consistent":(
                 isinstance(obj.get("repository_url"),str) and
                 obj["repository_url"].rstrip("/").casefold()==url.casefold()),
            "original_code_execution_verified":False,
            "original_functional_suitability_verified":False,
        })
    all_original=[original[x.casefold()] for x in absent]
    summary={
        "schema":SCHEMA,
        "source_full_census_sha256":SOURCE_SHA,
        "sample_selection_seed":SEED,
        "source_matched_total":398,"source_unmatched_total":889,
        "matched_sample_size":20,"unmatched_sample_size":20,
        "original_github_unmatched_snapshot_description_present":sum(
            bool(r.get("description")) for r in all_original),
        "original_github_matched_snapshot_description_present":sum(
            bool(original[x["repository"].casefold()].get("description")) for x in matched),
        "source_categories_count":44,
        "original_category_memberships_with_overlap":1360,
        "source_category_coverage":category_review,
        "science_context_read_successes":counts["contexts_read"],
        "science_context_errors":dict(sorted(errors.items())),
        "science_with_package_metadata":counts["with_package_relationships"],
        "science_with_indexed_direct_dependencies":counts["with_indexed_direct_dependencies"],
        "science_with_multiple_descriptions":counts["with_multiple_description_records"],
        "science_with_languages":counts["with_language_context"],
        "status":("complete_catalogue_metadata_utility_only" if not errors else
                  "partial_catalogue_metadata_utility_provider_failure"),
        "inspection":sorted(rows,key=lambda x:x["repository"].casefold()),
        "observational_comparison_only":True,
        "independent_software_quality_improvement_verified":False,
        "independent_analyst_time_savings_measured":False,
        "real_program_deployment_or_value_verified":False,
        "license_rights_or_adoption_verified":False,
        "accepted_graph_evidence_edges":0,
        "recommended_role":"optional_external_metadata_enrichment_not_original_functional_testing",
    }
    _require(summary["science_context_read_successes"]+len(errors)==20 and
             len(summary["inspection"])==20,"Source-census value evaluation incomplete")
    return summary


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sample",required=True,type=Path)
    p.add_argument("--census",required=True,type=Path)
    p.add_argument("--primary",required=True,type=Path)
    p.add_argument("--frontier",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    _require(not args.out.exists(),"No overwrite of previous Science source benchmark")
    result=benchmark(_read(args.sample),_read(args.census,350_000),
                     _read(args.primary),_read(args.frontier))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    print("SCIENCE_MARGINAL_METADATA",json.dumps({k:result[k] for k in (
        "science_context_read_successes","science_with_package_metadata",
        "science_with_indexed_direct_dependencies","science_with_multiple_descriptions",
        "science_with_languages","status")},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
