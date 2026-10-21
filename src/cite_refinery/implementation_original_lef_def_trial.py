"""Second vetted original-source function replay: LEF/DEF layer-name parsing.

Pinned to a specific checked EDAgent GitHub source blob from the
44-repository balanced original-code inspection. No arbitrary source
execution, external binaries or real foundry designs. Local synthetic
text/DEF files only; no network or OS sandbox claim.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1,sha256
from pathlib import Path
import ast
import base64
import json
import os
import subprocess
import sys

from .implementation_original_code_audit import _get

SCHEMA="cite_refinery.original_lef_def_replay.v1"
AUDIT="cite_refinery.implementation_original_code_structure_audit.v1"
REPO="github:Mr-Fang-VLSI/EDAgent"
REVISION="18211ef80ae15c75e17100ed18890706f4245314"
PATH="skills/bspdn-physical-contract-auditor/references/scripts/scripts__debug__check_lef_layer_compatibility.py"
BLOB="17d4689a87890c80c92a71aaae51cc9c856d9e6d"
DIGEST="5f5b449584a86ceecf90330e412fab8f511771976238aad168a562dfcd332d78"
URL="https://api.github.com/repos/Mr-Fang-VLSI/EDAgent/git/blobs/"+BLOB
LIMIT=16000

# Expected outputs are predeclared independently of the upstream implementation.
# The adverse design-LEF comment case intentionally tests false reference matches.
FIXTURES=[
 {"id":"tech_three_layers","kind":"tech","input":"LAYER M1\nLAYER M2\nLAYER V1\n",
  "expected":["M1","M2","V1"]},
 {"id":"tech_leading_whitespace","kind":"tech","input":"   LAYER M3\n","expected":["M3"]},
 {"id":"tech_lowercase_keyword","kind":"tech","input":"layer M1\n","expected":[]},
 {"id":"tech_commented_keyword","kind":"tech","input":"# LAYER GHOST\n","expected":[]},
 {"id":"design_lef_single_reference","kind":"design","input":"PIN VDD\n  LAYER M1 ;\nEND VDD\n","expected":["M1"]},
 {"id":"design_lef_multiple_refs","kind":"design","input":"LAYER M1 ;\nLAYER V1 ;\n","expected":["M1","V1"]},
 {"id":"def_track_layer","kind":"def","input":"TRACKS X 0 DO 2 STEP 10 LAYER M2 ;\n","expected":["M2"]},
 {"id":"def_absent","kind":"def_none","input":"","expected":[]},
 {"id":"def_missing_file","kind":"def_missing","input":"","expected":[]},
 {"id":"style_m_v","kind":"style","input":["M1","V1"],"expected":"M/V"},
 {"id":"style_metal_via","kind":"style","input":["metal3","via2"],"expected":"metal/via"},
 {"id":"style_unknown","kind":"style","input":["routing","contact"],"expected":"unknown"},
 {"id":"cross_file_missing_m3","kind":"missing",
  "input":{"tech":"LAYER M1\nLAYER M2\n",
           "design":"PIN INPUT\n LAYER M1 ;\n LAYER M3 ;\n"},
  "expected":["M3"]},
 {"id":"design_comment_is_not_real_layer","kind":"design",
  "input":"# This is a comment: LAYER PHANTOM\nLAYER M1 ;\n",
  "expected":["M1"]},
 {"id":"design_duplicate_refs_collapsed","kind":"design",
  "input":"LAYER M1 ;\nLAYER M1 ;\n","expected":["M1"]},
 {"id":"def_commented_tracks_ignored","kind":"def",
  "input":"# TRACKS X 0 DO 3 STEP 10 LAYER PHANTOM ;\n","expected":[]},
]


def _sha(raw):return sha256(raw).hexdigest()
def _git_blob(raw):return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def fixture_sha256():
    return _sha(json.dumps(FIXTURES,sort_keys=True,separators=(",",":")).encode())


def check_reviewed_source(raw):
    if (not isinstance(raw,bytes) or len(raw)>LIMIT or
        _sha(raw)!=DIGEST or _git_blob(raw)!=BLOB):
        raise ValueError("EDA original bytes differ from independently reviewed source snapshot")
    tree=ast.parse(raw.decode("utf-8"),filename=PATH)
    imported=[]
    for row in tree.body:
        if isinstance(row,ast.Import):imported.extend(x.name for x in row.names)
        elif isinstance(row,ast.ImportFrom):imported.append(row.module)
        elif isinstance(row,(ast.Expr,ast.Assign,ast.AnnAssign,ast.FunctionDef,ast.ClassDef,ast.If)):
            pass
        else:raise ValueError("Unexpected top-level EDA source instruction")
    if sorted(imported)!=["argparse","pathlib","re","sys","typing"]:
        raise ValueError("EDA module import boundary changed")
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)) and node not in tree.body:
            raise ValueError("Late import in original EDA source")
        if isinstance(node,ast.Name) and node.id in {
            "eval","exec","open","__import__","subprocess","socket","ctypes",
            "pickle","requests","urllib","shutil"}:
            raise ValueError("Unexpected dynamic operation in checked EDA source")
    names={x.name for x in tree.body if isinstance(x,ast.FunctionDef)}
    if not {"parse_tech_layers","parse_lef_refs","parse_def_track_layers",
            "style_hint"} <= names:
        raise ValueError("Missing reviewed LEF/DEF parsing functions")
    return raw


def audit_row(audit):
    if audit.get("schema")!=AUDIT or not isinstance(audit.get("records"),list):
        raise ValueError("Original checked 44-repository source audit required")
    rows=[x for x in audit["records"] if x.get("repository_id")==REPO]
    if len(rows)!=1 or rows[0].get("pinned_commit")!=REVISION or (
        rows[0].get("status")!="source_files_sha_verified"
    ) or rows[0].get("source_code_executed") is not False or (
        rows[0].get("functionality_demonstrated") is not False
    ):
        raise ValueError("EDA source does not match pinned original snapshot")
    samples=[x for x in rows[0]["source_file_samples"] if x.get("path")==PATH]
    if (len(samples)!=1 or samples[0].get("blob_sha")!=BLOB or
        samples[0].get("body_sha256")!=DIGEST or
        samples[0].get("code_executed") is not False):
        raise ValueError("EDA source path or content fingerprint changed")
    return rows[0]


def fetch_original(audit,*,fetcher=_get,token=None):
    audit_row(audit)
    blob=fetcher(URL,token=token)
    if not isinstance(blob,dict) or blob.get("sha")!=BLOB or blob.get("encoding")!="base64":
        raise ValueError("Original EDA GitHub blob identity mismatch")
    try:raw=base64.b64decode(blob["content"])
    except (KeyError,TypeError,ValueError) as exc:raise ValueError("Malformed EDA blob transfer") from exc
    check_reviewed_source(raw)
    return raw


_CHILD=r'''
import json,sys,types,tempfile
from hashlib import sha1,sha256
from pathlib import Path

path,expected_sha,expected_git_blob=sys.argv[1:]
raw=Path(path).read_bytes()
if (sha256(raw).hexdigest()!=expected_sha or
    sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=expected_git_blob):
    raise ValueError("Pinned EDA original source changed since verification")
module=types.ModuleType("_original_lef_checker")
sys.modules[module.__name__]=module
exec(compile(raw,"pinned:"+path,"exec"),module.__dict__)
cases=json.loads(sys.stdin.read())
result=[]
with tempfile.TemporaryDirectory(prefix="refinery-original-lef-") as td:
    root=Path(td)
    for row in cases:
        try:
            kind=row["kind"]
            x=row["input"]
            f=root/"design.lef"
            f.write_text(x if isinstance(x,str) else "",encoding="utf-8")
            if kind=="tech":actual=sorted(module.parse_tech_layers(f))
            elif kind=="design":actual=sorted(module.parse_lef_refs([f]))
            elif kind=="def":actual=sorted(module.parse_def_track_layers(f))
            elif kind=="def_none":actual=sorted(module.parse_def_track_layers(None))
            elif kind=="def_missing":
                actual=sorted(module.parse_def_track_layers(root/"nonexistent.def"))
            elif kind=="style":actual=module.style_hint(set(x))
            elif kind=="missing":
                tech=root/"tech.lef";design=root/"other.lef"
                tech.write_text(x["tech"],encoding="utf-8")
                design.write_text(x["design"],encoding="utf-8")
                actual=sorted(module.parse_lef_refs([design])-
                              module.parse_tech_layers(tech))
            else:raise ValueError("Unexpected test fixture kind")
            status="pass" if actual==row["expected"] else "fail"
            result.append({"id":row["id"],"status":status,
                           "actual":actual,"expected":row["expected"]})
        except Exception as exc:
            result.append({"id":row["id"],"status":"error",
                           "exception_type":type(exc).__name__,
                           "expected":row["expected"]})
print(json.dumps({"cases":result},sort_keys=True))
'''


def replay(original_source,*,expected_fixture_sha256,timeout_seconds=10):
    raw=Path(original_source).read_bytes()
    check_reviewed_source(raw)
    if expected_fixture_sha256!=fixture_sha256():
        raise ValueError("Predeclared EDA test fixture hash mismatch")
    proc=subprocess.run(
        [sys.executable,"-I","-S","-c",_CHILD,str(Path(original_source).resolve()),
         DIGEST,BLOB],
        input=json.dumps(FIXTURES),text=True,capture_output=True,timeout=timeout_seconds,
        env={"PATH":os.defpath,"LANG":"C.UTF-8"},
        cwd=Path(original_source).parent,check=False)
    if proc.returncode or not proc.stdout.strip():
        raise ValueError("Original EDA parsing subprocess did not complete")
    try:payload=json.loads(proc.stdout)
    except ValueError as exc:raise ValueError("Malformed executable EDA result") from exc
    cases=payload.get("cases")
    if (not isinstance(cases,list) or len(cases)!=len(FIXTURES) or
        [x.get("id") for x in cases]!=[x["id"] for x in FIXTURES] or
        any(x.get("status") not in {"pass","fail","error"} for x in cases)):
        raise ValueError("Original EDA fixture result list incomplete")
    counts=dict(Counter(x["status"] for x in cases))
    return {
        "schema":SCHEMA,"original_repository":REPO,"original_commit":REVISION,
        "original_path":PATH,"original_blob_sha1":BLOB,
        "original_full_source_sha256":DIGEST,
        "preregistered_fixture_sha256":fixture_sha256(),
        "original_program_functions_executed":True,
        "test_scope":"synthetic_LEF_DEF_layer_name_parsing_and_classification_only",
        "execution_scope":"original_python_module_stripped_environment_not_OS_or_network_sandbox",
        "case_count":len(cases),"case_status_counts":counts,"cases":cases,
        "no_field_chip_design_verified":True,
        "no_real_foundry_or_PDK_validation":True,
        "real_automation_safety_not_established":True,
        "license_reuse_rights_not_cleared":True,
        "cross_layer_effectiveness_not_established":True,
        "operational_reuse_approved":False,
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    f=sub.add_parser("fetch");f.add_argument("--original-code-audit",required=True,type=Path)
    f.add_argument("--out-dir",required=True,type=Path)
    r=sub.add_parser("replay");r.add_argument("--source-dir",required=True,type=Path)
    r.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    if args.action=="fetch":
        if args.out_dir.exists():raise ValueError("Refusing to overwrite upstream EDA staging")
        if args.original_code_audit.stat().st_size>5_000_000:raise ValueError("Source audit oversized")
        raw=fetch_original(json.loads(args.original_code_audit.read_text()),
                           token=os.environ.get("GITHUB_TOKEN"))
        args.out_dir.mkdir(parents=True,exist_ok=False)
        (args.out_dir/"original.py").write_bytes(raw)
        (args.out_dir/"fixture_sha256.txt").write_text(fixture_sha256()+"\n")
        print(json.dumps({"source_sha256":DIGEST,"source_executed":False}))
        return 0
    if args.out.exists():raise ValueError("Refusing to overwrite actual EDA replay evidence")
    result=replay(args.source_dir/"original.py",
                  expected_fixture_sha256=(args.source_dir/"fixture_sha256.txt").read_text().strip())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"case_count":result["case_count"],
                      "case_status_counts":result["case_status_counts"],
                      "operational_reuse_approved":False}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
