"""016: deterministic event replay of proposed controls, not production enforcement.

Inputs MUST be explicitly synthetic. Hashes bind fixture content, not government
signatures. Knowledge enters only at an evidence event. The replay never edits a
live order, collects money, decides entitlement, or estimates prevention efficacy.
The human-review policy and escalation interval are proposed design choices.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA = "legal_codex.control_replay.v1"
POLICIES = {
    "procurement": ("Indonesia", "proposed_procurement_control_016"),
    "recovery": ("Netherlands", "proposed_protective_review_016"),
}
BASE_FIELDS = {"schema", "mode", "scenario_id", "domain", "jurisdiction",
               "case_id", "handler", "reviewers", "objects", "events"}
OBJECT_FIELDS = {
    "package": {"kind", "case_id", "package_id", "amount_minor", "currency", "description"},
    "appointment": {"kind", "subject", "package_ids", "currency", "limit_minor",
                    "signed_at", "effective_from", "effective_until"},
    "record": {"kind", "case_id", "role", "custodian", "status", "content"},
    "review": {"kind", "case_id", "reviewer", "decided_at", "package_sha256",
               "evidence_sha256", "disposition", "remaining_minor", "reasons",
               "missing_roles_addressed"},
}
EVENT_FIELDS = {
    "evidence": {"object_id"}, "propose": {"object_id"},
    "revoke": {"object_id"}, "check": {"actor", "appointment_id"},
    "commit": {"actor", "approval_event"}, "override": {"reason"},
    "assess": set(), "review": {"object_id"},
    "collect": {"review_event"}, "tick": set(),
}
REQUIRED_RECORDS = ("application", "assessment")
HEX = re.compile(r"[a-f0-9]{64}\Z")
IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,95}\Z")


def digest(value: Any) -> str:
    """Canonical JSON commitment; not a digital signature or trusted timestamp."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def instant(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return result


def identifier(value: str) -> None:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise ValueError("invalid identifier")


def money(value: Any) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("money must be nonnegative integer minor units")


