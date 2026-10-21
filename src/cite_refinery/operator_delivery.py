"""One operator-facing delivery packet from the existing investigation.

Consolidation surface: no new engine, source parser, model runner or console
script. Join immutable, locally source-pinned scoped original-code tests to
authenticated GitHub blob receipts ONLY when exact bytes agree. An attached
bounded test is not a full-app fix, evidence of profit, or an accepted graph edge.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA="cite_refinery.operator_decision_packet.v1"
_FRAMEWORK_SHA256="ebcfde5247668f2aeb105cfc814069ed10d7a3893128d8e39de73b71788d88b4"
_PROJECTS={
    "openfoodnetwork":{
        "github_repo":"openfoodfoundation/openfoodnetwork",
        "report_case":"open_food_network",
        "source_path":"app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee",
        "next_gate":"Connect configured instance bounds, verify valid remote locations and actual zoom in full OFN frontend tests",
        "scope":"Original CoffeeScript service and original Jasmine tests run in headless Chrome with bounded synthetic geographic cases",
    },
    "foodsoft":{
        "github_repo":"foodcoops/foodsoft",
        "report_case":"foodsoft",
        "source_path":"app/helpers/orders_helper.rb",
        "next_gate":"Run complete Foodsoft Rails/RSpec and ActiveRecord precision/units tests, then obtain maintainer agreement",
        "scope":"Original Ruby helper loaded in network-disabled Ruby RSpec with realistic BigDecimal doubles, not real Rails order models",
    }
}

def _repo_root():
    return Path(__file__).resolve().parents[2]

def _load_curated_scoped_report(root:Path,artifact_path:Path|None=None):
    artifact=(artifact_path if artifact_path is not None
              else root/"research_materials/opportunity_atlas/framework_scoped_integration.json")
    bytes_=artifact.read_bytes()
    if sha256(bytes_).hexdigest()!=_FRAMEWORK_SHA256:
        raise ValueError("Committed scoped original-runtime artifact fingerprint differs; refuse to attach")
    data=json.loads(bytes_)
    if data.get("schema")!="cite_refinery.framework_scoped_integration.v1":
        raise ValueError("Unsupported frozen component framework result")
    e=data["evidence"]
    if (e["complete_Rails_or_Angular_application_suite_run"] is not False or
        e["third_party_repo_modified"] is not False or
        e["commercial_contract_or_revenue_verified"] is not False or
        e["native_graph_status_promoted"] is not False):
        raise ValueError("Framework artifact asserts full application or unsupported outcome")
    return data

def _matching_runtime(state,source_id,curated):
    """Require blob identity and original GitHub source URL (commit may differ
    when identical blob content is demonstrated across revisions)."""
    publisher={r["id"]:r for r in state.get("source_authentication",[])}
    sources={s["id"]:s for s in state.get("supplied_sources",[])}
    receipt=publisher.get(source_id)
    source=sources.get(source_id)
    if not receipt or not source:
        return None
    if (receipt.get("status")!="publisher_passage_matched_claim_unreviewed" or
        receipt.get("authority")!="NONE_ACCEPTED" or
        receipt.get("source_claim_verified") is not False or
        receipt.get("text_sha256")!=source.get("text_sha256") or
        receipt.get("url")!=source.get("url") or
        receipt.get("family")!="implementation"):
        return None
    url=urlsplit(source["url"])
    if url.scheme!="https" or url.hostname!="github.com":
        return None
    for key,project in _PROJECTS.items():
        # The exact code bytes as recognized by the Git blob digest matter:
        # no runtime inferred merely from a repo or project name.
        check=curated["source_checks"].get(key,{})
        candidate=url.path.split("/")
        if (candidate[:4]!=["",*project["github_repo"].split("/"),"blob"] or
            len(candidate)!=5+len(project["source_path"].split("/")) or
            "/".join(candidate[5:])!=project["source_path"]):
            continue
        if (receipt.get("publisher_git_blob_sha")!=check.get("blob") or
            check.get("verified_against_local_checkout") is not True):
            continue
        result=curated[project["report_case"]]
        original=result["original"]
        candidate=result["local_candidate"]
        if (result["candidate_complete_application_fix"] is not False or
            original["tests"]!=candidate["tests"] or
            original["failed"]<=0 or candidate["failed"]!=0):
            raise ValueError("Curated original-source regression expectations changed")
        return {
            "project":project["github_repo"],
            "source_id":source_id,
            "publisher_blob_sha":receipt["publisher_git_blob_sha"],
            "curated_original_source_commit":check["commit"],
            "publisher_source_commit":url.path.split("/")[4],
            "same_source_bytes_proven":True,
            "source_test_artifact_sha256":_FRAMEWORK_SHA256,
            "scope":project["scope"],
            "original_tests":original["tests"],
            "original_failures":original["failed"],
            "experimental_candidate_tests":candidate["tests"],
            "experimental_candidate_failures":candidate["failed"],
            "full_original_application_integration_passed":False,
            "experimental_patch_merged_upstream":False,
            "real_field_impact_verified":False,
            "proposed_next_validation":project["next_gate"],
            "classification":"bounded_original_source_framework_regression_not_product_approval"
        }
    return None

def _action(row,attached):
    status=row["status"]
    if status=="evidence_preflight_blocked":
        return "REJECT until valid source identities, matched quoted spans and publisher receipts exist."
    if status=="reviewer_reports_mismatch_or_contradiction":
        return ("REJECT this proposed cross-layer explanation; separate component-level test evidence "
                "does not repair the academic applicability mismatch.")
    if status=="critic_output_invalid_untrusted":
        return "HOLD: model critique failed contract; request independent new review."
    if attached and status in {"semantic_fit_uncertain",
                              "plausible_mechanism_not_established_solution"}:
        return ("VALIDATE next with real application integration and an operator-defined acceptance test; "
                "a bounded repair exists, but neither mechanism-to-product nor outcome is proven.")
    if attached:
        return "REVIEW source-to-problem connection; test evidence alone does not establish intervention fit."
    return "INSUFFICIENT executable evidence: reproduce the actual source component before proposing a funded fix."

def build(state,*,repo_root:Path|None=None,framework_artifact:Path|None=None):
    if not isinstance(state,dict) or not state.get("id") or not state.get("question"):
        raise ValueError("Actual persisted investigation state required")
    reviews=state.get("cross_layer_assessments",[])
    if not reviews:
        raise ValueError("Run assess-links first; cannot produce a defensible operator decision from only citations")
    latest=reviews[-1]
    if (latest.get("schema")!="cite_refinery.cross_layer_applicability_review.v1" or
        latest.get("graph_write_performed") is not False):
        raise ValueError("Cross-layer review is not candidate-only")
    scoped=_load_curated_scoped_report(repo_root or _repo_root(),framework_artifact)
    rows=[]
    for row in latest["rows"]:
        impl=row.get("family_receipts",{}).get("implementation",{})
        practical=row.get("family_receipts",{}).get("practical",{})
        academic=row.get("family_receipts",{}).get("academic",{})
        if not impl or not practical or not academic:
            raise ValueError("All three source families required")
        runtime=_matching_runtime(state,impl.get("source_id"),scoped)
        critic=row.get("critic",{})
        rows.append({
            "id":row["id"],
            "cross_layer_status":row["status"],
            "proposed_link_authority":"CANDIDATE_ONLY",
            "source_ids":{
                "practical":practical.get("source_id"),
                "academic":academic.get("source_id"),
                "implementation":impl.get("source_id"),
            },
            "source_publisher_matching": {
                k: bool(x.get("publisher_text_verified")) for k,x in (
                    ("practical",practical),("academic",academic),
                    ("implementation",impl))
            },
            "semantic_critic_relation":critic.get("cross_layer_relation","not_run"),
            "academic_fit":critic.get("academic_fit","not_run"),
            "bounded_component_executable_receipt":runtime,
            "full_application_fitness_verified":False,
            "operator_field_success_verified":False,
            "customer_commitment_verified":False,
            "delivery_action":_action(row,runtime),
            "required_next_tests":(
                list(critic.get("missing_tests",[]))[:4] if critic
                else ["Obtain independent source entailment review before drawing conclusions"]
            ),
        })
    receipts=state.get("source_authentication",[])
    packet={
        "schema":SCHEMA,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "investigation_id":state["id"],
        "research_question":state["question"],
        "scope":"One bounded evidence-to-decision pilot; source authenticity, semantic review, source-scoped execution and business demand are separate proof classes.",
        "publisher_checks":len(receipts),
        "publisher_matching_passages":sum(r.get("status")=="publisher_passage_matched_claim_unreviewed" for r in receipts),
        "case_decisions":rows,
        "proposed_commercial_service":"Source-to-Solution Verification Sprint",
        "service_deliverable":"Source provenance and entailment matrix, executable fault reproduction where permitted, scoped candidate comparison, risk/rights limitations, and an operator-directed next-test plan.",
        "delivery_suitability":"external_demo_requires_human_review_and_client_permission",
        "pilot_pricing_status":"HYPOTHESIS_NOT_TESTED_WITH_BUYERS",
        "pilot_sales_and_revenue":0,
        "buyer_interest_verified":False,
        "source_claims_independently_true":False,
        "graph_or_scientific_claims_promoted":False,
        "total_full_application_approvals":0,
        "upstream_changes_submitted":False,
        "legal_and_licensing_cleared":False,
        "research_holdout_touched":False,
        "runtime_evidence_scope":"A frozen, digest-pinned, previously executed original-source framework result only. Not a new real execution and not generalized to unknown software.",
    }
    return packet

def render_markdown(packet):
    if packet.get("schema")!=SCHEMA:
        raise ValueError("Unsupported delivery schema")
    lines=[
        "# Source-to-Solution Verification | Operator decision brief","",
        f"**Question:** {packet['research_question']}","",
        f"**Investigation:** `{packet['investigation_id']}`","",
        "**Decision:** No cross-layer connection has been promoted to verified outcome or commercial value. "
        "Use the following results for scoped next-step decisions, not certification.","",
        f"**Publisher source receipts:** {packet['publisher_matching_passages']}/"
        f"{packet['publisher_checks']} matching reported passages. "
        "Matching a source is not proof of the report's substantive claims.","",
        "## Decision matrix","",
        "| Link | Semantic evidence | Original-code regression | Recommended action |",
        "|---|---|---|---|",
    ]
    for row in packet["case_decisions"]:
        tests=row["bounded_component_executable_receipt"]
        count=(f"{tests['original_tests']-tests['original_failures']}/"
               f"{tests['original_tests']} original vs "
               f"{tests['experimental_candidate_tests']-tests['experimental_candidate_failures']}/"
               f"{tests['experimental_candidate_tests']} temporary candidate, "
               "NOT complete application") if tests else "No source-matched executable receipt"
        action=row["delivery_action"].replace("|","/")
        lines.append(f"| {row['id']} | {row['cross_layer_status']} | {count} | {action} |")
    lines.extend(["","## Evidence and remaining obligations",""])
    for row in packet["case_decisions"]:
        lines.extend([
            f"### {row['id']}: {row['cross_layer_status']}",
            f"Practical: `{row['source_ids']['practical']}` · "
            f"Academic: `{row['source_ids']['academic']}` · "
            f"Implementation: `{row['source_ids']['implementation']}`.",
            "",
            f"**Action:** {row['delivery_action']}","",
        ])
        runtime=row["bounded_component_executable_receipt"]
        if runtime:
            lines.extend([
                f"**Pinned original-code evidence:** {runtime['project']}, "
                f"Git blob `{runtime['publisher_blob_sha']}`. "
                f"Original scoped tests: {runtime['original_tests']-runtime['original_failures']}/"
                f"{runtime['original_tests']} pass; temporary patch: "
                f"{runtime['experimental_candidate_tests']-runtime['experimental_candidate_failures']}/"
                f"{runtime['experimental_candidate_tests']} pass. "
                "**No full original application suite, upstream acceptance or field impact.**",
                "",
                f"**Next functional gate:** {runtime['proposed_next_validation']}","",
            ])
        if row["required_next_tests"]:
            lines.append("**Additional validation required:**")
            lines.extend(f"- {item}" for item in row["required_next_tests"])
            lines.append("")
    lines.extend([
        "## Proposed customer deliverable (commercial hypothesis)","",
        "**Source-to-Solution Verification Sprint:** Given a documented bug, investigation question "
        "or disputed engineering claim, produce a source-pinned report, a reproducible component "
        "test where legally/technically permitted, and a scoped go/hold/reject next-step decision. "
        "Optional implementation work must be a separately authorized engagement.","",
        "**Not a paid result:** No buyer, price acceptance, signed statement of work, "
        "real operational improvement, security certification, or revenue has been established. "
        "The near-term commercial test is a manually delivered pilot with a consenting "
        "client and measured effort/decision utility, not a speculative SaaS launch.","",
        "**Limitations:** Only available authenticated source-passage receipts and a previously "
        "curated source-pinned runtime report are joined. Original app/browser/Rails completeness, "
        "academic mechanism applicability, owner permissions and buyer demand remain distinct gates.","",
    ])
    return "\n".join(lines)
