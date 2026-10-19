"""Generate a public, AI-independent, read-only Cite-Refinery atlas preview.

No live/private workspace is included. The snapshot is derived from the
public, provenance-bearing three-layer semantic pilot in examples/.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cite_refinery import CiteRefinery, ProductWorkspace, SemanticGraph
from cite_refinery.web_shell import APP_HTML


def build(output: Path) -> dict:
    packet_path = ROOT / "examples/free_roaming_dog_semantic_pilot.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet.get("schema") != "cite_refinery.semantic_graph.v1":
        raise ValueError("Unexpected semantic pilot schema")

    with tempfile.TemporaryDirectory(prefix="cite-refinery-public-demo-") as tmp:
        app = CiteRefinery(tmp)
        project = app.init_project(
            "Free-roaming dog observability · Taiwan",
            "Explore the public-source evidence, scholarly methods, and program capabilities attached to exact semantic modules.",
        )
        graph = SemanticGraph(app.store)
        graph.ingest_packet(project.id, packet, packet_ref="examples/free_roaming_dog_semantic_pilot.json")
        ws = ProductWorkspace(app.store)
        view = ws.project_view(project.id)
        snapshot = {
            "schema": "cite_refinery.public_preview_snapshot.v1",
            "demo": True,
            "data_origin": "examples/free_roaming_dog_semantic_pilot.json",
            "projects": ws.list_projects(),
            "workspaces": {project.id: view},
            "coverage": {
                node_id: ws.node_view(project.id, node_id)
                for node_id in view["graph_export"]["nodes"]
            },
        }

    html = APP_HTML
    needle = """async function api(path){const r=await fetch(path);if(!r.ok)throw new Error(await r.text());return r.json()}"""
    replacement = """let __publicSnapshotPromise=null;
async function api(path){
  if(!__publicSnapshotPromise){
    __publicSnapshotPromise=fetch('/snapshot.json').then(r=>{
      if(!r.ok)throw new Error('Public preview snapshot unavailable');
      return r.json();
    });
  }
  const snapshot=await __publicSnapshotPromise;
  const parts=new URL(path,location.origin).pathname.split('/').filter(Boolean);
  if(parts.length===2 && parts[0]==='api' && parts[1]==='projects')return snapshot.projects;
  if(parts[0]!=='api'||parts[1]!=='projects')throw Error('Unsupported read-only preview API route');
  const pid=decodeURIComponent(parts[2]||'');
  const project=snapshot.workspaces[pid];
  if(!project)throw Error('Project not in the public snapshot');
  if(parts.length===3)return project;
  if(parts.length===4 && parts[3]==='graph')return project.graph_export;
  if(parts.length===4 && parts[3]==='atlas')return project.atlas;
  if(parts.length===6 && parts[3]==='nodes' && parts[5]==='trace'){
    const coverage=snapshot.coverage[decodeURIComponent(parts[4])];
    if(!coverage)throw Error('Node not in the public snapshot');
    return coverage.trace;
  }
  if(parts.length===6 && parts[3]==='nodes' && parts[5]==='coverage'){
    const coverage=snapshot.coverage[decodeURIComponent(parts[4])];
    if(!coverage)throw Error('Node not in the public snapshot');
    return coverage;
  }
  if(parts.length===5 && parts[3]==='clusters'){
    const c=project.atlas.clusters.find(x=>x.id===decodeURIComponent(parts[4]));
    if(!c)throw Error('Cluster not in the public snapshot');
    return c;
  }
  throw Error('Unsupported read-only preview API route');
}"""
    if html.count(needle) != 1:
        raise ValueError("Web UI API seam changed; public preview builder needs review")
    html = html.replace(needle, replacement)
    html = html.replace(
        '<div class="shell">',
        '<div style="background:#eaeef1;color:#263747;padding:9px 20px;font:12px system-ui;text-align:center">'
        '<strong>Public demonstration</strong> · Snapshot of sourced Taiwan research · '
        'Read-only · No login, private project data, or live ingestion</div>'
        '<div class="shell">',
        1,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return {
        "project_id": project.id,
        "clusters": len(view["atlas"]["clusters"]),
        "nodes": len(view["graph_export"]["nodes"]),
        "edges": len(view["graph_export"]["edges"]),
        "output": str(output),
    }


if __name__ == "__main__":
    print(json.dumps(build(ROOT / "dist"), indent=2))