def validate(bundle: dict) -> dict[str, dict]:
    if not isinstance(bundle, dict) or set(bundle) != BASE_FIELDS:
        raise ValueError("unsupported replay fields")
    if bundle["schema"] != SCHEMA or bundle["mode"] != "synthetic_replay":
        raise ValueError("only explicitly synthetic replay is supported")
    domain = bundle["domain"]
    if domain not in POLICIES or bundle["jurisdiction"] != POLICIES[domain][0]:
        raise ValueError("policy jurisdiction mismatch; no foreign legal transfer")
    for k in ("scenario_id", "case_id", "handler"):
        identifier(bundle[k])
    reviewers = bundle["reviewers"]
    if (not isinstance(reviewers, list) or not reviewers or
            len(set(reviewers)) != len(reviewers)):
        raise ValueError("explicit unique synthetic reviewer registry required")
    for reviewer in reviewers:
        identifier(reviewer)
    objects = {}
    if not isinstance(bundle["objects"], list):
        raise ValueError("object array required")
    for obj in bundle["objects"]:
        if not isinstance(obj, dict) or set(obj) != {"id", "body", "sha256"}:
            raise ValueError("invalid object record")
        identifier(obj["id"])
        if obj["id"] in objects:
            raise ValueError("duplicate object identity")
        body = obj["body"]
        if not isinstance(body, dict) or body.get("kind") not in OBJECT_FIELDS:
            raise ValueError("unknown evidence kind")
        if set(body) != OBJECT_FIELDS[body["kind"]] or obj["sha256"] != digest(body):
            raise ValueError("evidence schema or digest mismatch")
        if "case_id" in body:
            identifier(body["case_id"])
        kind = body["kind"]
        if kind == "package":
            identifier(body["package_id"])
            money(body["amount_minor"])
            if not isinstance(body["description"], str) or not body["description"]:
                raise ValueError("package description required")
        if kind in {"package", "appointment"}:
            if body["currency"] not in {"IDR", "EUR"}:
                raise ValueError("unsupported currency")
        if kind == "appointment":
            identifier(body["subject"])
            money(body["limit_minor"])
            ids = body["package_ids"]
            if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
                raise ValueError("explicit unique delegation package scope required")
            for ident in ids:
                identifier(ident)
            if instant(body["effective_from"]) >= instant(body["effective_until"]):
                raise ValueError("empty appointment validity interval")
            instant(body["signed_at"])
        if kind == "record":
            if (body["role"] not in REQUIRED_RECORDS or
                    body["custodian"] not in {"agency", "claimant", "unknown"} or
                    body["status"] not in {"present", "unavailable"} or
                    not isinstance(body["content"], str) or not body["content"]):
                raise ValueError("record provenance/status invalid")
        if kind == "review":
            identifier(body["reviewer"])
            instant(body["decided_at"])
            money(body["remaining_minor"])
            if (body["disposition"] not in {"uphold", "mitigate", "waive"} or
                    not HEX.fullmatch(str(body["package_sha256"])) or
                    not HEX.fullmatch(str(body["evidence_sha256"])) or
                    not isinstance(body["reasons"], str) or len(body["reasons"].strip()) < 40):
                raise ValueError("reasoned, content-bound review required")
            addressed = body["missing_roles_addressed"]
            if (not isinstance(addressed, list) or len(set(addressed)) != len(addressed) or
                    any(r not in REQUIRED_RECORDS for r in addressed)):
                raise ValueError("missing-record review scope invalid")
        objects[obj["id"]] = obj
    events = bundle["events"]
    if not isinstance(events, list) or not events or len(events) > 10000:
        raise ValueError("bounded nonempty event log required")
    ids, prior = set(), None
    for event in events:
        if not isinstance(event, dict) or set(event) != {"id", "at", "kind", "data"}:
            raise ValueError("invalid event envelope")
        identifier(event["id"])
        if event["id"] in ids:
            raise ValueError("duplicate event ID")
        ids.add(event["id"])
        when = instant(event["at"])
        if prior is not None and when < prior:
            raise ValueError("recorded order cannot be silently reordered or backdated")
        prior = when
        kind = event["kind"]
        if (kind not in EVENT_FIELDS or not isinstance(event["data"], dict) or
                set(event["data"]) != EVENT_FIELDS[kind]):
            raise ValueError("unsupported event/action fields")
        allowed = ({"evidence", "propose", "revoke", "check", "commit", "override"}
                   if domain == "procurement" else
                   {"evidence", "propose", "assess", "review", "collect", "tick", "override"})
        if kind not in allowed:
            raise ValueError("wrong decision domain")
        if "object_id" in event["data"] and event["data"]["object_id"] not in objects:
            raise ValueError("event references absent object")
        for k, value in event["data"].items():
            if k == "reason":
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("override request must be logged with reason")
            else:
                identifier(value)
    return objects


def review_digest(package_hash: str, records: dict[str, str]) -> str:
    """Bind human review to exact package and current case-local record versions."""
    return digest({"package": package_hash, "records": records})


