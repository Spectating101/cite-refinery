"""Original-source metadata evidence gate for Atlas discovery candidates.

Provider-owned READMEs and abstracts are treated as *claims of functionality*.
No package downloads, imports, browser execution, API writes, or graph promotion.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from .discovery_capability_review import _hits, load_requirements, match_one
from .multi_source_discovery import _save

SCHEMA = "cite_refinery.original_source_gate.v1"
CONFIG_SCHEMA = "cite_refinery.original_source_gate_config.v1"
REPO = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
ARXIV = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$")
MAX_ORIGINAL = 65_536
MAX_GITHUB_README = 256 * 1024
MAX_CASES = 32
Fetch = Callable[[str], bytes]
GitHubRead = Callable[[str], dict[str, Any]]


class _Strip(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


class SourceUnverified(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(url: str) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in {"zenodo.org", "export.arxiv.org"}
            or parsed.port is not None or parsed.username or parsed.password):
        raise SourceUnverified("disallowed original metadata endpoint")
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"AtlasOriginalSourceReview/0.1"},
                                     method="GET")
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=12) as reply:
            if reply.status != 200:
                raise SourceUnverified("original metadata unavailable")
            data = reply.read(MAX_ORIGINAL + 1)
    except (OSError, ValueError) as ex:
        raise SourceUnverified("original_metadata_fetch:" + type(ex).__name__) from ex
    if len(data) > MAX_ORIGINAL:
        raise SourceUnverified("original metadata exceeds cap")
    return data


def _gh_readme(slug: str) -> dict[str, Any]:
    if not REPO.fullmatch(slug) or ".." in slug:
        raise SourceUnverified("invalid repository identity")
    try:
        p = subprocess.run(["gh", "api", "--method", "GET", f"repos/{slug}/readme"],
                           capture_output=True, timeout=16, check=False)
    except (OSError, subprocess.TimeoutExpired) as ex:
        raise SourceUnverified("readme_cli_unavailable") from ex
    if p.returncode or len(p.stdout) > 380_000:
        raise SourceUnverified("readme_missing_or_oversize")
    try:
        row = json.loads(p.stdout)
    except (ValueError, UnicodeDecodeError) as ex:
        raise SourceUnverified("invalid_github_readme") from ex
    if not isinstance(row, dict):
        raise SourceUnverified("invalid_github_payload")
    return row


def _clean_html(value: str) -> str:
    parser = _Strip()
    parser.feed(value)
    return " ".join(html.unescape(" ".join(parser.parts)).split())[:MAX_ORIGINAL]


def load_config(doc: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, dict) or doc.get("schema") != CONFIG_SCHEMA:
        raise ValueError("invalid evidence gate schema")
    raw = doc.get("gates")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        raise ValueError("invalid gate list")
    known = {r["id"] for r in load_requirements(doc["requirements"])}
    seen = set()
    gates = {}
    for row in raw:
        rid = row.get("requirement_id")
        if rid not in known or rid in seen:
            raise ValueError("gate not linked to distinct known requirement")
        groups = row.get("evidence_must_contain")
        if not isinstance(groups, list) or not 2 <= len(groups) <= 5:
            raise ValueError("require 2..5 source-specific evidence groups")
        vetted = []
        for terms in groups:
            if not isinstance(terms, list) or not 1 <= len(terms) <= 12:
                raise ValueError("invalid source-evidence terms")
            if any(not isinstance(t, str) or not re.fullmatch(r"[a-z0-9 _-]{2,70}", t) for t in terms):
                raise ValueError("invalid evidence search term")
            vetted.append(terms)
        seen.add(rid)
        gates[rid] = vetted
    lookup = doc.get("originals", {})
    if not isinstance(lookup, dict) or len(lookup) > 40:
        raise ValueError("invalid original-source lookup")
    for rid, url in lookup.items():
        if not isinstance(rid, str) or len(rid) > 240 or not isinstance(url, str):
            raise ValueError("invalid source override")
        # Overrides only select two *official* metadata sources.
        if not (re.fullmatch(r"https://zenodo.org/records/\d{1,12}", url)
                or re.fullmatch(r"https://arxiv.org/abs/\d{4}\.\d{4,5}(?:v\d+)?", url)):
            raise ValueError("original-source override must use official Zenodo or arXiv identity")
    return {"requirements":load_requirements(doc["requirements"]),
            "gates":gates, "originals":lookup}


def _resolve(record: dict[str, Any], originals: dict[str, str]) -> tuple[str, str]:
    rid, url = record.get("id"), originals.get(record.get("id")) or record.get("source_url")
    if not isinstance(url, str):
        raise SourceUnverified("no original source")
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.query or p.fragment or p.username or p.password:
        raise SourceUnverified("not a supported canonical original URL")
    if p.hostname == "github.com":
        slug = p.path.strip("/")
        if not REPO.fullmatch(slug) or ".." in slug:
            raise SourceUnverified("github URL not canonical repo root")
        # Never allow a redirect to an arbitrary endpoint or a cross-repo read.
        if record.get("entity_key") != "github:" + slug.casefold():
            raise SourceUnverified("GitHub URL identity differs from discovery record")
        return "github_readme", slug
    if p.hostname == "zenodo.org":
        matched = re.fullmatch(r"/records/(\d{1,12})", p.path)
        if matched:
            return "zenodo_record", matched.group(1)
    if p.hostname == "doi.org":
        matched = re.fullmatch(r"/10\.5281/zenodo\.(\d{1,12})", p.path, re.IGNORECASE)
        if matched:
            return "zenodo_record", matched.group(1)
    if p.hostname == "arxiv.org":
        matched = re.fullmatch(r"/abs/(\d{4}\.\d{4,5}(?:v\d+)?)", p.path)
        if matched:
            return "arxiv_metadata", matched.group(1)
    raise SourceUnverified("original source not directly supported or not mapped")


def original_receipt(record: dict[str, Any], *, originals: dict[str, str],
                     http: Fetch = _http, github: GitHubRead = _gh_readme) -> dict[str, Any]:
    kind, ident = _resolve(record, originals)
    observed = datetime.now(timezone.utc).isoformat()
    if kind == "github_readme":
        row = github(ident)
        if row.get("encoding") != "base64" or not SHA.fullmatch(str(row.get("sha") or "")):
            raise SourceUnverified("GitHub README encoding/blob identity invalid")
        try:
            data = base64.b64decode("".join(str(row.get("content") or "").split()), validate=True)
            text = data.decode("utf-8")
        except (ValueError, UnicodeDecodeError, TypeError) as ex:
            raise SourceUnverified("GitHub README data invalid") from ex
        if len(data) > MAX_GITHUB_README or not text.strip():
            raise SourceUnverified("GitHub README too large or empty")
        git_blob_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if git_blob_sha != row["sha"]:
            raise SourceUnverified("GitHub README SHA1 does not match response bytes")
        url = row.get("html_url")
        if not isinstance(url, str) or not url.startswith("https://github.com/" + ident + "/blob/"):
            raise SourceUnverified("GitHub README source URL is not original repository")
        return {"source_kind":kind, "source_url":url,
                "pinned_source_blob":row["sha"],"captured_at":observed,
                "sha256":hashlib.sha256(data).hexdigest(),"source_text":text[:MAX_ORIGINAL],
                "source_text_truncated":len(text)>MAX_ORIGINAL}
    if kind == "zenodo_record":
        data = http(f"https://zenodo.org/api/records/{ident}")
        try:
            row = json.loads(data)
        except (ValueError, UnicodeDecodeError) as ex:
            raise SourceUnverified("invalid Zenodo JSON") from ex
        if str(row.get("id")) != ident:
            raise SourceUnverified("Zenodo record ID mismatch")
        body = row.get("metadata") or {}
        text = _clean_html(str(body.get("title") or "") + " " + str(body.get("description") or ""))
        return {"source_kind":kind,"source_url":f"https://zenodo.org/records/{ident}",
                "pinned_source_blob":None,"captured_at":observed,
                "sha256":hashlib.sha256(data).hexdigest(),"source_text":text}
    if kind == "arxiv_metadata":
        data = http(f"https://export.arxiv.org/api/query?id_list={ident}")
        try:
            root = ET.fromstring(data)
        except ET.ParseError as ex:
            raise SourceUnverified("invalid arxiv Atom response") from ex
        ns="{http://www.w3.org/2005/Atom}"
        entries = root.findall(ns+"entry")
        if len(entries) != 1:
            raise SourceUnverified("arxiv metadata entry unavailable or ambiguous")
        entry = entries[0]
        ref = entry.findtext(ns+"id") or ""
        arxiv_url = urllib.parse.urlsplit(ref)
        if arxiv_url.scheme not in {"https", "http"} or arxiv_url.hostname != "arxiv.org" or not arxiv_url.path.startswith("/abs/"):
            raise SourceUnverified("arxiv entry not on official host")
        # Compare exact paper identifier even when Atom reports an explicit version.
        code = ref.rsplit("/",1)[-1].split("v",1)[0]
        if code != ident.split("v",1)[0]:
            raise SourceUnverified("arxiv paper identity mismatch")
        raw_title = entry.findtext(ns+"title") or ""
        summary = entry.findtext(ns+"summary") or ""
        return {"source_kind":kind,"source_url":f"https://arxiv.org/abs/{ident}",
                "pinned_source_blob":None,"captured_at":observed,
                "sha256":hashlib.sha256(data).hexdigest(),"source_text":" ".join((raw_title+" "+summary).split())}
    raise SourceUnverified("unknown original source kind")


def assess(record: dict[str, Any], requirement: dict[str, Any], groups: list[list[str]],
           *, originals: dict[str, str], http: Fetch = _http,
           github: GitHubRead = _gh_readme) -> dict[str, Any]:
    baseline = match_one(requirement, record)
    result = {"record_id":record["id"],"requirement_id":requirement["id"],
              "source_url":record["source_url"],
              "lexical_baseline": bool(baseline),
              "status":"ABSTAIN_ORIGINAL_UNAVAILABLE", "authority":"DOCUMENTATION_CLAIMS_ONLY"}
    if not baseline:
        return {**result,"status":"NOT_LEXICALLY_SHORTLISTED"}
    try:
        receipt = original_receipt(record, originals=originals,http=http,github=github)
    except (SourceUnverified, TypeError, KeyError) as ex:
        return {**result,"unavailable_reason":str(ex)[:90]}
    groups_found = [_hits(group, receipt["source_text"].casefold()) for group in groups]
    valid = all(groups_found)
    # A source index/directory can mention all capabilities without
    # implementing any; it is a discovery reference, not a tool.
    ref_slug = record.get("source_url","").lower().removeprefix("https://github.com/")
    is_list = (receipt["source_kind"]=="github_readme"
               and (ref_slug.split("/")[-1].startswith("awesome-")
                    or ref_slug.split("/")[-1].startswith("list-of-")))
    status = ("SOURCE_REFERENCE_LIST_ONLY" if is_list else
              "DOC_CLAIMS_MATCH" if valid else "DOC_MODALITY_NOT_ESTABLISHED")
    result.update({
        "status":status,
        "documentation_support":groups_found,
        "source_kind":receipt["source_kind"],
        "original_url":receipt["source_url"],
        "pinned_source_blob":receipt["pinned_source_blob"],
        "source_text_truncated":receipt.get("source_text_truncated",False),
        "captured_at":receipt["captured_at"],
        "original_sha256":receipt["sha256"],
        "note":"Matches in source-authored documentation/abstract, NOT tested code, full text verification, or independently established performance.",
    })
    return result


def run(collection: dict[str, Any], config: dict[str, Any],
        cases: list[dict[str,str]], *,http: Fetch = _http,
        github: GitHubRead = _gh_readme) -> dict[str, Any]:
    if not isinstance(collection, dict) or collection.get("schema") != "cite_refinery.multisource_discovery.v1":
        raise ValueError("invalid input discovery collection")
    config = load_config(config)
    records = {r["id"]:r for r in collection.get("records",[])}
    reqs = {r["id"]:r for r in config["requirements"]}
    if not isinstance(cases,list) or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError("1..32 evidence cases required")
    seen = set()
    results = []
    for case in cases:
        rid, reqid = case["record_id"], case["requirement_id"]
        if (rid,reqid) in seen or rid not in records or reqid not in config["gates"]:
            raise ValueError("duplicate, unknown record or unconfigured requirement")
        seen.add((rid,reqid))
        results.append(assess(records[rid], reqs[reqid], config["gates"][reqid],
                              originals=config["originals"],http=http,github=github))
    return {"schema":SCHEMA, "authority":"ORIGINAL_METADATA_GATE_NO_AUTOMATIC_ADOPTION",
            "cases":results, "reviewed":len(results),
            "counts":{status:sum(r["status"]==status for r in results)
                      for status in sorted(set(r["status"] for r in results))}}


def compare_labels(screen: dict[str,Any], labels: dict[str,Any]) -> dict[str, Any]:
    """Diagnostic comparison only, NEVER training or acceptance certification."""
    audit={(a["requirement_id"],a["record_id"]):a["decision"]
           for a in labels.get("cases",[])}
    tp=fp=tn=fn=unknown=0
    abstained=0
    for result in screen["cases"]:
        label=audit.get((result["requirement_id"],result["record_id"]))
        if label not in {"ON_SCOPE_BENCHMARK_LEAD","OFF_SCOPE","OFF_SCOPE_FOR_PLANT_TIME_SERIES"}:
            unknown+=1
            continue
        expected=label=="ON_SCOPE_BENCHMARK_LEAD"
        predicted=result["status"]=="DOC_CLAIMS_MATCH"
        if not predicted: abstained+=1
        if predicted and expected:tp+=1
        elif predicted and not expected:fp+=1
        elif not predicted and not expected:tn+=1
        else:fn+=1
    return {
        "schema":"cite_refinery.original_source_comparison.v1",
        "scope":"Nonrandom previously manually reviewed cases; descriptive diagnostic, not population accuracy",
        "true_positive":tp,"false_positive":fp,"true_negative_or_abstained":tn,
        "missed_positive_or_abstained":fn,"unknown_label":unknown,
        "precision_for_promoted_docs":round(tp/(tp+fp),4) if tp+fp else None,
        "coverage_of_known_positive_docs":round(tp/(tp+fn),4) if tp+fn else None,
        "no_auto_adoption":True,
    }


def main() -> None:
    cli=argparse.ArgumentParser(description="Source-author documentation gate for Atlas discovery")
    cli.add_argument("--collection",required=True)
    cli.add_argument("--config",required=True)
    cli.add_argument("--cases",required=True)
    cli.add_argument("--labels",help="optional human-reviewed diagnostic labels")
    cli.add_argument("--out",required=True)
    a=cli.parse_args()
    collection=json.loads(Path(a.collection).read_text(encoding="utf-8"))
    config=json.loads(Path(a.config).read_text(encoding="utf-8"))
    case_doc=json.loads(Path(a.cases).read_text(encoding="utf-8"))
    if case_doc.get("schema") != "cite_refinery.original_source_cases.v1":
        cli.error("unrecognized cases document")
    cases=case_doc["cases"]
    res=run(collection,config,cases)
    out=Path(a.out).expanduser().resolve()
    _save(out/"original_receipts.json",res)
    if a.labels:
        labels=json.loads(Path(a.labels).read_text(encoding="utf-8"))
        _save(out/"diagnostic_comparison.json",compare_labels(res,labels))
    print(json.dumps({"counts":res["counts"],"results":len(res["cases"]),"out":str(out)},indent=2))


if __name__=="__main__":
    main()
