"""Inspect original GitHub code/tree identity for selected *already pinned* leads.

Read-only. Does not execute upstream code, install dependencies, or grant rights.
Checks git commit->tree identity and git-blob SHA-1; imports no source code.
Only public GitHub API URLs built from validated repository slugs/revisions.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
from hashlib import sha1,sha256
from urllib.error import HTTPError,URLError
from urllib.parse import quote
from urllib.request import Request,urlopen
import ast
import base64
import json
import re

SCHEMA="cite_refinery.implementation_original_code_structure_audit.v1"
ORIGINAL="cite_refinery.implementation_original_source_audit.v1"
GITHUB="https://api.github.com/repos/"
SHA=re.compile(r"^[a-f0-9]{40}$")
SLUG=re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_HTTP_BYTES=3_000_000
FILE_CAP=28_000
SOURCE_EXT={".py": "python",".js": "javascript",".ts": "typescript",
            ".go": "go",".rs": "rust",".c": "c",".cpp": "cpp",
            ".java": "java",".sh": "shell",".yml": "yaml",".yaml": "yaml"}


class SourceUnavailable(Exception):
    pass


def _get(url, token=None):
    if not isinstance(url,str) or not url.startswith(GITHUB):
        raise ValueError("Only fixed original public GitHub repository endpoints permitted")
    headers={"Accept":"application/vnd.github+json",
             "User-Agent":"CiteRefinery-OriginalImplementationCodeAudit/1.0",
             "X-GitHub-Api-Version":"2022-11-28"}
    if token: headers["Authorization"]="Bearer "+token
    try:
        with urlopen(Request(url,headers=headers),timeout=18) as res:
            if not res.geturl().startswith(GITHUB):
                raise SourceUnavailable("external_redirect")
            data=res.read(MAX_HTTP_BYTES+1)
    except (HTTPError,URLError,TimeoutError,OSError) as exc:
        raise SourceUnavailable(type(exc).__name__) from exc
    if len(data)>MAX_HTTP_BYTES:
        raise SourceUnavailable("bounded_api_response_exceeded")
    try:
        return json.loads(data)
    except (ValueError,UnicodeError) as exc:
        raise SourceUnavailable("malformed_original_github_response") from exc


def _blob_matches(content,blob_sha):
    prefix=("blob "+str(len(content))+"\0").encode()
    return sha1(prefix+content).hexdigest()==blob_sha


def _path_kind(path):
    if not isinstance(path,str) or not path or "\x00" in path:
        return None
    suffix="."+path.rsplit(".",1)[-1].lower() if "." in path else ""
    return SOURCE_EXT.get(suffix)


def _choose_paths(entries):
    eligible=[]
    for item in entries:
        path=item.get("path")
        if (item.get("type")!="blob" or item.get("size",0)>FILE_CAP or
            not isinstance(path,str) or len(path)>320 or
            not isinstance(item.get("sha"),str) or not SHA.fullmatch(item["sha"])):
            continue
        lang=_path_kind(path)
        if not lang: continue
        p=path.lower()
        if any(t in p.split("/") for t in (".git","node_modules","vendor","dist","target","build",
                                           "third_party",".venv","site-packages","assets")):
            continue
        rank=(0 if lang=="python" else 1,
              0 if any(x in p.split("/") for x in ("src","lib","app","pkg","floodsystem")) else 1,
              0 if p.startswith(("src/","lib/","app/","pkg/")) else 1,
              sha256(p.encode()).hexdigest())
        if (p.rsplit("/",1)[-1].startswith("test_") or "/tests/" in p or
            p.startswith("tests/") or p.endswith("_test.py")):
            rank=(3,rank[1],rank[2],rank[3])
        eligible.append((rank,item,lang))
    eligible.sort(key=lambda row:row[0])
    # One implementation file + one test, where present. Do not pick two
    # easy-success samples from one project; failures remain in results.
    source=next((x for x in eligible if x[0][0]<3),None)
    test=next((x for x in eligible if x[0][0]==3),None)
    return [x for x in (source,test) if x is not None]


def _sample(blob, item, language):
    sha=item["sha"]
    if not isinstance(blob,dict) or blob.get("sha")!=sha:
        raise SourceUnavailable("source_blob_identity_mismatch")
    if blob.get("encoding")!="base64" or not isinstance(blob.get("content"),str):
        raise SourceUnavailable("source_blob_encoding_not_supported")
    try:
        payload=base64.b64decode(blob["content"],validate=False)
    except (ValueError,TypeError) as exc:
        raise SourceUnavailable("original_blob_not_base64") from exc
    if len(payload)>FILE_CAP or not _blob_matches(payload,sha):
        raise SourceUnavailable("original_blob_sha1_or_size_mismatch")
    item_report={
        "path":item["path"],"blob_sha":sha,
        "body_sha256":sha256(payload).hexdigest(),
        "body_bytes":len(payload),"source_language":language,
        "code_executed":False,"dependency_installation_attempted":False,
        "structural_function_names_not_a_behavioral_test":[],
    }
    if language=="python":
        try:
            tree=ast.parse(payload.decode("utf-8"))
            # AST parsing is syntax inspection, not import or execution.
            symbols=[(node.name,node.lineno) for node in tree.body
                     if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
            item_report["python_ast_syntax_parsed_only"]=True
            item_report["structural_function_names_not_a_behavioral_test"]=[
                {"name":name,"line":lineno} for name,lineno in symbols[:25]]
        except (SyntaxError,UnicodeError,ValueError):
            item_report["python_ast_syntax_parsed_only"]=False
    return item_report


def audit_original_code(original_audit, *, fetcher=_get, token=None,
                        max_repositories=8):
    if (original_audit.get("schema")!=ORIGINAL or
        not isinstance(max_repositories,int) or
        not 1<=max_repositories<=30 or
        not isinstance(original_audit.get("records"),list) or
        original_audit.get("selected_category_pairs")!=len(original_audit["records"])):
        raise ValueError("Expected bounded original source-pinned review receipt")
    allowed=[]
    indexed={}
    for row in original_audit["records"]:
        rid=row.get("repository_id")
        snap=row.get("original_source_snapshot",{})
        if not isinstance(rid,str) or not rid.startswith("github:"):
            raise ValueError("Unknown original repository ID")
        slug=rid[len("github:"):]
        if not SLUG.fullmatch(slug) or row.get("source_original_url")!=(
            "https://github.com/"+slug):
            raise ValueError("Unsafe or contradicted original GitHub identity")
        if snap.get("status")!="original_source_metadata_checked":
            continue
        commit=snap.get("source_commit")
        if not isinstance(commit,str) or not SHA.fullmatch(commit):
            raise ValueError("Pinned original source commit missing")
        if rid in indexed and indexed[rid]!=commit:
            raise ValueError("Original repository has conflicting source revisions")
        indexed[rid]=commit
        if rid not in allowed: allowed.append(rid)
    # Deterministic sampling without preferentially selecting "successful" code.
    allowed.sort(key=lambda rid:sha256(rid.encode()).hexdigest())
    records=[]
    for rid in allowed[:max_repositories]:
        slug=rid.removeprefix("github:")
        commit=indexed[rid]
        result={
            "repository_id":rid,"original_repository_url":"https://github.com/"+slug,
            "pinned_commit":commit,"status":"unavailable_or_inconclusive",
            "source_code_executed":False,"functionality_demonstrated":False,
            "license_reuse_rights_cleared":False,"observed_end_user_adoption":False,
            "source_tree_is_not_complete_quality_review":True,
        }
        try:
            root=GITHUB+slug+"/git/"
            git_commit=fetcher(root+"commits/"+commit,token=token)
            if git_commit.get("sha")!=commit:
                raise SourceUnavailable("pinned_commit_api_identity_mismatch")
            tree_sha=(git_commit.get("tree") or {}).get("sha")
            if not isinstance(tree_sha,str) or not SHA.fullmatch(tree_sha):
                raise SourceUnavailable("commit_tree_digest_unavailable")
            tree=fetcher(root+"trees/"+tree_sha+"?recursive=1",token=token)
            if tree.get("sha")!=tree_sha:
                raise SourceUnavailable("original_tree_identity_mismatch")
            if tree.get("truncated") is not False or not isinstance(tree.get("tree"),list):
                result.update(status="tree_truncated_or_unusable",tree_sha=tree_sha)
                records.append(result)
                continue
            entries=tree["tree"]
            result.update(tree_sha=tree_sha,tree_entry_count=len(entries),
                          python_files_observed=sum(
                              x.get("path","").endswith(".py") and x.get("type")=="blob"
                              for x in entries),
                          test_files_observed=sum(
                              x.get("type")=="blob" and
                              (x.get("path","").startswith("tests/") or
                               "/tests/" in x.get("path","") or
                               x.get("path","").rsplit("/",1)[-1].startswith("test_"))
                              for x in entries),
                          source_layout_hints=sorted({x.get("path","").split("/")[0]
                                                     for x in entries if x.get("path")})[:35])
            targets=_choose_paths(entries)
            if not targets:
                result["status"]="source_snapshot_has_no_eligible_code"
            else:
                samples=[]
                for _,entry,language in targets:
                    blob=fetcher(root+"blobs/"+entry["sha"],token=token)
                    samples.append(_sample(blob,entry,language))
                result.update(
                    status="source_files_sha_verified",
                    source_file_samples=samples,
                    source_language_sampled=sorted({x["source_language"] for x in samples}),
                )
        except (SourceUnavailable,KeyError,ValueError,TypeError) as exc:
            result["status"]="unavailable_or_inconclusive"
            result["error_type"]=type(exc).__name__
        records.append(result)
    return {
        "schema":SCHEMA,
        "observed_at_utc":datetime.now(timezone.utc).isoformat(),
        "population":"previously_source_pinned_GitHub_sample_only",
        "source_selection":"stable_sha256_original_repo_ID_not_stars_or_success",
        "previously_checked_distinct_source_repositories":len(allowed),
        "sampled_repositories":len(records),
        "source_file_inspection_successes":sum(
            r["status"]=="source_files_sha_verified" for r in records),
        "python_syntax_not_execution":True,
        "original_source_text_not_redistributed":True,
        "execution_attempts":0,"live_field_trials":0,
        "license_rights_verified":0,"end_user_adoption_verified":0,
        "records":records,
    }
