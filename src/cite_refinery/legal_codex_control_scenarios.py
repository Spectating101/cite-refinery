"""016 synthetic scenario catalogue. Contains no observed operational case logs.

Counterexamples probe a proposed design, not legal compliance or causal effects.
The separate test module holds expected outcomes; the replay sees no answer key.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from .legal_codex_control_replay import SCHEMA, digest, replay, review_digest

BASE = datetime(2020, 7, 1, 8, 0, tzinfo=timezone.utc)


def at(minutes):
    return (BASE + timedelta(minutes=minutes)).isoformat()


def bundle(name, domain="procurement"):
    return {"schema": SCHEMA, "mode": "synthetic_replay", "scenario_id": name,
            "domain": domain, "jurisdiction": "Indonesia" if domain == "procurement" else "Netherlands",
            "case_id": "fictional-case", "handler": "test-handler", "reviewers": ["test-reviewer"],
            "objects": [], "events": []}


def obj(b, ident, body):
    record = {"id": ident, "body": body, "sha256": digest(body)}
    b["objects"].append(record)
    return record


def event(b, ident, minute, kind, **data):
    b["events"].append({"id": ident, "at": at(minute), "kind": kind, "data": data})


def package(b, ident="p1", **changes):
    body = {"kind": "package", "case_id": b["case_id"], "package_id": "fictional-package",
            "amount_minor": 10000, "currency": "IDR" if b["domain"] == "procurement" else "EUR",
            "description": "Wholly fictional package; not an original procurement or benefit decision."}
    body.update(changes)
    return obj(b, ident, body)


def appointment(b, ident="a1", **changes):
    body = {"kind": "appointment", "subject": "test-officer", "package_ids": ["fictional-package"],
            "currency": "IDR", "limit_minor": 20000, "signed_at": at(-120),
            "effective_from": at(-60), "effective_until": at(120)}
    body.update(changes)
    return obj(b, ident, body)


def procurement(name, *, evidence=True, **appointment_changes):
    b = bundle(name)
    package(b)
    appointment(b, **appointment_changes)
    if evidence:
        event(b, "appointment_received", 0, "evidence", object_id="a1")
    event(b, "proposal", 1, "propose", object_id="p1")
    return b


def check(b, minute=2, ident="approval", actor="test-officer"):
    event(b, ident, minute, "check", actor=actor, appointment_id="a1")


def commit(b, minute=3, ident="execution", approval="approval", actor="test-officer"):
    event(b, ident, minute, "commit", actor=actor, approval_event=approval)


def record(b, ident, role, *, status="present", custodian="agency", case_id=None):
    return obj(b, ident, {"kind": "record", "case_id": case_id or b["case_id"], "role": role,
                          "custodian": custodian, "status": status,
                          "content": "Synthetic record content, not evidence of actual government files."})


def recovery(name, *, missing=False, custodian="agency"):
    b = bundle(name, "recovery")
    package(b)
    record(b, "application", "application", status="unavailable" if missing else "present", custodian=custodian)
    record(b, "assessment", "assessment")
    event(b, "proposal", 0, "propose", object_id="p1")
    event(b, "application_received", 1, "evidence", object_id="application")
    event(b, "assessment_received", 2, "evidence", object_id="assessment")
    event(b, "triage", 3, "assess")
    return b


def human_review(b, *, disposition="waive", remaining=0, reviewer="test-reviewer",
                 addressed=None, ident="r1", decided=4, record_at=4, **changes):
    objects = {o["id"]: o for o in b["objects"]}
    p = next(o for o in b["objects"] if o["body"]["kind"] == "package")
    records = {r: objects[r]["sha256"] for r in ("application", "assessment")}
    body = {"kind": "review", "case_id": b["case_id"], "reviewer": reviewer,
            "decided_at": at(decided), "package_sha256": p["sha256"],
            "evidence_sha256": review_digest(p["sha256"], records),
            "disposition": disposition, "remaining_minor": remaining,
            "reasons": "Synthetic professional-review placeholder addressing facts and proportionality; not a real legal opinion.",
            "missing_roles_addressed": [] if addressed is None else addressed}
    body.update(changes)
    obj(b, ident, body)
    event(b, "review", record_at, "review", object_id=ident)


def scenarios():
    out = []
    def keep(b):
        out.append(b)
    b=procurement("valid_purchase");check(b);commit(b);keep(b)
    b=procurement("missing_appointment",evidence=False);check(b);commit(b);keep(b)
    b=procurement("future_appointment",effective_from=at(30));check(b);commit(b);keep(b)
    b=procurement("wrong_officer",subject="other-officer");check(b);commit(b);keep(b)
    b=procurement("wrong_scope",package_ids=["other-package"]);check(b);commit(b);keep(b)
    b=procurement("excess_amount",limit_minor=9999);check(b);commit(b);keep(b)
    b=procurement("expiry_between_check_and_commit",effective_until=at(3));check(b);commit(b,minute=4);keep(b)
    b=procurement("revocation_after_approval");check(b);event(b,"revoked",3,"revoke",object_id="a1");commit(b,4);keep(b)
    b=procurement("changed_package");check(b);package(b,"p2",amount_minor=15000)
    event(b,"changed",3,"propose",object_id="p2");commit(b,4);keep(b)
    b=procurement("actor_swap");check(b);commit(b,actor="other-officer");keep(b)
    b=procurement("reused_approval");check(b);commit(b);commit(b,4,ident="duplicate_execution");keep(b)
    b=procurement("direct_execution_bypass");commit(b);keep(b)
    b=procurement("unsupported_override",evidence=False);check(b)
    event(b,"override",3,"override",reason="Synthetic urgency without verified authority")
    commit(b,4);keep(b)
    b=procurement("late_evidence_no_hindsight",evidence=False);check(b);commit(b)
    event(b,"late_document",4,"evidence",object_id="a1");check(b,5,"new_approval")
    commit(b,6,"new_execution","new_approval");keep(b)
    b=recovery("agency_record_missing",missing=True)
    event(b,"collection",4,"collect",review_event="no-review");keep(b)
    b=recovery("waiver_after_reasoned_review",missing=True)
    human_review(b,addressed=["application"])
    event(b,"collection",5,"collect",review_event="review");keep(b)
    b=recovery("recovery_after_reasoned_review")
    human_review(b,disposition="uphold",remaining=10000)
    event(b,"collection",5,"collect",review_event="review");keep(b)
    b=recovery("claimant_document_missing",missing=True,custodian="claimant")
    event(b,"collection",4,"collect",review_event="no-review");keep(b)
    b=recovery("reviewer_conflict")
    human_review(b,reviewer="test-handler")
    event(b,"collection",5,"collect",review_event="review");keep(b)
    b=recovery("stale_review_after_new_record")
    human_review(b,disposition="uphold",remaining=10000)
    record(b,"application_v2","application",status="unavailable")
    event(b,"new_record",5,"evidence",object_id="application_v2")
    event(b,"collection",6,"collect",review_event="review");keep(b)
    b=recovery("missingness_not_considered",missing=True)
    human_review(b,disposition="uphold",remaining=10000)
    event(b,"collection",5,"collect",review_event="review");keep(b)
    b=recovery("overdue_review",missing=True)
    event(b,"deadline",10080,"tick");keep(b)
    b=recovery("collection_replay")
    human_review(b,disposition="uphold",remaining=10000)
    event(b,"collection",5,"collect",review_event="review")
    event(b,"duplicate_collection",6,"collect",review_event="review");keep(b)
    b=recovery("wrong_case_review")
    human_review(b,case_id="different-case")
    event(b,"collection",5,"collect",review_event="review");keep(b)
    return out


def run_benchmark():
    rows = []
    for b in scenarios():
        result = replay(b)
        rows.append({"scenario_id": b["scenario_id"], "domain": b["domain"],
                     "last_status": result["trace"][-1]["status"],
                     "trace": result["trace"], "input_sha256": result["input_sha256"]})
    return {"schema": "legal_codex.synthetic_control_benchmark.v1", "mode": "synthetic_replay",
            "scenario_count": len(rows), "scenarios": rows,
            "observed_government_decision_logs": 0, "real_transactions_executed": 0,
            "prevention_rate": None, "publication_authorized": False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--examples-dir")
    args=p.parse_args(argv)
    result=run_benchmark()
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if args.examples_dir:
        dest=Path(args.examples_dir);dest.mkdir(parents=True,exist_ok=True)
        for b in scenarios():
            (dest/(b["scenario_id"]+".json")).write_text(json.dumps(b,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"synthetic_scenarios":result["scenario_count"],"observed_operational_logs":0}))


if __name__ == "__main__":
    main()
