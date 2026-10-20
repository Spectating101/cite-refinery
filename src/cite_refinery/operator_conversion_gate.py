"""Source-backed operator/maintainer conversion gate across five engineering cases.

Public GitHub issues are problem signals, NOT paid work orders.
A reproducible local fix is engineering proof, NOT maintainer consent.
A license metadata field is NOT a complete legal or commercial rights check.

Collector calls GitHub's authenticated gh CLI for PUBLIC issue/repo evidence.
The normal report generation path is deterministic and offline from the saved
snapshot. Neither path posts issues, PRs, comments or contacts maintainers.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any

SCHEMA="cite_refinery.operator_conversion_gate.v1"
SNAPSHOT="cite_refinery.operator_github_snapshot.v1"

CASES=(
    {
        "id":"lfp_positive_gate_fee",
        "repo":"lingrany/EverBatt-LFP-Recycling-Analysis",
        "kind":"reproduced_unrequested",
        "issue":None,
        "layer_practical":"Unreliable process economics when feedstock is purchased for a positive gate fee.",
        "layer_academic":"Cash-flow sensitivity to feedstock purchase fees and process assumptions.",
        "layer_implementation":"Three-route LFP model with scratch-only accounting repair.",
        "asset_id":"github:lingrany/EverBatt-LFP-Recycling-Analysis",
        "mechanism_id":"mechanism:battery_recycling_economics",
        "source_checked_commit":"246c4d478f9ceb05c580856720ca56a66064e205",
        "technical_proof":"battery_repair",
        "required_next_proof":"Propose a minimal maintainer-approved fee-cost regression; obtain actual operating inputs before economic claims.",
    },
    {
        "id":"flood_nan_priority",
        "repo":"WeixuanZ/flood-warning-system",
        "kind":"reproduced_unrequested",
        "issue":None,
        "layer_practical":"Nonfinite telemetry can corrupt highest-risk station ordering.",
        "layer_academic":"NaN violates ordinary numeric ordering and should not enter valid normalized water-level comparisons.",
        "layer_implementation":"MonitoringStation ratio and sorting with scratch-only finite-value repair.",
        "asset_id":"github:WeixuanZ/flood-warning-system",
        "mechanism_id":"mechanism:flood_warning_to_impact",
        "source_checked_commit":"c1c7facf2c5577a155edd93a0b7279ad7630518c",
        "technical_proof":"flood_repair",
        "required_next_proof":"Validate with repo maintainer, obtain operational station schemas, expand fault injection and downstream alert contract.",
    },
    {
        "id":"co2_yaml_and_license",
        "repo":"ajlongshanks/co2_esphome",
        "kind":"rights_blocked",
        "issue":None,
        "license_pr":1,
        "layer_practical":"A CO2 device configuration cannot be deployed from an invalid YAML file and unresolved assets.",
        "layer_academic":"Sensor hardware IDs, configuration syntax and calibration are separate prerequisites to any exposure outcome.",
        "layer_implementation":"ESPHome SCD30 configuration fails YAML syntax; license creation PR is still pending.",
        "asset_id":"github:ajlongshanks/co2_esphome",
        "mechanism_id":"mechanism:classroom_ventilation_outcomes",
        "source_checked_commit":"d1b3c500ae475e3dcfef6e5dbb38279cdc267708",
        "technical_proof":"co2_blocked",
        "required_next_proof":"Clarify license, repair YAML and missing references on a permitted fork or with consent, compile and test actual hardware.",
    },
    {
        "id":"ofn_canada_map_bounds",
        "repo":"openfoodfoundation/openfoodnetwork",
        "kind":"externally_reported_issue",
        "issue":14924,
        "source_expected_commit":"1167aa7b7585c1794199e032fc15c0e9c1c74104",
        "source_expected_blob_sha":"74a669690f56c15f2c15ceffe34c8f02a96d0e27",
        "layer_practical":"Canadian platform shoppers were shown an incorrect starting map location.",
        "layer_academic":"Coordinate outliers can distort extreme-value midpoint centers; map bounds/zoom need robust geographic selection.",
        "layer_implementation":"Open Food Network MapCentreCalculator and instance-map configuration require an independently reproduced fix.",
        "asset_id":"github:openfoodfoundation/openfoodnetwork",
        "mechanism_id":None,
        "technical_proof":"none",
        "required_next_proof":"Read production MapCentreCalculator and tests; add geographic outlier and nationwide bounds fixtures, then offer maintainer PR if appropriate.",
    },
    {
        "id":"foodsoft_order_quantity_rounding",
        "repo":"foodcoops/foodsoft",
        "kind":"externally_reported_issue",
        "issue":1368,
        "source_expected_commit":"f594be8e64f4d3748d0e418df05fbb554ccce71b",
        "source_expected_blob_sha":"64567d22f2a02cd3d4b0a481ff1f8b581e90420d",
        "layer_practical":"Group order balancing shows an erroneous discrepancy marker for apparently equal quantities.",
        "layer_academic":"Comparisons at different decimal precision can misclassify equivalent converted quantities.",
        "layer_implementation":"OrdersHelper quantity comparison rounds only one of the two operands at three decimals.",
        "asset_id":"github:foodcoops/foodsoft",
        "mechanism_id":None,
        "technical_proof":"reported_code_arithmetic",
        "required_next_proof":"Run the original Ruby helper test at pinned revision; reproduce converted 1.7kg / 1.3kg/unit and add a symmetric precision regression.",
    },
)

def _api(path:str)->dict[str,Any]:
    if not re.fullmatch(r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_?=&.-]+)*",path):
        raise ValueError("GitHub REST path outside allowed public repository scope")
    proc=subprocess.run(["gh","api",path],capture_output=True,text=True,timeout=25)
    if proc.returncode:
        raise RuntimeError("GitHub API unavailable; do not infer current repository state")
    data=json.loads(proc.stdout)
    if not isinstance(data,dict):
        raise ValueError("unexpected API payload")
    return data

def collect() -> dict[str,Any]:
    repos={}
    for case in CASES:
        repo=case["repo"]
        if repo in repos:continue
        obj=_api("repos/"+repo)
        if obj.get("full_name")!=repo:
            raise ValueError("GitHub repository identity mismatch")
        info={
            "full_name":repo,"url":obj["html_url"],
            "default_branch":obj["default_branch"],
            "current_pushed_at":obj["pushed_at"],
            "archived":obj["archived"],"disabled":obj["disabled"],
            "license_spdx_metadata":(obj.get("license") or {}).get("spdx_id"),
            "license_metadata_is_legal_clearance":False,
            "source":"public_github_rest_repo",
            "issues":{},
            "pull_requests":{},
        }
        for query_id,source_kind in ((case.get("issue"),"issues"),
                                     (case.get("license_pr"),"pull_requests")):
            if not query_id:continue
            obj2=_api("repos/"+repo+"/issues/"+str(query_id))
            if obj2.get("number")!=query_id or obj2.get("repository_url","").split("/repos/")[-1]!=repo:
                raise ValueError("issue identity not associated with repository")
            is_pr=bool(obj2.get("pull_request"))
            if is_pr != (source_kind=="pull_requests"):
                raise ValueError("issue and PR must never be conflated")
            info[source_kind][str(query_id)]={
                "number":query_id,"title":obj2["title"],"state":obj2["state"],
                "created_at":obj2["created_at"],"updated_at":obj2["updated_at"],
                "url":obj2["html_url"],
                "unassigned":obj2.get("assignee") is None,
                "labels":sorted(x["name"] for x in obj2.get("labels",[])),
                "body_sha256":sha256((obj2.get("body") or "").encode()).hexdigest(),
                "body_not_published_in_report":True,
                "source":"public_github_rest_issue_or_pr",
            }
        repos[repo]=info
    return {
        "schema":SNAPSHOT,
        "collected_at_utc":datetime.now(timezone.utc).isoformat(),
        "repositories":repos,
        "method":"Read-only authenticated GitHub API; current states are a snapshot, not a promise of future availability.",
        "no_maintainer_contact":True,
        "no_payment_or_contract_sourcing":True,
    }

def _technical(case:dict[str,Any],functional:dict[str,Any],repair:dict[str,Any])->dict[str,Any]:
    name=case["technical_proof"]
    source_sha=case.get("source_checked_commit")
    if name=="none":
        return {
            "status":"reported_problem_not_reproduced_in_target_repository",
            "scope":"Issue text only; functional proof requires live source/Ruby/JS execution.",
            "checked_source_sha":None,
            "synthetic_result_reproduced":False,
        }
    if name=="reported_code_arithmetic":
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=35
            group=Decimal("1.7")/Decimal("1.3")
            displayed=group.quantize(Decimal(".001"))
            actual=displayed == group
            fixed=displayed == group.quantize(Decimal(".001"))
        return {
            "status":"source_referenced_arithmetic_analog_only",
            "scope":"Independent Decimal arithmetic of reporter's example; actual Foodsoft Ruby helper not executed.",
            "checked_source_sha":None,
            "synthetic_result_reproduced":not actual and fixed,
            "reporter_value_unrounded":str(group),
            "rounded_three_decimals":str(displayed),
            "asymmetric_comparison_equal":actual,
            "symmetric_comparison_equal":fixed,
            "ruby_behavior_executed":False,
        }
    if functional.get("schema")!="cite_refinery.functional_component_trials.v1" or \
        repair.get("schema")!="cite_refinery.repair_replace_executable_review.v1":
        raise ValueError("unverified local technical record")
    by_asset={p["asset_id"]:p for p in functional["probes"]}
    matched=by_asset.get(case["asset_id"])
    if matched is None or matched["source"]["git_commit"]!=source_sha:
        raise ValueError("tested source revision not exact")
    repaired={x["mechanism_id"]:x for x in repair["domains"]}
    r=repaired.get(case["mechanism_id"])
    if r is None:
        raise ValueError("scratch repair mechanism identity mismatch")
    original_pin = (r.get("upstream_source_sha") if name!="co2_blocked"
                    else repair.get("source_pins",{}).get("ajlongshanks__co2_esphome"))
    if original_pin!=source_sha:
        raise ValueError("scratch repair source revision mismatch")
    if name=="battery_repair":
        ok=(r.get("local_repair_synthetic_pass") is True and
            len(r["route_trials"])==3 and all(x["passed"] for x in r["route_trials"]))
    elif name=="flood_repair":
        ok=(r.get("local_repair_synthetic_pass") is True and
            len(r["input_ordering_trials"])==6 and
            all(x["pass"] for x in r["input_ordering_trials"]))
    elif name=="co2_blocked":
        ok=(r.get("original_yaml_valid") is False and
            len(r["config_alternative_checks"])==2 and
            r.get("firmware_compiled") is False)
    else:
        raise ValueError("unknown technical proof kind")
    if not ok:raise ValueError("technical fixture expectation not met")
    return {
        "status": "scratch_only_synthetic_repair_verified" if name.endswith("_repair")
                  else "invalid_config_reproduced_deployment_blocked",
        "scope":"Batched deterministic synthetic tests only; no operator production deployment.",
        "checked_source_sha":source_sha,
        "synthetic_result_reproduced":True,
        "upstream_patch_submitted":False,
        "deployed_fit_verified":False,
    }

def decide(snapshot:dict[str,Any],functional:dict[str,Any],repair:dict[str,Any],
           issue_contracts:dict[str,Any],*,now:datetime|None=None)->dict[str,Any]:
    if snapshot.get("schema")!=SNAPSHOT or snapshot.get("no_maintainer_contact") is not True or \
       snapshot.get("no_payment_or_contract_sourcing") is not True:
        raise ValueError("untrusted external observation")
    time_now = now or datetime.now(timezone.utc)
    if time_now.tzinfo is None:
        raise ValueError("comparison time must be timezone-aware")
    try:
        observed_at=datetime.fromisoformat(snapshot["collected_at_utc"])
    except (ValueError,TypeError,KeyError) as exc:
        raise ValueError("missing authoritative snapshot time") from exc
    if observed_at.tzinfo is None or observed_at>time_now+timedelta(minutes=5):
        raise ValueError("untrustworthy future or naive snapshot")
    age=time_now-observed_at
    stale=age>timedelta(days=14)
    found=snapshot.get("repositories",{})
    if (issue_contracts.get("schema")!="cite_refinery.reported_issue_arithmetic_contracts.v1" or
        issue_contracts.get("original_app_executed") is not False or
        issue_contracts.get("commercial_revenue_verified") is not False):
        raise ValueError("unreviewed or promoted original-issue source contracts")
    code_contracts={r["id"]:r for r in issue_contracts.get("cases",[])}
    if len(code_contracts)!=2:
        raise ValueError("exact two source-backed reported issue contracts required")
    observations=[]
    for case in CASES:
        repo=found.get(case["repo"])
        if not repo or repo.get("full_name")!=case["repo"]:
            raise ValueError("missing exact public repository observation")
        refs=[]
        reported=False
        rights_blocked=False
        if case.get("issue"):
            evidence=repo.get("issues",{}).get(str(case["issue"]))
            if not evidence or evidence.get("number")!=case["issue"] or \
               "/issues/" not in evidence.get("url","") or evidence.get("body_not_published_in_report") is not True:
                raise ValueError("missing independent issue evidence")
            if evidence["state"] not in ("open","closed") or len(evidence.get("body_sha256",""))!=64:
                raise ValueError("invalid issue state or missing preserved body digest")
            reported=evidence["state"]=="open" and not stale
            refs.append(evidence["url"])
        if case.get("license_pr"):
            pr=repo.get("pull_requests",{}).get(str(case["license_pr"]))
            if not pr or pr.get("number")!=case["license_pr"] or "/pull/" not in pr.get("url",""):
                raise ValueError("license PR cannot be reclassified as end-user issue")
            if pr["state"] not in ("open","closed"):
                raise ValueError("unrecognized license PR lifecycle")
            rights_blocked=not repo.get("license_spdx_metadata")
            refs.append(pr["url"])
        tech=_technical(case,functional,repair)
        if case.get("issue"):
            candidate=code_contracts.get(case["id"])
            if (not candidate or
                candidate.get("source_anchors_present") is not True or
                candidate.get("arithmetic_analog_reproduced") is not True or
                candidate.get("upstream_application_executed") is not False or
                candidate.get("issue_url")!=refs[0] or
                not candidate.get("source_url","").startswith("https://github.com/"+case["repo"]+"/blob/") or
                candidate.get("source_commit")!=case["source_expected_commit"] or
                candidate.get("source_git_blob_sha")!=case["source_expected_blob_sha"]):
                raise ValueError("source-checked issue contract is not grounded in matching public evidence")
            tech={
                "status":"source_pinned_arithmetic_analog_requires_runtime_test",
                "scope":"Exact GitHub source blob and faithful standalone arithmetic analog only; target Ruby/CoffeeScript app not executed.",
                "checked_source_sha":candidate["source_commit"],
                "source_blob_sha":candidate["source_git_blob_sha"],
                "source_url":candidate["source_url"],
                "synthetic_result_reproduced":True,
                "original_application_executed":False,
                "deployed_fit_verified":False,
            }
        if stale:
            lane="refresh_public_source_before_contact"
            reason="GitHub evidence snapshot is over 14 days old; no current issue or maintainer state may be claimed."
        elif repo.get("archived") or repo.get("disabled"):
            lane="inactive_repository_requires_owner_review"
            reason="Repository is archived/disabled; do not route work as an ordinary active maintainer request."
        elif reported:
            lane="reproduce_public_maintainer_issue"
            reason="Open, specific public problem report plus pinned-source arithmetic analog; original application regression and buyer budget still absent."
        elif rights_blocked:
            lane="license_and_deployment_blocked"
            reason="Pending license creation PR and source/config defects; no permission to copy or deploy presumed."
        elif tech["status"]=="scratch_only_synthetic_repair_verified":
            lane="propose_opt_in_upstream_contribution"
            reason="Reproduced scratch-only repair with no matched maintainer request or confirmed demand."
        else:
            lane="research_candidate_unready"
            reason="No verified current maintainer work request or deployed technical remedy."
        # No GitHub signal is buyer consent. Repository existence, a public issue
        # and a passing unit test do not create revenue, a contract or authority.
        observations.append({
            "id":case["id"],"repository":case["repo"],"github_url":repo["url"],
            "practical":case["layer_practical"],"academic":case["layer_academic"],
            "implementation":case["layer_implementation"],
            "asset_id":case["asset_id"],"technical":tech,
            "public_maintainer_issue_open":reported,
            "source_snapshot_stale":stale,
            "source_issue_urls":refs,"source_repo_pushed_at":repo["current_pushed_at"],
            "public_repo_archived":repo["archived"],
            "license_spdx_metadata":repo["license_spdx_metadata"],
            "license_rights_review_completed":False,
            "operator_budget_verified":False,"paid_work_order_verified":False,
            "maintainer_permission_or_interest_verified":False,
            "buyer_verified":False,"commercial_unit_economics_verified":False,
            "economic_capture_realized":False,
            "route":lane,"route_reason":reason,
            "next_evidence_test":case["required_next_proof"],
            "right_to_offer_contribution":"no contact or submission performed",
            "source_snapshot_utc":snapshot["collected_at_utc"],
        })
    return {
        "schema":SCHEMA,"source_snapshot_utc":snapshot["collected_at_utc"],
        "rows":observations,
        "source_snapshot_stale":stale,
        "checks":{
            "source_backed_open_public_issues":sum(x["public_maintainer_issue_open"] for x in observations),
            "scratch_only_technical_repairs":sum(x["technical"]["status"]=="scratch_only_synthetic_repair_verified" for x in observations),
            "verified_paid_contracts":0,"verified_revenue":0,
            "approved_external_reuse_or_contribution":0,
        },
        "boundary":"Public issue = problem report, not procurement. Synthetic code test = bounded engineering result, not an operator commitment. License metadata is not full legal review. No contact, tender, deployment, revenue or graph authority promotion.",
        "research_holdout_touched":False,"native_evidence_status_promoted":False,
    }

def markdown(report:dict[str,Any])->str:
    if report.get("schema")!=SCHEMA:raise ValueError("conversion gate required")
    lines=[
        "# From functional fixes to real maintainer/operator signals", "",
        "Source-state checked at "+report["source_snapshot_utc"]+
        ". **This is an external problem-evidence matrix, not a revenue pipeline.**","",
        "| Repository / problem | Independent practical signal | Technical proof | Present route |",
        "|---|---|---|---|",
    ]
    for row in report["rows"]:
        signal="open public issue" if row["public_maintainer_issue_open"] else "no specific current issue validated in this case record"
        if row["source_snapshot_stale"]:signal="source snapshot stale; refresh before action"
        if row["route"]=="license_and_deployment_blocked":signal="pending license PR; rights unclear"
        lines.append("| ["+row["repository"]+"]("+row["github_url"]+") | "+signal+
                     " | "+row["technical"]["status"].replace("_"," ")+
                     " | "+row["route"].replace("_"," ")+" |")
    lines+=["","## Conversion evidence still required",""]
    for row in report["rows"]:
        lines+=["### "+row["id"].replace("_"," ").title(),"",
                "**Three layers** — Practical: "+row["practical"]+
                " Academic: "+row["academic"]+
                " Implementation: "+row["implementation"],"",
                "**Next decisive step:** "+row["next_evidence_test"],"",
                "**Evidence links:** "+(", ".join(row["source_issue_urls"]) if row["source_issue_urls"] else
                                        "No relevant issue requested in this bounded source sample."),""]
    lines+=["## Hard authority and commercial gates","",
            "All five cases have **zero independently verified buyer commitments, paid work orders, "
            "full rights/compliance clearance, measured value capture, or external deployments**. "
            "A public issue is not a funded request. The license PR is a pull request, "
            "**not** independent external customer demand. Never rank by star count or "
            "promote a candidate merely because a repair passes tests.",""]
    return "\n".join(lines)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="cite-refinery-operator-conversion-gate")
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--functional",type=Path,required=True)
    p.add_argument("--repair",type=Path,required=True)
    p.add_argument("--issue-contracts",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    p.add_argument("--collect",action="store_true",
                   help="Refresh read-only public GitHub evidence. Never posts external changes.")
    args=p.parse_args(argv)
    if args.collect:
        snap=collect()
        args.snapshot.parent.mkdir(parents=True,exist_ok=True)
        args.snapshot.write_text(json.dumps(snap,ensure_ascii=False,indent=2)+"\n")
    def read(path):return json.loads(path.read_text(encoding="utf-8"))
    result=decide(read(args.snapshot),read(args.functional),
                  read(args.repair),read(args.issue_contracts))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print("Source-backed issue signals",result["checks"]["source_backed_open_public_issues"],
          "scratch-only fixes",result["checks"]["scratch_only_technical_repairs"],
          "paying contracts",result["checks"]["verified_paid_contracts"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