def replay(bundle: dict) -> dict:
    objects = validate(bundle)
    available, revoked, records, decisions, used = set(), set(), {}, {}, set()
    package = None
    package_revision, evidence_revision = 0, 0
    package_known_at, record_known_at = None, {}
    completed_packages = set()
    pending_since = None
    trace = []
    previous_hash = None
    domain = bundle["domain"]

    def authority(appointment_id: str, actor: str, now: datetime) -> list[str]:
        errors = []
        if package is None:
            errors.append("no_current_package")
        if appointment_id not in available:
            return errors + ["appointment_not_available_at_decision"]
        obj = objects[appointment_id]
        doc = obj["body"]
        if doc["kind"] != "appointment":
            return errors + ["not_an_appointment"]
        if appointment_id in revoked:
            errors.append("appointment_revoked")
        if doc["subject"] != actor:
            errors.append("actor_not_appointed")
        if instant(doc["signed_at"]) > now:
            errors.append("appointment_not_yet_signed")
        if not (instant(doc["effective_from"]) <= now < instant(doc["effective_until"])):
            errors.append("outside_appointment_validity")
        if package is not None:
            p = package["body"]
            if p["package_id"] in completed_packages:
                errors.append("package_already_executed")
            if p["package_id"] not in doc["package_ids"]:
                errors.append("delegation_wrong_package")
            if p["currency"] != doc["currency"]:
                errors.append("delegation_currency_mismatch")
            if p["amount_minor"] > doc["limit_minor"]:
                errors.append("delegation_amount_exceeded")
        return errors

    def state_digest() -> str:
        return review_digest(package["sha256"], {k: v["sha256"] for k, v in records.items()})

    def missing_records() -> list[str]:
        return [r for r in REQUIRED_RECORDS
                if r not in records or records[r]["body"]["status"] != "present"]

    for event in bundle["events"]:
        kind, data, now = event["kind"], event["data"], instant(event["at"])
        errors, status = [], "RECORDED"
        ref = None
        if kind == "evidence":
            obj = objects[data["object_id"]]
            body = obj["body"]
            if body.get("case_id", bundle["case_id"]) != bundle["case_id"]:
                errors = ["evidence_belongs_to_other_case"]
                status = "REJECTED"
            elif body["kind"] in {"package", "review"}:
                errors, status = ["wrong_evidence_event_type"], "REJECTED"
            elif domain == "procurement" and body["kind"] != "appointment":
                errors, status = ["wrong_evidence_domain"], "REJECTED"
            elif domain == "recovery" and body["kind"] != "record":
                errors, status = ["wrong_evidence_domain"], "REJECTED"
            else:
                available.add(obj["id"])
                if body["kind"] == "record":
                    old = records.get(body["role"])
                    if old is None or old["sha256"] != obj["sha256"]:
                        evidence_revision += 1
                        record_known_at[body["role"]] = now
                    records[body["role"]] = obj
        elif kind == "propose":
            obj = objects[data["object_id"]]
            if obj["body"]["kind"] != "package" or obj["body"]["case_id"] != bundle["case_id"]:
                errors, status = ["proposal_case_or_type_mismatch"], "REJECTED"
            else:
                changed = package is None or package["sha256"] != obj["sha256"]
                package = obj
                if changed:
                    package_revision += 1
                    package_known_at = now
                if domain == "recovery" and pending_since is None:
                    pending_since = now
                status = "PROPOSAL_REPLACED_REVIEW_REQUIRED" if changed else "UNCHANGED_PROPOSAL"
        elif kind == "revoke":
            obj = objects[data["object_id"]]
            if obj["body"]["kind"] != "appointment":
                errors, status = ["not_an_appointment"], "REJECTED"
            else:
                revoked.add(obj["id"])
                status = "AUTHORITY_REVOKED"
        elif kind == "check":
            errors = authority(data["appointment_id"], data["actor"], now)
            status = "HOLD_PURCHASE" if errors else "READY_FOR_SIMULATED_COMMIT"
            if not errors:
                decisions[event["id"]] = {"kind": "check", "package_sha": package["sha256"],
                    "appointment": data["appointment_id"], "actor": data["actor"],
                    "package_revision": package_revision}
        elif kind == "commit":
            ref = data["approval_event"]
            approved = decisions.get(ref)
            if approved is None or approved["kind"] != "check":
                errors.append("no_successful_prior_approval")
            else:
                if ref in used:
                    errors.append("approval_already_consumed")
                if package is None or approved["package_sha"] != package["sha256"]:
                    errors.append("proposal_changed_after_approval")
                if approved["package_revision"] != package_revision:
                    errors.append("approval_invalidated_by_package_revision")
                if data["actor"] != approved["actor"]:
                    errors.append("committing_actor_changed")
                errors.extend(authority(approved["appointment"], data["actor"], now))
            status = "HOLD_PURCHASE" if errors else "SIMULATED_COMMIT"
            if not errors:
                used.add(ref)
                completed_packages.add(package["body"]["package_id"])
        elif kind == "override":
            errors, status = ["override_is_not_approval_authority"], "OVERRIDE_REFUSED"
        elif kind == "assess":
            if package is None:
                errors, status = ["no_current_package"], "REVIEW_REQUIRED"
            else:
                missing = missing_records()
                agency = [r for r in missing if r in records and records[r]["body"]["custodian"] == "agency"]
                status = "PROTECTIVE_REVIEW" if agency else "HUMAN_REVIEW_REQUIRED"
                errors = ["missing_" + r for r in missing] or ["reasoned_review_required"]
        elif kind == "review":
            obj = objects[data["object_id"]]
            body = obj["body"]
            if body["kind"] != "review" or package is None:
                errors.append("review_without_proposal_or_wrong_type")
            else:
                if body["case_id"] != bundle["case_id"]:
                    errors.append("review_wrong_case")
                if body["reviewer"] not in bundle["reviewers"] or body["reviewer"] == bundle["handler"]:
                    errors.append("reviewer_not_independent_authorized_person")
                if instant(body["decided_at"]) > now:
                    errors.append("review_not_yet_decided")
                known_at = max([package_known_at, *record_known_at.values()])
                if instant(body["decided_at"]) < known_at:
                    errors.append("review_predates_available_evidence")
                if package["body"]["package_id"] in completed_packages:
                    errors.append("recovery_package_already_resolved")
                if body["package_sha256"] != package["sha256"] or body["evidence_sha256"] != state_digest():
                    errors.append("review_not_bound_to_current_evidence")
                if not set(missing_records()).issubset(body["missing_roles_addressed"]):
                    errors.append("missing_records_not_addressed")
                amount, total = body["remaining_minor"], package["body"]["amount_minor"]
                disposition = body["disposition"]
                if ((disposition == "waive" and amount != 0) or
                    (disposition == "uphold" and amount != total) or
                    (disposition == "mitigate" and not 0 < amount < total)):
                    errors.append("review_disposition_amount_conflict")
            status = "REVIEW_REJECTED" if errors else "REASONED_REVIEW_RECORDED"
            if not errors:
                decisions[event["id"]] = {"kind": "review", "package_sha": package["sha256"],
                    "evidence_sha": state_digest(), "remaining": body["remaining_minor"],
                    "package_revision": package_revision, "evidence_revision": evidence_revision}
        elif kind == "collect":
            ref = data["review_event"]
            decision = decisions.get(ref)
            if decision is None or decision["kind"] != "review":
                errors.append("no_current_reasoned_review")
            else:
                if ref in used:
                    errors.append("review_already_consumed")
                if (decision["package_revision"] != package_revision or
                        decision["evidence_revision"] != evidence_revision):
                    errors.append("review_invalidated_by_state_revision")
                if package and package["body"]["package_id"] in completed_packages:
                    errors.append("recovery_package_already_resolved")
                if package is None or decision["package_sha"] != package["sha256"] or decision["evidence_sha"] != state_digest():
                    errors.append("evidence_changed_after_review")
            if errors:
                status = "HOLD_ADVERSE_COLLECTION"
            else:
                status = "NO_COLLECTION_SIMULATED" if decision["remaining"] == 0 else "SIMULATED_COLLECTION"
                used.add(ref)
                completed_packages.add(package["body"]["package_id"])
                pending_since = None
        elif kind == "tick":
            status = ("ESCALATE_UNRESOLVED_REVIEW" if pending_since is not None and
                      now - pending_since >= timedelta(days=7) else "NO_DEADLINE_ESCALATION")
        row = {"event_id": event["id"], "at": event["at"], "kind": kind, "status": status,
               "reasons": sorted(set(errors)), "package_sha256": package["sha256"] if package else None,
               "prior_decision": ref, "previous_event_sha256": previous_hash}
        row["event_sha256"] = digest(row)
        trace.append(row)
        previous_hash = row["event_sha256"]
    return {"schema": "legal_codex.control_replay_result.v1", "scenario_id": bundle["scenario_id"],
            "mode": "synthetic_replay", "policy": POLICIES[domain][1], "trace": trace,
            "input_sha256": digest(bundle), "result_head_sha256": previous_hash,
            "source_authenticity_established": False, "historical_legality_decided": False,
            "real_transaction_executed": False, "real_collection_executed": False,
            "historical_prevention_established": False, "publication_authorized": False}


def semantic_packet(bundle: dict, result: dict) -> dict:
    if result != replay(bundle):
        raise ValueError("stale or fabricated result cannot enter graph")
    sid = bundle["scenario_id"]
    nodes, edges = [], []
    for row in result["trace"]:
        key = sid + "-" + row["event_id"]
        nodes.append({"key": key, "kind": "observation", "layer": "neutral",
                      "statement": "SYNTHETIC replay: " + row["status"],
                      "provenance": {"synthetic": True, "event_sha256": row["event_sha256"],
                                     "historical_prevention_established": False}})
        if len(nodes) > 1:
            edges.append({"source": nodes[-2]["key"], "target": key,
                          "relation": "PRECEDES_SYNTHETIC_DECISION", "status": "candidate"})
    return {"schema": "cite_refinery.semantic_graph.v1", "source_system": "legal-control-replay-016",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="Explicitly synthetic event-log fixture")
    p.add_argument("--output", required=True)
    p.add_argument("--packet")
    args = p.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = replay(bundle)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(semantic_packet(bundle, result), indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"scenario": result["scenario_id"], "events": len(result["trace"]),
                      "synthetic": True, "real_transaction_executed": False}))


if __name__ == "__main__":
    main()
