"""Implementation Atlas: 1,287 surveyed leads, source-inspected code, scoped trials.

Separate records from metadata, source inspection, and previously recorded
synthetic/static capability trials. Neither counts as validated field deployment,
independent reproduction, commercial permission, or underconversion.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
import re

SCHEMA="cite_refinery.implementation_evidence_atlas.v1"
FOUNDATION="cite_refinery.layer_foundations.v1"
ORIGINAL="cite_refinery.implementation_original_source_audit.v1"
TRIAL="cite_refinery.functional_component_trials.v1"
DEPTH="cite_refinery.implementation_original_code_structure_audit.v1"
SHA40=re.compile(r"^[a-f0-9]{40}$")
STATUSES={"pass","fail","blocked","not_tested"}
CAPTURES={"actual_upstream_python_calculation_synthetic_input",
          "actual_upstream_python_code_synthetic_station_fixtures",
          "static_yaml_syntax_and_reference_inspection_only_not_firmware_execution"}


def _count(cases):
    return dict(Counter(row["status"] for row in cases))


def _require(condition,why):
    if not condition:raise ValueError(why)


def build_implementation_atlas(foundations, *, original_audit=None,
                               functional_trials=None, code_audit=None):
    _require(foundations.get("schema")==FOUNDATION,
             "Expected frozen source-qualified standalone foundations")
    base=foundations["implementation"]
    repos=base["repository_leads"]
    _require(len(repos)==base["unique_repositories"]==1287,
             "Full frozen implementation survey must be present")
    identities={}
    for row in repos:
        rid=row["id"]
        _require(rid=="github:"+row["name"] and
                 row["url"]=="https://github.com/"+row["name"] and
                 rid not in identities, "Original repository identity tampered")
        identities[rid]={
            "id":rid,"name":row["name"],"url":row["url"],
            "publisher_description_not_capability_proof":row["publisher_description"],
            "provider_stars_not_adoption":row["provider_stars_not_quality"],
            "provider_license_label_not_permission":row["provider_license_label_not_rights_clearance"],
            "categories":row["categories"],
            "survey_frames":row["survey_frames"],
            "source_identity_state":"survey_metadata_only",
            "pinned_source_checks":[],
            "source_code_structure_audits":[],
            "bounded_component_probe_ids":[],
            "scoped_capability_confirmed_in_live_deployment":False,
            "underconversion_established":False,
        }
    metadata_pairs=set()
    for r in repos:
        for c in r["categories"]:
            k=(r["id"],c["category"])
            _require(k not in metadata_pairs,"Repeated repo/category membership")
            metadata_pairs.add(k)
    _require(len(metadata_pairs)==base["repository_category_memberships"],
             "Original repository category accounting changed")
    pinned_pairs={}
    pinned_versions={}
    if original_audit is not None:
        _require(original_audit.get("schema")==ORIGINAL and
                 isinstance(original_audit.get("records"),list) and
                 original_audit.get("selected_category_pairs")==len(original_audit["records"]),
                 "Invalid pinned original repository audit")
        for r in original_audit["records"]:
            rid,cat=r["repository_id"],r["category"]
            k=(rid,cat)
            _require(k in metadata_pairs and k not in pinned_pairs and
                     r["source_original_url"]==identities[rid]["url"] and
                     r["original_code_executed"] is False and
                     r["independent_capability_demonstrated"] is False and
                     r["observed_adoption_or_conversion_gap"] is False,
                     "Original source record cannot promote or replace inventory evidence")
            snap=r["original_source_snapshot"]
            status=snap.get("status")
            _require(status in {"original_source_metadata_checked","unavailable_or_inconclusive"},
                     "Unknown original GitHub API audit status")
            if status=="original_source_metadata_checked":
                commit=snap.get("source_commit")
                _require(isinstance(commit,str) and SHA40.fullmatch(commit) and
                         snap.get("functional_quality_or_adoption_verified") is False and
                         snap.get("original_test_commands_executed")==0 and
                         snap.get("license_entitlement_verified") is False,
                         "Pinned GitHub audit cannot qualify software function")
                if rid in pinned_versions:
                    _require(pinned_versions[rid]==commit,
                             "Contradictory pinned revisions for one repository")
                pinned_versions[rid]=commit
                identities[rid]["source_identity_state"]="original_commit_and_root_checked"
                identities[rid]["pinned_source_checks"].append({
                    "category":cat,"original_commit":commit,
                    "root_tests_visible_not_executed":snap["root_test_directory_visible_not_executed"],
                    "source_archived":snap.get("archived",False),
                    "status":"source_identity_only_not_functional_test"})
            else:
                identities[rid]["pinned_source_checks"].append({
                    "category":cat,"status":"original_unavailable_or_inconclusive"})
            pinned_pairs[k]=status
        _require(original_audit["original_repo_revision_and_root_checked_pairs"]==
                 sum(s=="original_source_metadata_checked" for s in pinned_pairs.values()),
                 "Original source audit count mismatch")
    scoped={}
    external={}
    trial_counts=Counter()
    if functional_trials is not None:
        _require(functional_trials.get("schema")==TRIAL and
                 functional_trials.get("graph_status_promotion_allowed") is False and
                 functional_trials.get("technical_fit_confirmed") is False and
                 functional_trials.get("real_deployment_confirmed") is False and
                 functional_trials.get("commercial_eligibility_confirmed") is False and
                 functional_trials.get("scientific_intervention_outcome_confirmed") is False and
                 functional_trials.get("development_source_holdout_touched") is False and
                 isinstance(functional_trials.get("probes"),list) and
                 1<=len(functional_trials["probes"])<=15,
                 "Functional receipt does not have cautious bounded scope")
        for probe in functional_trials["probes"]:
            rid=probe.get("asset_id")
            _require(isinstance(rid,str) and rid.startswith("github:") and
                     rid not in scoped, "Duplicate or malformed execution asset")
            slug=rid.removeprefix("github:")
            source=probe.get("source")
            commit=source.get("git_commit") if isinstance(source,dict) else None
            _require(isinstance(commit,str) and SHA40.fullmatch(commit) and
                     source.get("source_url")=="https://github.com/"+slug+"/tree/"+commit and
                     source.get("test_isolated_from_authority") is True and
                     probe.get("execution") in CAPTURES and
                     isinstance(probe.get("cases"),list) and
                     1<=len(probe["cases"])<=100,
                     "Functional trial not pinned to recognized synthetic or static execution")
            cases={}
            for row in probe["cases"]:
                name=row.get("name")
                _require(isinstance(name,str) and 1<=len(name)<=128 and name not in cases and
                         row.get("status") in STATUSES and
                         row.get("critical") in (True,False) and
                         type(row.get("critical")) is bool and
                         row.get("claim_authority")=="synthetic_code_or_static_configuration_probe_only" and
                         isinstance(row.get("requirement"),str) and
                         1<=len(row["requirement"])<=1200,
                         "Invalid or falsely qualified original functional trial case")
                cases[name]={
                    "requirement":row["requirement"],"status":row["status"],
                    "critical":row["critical"],
                    "actual_from_prior_record_not_independently_replayed":row.get("actual"),
                    "expected_from_prior_record":row.get("expected"),
                    "interpretation_operator_supplied":row.get("interpretation"),
                }
                trial_counts[row["status"]]+=1
            report={
                "id":rid,"upstream_commit":commit,
                "upstream_source_url":source["source_url"],
                "technology_type_operator_supplied":probe.get("technology_type"),
                "source_entry_point_operator_supplied":probe.get("source_entry_point"),
                "execution_mode_reported":probe["execution"],
                "case_counts":_count(probe["cases"]),
                "cases":cases,
                "relevant_scope_operator_supplied":probe.get("relevant_scope"),
                "reuse_rights_not_independently_cleared":probe.get("commercial_reuse_permission"),
                "prior_source_pinned_execution_record_not_replayed_by_this_atlas":True,
                "execution_receipt_cryptographically_signed":False,
                "independently_confirmed_operational_function":False,
                "live_implementation_adoption_or_market_gap_confirmed":False,
                "experimental_blockers":sorted(n for n,v in cases.items()
                                               if v["status"] in {"fail","blocked","not_tested"}),
            }
            scoped[rid]=report
            if rid in identities:
                identities[rid]["bounded_component_probe_ids"].append(rid)
                _require(rid not in pinned_versions or pinned_versions[rid]==commit,
                         "Historic synthetic trial revision differs from independently pinned snapshot")
            else:
                external[rid]=report
        _require({k:v for k,v in trial_counts.items()}==
                 functional_trials.get("test_case_counts"),
                 "Functional trial case-count integrity mismatch")
    source_depth={}
    if code_audit is not None:
        _require(code_audit.get("schema")==DEPTH and
                 isinstance(code_audit.get("records"),list) and
                 code_audit.get("sampled_repositories")==len(code_audit["records"]) and
                 original_audit is not None,
                 "Original source-tree structure requires approved pinned repository audit")
        seen=set()
        inspected=0
        for record in code_audit["records"]:
            rid=record.get("repository_id")
            _require(rid in pinned_versions and rid not in seen and
                     record.get("pinned_commit")==pinned_versions[rid] and
                     record.get("source_code_executed") is False and
                     record.get("license_reuse_rights_cleared") is False and
                     record.get("functionality_demonstrated") is False and
                     record.get("observed_end_user_adoption") is False,
                     "Tree audit cannot promote a repo or override a pinned revision")
            seen.add(rid)
            status=record.get("status")
            _require(status in {"source_files_sha_verified","unavailable_or_inconclusive",
                                "tree_truncated_or_unusable","source_snapshot_has_no_eligible_code"},
                     "Unrecognized source inspection state")
            checked=status=="source_files_sha_verified"
            if checked:
                _require(isinstance(record.get("tree_sha"),str)
                         and SHA40.fullmatch(record["tree_sha"])
                         and isinstance(record.get("source_file_samples"),list)
                         and len(record["source_file_samples"])>0,
                         "Missing source-tree and file fingerprints")
                for file in record["source_file_samples"]:
                    _require(isinstance(file.get("blob_sha"),str)
                             and SHA40.fullmatch(file["blob_sha"])
                             and isinstance(file.get("path"),str) and file["path"]
                             and file.get("code_executed") is False,
                             "Source-blob proof absent")
                inspected+=1
            short={key:record[key] for key in (
                "repository_id","pinned_commit","status","tree_sha",
                "tree_entry_count","python_files_observed","test_files_observed",
                "source_file_samples","source_language_sampled","source_layout_hints",
                "error_type") if key in record}
            identities[rid]["source_code_structure_audits"].append(short)
            source_depth[rid]=short
        _require(code_audit.get("source_file_inspection_successes")==inspected,
                 "Original code source inspection count mismatch")
    staged={
        "index_only":sum(r["source_identity_state"]=="survey_metadata_only" for r in identities.values()),
        "commit_root_identity_checked":sum(r["source_identity_state"]=="original_commit_and_root_checked"
                                          for r in identities.values()),
        "source_file_identity_checked":sum(bool(r["source_code_structure_audits"]) and
                                            r["source_code_structure_audits"][0]["status"]=="source_files_sha_verified"
                                            for r in identities.values()),
    }
    def category_coverage():
        by_category=defaultdict(lambda:{"total":0,"metadata_reviewed":0,
                                        "commit_root_checked":0,"code_sample_checked":0,
                                        "prior_component_trial":0})
        for rid,row in identities.items():
            for cat in row["categories"]:
                key=cat["category"]
                by_category[key]["total"]+=1
                by_category[key]["metadata_reviewed"]+=int(cat["metadata_semantic_review"]!="not_reviewed")
                by_category[key]["commit_root_checked"]+=int(any(
                    p["category"]==key and p["status"]=="source_identity_only_not_functional_test"
                    for p in row["pinned_source_checks"]))
                by_category[key]["code_sample_checked"]+=int(
                    rid in source_depth and source_depth[rid]["status"]=="source_files_sha_verified")
                by_category[key]["prior_component_trial"]+=int(rid in scoped)
        return dict(sorted(by_category.items()))
    return {
        "schema":SCHEMA,"layer":"implementation",
        "provenance":{
            "original_repository_lead_count":1287,
            "survey_is_topic_search_not_a_census":True,
            "pinned_source_sample_only":True,
            "external_historic_probes_not_claimed_as_original_survey_coverage":True,
            "prior_execution_receipts_not_replayed_in_this_atlas":True,
        },
        "coverage":{
            "survey_repository_leads":len(identities),
            "repository_category_memberships":len(metadata_pairs),
            "metadata_reviewed_memberships":base["metadata_reviewed_memberships"],
            "original_commit_root_pinned_pairs":sum(
                s=="original_source_metadata_checked" for s in pinned_pairs.values()),
            "distinct_repositories_original_commit_root_checked":len(pinned_versions),
            "original_source_file_samples_sha_checked":staged["source_file_identity_checked"],
            "historical_scoped_trial_assets":len(scoped),
            "historical_scoped_trial_assets_also_in_survey":len(scoped)-len(external),
            "historical_scoped_trial_assets_outside_survey":len(external),
            "historic_synthetic_or_static_case_status_counts":dict(trial_counts),
            "technical_capabilities_independently_replayed_in_this_map":0,
            "live_operational_implementations_verified":0,
            "reuse_rights_independently_cleared":0,
            "underconverted_assets_proven":0,
            "representative_field_coverage_established":False,
        },
        "source_stages":staged,
        "surveyed_repositories":identities,
        "historical_scoped_component_trials":scoped,
        "external_tested_assets_not_in_survey":external,
        "original_code_structure_receipts":source_depth,
        "category_coverage":category_coverage(),
        "cross_layer_edges_generated":0,
        "interpretation":{
            "git_sha_identity_is_not_functional_evidence":True,
            "source_file_sha_is_not_test_pass":True,
            "passed_synthetic_case_is_not_live_deployment":True,
            "failed_synthetic_case_is_not_all_uses_fail":True,
            "source_author_claim_is_not_observed_adoption":True,
            "license_label_is_not_permission":True,
        }
    }


def browse_implementation(atlas, *, category=None, terms=None, stage=None, limit=25):
    _require(atlas.get("schema")==SCHEMA and isinstance(limit,int) and 1<=limit<=100,
             "Invalid Implementation Atlas")
    _require(stage in {None,"survey","original_commit","source_sample","historical_trial"},
             "Unrecognized implementation evidence stage")
    for s in (category,terms):
        _require(s is None or isinstance(s,str) and len(s)<=160,
                 "Invalid implementation browse filter")
    candidates=list(atlas["surveyed_repositories"].values())
    candidates+=([
        {"id":x["id"],"name":x["id"].removeprefix("github:"),
         "url":"https://github.com/"+x["id"].removeprefix("github:"),
         "publisher_description_not_capability_proof":x.get("technology_type_operator_supplied") or "",
         "categories":[],"bounded_component_probe_ids":[x["id"]],
         "source_identity_state":"historic_trial_only_outside_source_survey",
         "source_code_structure_audits":[],
         "pinned_source_checks":[]}
        for x in atlas["external_tested_assets_not_in_survey"].values()])
    matches=[]
    for row in candidates:
        if category and category not in {c["category"] for c in row["categories"]}:
            continue
        if stage=="survey" and row["source_identity_state"]!="survey_metadata_only":
            continue
        if stage=="original_commit" and not any(p["status"]=="source_identity_only_not_functional_test"
                                                for p in row["pinned_source_checks"]):
            continue
        if stage=="source_sample" and not any(p["status"]=="source_files_sha_verified"
                                             for p in row["source_code_structure_audits"]):
            continue
        if stage=="historical_trial" and not row["bounded_component_probe_ids"]:
            continue
        sentence=(" ".join([row["id"],row["name"],
                   row["publisher_description_not_capability_proof"]]+
                   [c["category"] for c in row["categories"]])).casefold()
        if terms and not all(word in sentence for word in terms.casefold().split()):
            continue
        matches.append(row)
    matches.sort(key=lambda r:r["id"])
    return {
        "schema":"cite_refinery.implementation_evidence_browse.v1",
        "terms":terms,"category":category,"stage":stage,
        "matching_count":len(matches),"results":matches[:limit],
        "lexical_only":True,"not_quality_ranked":True,
        "source_evidence_is_not_functionality_proof":True,
        "cross_layer_join_performed":False,
    }
