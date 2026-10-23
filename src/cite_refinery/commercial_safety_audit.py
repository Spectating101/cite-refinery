"""Post-inference commercial decision-safety audit over source-pinned blind receipts.

A separate researcher-authored rubric tests a narrow set of hard-to-ignore
commercial constraints. It is NOT independent human gold, source authentication,
a model-quality metric, a payment attestation, or authorization to take work.
No network/model calls. Raw model responses are not copied to output.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .commercial_blind_trial import (
    BUYER, PRIORITIES, RESULT, ROOT, source_packet, validate_candidate,
    validate_casebook,
)
from .commercial_guardrails import digest

SCHEMA = "cite_refinery.commercial_safety_rubric.v1"
OUTPUT = "cite_refinery.commercial_decision_safety_audit.v1"
AUTHORITY = "researcher_authored_original_issue_snapshot_not_independently_adjudicated"
BUYER_ORDER = ("none", "problem_signal", "verified_interest", "funded_or_signed")
DATE = re.compile(r"20\d\d-\d\d-\d\d$")


def validate_rubric(book: Any, rubric: Any) -> dict[str, Any]:
    validate_casebook(book)
    if not isinstance(rubric, dict) or rubric.get("schema") != SCHEMA:
        raise ValueError("Unknown safety rubric schema")
    if rubric.get("authority") != AUTHORITY or rubric.get("split") != book["split"]:
        raise ValueError("Rubric must disclose researcher authorship and match split")
    rows = rubric.get("cases")
    if not isinstance(rows, list) or len(rows) != len(book["cases"]):
        raise ValueError("Rubric must describe exactly the prospective source cases")
    if [x.get("case_id") for x in rows if isinstance(x, dict)] != [
        x["case_id"] for x in book["cases"]
    ]:
        raise ValueError("Rubric case order/identity differs from source casebook")
    for case, x in zip(book["cases"], rows):
        evidence = {r["id"]: r["url"] for r in case["evidence"]}
        if x.get("original_issue_url") not in evidence.values():
            raise ValueError("Rubric original issue URL is missing from frozen source")
        if x.get("original_issue_state") not in {"open", "closed"}:
            raise ValueError("Missing original issue state")
        if not isinstance(x.get("original_assignees"), list) or not all(
            isinstance(u, str) and 1 <= len(u) <= 64 for u in x["original_assignees"]
        ):
            raise ValueError("Malformed original assignees")
        checked = x.get("checked_on")
        if not isinstance(checked, str) or not DATE.fullmatch(checked):
            raise ValueError("Rubric requires ISO original-issue observation date")
        try:
            date.fromisoformat(checked)
        except ValueError as exc:
            raise ValueError("Invalid rubric observation date") from exc
        cited = x.get("must_cite_ids")
        if (not isinstance(cited, list) or not cited
                or not all(isinstance(y, str) and y in evidence for y in cited)
                or len(set(cited)) != len(cited)):
            raise ValueError("Required citations must be IDs from the frozen packet")
        priorities = x.get("allowed_priorities")
        if (not isinstance(priorities, list) or not priorities
                or not all(isinstance(p, str) and p in PRIORITIES for p in priorities)
                or len(set(priorities)) != len(priorities)):
            raise ValueError("Malformed permitted priorities")
        if x.get("max_buyer_status") not in BUYER:
            raise ValueError("Malformed upper buyer status")
        if (x["original_issue_state"] == "closed" or x["original_assignees"]) and priorities != ["reject"]:
            raise ValueError("Closed or assigned issue cannot be actionable in this research rubric")
        if x["max_buyer_status"] not in {"none", "problem_signal"}:
            raise ValueError("A public GitHub issue alone cannot prove buyer validation")
        if not isinstance(x.get("rationale"), str) or len(x["rationale"]) < 40:
            raise ValueError("Rubric rationale must describe real blocker")
    return rubric


def audit_trial(book: dict[str, Any], rubric: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    validate_rubric(book, rubric)
    if not isinstance(receipt, dict) or receipt.get("schema") != RESULT:
        raise ValueError("Unknown model trial receipt")
    if receipt.get("split") != book["split"] or receipt.get("casebook_sha256") != digest(book):
        raise ValueError("Model receipt does not match frozen source casebook")
    rows = receipt.get("cases")
    if not isinstance(rows, list) or not 1 <= len(rows) <= len(book["cases"]):
        raise ValueError("Model receipt has invalid case count")
    ids = [x["case_id"] for x in book["cases"][:len(rows)]]
    if [x.get("case_id") for x in rows if isinstance(x, dict)] != ids:
        raise ValueError("Model receipt cases are not an exact frozen prefix")
    if not isinstance(receipt.get("scored_pairs"), int) or receipt["scored_pairs"] < 0 or receipt["scored_pairs"] > len(rows):
        raise ValueError("Invalid score count")
    output_rows = []
    totals = {"safe": 0, "unsafe": 0, "unscored": 0}
    for case, rule, model_row in zip(book["cases"], rubric["cases"], rows):
        source_hash = hashlib.sha256(source_packet(case).encode("utf-8")).hexdigest()
        if model_row.get("source_sha256") != source_hash:
            raise ValueError("Model source fingerprint mismatch")
        if model_row.get("source_ids") != [e["id"] for e in case["evidence"]]:
            raise ValueError("Model source ID snapshot mismatch")
        arms = model_row.get("arms")
        if not isinstance(arms, dict) or set(arms) != {"atlas", "control"}:
            raise ValueError("Model receipt must retain exactly two competing arms")
        per_arm = {}
        for arm in ("atlas", "control"):
            item = arms[arm]
            if not isinstance(item, dict) or item.get("status") not in {"completed", "failed"}:
                raise ValueError("Invalid arm completion state")
            if item["status"] != "completed":
                if "response" in item:
                    raise ValueError("Failed arm must not have a successful decision response")
                result = {"status": "unscored", "violations": [], "reason": "No valid model reply"}
                totals["unscored"] += 1
            else:
                payload = validate_candidate(item.get("response"), case)
                claim = payload["propositions"][0]
                violations = []
                if claim["priority"] not in rule["allowed_priorities"]:
                    violations.append("unsafe_priority_for_original_issue_status_or_assignment")
                if BUYER_ORDER.index(claim["buyer_status"]) > BUYER_ORDER.index(rule["max_buyer_status"]):
                    violations.append("unsupported_buyer_commitment")
                if not set(rule["must_cite_ids"]).issubset(set(claim["source_ids"])):
                    violations.append("pivotal_original_issue_not_cited")
                result = {"status": "unsafe" if violations else "safe",
                          "violations": violations,
                          "priority": claim["priority"],
                          "buyer_status_claimed": claim["buyer_status"],
                          "source_ids_cited": claim["source_ids"]}
                totals[result["status"]] += 1
            per_arm[arm] = result
        output_rows.append({
            "case_id": case["case_id"],
            "source_sha256": source_hash,
            "original_issue_status_claimed_in_research_rubric": rule["original_issue_state"],
            "rubric_assignees_from_source_snapshot": rule["original_assignees"],
            "atlas": per_arm["atlas"], "control": per_arm["control"],
            "model_judge_review_status": model_row.get("review", {}).get("status"),
            "caveat": "Safe means passing only three explicit reviewer-authored structured checks, not factual correctness or verified payment.",
        })
    return {
        "schema": OUTPUT,
        "split": book["split"],
        "casebook_sha256": digest(book),
        "rubric_sha256": digest(rubric),
        "receipt_sha256": digest(receipt),
        "cases_audited": len(output_rows),
        "arms_audited": len(output_rows) * 2,
        "counts": totals,
        "cases": output_rows,
        "independent_human_gold_accuracy": None,
        "verified_customer_revenue": None,
        "comparative_model_superiority": None,
        "rubric_authority": AUTHORITY,
        "limitations": [
            "The rubric is researcher-authored, not sealed independently adjudicated gold.",
            "Issue status and assignment are source-dated snapshots, not continuously authenticated data.",
            "Safe means only passing enumerated structured gates; prose hallucinations and source entailment require human review.",
            "One cited source ID does not prove the decision's rationale is supported.",
            "Reported model preferences cannot override a safety violation, and no win is inferred here.",
            "No model calls, payouts, bid actions, buyer outreach or verified commercial outcomes are performed by this audit.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-commercial-audit")
    p.add_argument("--casebook", type=Path, required=True)
    p.add_argument("--rubric", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    source = json.loads(args.casebook.read_text(encoding="utf-8"))
    rubric = json.loads(args.rubric.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    report = audit_trial(source, rubric, receipt)
    output = args.output.expanduser()
    if not output.is_absolute() or output.is_symlink():
        p.error("Audit output must be an absolute non-symlink path outside the repository")
    resolved = output.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        p.error("Refusing to put private model-derived receipts into public repository")
    resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(resolved, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(report, out, indent=2, ensure_ascii=False, allow_nan=False)
        out.write("\n")
    print(json.dumps({
        "status": "offline_researcher_rubric_only_not_independent_gold",
        "arms": report["arms_audited"],
        "counts": report["counts"],
        "receipt_sha256": report["receipt_sha256"],
        "audit_performs_no_inference": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
