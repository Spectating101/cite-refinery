"""Reconcile existing 1,287 frozen Implementation leads with Science's actual index.

Read-only exact-repository identity lookup, not semantic software validation.
No Science source text, Academic holdout, Nocturnal data, or graph mutations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener
import argparse
import json
import re

from .external_reuse_bridge import SCIENCE

SCHEMA = "cite_refinery.science_reuse_census.v1"
SURVEY = "cite_refinery.opportunity_atlas_github_snapshot.v1"
SEED = "frozen-implementation-2026-10-22-independent-source-reuse-v1"
API = SCIENCE + "/projects/bulk_lookup"
CHUNK = 25
MAX_BYTES = 5_000_000


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(data):
    return sha256(_canonical(data).encode("utf-8")).hexdigest()


def _read(path: Path):
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size < 2_500_000,
             "Original frozen survey missing or oversized")
    return json.loads(path.read_text("utf-8"))


def frozen_repositories(primary, frontier):
    """Reconstruct the frozen survey census. Preserve only original URL + strata."""
    for original in (primary, frontier):
        _require(isinstance(original, dict) and original.get("schema") == SURVEY
                 and original.get("collection_errors") in ([], {})
                 and isinstance(original.get("repositories"), list),
                 "Survey metadata not the original clean repository inventory")
    seen = {}
    for snapshot in (primary, frontier):
        for item in snapshot["repositories"]:
            _require(isinstance(item, dict), "Non-repository in original inventory")
            name, url = item.get("full_name"), item.get("url")
            _require(isinstance(name, str) and re.fullmatch(
                r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", name)
                and ".." not in name and
                url == "https://github.com/" + name and
                item.get("id") == "github:" + name,
                "Original source identity changed")
            cats = item.get("found_in", [])
            _require(isinstance(cats, list) and
                     all(isinstance(c, str) and 1 <= len(c) <= 100 for c in cats),
                     "Invalid original strata")
            normalized = name.casefold()
            if normalized in seen:
                _require(seen[normalized]["url"].casefold() == url.casefold(),
                         "Duplicate sources have conflicting identities")
                seen[normalized]["categories"].update(cats)
            else:
                seen[normalized] = {"url": url, "name": name,
                                    "categories": set(cats)}
    _require(len(seen) == 1287, "Frozen 1,287 unique repository survey not present")
    return [{"url": r["url"], "name": r["name"], "categories": sorted(r["categories"])}
            for r in sorted(seen.values(), key=lambda x: x["name"].casefold())]


def preregister_cohort(repositories, *, count=100, seed=SEED):
    """Category-covered source identity sample; not statistical random sampling."""
    _require(type(count) is int and 44 <= count <= 1287,
             "Cohort must include at least 44 categorical slots")
    all_categories = sorted(set(c for x in repositories for c in x["categories"]))
    _require(len(repositories) == 1287 and len(all_categories) == 44,
             "Frozen category count or full source census changed")
    if count == 1287:
        return list(repositories)
    def order(url):
        return sha256((seed + "|" + url.casefold()).encode("utf-8")).hexdigest()
    selected = {}
    for category in all_categories:
        pool = [x for x in repositories if category in x["categories"]]
        _require(bool(pool), "Missing original source category")
        x = min(pool, key=lambda item: (order(item["url"]), item["url"]))
        selected[x["url"]] = x
    # Selected repositories may represent multiple categories. Refill until
    # reaching count, respecting original full census rather than fake sampling.
    for x in sorted(repositories, key=lambda item: (order(item["url"]), item["url"])):
        if len(selected) >= count:
            break
        selected.setdefault(x["url"], x)
    _require(len(selected) == count, "Cohort incomplete")
    return sorted(selected.values(), key=lambda x: x["url"].casefold())


def fetch_science_bulk(urls: list[str], *, timeout=15) -> list[dict]:
    """Official Science bulk contract: POST exactly 1-25 existing public URLs."""
    _require(1 <= len(urls) <= CHUNK and len(set(urls)) == len(urls),
             "Bulk URLs must be unique and limited to 25")
    _require(all(isinstance(url, str) and url.startswith("https://github.com/")
                 for url in urls), "Only fixed inventory GitHub identities permitted")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("Science redirected bulk lookup to another host")

    request = Request(API, data=json.dumps({"repository_urls": urls}).encode("utf-8"),
                      headers={"Content-Type": "application/json",
                               "Accept": "application/json",
                               "User-Agent": "CiteRefineryReuseBenchmark/0.1"},
                      method="POST")
    with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        _require(response.status == 200 and
                 "json" in response.headers.get("Content-Type", "").lower(),
                 "Science bulk endpoint did not return JSON HTTP 200")
        raw = response.read(MAX_BYTES + 1)
    _require(len(raw) <= MAX_BYTES, "Oversized Science bulk response")
    parsed = json.loads(raw)
    _require(isinstance(parsed, list), "Invalid Science bulk lookup shape")
    return parsed


def run_census(primary, frontier, *, max_repos=100, fetch_batch: Callable=fetch_science_bulk,
               workers=4):
    """Identity reconciliation. Provider errors cause an explicit INCOMPLETE verdict."""
    full = frozen_repositories(primary, frontier)
    selected = preregister_cohort(full, count=max_repos)
    _require(1 <= workers <= 6, "Provider concurrency must remain bounded")
    urls = [x["url"] for x in selected]
    groups = [urls[i:i+CHUNK] for i in range(0, len(urls), CHUNK)]
    responses = {}
    failures = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(fetch_batch, group): k for k, group in enumerate(groups)}
        for future in as_completed(jobs):
            k = jobs[future]
            try:
                responses[k] = future.result()
            except Exception as exc:
                failures[k] = ("HTTP_" + str(exc.code) if isinstance(exc, HTTPError)
                               else type(exc).__name__)
    exact, missing, ambiguous, invalid = [], [], [], []
    examined = 0
    for k, batch in enumerate(groups):
        if k in failures:
            continue
        data = responses[k]
        _require(isinstance(data, list), "Invalid provider batch")
        received = {}
        for row in data:
            _require(isinstance(row, dict) and isinstance(row.get("input_url"), str)
                     and row["input_url"] in batch
                     and row["input_url"] not in received
                     and isinstance(row.get("matches"), list),
                     "Source mismatch, extraneous record or duplicated input URL")
            received[row["input_url"]] = row
        # Provider omission != 'no match'; every input must be accounted for.
        for url in batch:
            if url not in received:
                invalid.append({"url": url, "reason": "provider_omitted_input"})
                continue
            examined += 1
            matches = received[url]["matches"]
            if not matches:
                missing.append(url)
                continue
            ids = set()
            for match in matches:
                if not isinstance(match, dict):
                    continue
                project = match.get("project")
                pid = project.get("id") if isinstance(project, dict) else None
                if type(pid) is int and pid > 0:
                    ids.add(pid)
            if len(ids) == 1:
                exact.append({"repository": url, "science_project_id": next(iter(ids)),
                              "provenance": "api_identity_match_not_code_verification"})
            elif len(ids) > 1:
                ambiguous.append({"repository": url, "project_ids": sorted(ids)})
            else:
                invalid.append({"url": url, "reason": "matched_but_unreadable_project_identity"})
    count = len(selected)
    results = {
        "schema": SCHEMA, "frozen_original_repository_total": len(full),
        "survey_fingerprint_sha256": _digest(full),
        "precommitted_seed": SEED,
        "cohort_method": ("full_original_inventory" if count == 1287
                          else "source_deterministic_category_covered_not_probability_sample"),
        "cohort_size": count,
        "cohort_fingerprint_sha256": _digest(selected),
        "covered_original_strata": len(set(c for x in selected for c in x["categories"])),
        "provider": "ecosyste.ms Science",
        "api_contract": API, "batch_limit": CHUNK,
        "attempted_batches": len(groups), "failed_batches": failures,
        "identity_responses_accounted_for": examined,
        "exact_single_project_matches": len(exact),
        "ambiguous_multiple_project_matches": len(ambiguous),
        "reported_no_matching_project": len(missing),
        "unaccounted_response_rows": len(invalid),
        "not_evaluated_due_to_provider_failure": sum(
            len(groups[k]) for k in failures),
        "exact_matches": sorted(exact, key=lambda x: x["repository"]),
        "ambiguous_matches": ambiguous,
        "reported_nonmatches": sorted(missing),
        "unaccounted": invalid,
        "status": ("partial_provider_or_response_failure" if failures or invalid
                   else "complete_metadata_identity_census_no_semantic_quality_claim"),
        "not_source_functionality_verified": True,
        "not_independent_relevance_or_accuracy_benchmark": True,
        "no_source_data_ingested_to_frozen_atlas": True,
        "source_catalog_license_review_required": True,
        "accepted_scientific_or_implementation_relations": 0,
        "underconversion_or_customer_adoption_verified": False,
    }
    _require(sum(results[k] for k in (
        "exact_single_project_matches", "ambiguous_multiple_project_matches",
        "reported_no_matching_project", "unaccounted_response_rows",
        "not_evaluated_due_to_provider_failure")) == count,
        "Identity categories do not partition source cohort")
    return results


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--primary", type=Path, required=True)
    p.add_argument("--frontier", type=Path, required=True)
    p.add_argument("--count", type=int, default=100, help="100 development sample, 1287 full inventory")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    _require(not args.out.exists(), "Refuse to overwrite existing source identity receipts")
    report = run_census(_read(args.primary), _read(args.frontier),
                        max_repos=args.count, workers=args.workers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print("SCIENCE_REUSE_CENSUS", json.dumps({
        key: report[key] for key in (
            "cohort_size", "covered_original_strata", "attempted_batches",
            "identity_responses_accounted_for", "exact_single_project_matches",
            "ambiguous_multiple_project_matches", "reported_no_matching_project",
            "not_evaluated_due_to_provider_failure", "status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
