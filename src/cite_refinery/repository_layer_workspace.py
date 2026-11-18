"""Immutable repository-only catalogues attached to existing workspace projects."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import quote

from .repository_layer import validate_repository_layer
from .store import JsonStore


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _project(state: dict, project_id: str) -> dict:
    if not isinstance(project_id, str) or not project_id or project_id not in state.get("projects", {}):
        raise KeyError("unknown project")
    project = state["projects"][project_id]
    if not isinstance(project, dict):
        raise ValueError("invalid workspace project")
    return project


def _validate(catalog: Any) -> None:
    if not isinstance(catalog, dict):
        raise ValueError("repository catalogue must be a JSON object")
    try:
        validate_repository_layer(catalog)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("malformed repository catalogue") from exc


def _artifact_path(store: JsonStore, project_id: str, digest: str, relative_path: str | None = None) -> tuple[Path, str]:
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError("invalid repository catalogue digest")
    project_hash = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
    expected = Path("repository_layers") / project_hash / (digest + ".json")
    # Require the exact content-addressed path, not just membership in a shared
    # directory. A valid artifact from a different project is not interchangeable.
    if relative_path is not None and relative_path != expected.as_posix():
        raise ValueError("repository layer path does not belong to this project and digest")
    workspace = store.workspace.resolve()
    root = workspace / "repository_layers"
    path = workspace / expected
    if root.is_symlink() or path.parent.is_symlink() or path.is_symlink():
        raise ValueError("repository layer artifacts must not use symbolic links")
    if not path.resolve().is_relative_to(root):
        raise ValueError("repository layer path escapes its artifact directory")
    return path, expected.as_posix()


def _read_artifact(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError("saved repository layer artifact is unavailable") from exc


def save_repository_layer(store: JsonStore, project_id: str, catalog: dict) -> dict:
    """Save a validated snapshot without changing its project or creating a problem.

    The snapshot file is never overwritten. Saving a newer catalogue only moves
    the project's state pointer, leaving earlier content-addressed files intact.
    """
    state = store.load()
    _project(state, project_id)
    _validate(catalog)
    body = (json.dumps(catalog, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    digest = catalog["catalog_digest"]
    path, relative_path = _artifact_path(store, project_id, digest)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # A completed temporary file is linked into place exclusively; an existing
    # immutable file is verified rather than overwritten, including on retries.
    fd, temporary = tempfile.mkstemp(prefix="catalog-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            _artifact_path(store, project_id, digest)
            if _read_artifact(path) != body:
                raise ValueError("immutable repository catalogue already exists with different bytes")
    finally:
        os.unlink(temporary)
    receipt = {
        "relative_path": relative_path,
        "catalog_digest": digest,
        "sha256": hashlib.sha256(body).hexdigest(),
        "coverage": deepcopy(catalog["coverage"]),
    }
    # Reload before updating the pointer to preserve changes made while the
    # relatively large snapshot was being serialized and written.
    state = store.load()
    _project(state, project_id)
    layers = state.setdefault("repository_layers", {})
    if not isinstance(layers, dict):
        raise ValueError("invalid repository layer registry")
    layers[project_id] = receipt
    store.save(state)
    return deepcopy(receipt)


def load_repository_layer(store: JsonStore, project_id: str) -> dict:
    """Load only a project-bound artifact whose file and catalogue hashes agree."""
    state = store.load()
    _project(state, project_id)
    layers = state.get("repository_layers", {})
    if not isinstance(layers, dict):
        raise ValueError("invalid repository layer registry")
    if project_id not in layers:
        raise KeyError("project has no saved repository layer")
    receipt = layers[project_id]
    if not isinstance(receipt, dict) or not isinstance(receipt.get("relative_path"), str):
        raise ValueError("invalid repository layer receipt")
    path, _ = _artifact_path(store, project_id, receipt.get("catalog_digest"), receipt["relative_path"])
    body = _read_artifact(path)
    if hashlib.sha256(body).hexdigest() != receipt.get("sha256"):
        raise ValueError("saved repository layer file SHA-256 mismatch")
    try:
        catalog = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("saved repository layer is not valid JSON") from exc
    _validate(catalog)
    if catalog["catalog_digest"] != receipt["catalog_digest"]:
        raise ValueError("saved repository layer catalogue digest differs from its receipt")
    if catalog["coverage"] != receipt.get("coverage"):
        raise ValueError("saved repository layer coverage differs from its receipt")
    return catalog


def render_repository_layer_index(store: JsonStore) -> str:
    """Small, escaped navigation page for independently saved repository layers."""
    state = store.load()
    layers = state.get("repository_layers", {})
    if not isinstance(layers, dict):
        raise ValueError("invalid repository layer registry")
    rows = []
    projects = state.get("projects", {})
    for project_id in sorted(layers):
        if project_id not in projects:
            continue
        title = escape(str(projects[project_id].get("title") or project_id))
        href = "/repositories/" + quote(project_id, safe="")
        try:
            catalog = load_repository_layer(store, project_id)
            counts = catalog["coverage"]
            summary = (
                f'{counts["repository_count"]:,} repositories · '
                f'{counts["source_captured_repository_count"]:,} with captured sources · '
                f'{counts.get("source_interpreted_repository_count", 0):,} with source interpretations · '
                f'{counts["reviewed_repository_count"]:,} with reviewed capabilities'
            )
            detail = escape(summary)
        except (KeyError, ValueError):
            detail = "Saved catalogue could not be verified. Open it to inspect the error."
        rows.append(f'<li><a href="{escape(href, quote=True)}">{title}</a><p>{detail}</p></li>')
    inventory = "<ul>" + "".join(rows) + "</ul>" if rows else '<p class="empty">No repository layers have been saved in this workspace.</p>'
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Repository layers · Cite-Refinery</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f7f8;color:#162e3b;font:16px/1.6 system-ui,sans-serif}
main{max-width:900px;margin:48px auto;padding:0 24px 48px}a{color:#086f75;text-underline-offset:3px}a:focus-visible{outline:3px solid #00a7a7;outline-offset:4px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin-top:36px;color:#47707a}h1{font-size:clamp(30px,5vw,46px);line-height:1.12;margin:12px 0}
.intro{color:#536d79;max-width:690px}ul{list-style:none;padding:0;margin:32px 0;display:grid;gap:16px}li,.empty{padding:22px 24px;border:1px solid #d5e0e5;border-radius:14px;background:#fff}li a{font-size:20px;font-weight:650;overflow-wrap:anywhere}li p{color:#536d79;margin:8px 0 0;font-size:14px}
</style></head><body><main><a href="/">Cite-Refinery workspace</a><div class="eyebrow">Repository inventory</div>
<h1>Repository layers</h1><p class="intro">Browse saved repository inventories, captured source evidence, reviewed technical capabilities, and their recorded connections.</p>''' + inventory + "</main></body></html>"
