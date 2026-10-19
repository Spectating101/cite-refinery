"""Explicitly authorized PRIVATE GitHub observation capture and local reviewed import."""
from __future__ import annotations
import argparse
import json
import os
import stat
import sys
from pathlib import Path
from uuid import uuid4

from .github_private_signals import collect_private, private_to_packet
from .github_signals import dependency_diff
from .hosted_store import WorkspaceDB, PermissionDenied, StateConflict, NotFound


def _read(path: Path, byte_limit: int) -> dict:
    if path.stat().st_size > byte_limit:
        raise ValueError("private input file too large")
    content=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content,dict):
        raise ValueError("private input file must be JSON object")
    return content


def _private_directory(db: WorkspaceDB) -> Path:
    dest=db.path.parent.resolve() / "private_github_snapshots"
    dest.mkdir(mode=0o700,exist_ok=True)
    if dest.is_symlink() or stat.S_IMODE(dest.stat().st_mode) != 0o700:
        raise PermissionDenied("private observation directory must be mode 0700")
    return dest


def _load_local(db: WorkspaceDB, name: str) -> dict:
    dest=_private_directory(db)
    path=Path(name)
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True).parent != dest:
        raise PermissionDenied("private snapshot must be a file inside local restricted directory")
    info=path.stat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600
            or info.st_uid != os.getuid()):
        raise PermissionDenied("private snapshot owner or mode invalid")
    return _read(path,900_000)


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(prog="cite-refinery-github-private")
    p.add_argument("--db",required=True)
    p.add_argument("--project",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--repo-root",required=True)
    p.add_argument("--token-env",default="CITE_REFINERY_TOKEN")
    sub=p.add_subparsers(dest="action",required=True)
    collect=sub.add_parser("collect")
    collect.add_argument("--repository",action="append",required=True,
                         help="Explicitly select an authorized private repo; repeat for others")
    for action in ("preview","enqueue"):
        cmd=sub.add_parser(action)
        cmd.add_argument("--snapshot",required=True)
        if action=="enqueue":
            cmd.add_argument("--expected-revision",type=int,required=True)
            cmd.add_argument("--expected-packet-digest",required=True)
    args=p.parse_args(argv)
    try:
        credential=os.environ.get(args.token_env)
        if not credential:
            raise PermissionDenied("private workspace credential required")
        db=WorkspaceDB(args.db)
        uid=db.authenticate(credential)
        # Authorized editor role is checked BEFORE source files or GitHub
        # endpoints. Viewers can view a project, not gather new private data.
        db.preview(uid,args.project,{"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"github_private_signals","clusters":[],"nodes":[],"edges":[]})
        project_state=db.project_state(uid,args.project)
        manifest=_read(Path(args.manifest),140_000)
        if manifest.get("schema")!="cite_refinery.repository_portfolio.v1":
            raise ValueError("explicit pinned portfolio manifest required")
        specs={rec["repository"]:rec for rec in manifest.get("repositories",[])}
        if len(specs)!=len(manifest.get("repositories",[])):
            raise ValueError("duplicate selected portfolio source")
        if args.action=="collect":
            selected=args.repository
            if len(selected)!=len(set(selected)) or len(selected)>8:
                raise ValueError("choose up to eight different private repositories")
            for slug in selected:
                if slug not in specs:
                    raise ValueError("requested private repo not in pinned portfolio manifest")
                matching=[
                    n for n in project_state.get("semantic_nodes",{}).values()
                    if n.get("project_id")==args.project and n.get("kind")=="repository"
                    and any(r.get("source_system")=="repository_portfolio"
                            and r.get("origin_verified") is True and r.get("repository")==slug
                            for r in n.get("provenance_receipts") or [])
                ]
                if len(matching)!=1:
                    raise ValueError("verified same-project Git identity required before collection")
                dependency_diff(args.repo_root,specs[slug])  # validate exact checked-out Git identity first
            snap=collect_private(selected)
            raw=json.dumps(snap,ensure_ascii=False,indent=2).encode("utf-8")
            if len(raw)>900_000:raise ValueError("private snapshot exceeds cap")
            folder=_private_directory(db)
            dest=folder/("private-github-"+uuid4().hex+".json")
            fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"wb") as fp:fp.write(raw)
            data={"status":"captured","path":str(dest),
                  "private_repositories":len(selected),"observed_at":snap["observed_at"],
                  "note":"restricted local metadata; do not commit or publish"}
        else:
            snap=_load_local(db,args.snapshot)
            packet=private_to_packet(snap,project_state=project_state,
                                      project_id=args.project,manifest=manifest,
                                      repo_root=args.repo_root)
            if args.action=="preview":
                data={"action":"preview_only","restricted_source":packet["conversion_metadata"],
                      "review":db.preview(uid,args.project,packet)}
            else:
                if args.expected_revision<0:raise ValueError("revision must be nonnegative")
                job=db.enqueue(uid,args.project,packet,
                               args.expected_revision,args.expected_packet_digest)
                data={"action":"enqueued","status":"queued","job_id":job}
        print(json.dumps(data,indent=2,ensure_ascii=False))
        return 0
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,NotFound,
            PermissionDenied,StateConflict) as exc:
        print("error: "+str(exc)[:180],file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
