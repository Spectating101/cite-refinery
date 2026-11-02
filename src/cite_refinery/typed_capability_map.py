"""Typed candidate capability map from inspected *original-source* documentation.

All edges describe source-authored claims, NOT tested implementations.
No external code is imported or executed; output is local, append-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from .source_evidence_gate import SourceUnverified, original_receipt
from .multi_source_discovery import _save

SCHEMA = "cite_refinery.typed_capability_map.v1"
RULES = "cite_refinery.typed_capability_rules.v1"
NEEDS = "cite_refinery.typed_capability_needs.v1"
COLLECTION = "cite_refinery.multisource_discovery.v1"
CASES = "cite_refinery.typed_trial_cases.v1"
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,64}$")
TERM_RE = re.compile(r"^[a-z0-9 _/-]{2,72}$")
DOMAINS = {"software", "research", "datasets", "models"}
STATES = {"IMPLEMENTATION_CLAIM", "DATASET_DESCRIPTION", "RESEARCH_METHOD_DESCRIPTION", "REFERENCE_DIRECTORY"}
STATUS = {"CANDIDATE_DOCUMENTED_MATCH", "NO_DOCUMENTARY_MATCH", "SOURCE_UNAVAILABLE", "DISCOVERY_INDEX_ONLY"}
MAX_CASES = 30
MAX_WINDOW = 1000


def _phrase(term: str, text: str) -> bool:
    needle = re.escape(term.casefold()).replace(r"\ ", r"\s+")
    return bool(re.search(r"(?<![a-z0-9])" + needle, text.casefold()))


def read_rules(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(doc, dict) or doc.get("schema") != RULES:
        raise ValueError("incorrect typed rulebook schema")
    rows = doc.get("capabilities")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("bounded capability rulebook required")
    ids = set()
    result = []
    for r in rows:
        if not isinstance(r, dict) or not isinstance(r.get("id"), str) or not ID_RE.fullmatch(r["id"]) or r["id"] in ids:
            raise ValueError("bad duplicate capability id")
        if r.get("kind") not in STATES or r.get("source_category") not in DOMAINS:
            raise ValueError("invalid capability kind or source category")
        groups = r.get("must_evidence")
        if not isinstance(groups, list) or not 2 <= len(groups) <= 5:
            raise ValueError("need 2..5 evidence concept groups")
        checked = []
        for group in groups:
            if not isinstance(group, list) or not group or len(group) > 10 or any(
                not isinstance(t, str) or not TERM_RE.fullmatch(t) for t in group
            ):
                raise ValueError("bad typed evidence terms")
            checked.append(group)
        for k in ("input", "output", "description"):
            if not isinstance(r.get(k), str) or not r[k].strip() or len(r[k]) > 220:
                raise ValueError("missing capability interface description")
        ids.add(r["id"])
        result.append({"id":r["id"], "kind":r["kind"], "source_category":r["source_category"],
                       "description":r["description"],"input":r["input"],"output":r["output"],
                       "must_evidence":checked})
    return result


def read_needs(doc: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(doc, dict) or doc.get("schema") != NEEDS:
        raise ValueError("wrong capability-needs schema")
    rows = doc.get("needs")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 15:
        raise ValueError("needs must have 1..15 entries")
    ids = set()
    output = []
    for r in rows:
        if not isinstance(r, dict) or not isinstance(r.get("id"), str) or not ID_RE.fullmatch(r["id"]) or r["id"] in ids:
            raise ValueError("invalid/duplicate need id")
        targets = r.get("capability_ids")
        if not isinstance(targets, list) or not targets or len(targets) > 8 or any(v not in valid_ids for v in targets):
            raise ValueError("need references unknown capabilities")
        if not isinstance(r.get("project"), str) or not ID_RE.fullmatch(r["project"]):
            raise ValueError("bad project")
        if not isinstance(r.get("requirement"), str) or not r["requirement"] or len(r["requirement"]) > 300:
            raise ValueError("bad requirement text")
        ids.add(r["id"])
        output.append({k:r[k] for k in ("id","project","requirement","capability_ids")})
    return output


def windows(text: str, size: int = MAX_WINDOW) -> list[tuple[int,str]]:
    """Overlapping bounded excerpts; full doc never becomes a bag of unrelated links."""
    # Prefer text chunks with overlap; a rule cannot pull independent
    # keywords from arbitrarily distant README sections.
    if not isinstance(text, str):
        return []
    return [(start,text[start:start+size]) for start in range(0,len(text),size//2)]


def classify_original(receipt: dict[str,Any], capability: dict[str,Any],
                      *, source_category: str) -> dict[str,Any] | None:
    if capability["source_category"] != source_category:
        return None
    text = receipt["source_text"]
    for offset,chunk in windows(text):
        found = [[t for t in group if _phrase(t,chunk)] for group in capability["must_evidence"]]
        if not all(found):
            continue
        # Center the excerpt on matched claims rather than README badges.
        # Match can still be semantically wrong; source review is compulsory.
        first_term = found[0][0]
        position = re.search(r"(?<![a-z0-9])" + re.escape(first_term).replace(r"\ ", r"\s+"), chunk.casefold())
        center = position.start() if position else 0
        local_start = max(0,center-85)
        snippet = " ".join(chunk[local_start:local_start+440].split())[:340]
        return {"capability_id":capability["id"], "kind":capability["kind"],
                "description":capability["description"],"input":capability["input"],
                "output":capability["output"],"matched_terms":found,
                "evidence":{"source_url":receipt["source_url"],
                            "source_kind":receipt["source_kind"],
                            "sha256":receipt["sha256"],"pinned_source_blob":receipt["pinned_source_blob"],
                            "excerpt_offset":offset+local_start,
                            "excerpt":snippet,
                            "source_text_truncated":receipt.get("source_text_truncated",False)},
                "authority":"SOURCE_AUTHORED_DESCRIPTION_ONLY"}
    return None


def compile_map(collection: dict[str,Any],rulebook: dict[str,Any],needs: dict[str,Any],
                cases: dict[str,Any],*,http: Callable | None = None,
                github: Callable | None = None) -> dict[str,Any]:
    if collection.get("schema") != COLLECTION or not isinstance(collection.get("records"),list):
        raise ValueError("invalid discovery collection")
    if cases.get("schema") != CASES or not isinstance(cases.get("cases"),list) or not 1 <= len(cases["cases"]) <= MAX_CASES:
        raise ValueError("invalid bounded typed trial cases")
    rules = read_rules(rulebook)
    reqs = read_needs(needs, {r["id"] for r in rules})
    originals = cases.get("originals",{})
    if not isinstance(originals,dict) or len(originals)>MAX_CASES:
        raise ValueError("invalid original source mapping")
    # The source gate independently applies strict official host and identity guards.
    # Prevent caller-supplied original links from being used as arbitrary web targets.
    from .source_evidence_gate import load_config, CONFIG_SCHEMA
    load_config({"schema":CONFIG_SCHEMA,
                 "requirements":{"schema":"cite_refinery.discovery_requirements.v1",
                     "requirements":[{"id":"typed_ref","project":"atlas","question":"Typed source evidence",
                       "must_match":[["source"],["evidence"]],"bonus":["source"],
                       "allow_source_types":["software","research","datasets"]}]},
                 "gates":[{"requirement_id":"typed_ref","evidence_must_contain":[["source"],["evidence"]]}],
                 "originals":originals})
    record_by_id={r["id"]:r for r in collection["records"]}
    entries=[]
    for case in cases["cases"]:
        rid=case.get("record_id") if isinstance(case,dict) else None
        if not isinstance(rid,str) or rid not in record_by_id or any(x["record_id"]==rid for x in entries):
            raise ValueError("duplicate or unknown record in case selection")
        row=record_by_id[rid]
        entry={"record_id":rid,"title":row["title"],"discovery_source":row["source_url"],
               "status":"SOURCE_UNAVAILABLE","capabilities":[]}
        try:
            keywords=(http is not None, github is not None)
            opts={"originals":originals}
            if http is not None: opts["http"]=http
            if github is not None: opts["github"]=github
            doc=original_receipt(row,**opts)
            entry["original_source"]=doc["source_url"]
            entry["original_sha256"]=doc["sha256"]
            category=row["observation_type"]
            slug=str(row["source_url"]).lower().split("/")[-1]
            index_only=(category=="software" and (slug.startswith("awesome-") or slug.startswith("list-of-")))
            if index_only:
                entry["status"]="DISCOVERY_INDEX_ONLY"
            else:
                claimed=[c for r in rules if (c:=classify_original(doc,r,source_category=category))]
                entry.update(capabilities=claimed,
                            status="CANDIDATE_DOCUMENTED_MATCH" if claimed else "NO_DOCUMENTARY_MATCH")
            entry["source_text_truncated"]=doc.get("source_text_truncated",False)
        except (SourceUnverified,TypeError,KeyError,ValueError) as ex:
            entry["unavailable_reason"]=str(ex)[:100]
        entries.append(entry)
    edges=[]
    for entry in entries:
        if entry["status"]!="CANDIDATE_DOCUMENTED_MATCH":
            continue
        for cap in entry["capabilities"]:
            for need in reqs:
                if cap["capability_id"] in need["capability_ids"]:
                    edges.append({"from_record_id":entry["record_id"],
                                  "candidate_capability_id":cap["capability_id"],
                                  "to_requirement":need["id"],"project":need["project"],
                                  "relation":"MAY_SUPPORT_REQUIREMENT_REVIEW_ONLY",
                                  "observed_doc_sha256":cap["evidence"]["sha256"],
                                  "authority":"NO_CODE_EXECUTION_NO_ADOPTION"})
    observed={edge["candidate_capability_id"] for edge in edges}
    return {"schema":SCHEMA,"authority":"READ_ONLY_DOCUMENTATION_CANDIDATES",
            "capability_types":rules,"project_needs":reqs,"sources":entries,
            "candidate_edges":edges,
            "unfilled_requirement_capabilities":[{"need":need["id"],
                "capabilities_not_documented_in_selected_sample":[c for c in need["capability_ids"] if c not in observed]}
                for need in reqs],
            "limitations":["Evidence from project-authored READMEs and abstracts only, not tested interfaces.",
                           "Typed match does not prove functionality, scientific transfer or suitability.",
                           "No edge is authorized for merger into a verified graph.",
                           "Absence in this tiny selected sample does not imply technology is unavailable."]}


def main() -> None:
    p=argparse.ArgumentParser(description="Atlas documentation-grounded typed capability mapping")
    p.add_argument("--collection",required=True)
    p.add_argument("--rules",required=True)
    p.add_argument("--needs",required=True)
    p.add_argument("--cases",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    objs=[json.loads(Path(x).read_text()) for x in (args.collection,args.rules,args.needs,args.cases)]
    result=compile_map(*objs)
    dest=Path(args.out).expanduser().resolve()
    _save(dest/"typed_capability_map.json",result)
    print(json.dumps({"sources":len(result["sources"]),"typed_edges":len(result["candidate_edges"]),
       "typed_capabilities_documented":{a["record_id"]:[c["capability_id"] for c in a["capabilities"]] for a in result["sources"] if a["capabilities"]},
       "statuses":{s:sum(z["status"]==s for z in result["sources"]) for s in sorted(STATUS)},
       "output":str(dest)},indent=2))


if __name__=="__main__":
    main()
