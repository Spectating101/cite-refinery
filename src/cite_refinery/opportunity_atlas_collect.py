"""Bounded public GitHub discovery for broad opportunity atlas.

Uses GitHub's public repository search endpoint with fixed topic queries.
This yields *implementation listings* only, not verified capabilities,
market evidence, commercial underutilization or a target shortlist.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib.parse import urlencode

SCHEMA = "cite_refinery.opportunity_atlas_survey.v1"
OUT = "cite_refinery.opportunity_atlas_github_snapshot.v1"
TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{1,70}$")
AREA = re.compile(r"^[a-z][a-z0-9_]{2,50}$")


def validate_manifest(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict) or obj.get("schema") != SCHEMA:
        raise ValueError("bad opportunity atlas manifest")
    rows = obj.get("domains")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 60:
        raise ValueError("survey must have 1..60 independent topic strata")
    config = obj.get("collection")
    if not isinstance(config, dict):
        raise ValueError("collection definition required")
    if config.get("provider") != "GitHub search/repositories" or config.get("query_basis") != "topic" or config.get("commercial_inference") is not False:
        raise ValueError("only public topic metadata with no commercial inference permitted")
    per_domain = config.get("per_domain")
    if not isinstance(per_domain, int) or isinstance(per_domain, bool) or not 1 <= per_domain <= 50:
        raise ValueError("bounded per-domain sample required")
    segment = config.get("sample_segment","primary")
    if segment not in {"primary","recent_lower_visibility"}:
        raise ValueError("unknown atlas sample segment")
    if segment == "recent_lower_visibility" and config.get("sort") != "updated":
        raise ValueError("frontier sample must use updated sort")
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("domain must be an object")
        if not all(isinstance(item.get(k), str) for k in ("macro", "id", "github_topic", "query")):
            raise ValueError("missing domain fields")
        if not AREA.fullmatch(item["macro"]) or not AREA.fullmatch(item["id"]):
            raise ValueError("invalid macro or domain ID")
        if not TOPIC.fullmatch(item["github_topic"]):
            raise ValueError("invalid GitHub topic tag")
        if item["id"] in seen:
            raise ValueError("duplicate domain ID")
        seen.add(item["id"])
        expected = ("topic:" + item["github_topic"] +
                    (" stars:5..300 pushed:>2025-10-20" if segment=="recent_lower_visibility" else "")
                    + " fork:false archived:false")
        if item["query"] != expected or item.get("mode") != "public_repo_metadata_only":
            raise ValueError("unallowlisted GitHub search query or evidence mode")
    return obj


def normalize(manifest: dict[str, Any], raw_by_domain: dict[str, dict[str, Any]], *,
              observed_at: str) -> dict[str, Any]:
    validate_manifest(manifest)
    registry = {}
    observed_strata = []
    requested = manifest["collection"]["per_domain"]
    segment = manifest["collection"].get("sample_segment","primary")
    for d in manifest["domains"]:
        data = raw_by_domain.get(d["id"])
        if data is None:
            observed_strata.append({"id": d["id"], "macro": d["macro"],
                                     "query": d["query"], "status": "not_collected",
                                     "total_reported": None, "sampled": 0})
            continue
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            observed_strata.append({"id": d["id"], "macro": d["macro"],
                                     "query": d["query"], "status": "provider_error",
                                     "total_reported": None, "sampled": 0})
            continue
        items = data["items"][:requested]
        n=0
        for x in items:
            if not isinstance(x, dict) or x.get("private") is not False or x.get("fork") is not False or x.get("archived") is not False:
                continue
            name = x.get("full_name")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}",name):
                continue
            n+=1
            if name not in registry:
                license_meta = x.get("license")
                registry[name] = {
                    "id": "github:" + name,
                    "full_name": name, "url": "https://github.com/"+name,
                    "description": str(x.get("description") or "")[:600],
                    "language": str(x.get("language") or "")[:100],
                    "topics": [str(t)[:80] for t in (x.get("topics") or [])[:30]],
                    "license_api_label": str((license_meta or {}).get("spdx_id") or "not_detected"),
                    "stars": x.get("stargazers_count"),
                    "forks": x.get("forks_count"),
                    "open_issues": x.get("open_issues_count"),
                    "last_push": x.get("pushed_at"),
                    "created_at": x.get("created_at"),
                    "found_in": [],
                    "sample_segments": [segment],
                    "evidence_level": "public_repository_metadata_unverified",
                    "commercial_status": "unknown",
                    "buyer_demand": "unknown",
                    "implementation_impact": "unknown",
                    "license_review_complete": False,
                }
            if d["id"] not in registry[name]["found_in"]:
                registry[name]["found_in"].append(d["id"])
        observed_strata.append({
            "id": d["id"], "macro": d["macro"], "query": d["query"],
            "source_url": "https://github.com/search?" + urlencode({"q": d["query"], "type": "repositories"}),
            "status": "sampled" if isinstance(data.get("total_count"), int) else "provider_incomplete",
            "total_reported": data.get("total_count"),
            "sampled": n, "sample_segment": segment,
            "selection": ("GitHub most recently updated among active 5..300 star projects; not statistical sampling"
                          if segment=="recent_lower_visibility" else
                          "GitHub relevance-order first page; not statistical sampling"),
        })
    return {
        "schema": OUT, "observed_at": observed_at,
        "survey_definition": manifest.get("version"), "query_count": len(manifest["domains"]),
        "sample_segment": segment,
        "strata": observed_strata,
        "repositories": sorted(registry.values(), key=lambda x: x["full_name"].lower()),
        "source_family": "GitHub public repository metadata",
        "boundary": "Topic-constrained GitHub search is non-exhaustive and order-biased. Repo metadata is not source-code review, deployability, independent use, paying demand, license clearance, or evidence of underconversion.",
    }


def collect(manifest: dict[str, Any], *, per_query_pause_seconds: float = 2.4,
            runner: Any = None) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_manifest(manifest)
    if not 0 <= per_query_pause_seconds <= 30:
        raise ValueError("invalid API pacing")
    if runner is None:
        def runner(q: str, n: int) -> dict[str, Any]:
            args = ["gh", "api", "-X", "GET", "search/repositories", "-f", "q="+q,
                    "-f", "per_page="+str(n)]
            if manifest["collection"].get("sample_segment") == "recent_lower_visibility":
                args.extend(["-f","sort=updated","-f","order=desc"])
            process = subprocess.run(args,capture_output=True, timeout=40, check=False)
            if process.returncode != 0 or len(process.stdout) > 8_000_000:
                raise ValueError("GitHub search failed (including rate limit)")
            return json.loads(process.stdout)
    raw: dict[str, Any] = {}
    errors = {}
    for index, domain in enumerate(manifest["domains"]):
        try:
            raw[domain["id"]] = runner(domain["query"],manifest["collection"]["per_domain"])
            print(f"{index+1}/{len(manifest['domains'])} {domain['id']} hits="
                  f"{raw[domain['id']].get('total_count')} sampled="
                  f"{len(raw[domain['id']].get('items', []))}",flush=True)
        except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            errors[domain["id"]] = type(exc).__name__
            print(f"{index+1}/{len(manifest['domains'])} {domain['id']} unavailable {type(exc).__name__}",flush=True)
        if index + 1 < len(manifest["domains"]):
            time.sleep(per_query_pause_seconds)
    snapshot=normalize(manifest,raw,observed_at=datetime.now(timezone.utc).isoformat())
    snapshot["collection_errors"] = errors
    return snapshot, raw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cite-refinery-wide-scan")
    ap.add_argument("manifest",type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--pause",type=float,default=2.4)
    opts=ap.parse_args(argv)
    manifest=json.loads(opts.manifest.read_text(encoding="utf-8"))
    snapshot,_=collect(manifest,per_query_pause_seconds=opts.pause)
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Completed",len(snapshot["repositories"]),"unique repositories across",
          len(snapshot["strata"]),"strata, errors",len(snapshot["collection_errors"]),flush=True)
    return 0 if not snapshot["collection_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
