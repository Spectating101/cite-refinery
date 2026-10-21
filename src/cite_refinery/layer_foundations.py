"""Standalone Practical / Academic / Implementation evidence foundations.

This module indexes observed source records, not world facts. Metadata/model
readings remain provisional. No cross-layer joins or asset ranking are made.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
import json

SCHEMA = "cite_refinery.layer_foundations.v1"
ACADEMIC_ORIGINS = {"scholarly_abstract_lead", "openalex_bibliographic_abstract_lead"}
PRACTICAL_ROLES = {"practical_observation", "reported_implementation",
                   "measured_program_outcome"}
SEMANTIC_LABELS = {"relevant", "adjacent", "different_meaning",
                   "insufficient_metadata", "not_reviewed"}


def _require_url(url):
    parts = urlsplit(url) if isinstance(url, str) else None
    if not parts or parts.scheme != "https" or not parts.hostname or parts.username:
        raise ValueError("Original source must have an HTTPS identity")
    return url


def _sha256(value):
    if not isinstance(value, str) or len(value) != 64 or any(
        c not in "0123456789abcdef" for c in value
    ):
        raise ValueError("Original source SHA-256 missing or malformed")
    return value


def _records(manifest, reading_shards, atlas):
    if manifest.get("schema") != "cite_refinery.open_corpus_manifest.v1":
        raise ValueError("Expected original retrieved-source manifest")
    if atlas.get("schema") != "cite_refinery.open_corpus_atlas.v1":
        raise ValueError("Expected original provisional research atlas")
    sources = {}
    for row in manifest["source_records"]:
        sid = row["id"]
        if sid in sources:
            raise ValueError("Repeated original source ID")
        _require_url(row["url"])
        _sha256(row["sha256"])
        sources[sid] = row
    if len(sources) != manifest["count"] or len(sources) > 300:
        raise ValueError("Incomplete/boundless source inventory")
    readings = {}
    for shard in reading_shards:
        if (shard.get("schema") != "cite_refinery.open_corpus_map_chunk.v1"
            or shard.get("authority") != "neutral_provisional"
            or shard.get("accepted_scientific_conclusions") != 0
            or len(shard["source_readings"]) != shard["source_count"]):
            raise ValueError("Non-neutral or malformed semantic source readings")
        for reading in shard["source_readings"]:
            sid = reading["source_id"]
            if sid not in sources or sid in readings:
                raise ValueError("Unknown or duplicated source reading")
            if (reading["source_sha256"] != sources[sid]["sha256"]
                or reading["source_url"] != sources[sid]["url"]
                or reading["epistemic_status"] != "unverified_role_and_proposition"):
                raise ValueError("Model reading is not pinned to original retrieved material")
            readings[sid] = reading
    if set(sources) != set(readings) or atlas["mapped_source_count"] != len(sources):
        raise ValueError("Source readings do not exhaust source universe")
    assignments = defaultdict(list)
    for area in atlas["domains"]:
        for sid in area["source_ids"]:
            if sid not in sources or area["label"] in assignments[sid]:
                raise ValueError("Invalid provisional research source assignment")
            assignments[sid].append(area["label"])
    unplaced = atlas["unplaced_source_ids"]
    if (len(set(unplaced)) != len(unplaced) or set(unplaced) & set(assignments)
        or set(unplaced) | set(assignments) != set(sources)
        or atlas["accepted_scientific_claims"] != 0):
        raise ValueError("Provisional academic map omits/promotes sources")
    return sources, readings, assignments


def _repo_inventory(primary, frontier, network):
    for snap in (primary, frontier):
        if (snap.get("schema") != "cite_refinery.opportunity_atlas_github_snapshot.v1"
            or snap.get("collection_errors")):
            raise ValueError("GitHub survey error/schema mismatch")
    if network.get("schema") != "cite_refinery.opportunity_atlas_network.v1":
        raise ValueError("Missing original repository-category review inventory")
    categories = {r["id"]: r for r in network["domain_areas"]}
    if len(categories) != len(network["domain_areas"]):
        raise ValueError("Repeated implementation category")
    repos = {}
    memberships = set()
    for frame, snap in enumerate((primary, frontier)):
        if {x["id"] for x in snap["strata"]} != set(categories):
            raise ValueError("Survey category drift")
        for repo in snap["repositories"]:
            rid = repo["id"]
            if rid != "github:" + repo["full_name"] or repo["url"] != (
                "https://github.com/" + repo["full_name"]
            ):
                raise ValueError("Noncanonical GitHub identity")
            _require_url(repo["url"])
            if not repo["found_in"] or not set(repo["found_in"]) <= set(categories):
                raise ValueError("Repository membership outside collected taxonomy")
            if rid not in repos:
                repos[rid] = {"source": repo, "frames": [frame], "categories": set()}
            else:
                original = repos[rid]["source"]
                for field in ("url", "description", "topics", "license_api_label",
                              "stars", "last_push"):
                    if original[field] != repo[field]:
                        raise ValueError("Conflicting duplicate repository snapshots")
                repos[rid]["frames"].append(frame)
            for cat in repo["found_in"]:
                memberships.add((cat, repo["full_name"]))
                repos[rid]["categories"].add(cat)
    reviews = {}
    for cat, area in categories.items():
        for item in area["sampled_repositories"]:
            key = (cat, item["repository"])
            if key in reviews or key not in memberships:
                raise ValueError("Unanchored or repeated category review")
            if item["semantic_review"] not in SEMANTIC_LABELS:
                raise ValueError("Unrecognized semantic category review")
            reviews[key] = item
    if set(reviews) != memberships:
        raise ValueError("Missing repository/category review provenance")
    return repos, categories, reviews


def build(manifest, shards, atlas, primary, frontier, network, ted):
    """Build standalone, auditable inventories without computing any joins."""
    sources, readings, areas = _records(manifest, shards, atlas)
    repos, categories, reviews = _repo_inventory(primary, frontier, network)
    if ted.get("schema") != "cite_refinery.ted_notice_context.v1":
        raise ValueError("Original published procurement notice data required")
    practical, academic = [], []
    for sid in sorted(sources):
        source, reading = sources[sid], readings[sid]
        core = {
            "id": sid, "title": source["title"], "url": source["url"],
            "origin_type": source["origin_type"],
            "retrieved_text_sha256": source["sha256"],
            "publication_year": source.get("year"),
            "provisional_model_role": reading["role"],
            "provisional_model_statement": reading["statement"],
            "provisional_model_scope": reading["scope"],
            "provisional_model_caveat": reading["caveat"],
            "source_quote_sha256": reading["quote_sha256"],
            "provisional_research_areas": sorted(areas[sid]),
            "independent_entailment_or_outcome_verification": False,
        }
        if source["origin_type"] in ACADEMIC_ORIGINS:
            academic.append({
                **core, "source_class": "abstract_or_bibliographic_lead",
                "full_text_method_and_results_appraised": False,
                "publisher_claim_not_independent_replication": True,
            })
        if reading["role"] in PRACTICAL_ROLES:
            practical.append({
                **core, "source_class": "reported_practical_claim",
                "reporting_channel": (
                    "research_abstract" if source["origin_type"] in ACADEMIC_ORIGINS
                    else "official_webpage_excerpt"
                ),
                "firsthand_field_record_verified": False,
                "program_effect_independently_measured": False,
            })
    notices = []
    for notice in ted["notices"]:
        _require_url(notice["url"])
        if notice["full_scope_reviewed"] is not False or notice["bid_eligibility"] != "unknown":
            raise ValueError("A notice may not imply a verified opportunity")
        notices.append({
            "id": notice["id"], "title": notice["title"], "url": notice["url"],
            "buyer": notice["buyer"], "published": notice["publication_date"],
            "classification": "published_notice_metadata_only",
            "operator_problem_verified": False,
            "active_contract_or_eligibility_verified": False,
        })
    implementation = []
    for rid in sorted(repos):
        r = repos[rid]
        meta = r["source"]
        categories_for_repo = []
        for cat in sorted(r["categories"]):
            item = reviews[(cat, meta["full_name"])]
            categories_for_repo.append({
                "category": cat, "macro": categories[cat]["macro"],
                "metadata_semantic_review": item["semantic_review"],
                "review_reason": item.get("semantic_review_reason"),
                "independent_code_category_review": False,
            })
        implementation.append({
            "id": rid, "url": meta["url"], "name": meta["full_name"],
            "publisher_description": meta["description"],
            "provider_topics": meta["topics"],
            "provider_license_label_not_rights_clearance": meta["license_api_label"],
            "provider_stars_not_quality": meta["stars"],
            "survey_frames": sorted(set(r["frames"])),
            "categories": categories_for_repo,
            "original_code_or_deployment_qualified_by_this_map": False,
            "underconversion_established": False,
        })
    category_counts = {}
    for cat, descriptor in sorted(categories.items()):
        decisions = [reviews[key]["semantic_review"]
                     for key in reviews if key[0] == cat]
        counts = Counter(decisions)
        category_counts[cat] = {
            "category": cat, "macro": descriptor["macro"],
            "repository_memberships_in_sample": len(decisions),
            "metadata_reviewed": len(decisions) - counts["not_reviewed"],
            "unreviewed": counts["not_reviewed"],
            "different_meaning": counts["different_meaning"],
            "independent_capability_test_coverage": 0,
            "representative_category_census_established": False,
        }
    label_counts = Counter(row["semantic_review"]
                           for row in reviews.values())
    inspected = len(reviews) - label_counts["not_reviewed"]
    if (len(implementation) != network["coverage_integrity"]["unique_repository_leads"]
        or inspected != network["coverage_integrity"]["semantically_audited_repo_domain_pairs"]
        or label_counts["not_reviewed"] != network["coverage_integrity"]["semantically_unaudited_pairs"]):
        raise ValueError("Cross-file coverage integrity failed")
    return {
        "schema": SCHEMA,
        "layers": ["practical", "academic", "implementation"],
        "independent_sources_not_equivalent_to_verified_facts": True,
        "total_unique_original_research_sources": len(sources),
        "cross_layer_edges_generated": 0,
        "complete_world_coverage": False,
        "practical": {
            "reported_cases": practical,
            "published_procurement_notices_as_separate_context": notices,
            "reported_case_count": len(practical),
            "firsthand_field_records_verified": 0,
            "program_effects_independently_verified": 0,
            "model_report_roles": dict(Counter(x["provisional_model_role"] for x in practical)),
            "reported_source_genres": dict(Counter(x["reporting_channel"] for x in practical)),
            "limitation": "Abstracts and institutional excerpts are not firsthand operations data.",
        },
        "academic": {
            "source_abstracts": academic,
            "provisional_themes": [{
                "label": a["label"], "source_ids": a["source_ids"],
                "independently_validated": False, "topic_quotas_biased_collection": True
            } for a in atlas["domains"]],
            "unplaced_source_ids": atlas["unplaced_source_ids"],
            "source_count": len(academic),
            "full_text_claims_verified": 0,
            "missing_publication_year": sum(r["publication_year"] is None for r in academic),
            "bibliographic_source_genres": dict(Counter(x["origin_type"] for x in academic)),
            "provisional_theme_source_counts": [
                {"theme": a["label"], "cited_sources": len(a["source_ids"]),
                 "academic_abstract_sources": sum(sources[sid]["origin_type"] in ACADEMIC_ORIGINS
                                                  for sid in a["source_ids"]),
                 "institutional_excerpt_sources": sum(sources[sid]["origin_type"] not in ACADEMIC_ORIGINS
                                                      for sid in a["source_ids"]),
                 "independently_validated": False}
                for a in atlas["domains"]],
            "limitation": "Original eight query quotas, partial abstracts, no independent review.",
        },
        "implementation": {
            "repository_leads": implementation,
            "unique_repositories": len(implementation),
            "deduplicated_survey_occurrences": (
                len(primary["repositories"]) + len(frontier["repositories"]) - len(repos)
            ),
            "category_count": len(categories),
            "repository_category_memberships": len(reviews),
            "metadata_reviewed_memberships": inspected,
            "unreviewed_memberships": label_counts["not_reviewed"],
            "metadata_review_labels": dict(label_counts),
            "within_layer_source_categories": list(category_counts.values()),
            "independently_qualified_technical_projects": 0,
            "confirmed_underconverted_assets": 0,
            "limitation": "GitHub topic and popularity data cannot prove functioning capability.",
        },
        "priority_gaps": [
            {"layer": "practical", "need": "Independent dated operator/field logs, measured actual outcomes"},
            {"layer": "academic", "need": "Full texts, methods, contrary findings, replication and study critique"},
            {"layer": "implementation", "need": "Semantic and source-code tests; other code forges, hardware and data assets"},
        ],
        "no_automatic_financial_ranking_or_funding_layer": True,
    }


def browse(map_data, *, layer, facet=None, terms=None, limit=25):
    """Stable literal navigation of ONE layer. Not semantic retrieval."""
    if map_data.get("schema") != SCHEMA or layer not in map_data["layers"]:
        raise ValueError("Choose a standalone foundation")
    if not 1 <= limit <= 100:
        raise ValueError("Bounded browse limit expected")
    if any(x is not None and (not isinstance(x, str) or len(x) > 160)
           for x in (facet, terms)):
        raise ValueError("Malformed browse criteria")
    key = {"practical": "reported_cases", "academic": "source_abstracts",
           "implementation": "repository_leads"}[layer]
    records = map_data[layer][key]
    matches = []
    for record in records:
        groups = ([c["category"] for c in record["categories"]]
                  + [c["macro"] for c in record["categories"]]
                  if layer == "implementation" else record["provisional_research_areas"])
        if facet and facet.casefold() not in [str(x).casefold() for x in groups]:
            continue
        sentence = (record["name"] + " " + record["publisher_description"]
                    if layer == "implementation" else
                    record["title"] + " " + record["provisional_model_statement"])
        if terms and not all(x in sentence.casefold() for x in terms.casefold().split()):
            continue
        matches.append(record)
    matches.sort(key=lambda x: x["id"])
    return {
        "layer": layer, "facet": facet, "terms": terms, "matching_count": len(matches),
        "results": matches[:limit], "lexical_only": True,
        "quality_ranking_performed": False, "cross_layer_join_performed": False
    }


def review_backlog(map_data, *, per_category=2):
    """Balanced review sample for EXISTING unreviewed implementation memberships."""
    if map_data.get("schema") != SCHEMA or not 1 <= per_category <= 5:
        raise ValueError("Bounded original map expected")
    groups = defaultdict(list)
    for repo in map_data["implementation"]["repository_leads"]:
        for member in repo["categories"]:
            if member["metadata_semantic_review"] == "not_reviewed":
                groups[member["category"]].append(repo)
    selected = []
    for category in sorted(groups):
        rows = sorted(groups[category], key=lambda r:
            sha256((category + "|" + r["id"]).encode()).hexdigest())
        for repo in rows[:per_category]:
            selected.append({
                "category": category, "repository_id": repo["id"],
                "original_repository_url": repo["url"],
                "publisher_description": repo["publisher_description"],
                "original_semantic_label": "not_reviewed",
                "review_complete": False, "independent_code_quality_verified": False,
            })
    return {
        "schema": "cite_refinery.standalone_metadata_review_backlog.v1",
        "unreviewed_memberships_in_full_source": map_data["implementation"]["unreviewed_memberships"],
        "sampled_pairs": len(selected),
        "sampling_method": "stable_sha256_sorted_per_category_not_popularity",
        "model_or_human_review_completed": 0, "entries": selected,
    }


def summary_markdown(m):
    if m.get("schema") != SCHEMA:
        raise ValueError("Invalid standalone map")
    p, a, i = m["practical"], m["academic"], m["implementation"]
    lines = [
        "# Cite–Refinery | Three independent evidence maps", "",
        "**Read-only, no cross-layer relationships or opportunity ranking.**", "",
        "| Layer | Original inventory | Evidence strength |", "|---|---:|---|",
        f"| Practical | {p['reported_case_count']} provisional practical reports; "
        f"{len(p['published_procurement_notices_as_separate_context'])} separate notices "
        "| No independent field records verified |",
        f"| Academic | {a['source_count']} abstract/index records; "
        f"{len(a['provisional_themes'])} provisional themes | No full-text claims verified |",
        f"| Implementation | {i['unique_repositories']} unique repository leads | "
        "No representative code qualification |",
        "",
        "## Practical / Nocturnal", "", p["limitation"], "",
        "A research abstract that reports an intervention is not itself primary "
        "operator data. Procurement notices are recorded as context, not verified demand.", "",
        "## Academic / Cite", "", a["limitation"], "",
        "Original sources retain URL, retrieved-text SHA-256 and provisional roles. "
        "Unplaced records remain visible; a model-selected theme is not a validated discipline map.", "",
        "## Implementation / Refinery", "", i["limitation"], "",
        f"- Distinct GitHub survey records: {i['unique_repositories']}.",
        f"- Duplicate snapshot occurrences collapsed: {i['deduplicated_survey_occurrences']}.",
        f"- Repository/category pairs: {i['repository_category_memberships']}.",
        f"- Model-reviewed metadata pairs: {i['metadata_reviewed_memberships']}.",
        f"- Still unreviewed: {i['unreviewed_memberships']}.",
        "",
        "| Original category | Macro area | Repo memberships | Metadata reviews | Unreviewed |",
        "|---|---|---:|---:|---:|",
        *[f"| {x['category']} | {x['macro']} | {x['repository_memberships_in_sample']} | "
          f"{x['metadata_reviewed']} | {x['unreviewed']} |"
          for x in i["within_layer_source_categories"]],
        "",
        "No GitHub stars, SPDX labels or model category judgments have been "
        "promoted into claims of technical quality, adoption or usage rights.", "",
        "## Next evidence work", "",
    ]
    lines += [f"- **{x['layer']}**: {x['need']}." for x in m["priority_gaps"]]
    lines += ["", "The snapshot is not a census or a complete world map. "
              "Original quotes are not republished, and SHA-256 alone does not establish entailment.", ""]
    return "\n".join(lines)
