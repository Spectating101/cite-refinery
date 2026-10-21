"""First independently executed original-source function trial: vetted recon lexical rules.

Two-stage contract:
1. Fetch *only* an explicitly frozen GitHub blob verified in the 44-repository
   original source-tree audit. No remote code is run during fetching.
2. Replay its narrowly reviewed, standard-library-only Python module against
   preregistered synthetic fixtures, in a short-lived stripped-environment
   Python subprocess. **Not a security sandbox**; no general untrusted code.

The emitted receipt can prove a bounded test was run in that environment,
not full product correctness, security, deployment, adoption or legal reuse.
"""
from __future__ import annotations

from hashlib import sha1,sha256
from pathlib import Path
from collections import Counter
import ast
import base64
import json
import os
import re
import subprocess
import sys

from .implementation_original_code_audit import _get

SCHEMA="cite_refinery.original_function_replay.v1"
SOURCE_AUDIT="cite_refinery.implementation_original_code_structure_audit.v1"
SOURCE_REPO="github:blisspixel/recon"
PINNED_COMMIT="aad9746c29b5427263d7f7788373fcc85e7d4261"
SOURCE_PATH="src/recon_tool/lexical.py"
SOURCE_BLOB="c1a3dcaa8ea552ed508f89c05a9533f4aa7c4f54"
SOURCE_SHA256="d95915d73bde20b99d8e3d3cde93c45cf8809fbaf70a3fbd20093e50e64e5155"
MAX_BYTES=22_000
URL="https://api.github.com/repos/blisspixel/recon/git/blobs/"+SOURCE_BLOB
MODES={"env_exact","env_digit","env_namespaced","env_negative",
       "env_repeated_pattern","region_positive","region_false_positive",
       "region_repeated_pattern","tenant_pattern","non_tenant",
       "wildcard_dedup","multi_category","threshold_single",
       "threshold_multi","duplicate_not_multiple","region_boundary"}

# Frozen requirements chosen before replay. Expected values originate in this
# independent test design; they are NOT computed from the upstream program.
FIXTURES=[
    {"id":"env_exact","input":"dev","expected":"dev"},
    {"id":"env_digit","input":"dev01","expected":"dev"},
    {"id":"env_namespaced","input":"api-dev","expected":"dev"},
    {"id":"env_negative","input":"device","expected":None},
    {"id":"env_repeated_pattern","input":"x-devx-dev","expected":"dev"},
    {"id":"region_positive","input":"us-east-1","expected":"us-east"},
    {"id":"region_false_positive","input":"europe","expected":None},
    {"id":"region_repeated_pattern","input":"house1-use1","expected":"use1"},
    {"id":"tenant_pattern","input":"tenant-abc123","expected":True},
    {"id":"non_tenant","input":"api","expected":False},
    {"id":"wildcard_dedup","input":["dev.example.invalid","prod.example.invalid",
         "api.example.invalid","*.example.invalid","dev.example.invalid"],
         "expected":{"env":["dev","prod"],"region":[],"shard":[]}},
    {"id":"multi_category","input":["dev-eu-west-1.example.invalid"],
         "expected":{"env":["dev-eu-west-1"],"region":["dev-eu-west-1"],"shard":[]}},
    {"id":"threshold_single","input":["dev.example.invalid"],"expected":[]},
    {"id":"threshold_multi","input":["dev.example.invalid","prod.example.invalid"],
         "expected":[["Environment-like Labels",2,["dev","prod"]]]},
    {"id":"duplicate_not_multiple","input":["dev.example.invalid","dev.example.invalid"],
         "expected":[]},
    {"id":"region_boundary","input":"preuse1","expected":None},
]


def _hash(raw):
    return sha256(raw).hexdigest()


def _blob_hash(raw):
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _fixture_hash():
    return _hash(json.dumps(FIXTURES,sort_keys=True,separators=(",",":")).encode())


