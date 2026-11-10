"""Source-attributed Chromebook authority chronology.

Unlike a guilt inference or graph ranking, this module asks what *records
report* about roles, decisions and administrative outcomes. It distinguishes
when an event allegedly happened from when the source stated it, and keeps
prosecution, defense, statute, court, and ministry records separate.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
import calendar
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "legal_codex.chromebook_source_audit.v1"
TYPES = {
    "prosecution_statement", "court_directory_metadata",
    "statute_index_and_text", "ministry_administrative_letter",
    "independent_reporting", "ministry_administrative_manual",
}
STANCES = {
    "prosecution_allegation", "prosecution_report_of_witness",
    "defense_position_as_reported", "external_witness_as_reported",
    "court_disposition_as_indexed", "regulatory_text_as_indexed",
    "administrative_statement",
}
TOPICS = {
    "specification", "budget_authority", "supplier_influence",
    "implementation", "regulation", "appeal_and_trial",
}
RID = re.compile(r"^[a-z][a-z0-9_]{2,70}$")


def _date(raw, *, optional=False):
    if raw is None and optional:
        return None
    if not isinstance(raw, str):
        raise ValueError("source/event date required")
    if re.fullmatch(r"\d{4}-\d{2}", raw):
        year, month = map(int, raw.split("-"))
        return date(year, month, calendar.monthrange(year, month)[1])
    return date.fromisoformat(raw)


def _url(u):
    if not isinstance(u, str):
        return False
    try:
        r = urlsplit(u)
        return r.scheme == "https" and bool(r.hostname) and not (r.username or r.password)
    except ValueError:
        return False


def _register(rows, name):
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"missing {name} records")
    out = {}
    for x in rows:
        if not isinstance(x, dict):
            raise ValueError(f"invalid {name} row")
        key = x.get("id")
        if not isinstance(key, str) or not RID.fullmatch(key) or key in out:
            raise ValueError(f"invalid or duplicate {name} id")
        out[key] = x
    return out


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("unsupported source audit schema")
    sources = _register(bundle.get("sources"), "sources")
    actors = _register(bundle.get("actors"), "actors")
    observations = _register(bundle.get("observations"), "observations")
    issues = _register(bundle.get("issues"), "issues")
    for ident, s in sources.items():
        if (s.get("type") not in TYPES or not _url(s.get("url"))
                or not isinstance(s.get("publisher"), str) or not s["publisher"]
                or not isinstance(s.get("document_role"), str) or not s["document_role"]):
            raise ValueError(f"{ident}: invalid source provenance")
        _date(s.get("published_at"))
        if s.get("claim_truth_authenticated") is not False:
            raise ValueError(f"{ident}: source truth cannot be auto-certified")
        if s.get("original_document_bytes_archived") not in {False}:
            raise ValueError(f"{ident}: original document not archived in this repository")
        receipt = s.get("capture_receipt")
        if receipt is not None:
            if (s["type"] != "prosecution_statement"
                    or receipt.get("archive_class") != "nocturnal_live_ci_capture"
                    or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("raw_sha256", "")))
                    or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("text_sha256", "")))
                    or not isinstance(receipt.get("workflow_run"), int)):
                raise ValueError(f"{ident}: invalid CI capture receipt")
    for ident, a in actors.items():
        if not isinstance(a.get("name"), str) or len(a["name"].strip()) < 3:
            raise ValueError(f"{ident}: missing actor name")
        if a.get("status") != "source_named_requires_identity_review":
            raise ValueError(f"{ident}: actor identity may not be automatically established")
        if not isinstance(a.get("source_ids"), list) or not a["source_ids"] or any(
                x not in sources for x in a["source_ids"]):
            raise ValueError(f"{ident}: actor lacks source")
    for ident, o in observations.items():
        src = sources.get(o.get("source_id"))
        if src is None:
            raise ValueError(f"{ident}: observation lacks source")
        when = _date(o.get("event_at"), optional=True)
        reported = _date(o.get("reported_at"))
        if reported != _date(src["published_at"]):
            raise ValueError(f"{ident}: observation reported-at must match source publication")
        if when is not None and when > reported:
            raise ValueError(f"{ident}: retrospective source cannot report a future event as settled")
        if o.get("stance") not in STANCES or o.get("topic") not in TOPICS:
            raise ValueError(f"{ident}: invalid epistemic stance/topic")
        if not isinstance(o.get("statement"), str) or len(o["statement"]) < 24:
            raise ValueError(f"{ident}: missing observation")
        if not isinstance(o.get("actor_ids"), list) or any(x not in actors for x in o["actor_ids"]):
            raise ValueError(f"{ident}: actor unknown")
        if o.get("human_review") != "pending" or o.get("factual_truth_established") is not False:
            raise ValueError(f"{ident}: may not upgrade a source assertion into a finding")
        if (o["stance"] == "administrative_statement" and src["type"] not in
                {"ministry_administrative_letter", "ministry_administrative_manual"}):
            raise ValueError("administrative claim source type mismatch")
        if o["stance"] == "regulatory_text_as_indexed":
            if src["type"] != "statute_index_and_text" or not o.get("effective_from"):
                raise ValueError("regulation lacks source or effective date")
            _date(o["effective_from"])
        if o["stance"] == "court_disposition_as_indexed" and src["type"] != "court_directory_metadata":
            raise ValueError("court disposition cannot be invented from a press release")
        if o["stance"] in {"prosecution_allegation", "prosecution_report_of_witness"} and src["type"] != "prosecution_statement":
            raise ValueError("prosecution claim lost its author attribution")
        if o["stance"] in {"defense_position_as_reported", "external_witness_as_reported"} and src["type"] != "independent_reporting":
            raise ValueError("counterevidence source provenance mismatch")
        metric = o.get("metric")
        if metric:
            if (metric.get("name") != "device_mapping_coverage" or
                    o["topic"] != "implementation" or
                    o["stance"] != "administrative_statement" or
                    src["type"] != "ministry_administrative_letter" or
                    metric.get("unit") != "percent" or
                    metric.get("population") not in {"APBN_Pusat", "DAK_Fisik"} or
                    type(metric.get("value")) not in {float, int} or
                    not 0 <= metric["value"] <= 100):
                raise ValueError("mapping coverage must not be described as actual device use")
    for ident, i in issues.items():
        if (i.get("topic") not in TOPICS or
                not isinstance(i.get("observation_ids"), list) or
                len(i["observation_ids"]) < 2 or
                any(k not in observations for k in i["observation_ids"])):
            raise ValueError(f"{ident}: issue not linked to competing source observations")
        if i.get("verdict") != "unresolved_requires_original_records":
            raise ValueError(f"{ident}: unsupported dispute resolution")
    return sources, actors, observations, issues


def evaluate(bundle):
    sources, actors, observations, issues = validate(bundle)
    reports = []
    for o in observations.values():
        reports.append({
            "id": o["id"], "event_at": o["event_at"],
            "reported_at": o["reported_at"], "source_id": o["source_id"],
            "source_type": sources[o["source_id"]]["type"],
            "stance": o["stance"], "topic": o["topic"],
            "statement": o["statement"],
            "actors_named": [actors[x]["name"] for x in o["actor_ids"]],
            "metric": o.get("metric"),
            "review": "pending",
            "factual_truth_established": False,
        })
    reports.sort(key=lambda r: (r["event_at"] or r["reported_at"], r["reported_at"], r["id"]))
    questions = []
    for i in issues.values():
        questions.append({
            "issue_id": i["id"], "question": i["question"],
            "source_claims": i["observation_ids"],
            "missing_original_records": i["missing_original_records"],
            "verdict": "unresolved_requires_original_records",
        })
    counts = Counter(o["stance"] for o in observations.values())
    return {
        "schema": "legal_codex.chromebook_audit_result.v1",
        "source_count": len(sources), "actor_count": len(actors),
        "observation_count": len(reports), "stance_counts": dict(counts),
        "timeline": reports, "disputes": questions,
        "actual_use_rate_measured": False,
        "mapping_counts_are_use_rates": False,
        "court_original_pdf_verified": False,
        "regulatory_applicability_to_all_funding_streams": "not_established",
        "actor_decision_authority_verified": False,
        "personal_guilt_assessed_by_system": False,
        "publication_authorized": False,
    }


def semantic_packet(bundle):
    sources, actors, observations, _ = validate(bundle)
    nodes = [{
        "key": "source-" + s["id"], "kind": "source", "layer": "neutral",
        "statement": s["publisher"] + ": " + s["document_role"],
        "source_refs": [s["url"]],
        "provenance": {"source_role": s["type"], "original_document_archived": False},
    } for s in sources.values()]
    nodes += [{
        "key": "actor-" + a["id"], "kind": "person" if a["kind"] == "person" else "institution",
        "layer": "neutral", "statement": a["name"],
        "source_refs": [sources[x]["url"] for x in a["source_ids"]],
        "provenance": {"identity_status": a["status"], "common_control_established": False},
    } for a in actors.values()]
    nodes += [{
        "key": "claim-" + o["id"], "kind": "observation", "layer": "neutral",
        "statement": ("Source-reported (" + o["stance"] + "): " + o["statement"]),
        "source_refs": [sources[o["source_id"]]["url"]],
        "provenance": {"human_review": "pending", "factual_truth_established": False,
                       "source_id": o["source_id"], "event_at": o["event_at"],
                       "reported_at": o["reported_at"],
                       "metric": o.get("metric")},
    } for o in observations.values()]
    edges = []
    for o in observations.values():
        edges.append({
            "source": "source-" + o["source_id"], "target": "claim-" + o["id"],
            "relation": "REPORTS", "status": "candidate",
            "evidence_refs": [sources[o["source_id"]]["url"]],
            "provenance": {"stance": o["stance"], "human_review": "pending"},
        })
        # No actor edges from a prosecution allegation; individuals may merely
        # be mentioned by a source. Actor IDs remain in the queryable audit.
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-chromebook-source-audit",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="legal_codex_chromebook_audit.json")
    p.add_argument("--packet")
    args = p.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(data)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(
            json.dumps(semantic_packet(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_count": result["source_count"],
                      "observation_count": result["observation_count"],
                      "unresolved_disputes": len(result["disputes"]),
                      "publication_authorized": False}))


if __name__ == "__main__":
    main()
