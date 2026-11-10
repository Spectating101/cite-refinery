"""Versioned court posture from attributed dockets, not a legal finality oracle.

Directory index metadata establishes a docket listing, not judgment PDF custody.
Reports about appeal/cassation/finality never become certified court status.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = "legal_codex.case_posture.v1"
_ALLOWED = {"official_court_index", "journalistic_case_reporting", "independent_legal_commentary"}
_EVENT_KINDS = {
    "trial_directory_listing", "trial_judgment_reported", "appeal_directory_listing",
    "cassation_filing_reported", "no_appeal_reported",
}
_TRIAL_DOCKETS = {
    "case_nadiem": "147/Pid.Sus-TPK/2025/PN Jkt.Pst",
    "case_ibam": "148/Pid.Sus-TPK/2025/PN Jkt.Pst",
    "case_sri": "149/Pid.Sus-TPK/2025/PN Jkt.Pst",
}
_APPEAL_DOCKETS = {
    "case_nadiem": "41/PID.SUS-TPK/2026/PT DKI",
    "case_ibam": "31/PID.SUS-TPK/2026/PT DKI",
}
_OFFICIAL_HOST = "putusan3.mahkamahagung.go.id"
_INDEX_PATH = "/direktori/index/pengadilan/pt-jakarta/kategori/korupsi-1/tahunjenis/putus/tahun/2026.html"


def _https(url):
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except ValueError:
        return False


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("invalid case posture schema")
    if (bundle.get("original_judgment_pdfs_in_hand") != []
            or bundle.get("authenticated_finality_certificates") != []
            or bundle.get("signed_2020_ppk_instruments") != []
            or bundle.get("matching_sd_e_purchase_orders") != []):
        raise ValueError("unobtained source documents promoted")
    raw_sources, raw_cases = bundle.get("sources"), bundle.get("cases")
    if not isinstance(raw_sources, list) or not raw_sources or not isinstance(raw_cases, list) or len(raw_cases) != 3:
        raise ValueError("three cases and nonempty sources required")
    sources = {}
    for s in raw_sources:
        key = s.get("id")
        if not isinstance(key, str) or key in sources or not re.fullmatch(r"s_[a-z0-9_]+", key):
            raise ValueError("duplicate or invalid source id")
        if s.get("class") not in _ALLOWED or not _https(s.get("url")):
            raise ValueError("unattributed source")
        if s.get("full_original_judgment_captured") is not False:
            raise ValueError("source page cannot assert judgment PDF custody")
        parsed = urlsplit(s["url"])
        if s["class"] == "official_court_index":
            if parsed.hostname != _OFFICIAL_HOST or parsed.path != _INDEX_PATH or parsed.query or parsed.fragment:
                raise ValueError("official index provenance invalid")
        elif parsed.hostname == _OFFICIAL_HOST:
            raise ValueError("official court source mislabeled as reporting")
        sources[key] = s
    cases = {}
    for c in raw_cases:
        key = c.get("id")
        if key not in _TRIAL_DOCKETS or key in cases or c.get("trial_docket") != _TRIAL_DOCKETS.get(key):
            raise ValueError("invalid or merged trial docket")
        if any(c.get(field) is not False for field in (
                "original_judgment_pdf_read", "finality_certificate_verified",
                "original_2020_ppk_appointment_verified", "original_sd_order_matched")):
            raise ValueError("unverified original or finality")
        events = c.get("events")
        if not isinstance(events, list) or len(events) < 2:
            raise ValueError("case trajectory requires at least two attributed events")
        dates = []
        for ev in events:
            kind, source_id, docket = ev.get("kind"), ev.get("source_id"), ev.get("docket")
            if kind not in _EVENT_KINDS or source_id not in sources:
                raise ValueError("event/source not supported")
            event_date = date.fromisoformat(ev["date"])
            dates.append(event_date)
            if (ev.get("original_court_document_acquired") is not False
                    or ev.get("legal_finality_verified") is not False
                    or ev.get("universal_culpability_inferred") is not False):
                raise ValueError("event overclaims original document or guilt")
            official = sources[source_id]["class"] == "official_court_index"
            if kind == "appeal_directory_listing":
                if not official or docket != _APPEAL_DOCKETS.get(key):
                    raise ValueError("appeal docket/provenance mismatch")
            elif kind == "trial_directory_listing":
                if not official or docket != c["trial_docket"]:
                    raise ValueError("trial directory metadata mismatch")
                # The official index used in this milestone is APPELLATE only.
                raise ValueError("trial listing requires direct trial page source, not appeal index")
            else:
                if official:
                    raise ValueError("reported procedural update cannot impersonate official directory")
                if kind == "trial_judgment_reported":
                    if docket != c["trial_docket"]:
                        raise ValueError("wrong reported trial docket")
                elif docket is not None:
                    raise ValueError("unverified new appeal/cassation docket invented")
            if kind == "no_appeal_reported" and key != "case_sri":
                raise ValueError("no-appeal claim assigned to wrong defendant")
            if kind == "cassation_filing_reported" and key != "case_nadiem":
                raise ValueError("cassation report assigned to wrong defendant")
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            raise ValueError("event dates must be strictly ascending")
        ordered = [ev["kind"] for ev in events]
        baseline = "trial_judgment_reported"
        if ordered[0] != baseline:
            raise ValueError("initial trial report missing")
        if key == "case_nadiem" and ordered != [
                "trial_judgment_reported", "appeal_directory_listing", "cassation_filing_reported"]:
            raise ValueError("Nadiem procedural chain changed")
        if key == "case_ibam" and ordered != ["trial_judgment_reported", "appeal_directory_listing"]:
            raise ValueError("Ibam procedural chain changed")
        if key == "case_sri" and ordered != ["trial_judgment_reported", "no_appeal_reported"]:
            raise ValueError("Sri no-appeal report changed")
        cases[key] = c
    if set(cases) != set(_TRIAL_DOCKETS):
        raise ValueError("missing or merged case")
    opinions = bundle.get("external_opinions")
    if not isinstance(opinions, list) or len(opinions) != 1:
        raise ValueError("external legal evaluation must remain separate")
    for o in opinions:
        if (o.get("source_id") not in sources
                or sources[o["source_id"]]["class"] != "independent_legal_commentary"
                or o.get("case_id") != "case_nadiem"
                or o.get("not_court_holding") is not True
                or o.get("allegations_adjudicated") is not False
                or not isinstance(o.get("summary"), str) or len(o["summary"]) < 50):
            raise ValueError("academic commentary laundered into court ruling")
    return sources, cases


def evaluate(bundle):
    sources, cases = validate(bundle)
    def stage(c):
        last = c["events"][-1]["kind"]
        return {
            "cassation_filing_reported": "cassation_reported_pending_official_verification",
            "appeal_directory_listing": "appeal_judgment_indexed_no_cassation_status_established",
            "no_appeal_reported": "finality_reported_without_official_certificate",
        }[last]
    return {
        "schema": "legal_codex.case_posture_result.v1",
        "case_count": 3,
        "event_count": sum(len(c["events"]) for c in cases.values()),
        "official_appeal_index_entries": sum(
            e["kind"] == "appeal_directory_listing"
            for c in cases.values() for e in c["events"]),
        "case_trajectories": [
            {"id": c["id"], "trial_docket": c["trial_docket"],
             "posture": stage(c),
             "reported_events": [{
                 "kind": e["kind"], "event_date": e["date"], "docket": e["docket"],
                 "source_url": sources[e["source_id"]]["url"],
                 "source_class": sources[e["source_id"]]["class"],
                 "original_document_obtained": False,
             } for e in c["events"]],
             "legal_finality_certified": False, "signed_ppk_appointment_verified": False,
             "original_sd_purchase_order_verified": False}
            for c in sorted(cases.values(), key=lambda c: c["id"])
        ],
        "external_legal_opinions": [{
            "source_url": sources[o["source_id"]]["url"],
            "summary": o["summary"], "not_a_court_holding": True}
            for o in bundle["external_opinions"]],
        "certified_finality_count": 0,
        "original_court_pdf_count": 0,
        "authenticated_2020_ppk_appointments": 0,
        "matched_original_2020_sd_orders": 0,
        "cross_case_guilt_proved_by_posture": False,
        "publication_authorized": False,
    }


def semantic_packet(bundle):
    sources, cases = validate(bundle)
    nodes, edges = [], []
    for c in cases.values():
        for ix, ev in enumerate(c["events"]):
            ref = sources[ev["source_id"]]["url"]
            key = c["id"] + "-event-" + str(ix)
            nodes.append({
                "key": key, "kind": "observation", "layer": "neutral",
                "statement": f"Reported procedural stage {ev['kind']} for {c['trial_docket']}",
                "source_refs": [ref],
                "provenance": {
                    "source_class": sources[ev["source_id"]]["class"],
                    "original_document_acquired": False,
                    "legal_finality_certified": False, "cross_case_guilt_established": False}})
            if ix:
                edges.append({
                    "source": c["id"] + "-event-" + str(ix-1),
                    "target": key, "relation": "PRECEDES_REPORTED_CASE_EVENT",
                    "status": "candidate"})
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-case-posture-010", "clusters": [],
            "nodes": nodes, "edges": edges}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", default="legal_codex_case_posture_010_result.json")
    parser.add_argument("--packet")
    args = parser.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = evaluate(bundle)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(semantic_packet(bundle), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"case_count": out["case_count"], "appeal_index_entries": 2,
                      "original_judgments": 0, "certified_finality": 0}))


if __name__ == "__main__":
    main()