def _source_row(audit):
    if (audit.get("schema")!=SOURCE_AUDIT or
        not isinstance(audit.get("records"),list)):
        raise ValueError("Original source-tree source audit required")
    candidates=[x for x in audit["records"] if x.get("repository_id")==SOURCE_REPO]
    if len(candidates)!=1:
        raise ValueError("Exact pinned original software source not in source audit")
    row=candidates[0]
    if (row.get("status")!="source_files_sha_verified" or
        row.get("pinned_commit")!=PINNED_COMMIT or
        row.get("source_code_executed") is not False or
        row.get("functionality_demonstrated") is not False):
        raise ValueError("Unapproved or changed original source-tree identity")
    matched=[x for x in row.get("source_file_samples",[]) if x.get("path")==SOURCE_PATH]
    if (len(matched)!=1 or matched[0].get("blob_sha")!=SOURCE_BLOB or
        matched[0].get("body_sha256")!=SOURCE_SHA256 or
        matched[0].get("code_executed") is not False):
        raise ValueError("Original source blob fingerprint differs from reviewed profile")
    return row


def _check_code(raw):
    if (not isinstance(raw,bytes) or len(raw)>MAX_BYTES or
        _hash(raw)!=SOURCE_SHA256 or _blob_hash(raw)!=SOURCE_BLOB):
        raise ValueError("Upstream source bytes do not match reviewed pinned module")
    code=raw.decode("utf-8")
    tree=ast.parse(code,filename=SOURCE_PATH)
    imported=[]
    for n in tree.body:
        if isinstance(n,ast.Import):
            imported.extend(a.name for a in n.names)
        elif isinstance(n,ast.ImportFrom):
            imported.append(n.module)
        elif isinstance(n,(ast.Expr,ast.Assign,ast.AnnAssign,ast.FunctionDef,
                           ast.AsyncFunctionDef,ast.ClassDef)):
            pass
        else:
            raise ValueError("Unreviewed module-level execution statement")
    if sorted(imported)!=["__future__","dataclasses","re"]:
        raise ValueError("Original import surface has drifted from reviewed standard library")
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)) and n not in tree.body:
            raise ValueError("Unreviewed late import in original module")
        if isinstance(n,ast.Name) and n.id in {
            "eval","exec","open","__import__","breakpoint","compile","input",
            "subprocess","socket","os","sys","pathlib","pickle","ctypes"}:
            raise ValueError("Unexpected dangerous dynamic function in original source")
    funcs={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    if not {"_label_matches_env","_label_matches_region",
            "_label_matches_shard","classify_subdomains","lexical_observations"}<=funcs:
        raise ValueError("Pinned upstream no longer implements fixture functions")
    return code


def fetch_frozen_source(source_audit, *, fetcher=_get, token=None):
    """Read only a one-blob allowlisted original identity; never execute fetch."""
    _source_row(source_audit)
    payload=fetcher(URL,token=token)
    if (not isinstance(payload,dict) or payload.get("sha")!=SOURCE_BLOB
        or payload.get("encoding")!="base64"):
        raise ValueError("Upstream original Git blob identity mismatch")
    try:
        raw=base64.b64decode(payload["content"])
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("Unusable source blob transfer") from exc
    _check_code(raw)
    return raw


# Spawned interpreter has no inherited secrets and no site-packages. Pinning
# full source bytes and manual review are relied on; this is NOT OS isolation.
_CHILD=r'''
import json,sys,types,traceback
from pathlib import Path
from hashlib import sha256,sha1

path,expected_sha,expected_blob=sys.argv[1:]
raw=Path(path).read_bytes()
if (sha256(raw).hexdigest()!=expected_sha or
    sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=expected_blob):
    raise ValueError("Pinned source bytes changed after parent validation")
module=types.ModuleType("_reviewed_original_lexical")
sys.modules[module.__name__]=module
exec(compile(raw,"reviewed:"+path,"exec"),module.__dict__)
fixtures=json.loads(sys.stdin.read())
results=[]
for f in fixtures:
    try:
        mode=f["id"]
        x=f["input"]
        if mode.startswith("env_"):
            result=module._label_matches_env(x)
        elif mode.startswith("region_"):
            result=module._label_matches_region(x)
        elif mode in ("tenant_pattern","non_tenant"):
            result=bool(module._label_matches_shard(x))
        elif mode in ("wildcard_dedup","multi_category"):
            result=module.classify_subdomains(x,"example.invalid")
        else:
            result=[[o.category,o.match_count,list(o.sample_labels)]
                    for o in module.lexical_observations(x,"example.invalid")]
        status="pass" if result==f["expected"] else "fail"
        results.append({"id":mode,"status":status,
                        "actual":result,"expected":f["expected"]})
    except Exception as exc:
        results.append({"id":f["id"],"status":"error",
                        "exception_type":type(exc).__name__})
print(json.dumps({"cases":results},sort_keys=True))
'''


def replay_frozen_source(source_path, *, expected_fixture_hash=None,
                         timeout_seconds=10):
    raw=Path(source_path).read_bytes()
    _check_code(raw)
    if expected_fixture_hash is not None and expected_fixture_hash!=_fixture_hash():
        raise ValueError("Pre-registered fixture digest mismatch")
    command=[sys.executable,"-I","-S","-c",_CHILD,
             str(Path(source_path).resolve()),SOURCE_SHA256,SOURCE_BLOB]
    # Explicitly discard GitHub credentials and user environment variables.
    proc=subprocess.run(
        command,input=json.dumps(FIXTURES),text=True,capture_output=True,
        timeout=timeout_seconds,env={"PATH":os.defpath,"LANG":"C.UTF-8"},
        cwd=Path(source_path).parent,check=False)
    if proc.returncode or not proc.stdout.strip():
        raise ValueError("Pinned original source subprocess did not complete: "+str(proc.returncode))
    try:
        result=json.loads(proc.stdout)
    except ValueError as exc:
        raise ValueError("Original source execution receipt not valid JSON") from exc
    cases=result.get("cases")
    if (not isinstance(cases,list) or len(cases)!=len(FIXTURES) or
        [c.get("id") for c in cases]!=[c["id"] for c in FIXTURES] or
        any(c.get("status") not in {"pass","fail","error"} for c in cases)):
        raise ValueError("Original execution did not preserve full predeclared fixture set")
    count=dict(Counter(c["status"] for c in cases))
    return {
        "schema":SCHEMA,
        "trial_subject":SOURCE_REPO,
        "upstream_revision":PINNED_COMMIT,
        "source_path":SOURCE_PATH,
        "original_git_blob_sha1":SOURCE_BLOB,
        "source_bytes_sha256":SOURCE_SHA256,
        "predeclared_fixture_sha256":_fixture_hash(),
        "source_checked_at_full_file_and_git_blob":True,
        "original_upstream_python_executed":True,
        "execute_mode":"python_isolated_flags_i_and_s_stripped_environment_not_OS_sandbox",
        "independent_inputs_and_expected_outputs":True,
        "case_count":len(cases),"case_status_counts":count,"cases":cases,
        "all_preregistered_fixtures_pass":count.get("pass",0)==len(cases),
        "approved_general_reuse_or_promotion":False,
        "upstream_software_is_secure_or_safe":False,
        "demonstrated_field_effect_or_real_user_benefit":False,
        "independent_original_algorithm_correctness_proven":False,
        "license_reuse_rights_cleared":False,
        "broad_repository_quality_or_adoption_verified":False,
        "network_sandbox_isolation_proven":False,
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    fetch=sub.add_parser("fetch")
    fetch.add_argument("--original-code-audit",type=Path,required=True)
    fetch.add_argument("--out-dir",type=Path,required=True)
    replay=sub.add_parser("replay")
    replay.add_argument("--source-dir",type=Path,required=True)
    replay.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=="fetch":
        if args.out_dir.exists():
            raise ValueError("Refusing to overwrite original source staging directory")
        if args.original_code_audit.stat().st_size>5_000_000:
            raise ValueError("Original source audit exceeds 5 MB")
        audited=json.loads(args.original_code_audit.read_text())
        raw=fetch_frozen_source(audited,token=os.environ.get("GITHUB_TOKEN"))
        args.out_dir.mkdir(parents=True,exist_ok=False)
        (args.out_dir/"source.py").write_bytes(raw)
        (args.out_dir/"pre_registered_fixture_sha256.txt").write_text(_fixture_hash()+"\n")
        print(json.dumps({"source_sha256":SOURCE_SHA256,
                          "fixture_sha256":_fixture_hash(),
                          "original_code_executed":False}))
        return 0
    if args.out.exists():
        raise ValueError("Refusing to overwrite functional trial output")
    path=args.source_dir/"source.py"
    declared=(args.source_dir/"pre_registered_fixture_sha256.txt").read_text().strip()
    report=replay_frozen_source(path,expected_fixture_hash=declared)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"schema":SCHEMA,"case_count":report["case_count"],
                      "case_status_counts":report["case_status_counts"],
                      "all_preregistered_fixtures_pass":report["all_preregistered_fixtures_pass"],
                      "field_effect_proven":False}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
