"""Capture PUBLIC GitHub provider observations, then manually review private import."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .github_signals import SCHEMA, collect_public, signals_to_packet
from .hosted_store import WorkspaceDB, PermissionDenied, StateConflict, NotFound


def _load(path: str, limit: int) -> dict:
    f=Path(path)
    if f.stat().st_size > limit:
        raise ValueError("input JSON over byte limit")
    x=json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise ValueError("input document must be an object")
    return x


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="cite-refinery-github-signals")
    sub=p.add_subparsers(dest="action",required=True)
    collect=sub.add_parser("collect",help="Capture public GitHub endpoint observations")
    collect.add_argument("--manifest",required=True,help="Source-pinned repo portfolio manifest")
    collect.add_argument("--out",required=True,help="New local JSON output path, never overwrite")
    collect.add_argument("--repository", action="append", dest="repositories",
                         help="Explicitly selected PUBLIC repository, repeatable; must be in pinned manifest")
    for action in ("preview","enqueue"):
        cmd=sub.add_parser(action,help="Review or import source-observation packet")
        cmd.add_argument("--db",required=True)
        cmd.add_argument("--project",required=True)
        cmd.add_argument("--snapshot",required=True)
        cmd.add_argument("--manifest",required=True)
        cmd.add_argument("--repo-root",required=True)
        cmd.add_argument("--token-env",default="CITE_REFINERY_TOKEN")
        if action=="enqueue":
            cmd.add_argument("--expected-revision",type=int,required=True)
            cmd.add_argument("--expected-packet-digest",required=True)
    args=p.parse_args(argv)
    try:
        if args.action=="collect":
            manifest=_load(args.manifest, 140_000)
            if manifest.get("schema")!="cite_refinery.repository_portfolio.v1":
                raise ValueError("invalid repository source manifest")
            declared=[r["repository"] for r in manifest.get("repositories",[])]
            repos=args.repositories or declared
            if any(repo not in declared for repo in repos):
                raise ValueError("requested repository not found in pinned source manifest")
            captured=collect_public(repos)
            out=Path(args.out)
            if out.exists():
                raise ValueError("snapshot already exists: choose a new output file")
            out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            # Explicit private file permissions and O_EXCL to forbid overwrites.
            flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
            fd=os.open(out,flags,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(captured,f,ensure_ascii=False,indent=2)
            print(json.dumps({
                "status":"captured","schema":SCHEMA,
                "observed_at":captured["observed_at"],
                "repositories":repos,"output":str(out),
                "warning":"review provider data before importing; this is not a signed provider attestation",
            },ensure_ascii=False,indent=2))
            return 0
        credential=os.environ.get(args.token_env)
        if not credential:
            raise PermissionDenied("missing private operator credential")
        db=WorkspaceDB(args.db)
        uid=db.authenticate(credential)
        # Authorization is checked before reading source files or Git objects.
        db.preview(uid,args.project,{
            "schema":"cite_refinery.semantic_graph.v1",
            "source_system":"github_public_signals",
            "clusters":[],"nodes":[],"edges":[],
        })
        snapshot=_load(args.snapshot,1_000_000)
        manifest=_load(args.manifest,140_000)
        packet=signals_to_packet(
            snapshot,project_state=db.project_state(uid,args.project),
            project_id=args.project,manifest=manifest,repo_root=args.repo_root)
        if args.action=="preview":
            data={
                "action":"preview_only",
                "source_observations":packet["conversion_metadata"],
                "review":db.preview(uid,args.project,packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("expected revision must be nonnegative")
            job=db.enqueue(uid,args.project,packet,
                           args.expected_revision,args.expected_packet_digest)
            data={"action":"enqueued","job_id":job,"status":"queued"}
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,RuntimeError,TypeError,KeyError,
            PermissionDenied,StateConflict,NotFound) as exc:
        print("error: "+str(exc)[:200],file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
