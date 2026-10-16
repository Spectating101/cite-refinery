from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .store import JsonStore
from .workspace import ProductWorkspace


APP_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cite-Refinery</title>
<style>
:root{--bg:#f1efe7;--paper:#fbfaf6;--ink:#1d1f1a;--muted:#707269;--line:#d5d2c7;--dark:#23251f;--olive:#687153;--rust:#95653f;--soft:#e8e5da}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}button,input{font:inherit}.shell{display:grid;grid-template-columns:260px 1fr;min-height:100vh}.side{background:var(--dark);color:#eee;padding:22px 16px;position:sticky;top:0;height:100vh;overflow:auto}.brand{font-size:20px;font-weight:760;letter-spacing:-.03em}.brand small{display:block;color:#a5a89a;font-size:10px;text-transform:uppercase;letter-spacing:.12em}.label{margin:28px 8px 8px;color:#929587;font-size:10px;text-transform:uppercase;letter-spacing:.12em}.project{width:100%;border:0;background:transparent;color:#d9d9d0;padding:10px;border-radius:8px;text-align:left;cursor:pointer;margin:2px 0}.project:hover,.project.active{background:#36382f;color:white}.project strong,.project span{display:block}.project span{font-size:11px;color:#9c9f91;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.main{min-width:0}.head{padding:28px 34px 0}.eyebrow,.engine{color:var(--rust);font-size:10px;text-transform:uppercase;letter-spacing:.11em;font-weight:700}.head h1{font-size:32px;letter-spacing:-.04em;margin:7px 0}.problem{max-width:900px;color:var(--muted)}.tabs{display:flex;gap:2px;padding:22px 34px 0;border-bottom:1px solid var(--line);overflow:auto}.tab{border:0;background:transparent;padding:11px 13px;color:var(--muted);cursor:pointer;text-transform:capitalize;border-bottom:2px solid transparent}.tab.active{color:var(--ink);font-weight:700;border-color:var(--olive)}.content{padding:28px 34px 60px;max-width:1450px}.grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}.two{grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr)}.three{grid-template-columns:repeat(3,minmax(0,1fr))}.card,.metric{background:var(--paper);border:1px solid var(--line);border-radius:10px}.card{padding:17px}.metric{padding:15px}.metric b{display:block;font-size:26px;letter-spacing:-.03em}.metric span{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}h2{font-size:20px;margin:0 0 14px}h3{font-size:14px;margin:0 0 10px}.row{padding:11px 0;border-top:1px solid var(--line)}.row:first-child{border-top:0;padding-top:0}.muted,.meta{color:var(--muted)}.meta{font-size:11px;margin-top:4px}.pill{display:inline-block;background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:2px 6px;font-size:10px;margin:2px 2px 2px 0}.empty{padding:25px;border:1px dashed var(--line);border-radius:9px;text-align:center;color:var(--muted)}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}.table th{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}.scroll{overflow:auto}.node{display:block;width:100%;text-align:left;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:10px;cursor:pointer}.node:hover{border-color:#a8a495}.node strong{display:block}.search{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:white;margin-bottom:10px}.inspector{position:sticky;top:18px}.layers{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:12px 0}.layer{padding:9px;border:1px solid var(--line);border-radius:8px}.layer b{display:block;text-transform:capitalize}.layer span{font-size:10px;color:var(--muted)}.relation{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:3px 5px;border-radius:4px;margin:2px;display:inline-block}.boundary{border-left:3px solid var(--line);padding-left:9px;font-size:11px;color:var(--muted);margin-top:10px}.source{font-size:11px;color:var(--muted);word-break:break-all}.topline{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-bottom:14px}.topline p{margin:0;color:var(--muted);font-size:11px}
@media(max-width:900px){.shell{grid-template-columns:1fr}.side{height:auto;position:relative}.two,.three{grid-template-columns:1fr}.head,.content{padding-left:18px;padding-right:18px}.tabs{padding-left:18px;padding-right:18px}}
</style></head><body>
<div class="shell"><aside class="side"><div class="brand">Cite-Refinery<small>problem intelligence workspace</small></div><div class="label">Projects</div><div id="projects"></div></aside><main class="main"><header class="head"><div class="eyebrow" id="status">Unified workspace</div><h1 id="title">Loading…</h1><div class="problem" id="problem"></div></header><nav class="tabs" id="tabs"></nav><section class="content" id="content"><div class="empty">Loading…</div></section></main></div>
<script>
const state={projects:[],project:null,tab:'overview',coverage:null,graphQuery:''};const $=s=>document.querySelector(s);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const fmt=n=>Number(n||0).toLocaleString();
async function api(p){const r=await fetch(p);if(!r.ok)throw new Error(await r.text());return r.json()}function pill(v){return v?`<span class="pill">${esc(v)}</span>`:''}function metric(l,v){return `<div class="metric"><b>${fmt(v)}</b><span>${esc(l)}</span></div>`}function empty(v){return `<div class="empty">${esc(v)}</div>`}
function renderProjects(){$('#projects').innerHTML=state.projects.map(p=>`<button class="project ${state.project?.project?.id===p.id?'active':''}" data-project="${esc(p.id)}"><strong>${esc(p.title)}</strong><span>${esc(p.problem||'')}</span></button>`).join('')||'<div class="muted">No projects.</div>';document.querySelectorAll('[data-project]').forEach(b=>b.onclick=()=>loadProject(b.dataset.project))}
function renderTabs(){$('#tabs').innerHTML=(state.project?.navigation||[]).map(t=>`<button class="tab ${t===state.tab?'active':''}" data-tab="${t}">${esc(t)}</button>`).join('');document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;state.coverage=null;renderTabs();renderContent()})}
function overview(s){const o=s.overview,g=s.graph.summary;return `<div class="topline"><div><div class="engine">One project · specialist engines</div><h2>Project state</h2></div><p>No composite score; counts expose represented state.</p></div><div class="grid metrics">${metric('Reality observations',o.reality_observations)}${metric('Research briefs',o.research_briefs)}${metric('Semantic nodes',o.semantic_nodes)}${metric('Graph edges',o.semantic_edges)}${metric('Open requirements',o.open_requirements)}${metric('Solution candidates',o.solution_candidates)}${metric('Experiments',o.experiments)}${metric('Feedback results',o.feedback_results)}</div><div class="grid three" style="margin-top:14px"><div class="card"><div class="engine">Nocturnal</div><h3>Reality</h3><div class="muted">${fmt(s.reality.observations.length)} observations · ${fmt(s.reality.matter_count)} matters · ${fmt(s.reality.source_link_count)} source links</div></div><div class="card"><div class="engine">Cite</div><h3>Research</h3><div class="muted">${fmt(s.research.research_question_count)} questions · ${fmt(s.research.paper_receipts)} paper receipts</div></div><div class="card"><div class="engine">Refinery</div><h3>Solutions</h3><div class="muted">${fmt(s.solutions.candidate_count)} candidates · ${fmt(s.solutions.capabilities.length)} adopted capabilities</div></div></div><div class="card" style="margin-top:14px"><h3>Semantic topology</h3><div class="layers">${['practical','academic','program'].map(l=>`<div class="layer"><b>${l}</b><span>${fmt(g.layer_counts[l]||0)} nodes</span></div>`).join('')}</div><div class="meta">${fmt(g.unresolved_or_candidate_edges)} unresolved/candidate edges · ${fmt(g.contradiction_edges)} contradictions · ${fmt(s.graph.clusters.length)} clusters</div></div>`}
function reality(r){return `<div class="topline"><div><div class="engine">${esc(r.engine)}</div><h2>Reality</h2></div><p>Empirical observations remain empirical.</p></div><div class="grid two"><div class="card"><h3>Observations</h3>${r.observations.length?r.observations.slice(0,200).map(o=>`<div class="row"><strong>${esc(o.text)}</strong><div class="meta">${pill(o.status_stage)}${pill(o.frame)}${pill(o.matter_id)}</div>${(o.sources||[]).slice(0,3).map(x=>`<div class="source">${esc(x)}</div>`).join('')}</div>`).join(''):empty('No observations yet.')}</div><div><div class="card"><h3>Source systems</h3>${Object.entries(r.source_system_counts||{}).map(([k,v])=>`<div class="row">${esc(k)} <b style="float:right">${fmt(v)}</b></div>`).join('')||empty('No sources.')}</div><div class="card" style="margin-top:14px"><h3>Status stages</h3>${Object.entries(r.status_stage_counts||{}).map(([k,v])=>`<div class="row">${esc(k)} <b style="float:right">${fmt(v)}</b></div>`).join('')||empty('No stages.')}</div></div></div>`}
function research(r){return `<div class="topline"><div><div class="engine">${esc(r.engine)}</div><h2>Research</h2></div><p>Discovery is not automatically support.</p></div><div class="grid metrics">${metric('Briefs',r.briefs.length)}${metric('Questions',r.research_question_count)}${metric('Paper receipts',r.paper_receipts)}${metric('Grounding audits',r.grounding_audits.length)}</div><div class="card" style="margin-top:14px"><h3>Research briefs</h3>${r.briefs.length?`<div class="scroll"><table class="table"><thead><tr><th>Brief</th><th>Status</th><th>Questions</th><th>Observations</th></tr></thead><tbody>${r.briefs.map(b=>`<tr><td><strong>${esc(b.title)}</strong><div class="meta">${esc(b.id)}</div></td><td>${pill(b.status)}</td><td>${fmt((b.questions||[]).length)}</td><td>${fmt((b.observation_ids||[]).length)}</td></tr>`).join('')}</tbody></table></div>`:empty('No research briefs yet.')}</div>`}
function nodeButton(n){return `<button class="node" data-node="${esc(n.id)}"><strong>${esc(n.statement)}</strong><div class="meta">${pill(n.layer)}${pill(n.kind)} ${esc(n.id)}</div></button>`}
function graph(g){const exp=state.project.graph_export||{};let nodes=Object.values(exp.nodes||{});const q=state.graphQuery.toLowerCase();if(q)nodes=nodes.filter(n=>(`${n.statement} ${n.kind} ${n.layer}`).toLowerCase().includes(q));const c=state.coverage;const inspect=c?`<div class="card inspector"><div class="engine">Trace this node</div><h3>${esc(c.node.statement)}</h3><div>${pill(c.node.layer)}${pill(c.node.kind)}</div><div class="layers">${['practical','academic','program'].map(l=>`<div class="layer"><b>${l}</b><span>${c.layer_presence[l]?'represented':'not represented'}</span></div>`).join('')}</div><div class="row"><strong>Intersection</strong><div class="meta">${esc(c.intersection)}</div></div><div class="row"><strong>Relations</strong><div class="meta">${Object.entries(c.relations||{}).map(([r,v])=>`<span class="relation">${esc(r)} × ${fmt(v.length)}</span>`).join('')||'None'}</div></div><div class="row"><strong>Unresolved / missing</strong><div class="meta">${fmt((c.unresolved_or_missing||[]).length)}</div></div><div class="row"><strong>Contradictions</strong><div class="meta">${fmt((c.contradictions||[]).length)}</div></div><div class="boundary">${esc(c.boundary)}</div></div>`:`<div class="card inspector"><h3>Node inspector</h3><div class="muted">Select a semantic node to inspect its practical, academic and program neighborhood.</div></div>`;return `<div class="topline"><div><div class="engine">${esc(g.engine)}</div><h2>Semantic map</h2></div><p>Specific modules, typed relations and represented gaps.</p></div><div class="grid metrics">${metric('Nodes',g.summary.node_count)}${metric('Edges',g.summary.edge_count)}${metric('Clusters',g.clusters.length)}${metric('Unresolved / candidate',g.summary.unresolved_or_candidate_edges)}</div><div class="grid two" style="margin-top:14px"><div><input class="search" id="graphSearch" placeholder="Search semantic nodes…" value="${esc(state.graphQuery)}"><div class="grid" id="nodes">${nodes.length?nodes.slice(0,250).map(nodeButton).join(''):empty('No matching nodes.')}</div></div>${inspect}</div>`}
function solutions(s){return `<div class="topline"><div><div class="engine">${esc(s.engine)}</div><h2>Solutions</h2></div><p>Candidate supply remains distinct from validation.</p></div><div class="grid metrics">${metric('Requirements',s.requirements.length)}${metric('Candidates',s.candidate_count)}${metric('Capabilities',s.capabilities.length)}${metric('Implementations',s.implementations.length)}</div><div class="grid two" style="margin-top:14px"><div class="card"><h3>Requirements</h3>${s.requirements.length?s.requirements.map(r=>`<div class="row"><strong>${esc(r.text)}</strong><div class="meta">${pill(r.status)}${pill(r.kind)}</div></div>`).join(''):empty('No requirements yet.')}</div><div class="card"><h3>Supply authority</h3>${Object.entries(s.candidate_authority_counts||{}).map(([k,v])=>`<div class="row">${esc(k)} <b style="float:right">${fmt(v)}</b></div>`).join('')||empty('No candidates.')}</div></div>`}
function build(b){return `<div class="topline"><div><h2>Build / Execute</h2></div><p>Capabilities become implementations, runs and artifacts.</p></div><div class="grid metrics">${metric('Implementations',b.implementations.length)}${metric('Runs',b.runs.length)}${metric('Succeeded runs',b.succeeded_runs)}${metric('Artifacts',b.artifacts.length)}</div><div class="card" style="margin-top:14px"><h3>Runs</h3>${b.runs.length?b.runs.map(r=>`<div class="row"><strong>${esc(r.provider)}</strong>${pill(r.status)}<div class="meta">${esc(r.id)} · ${fmt(r.duration_ms)} ms</div></div>`).join(''):empty('No runs yet.')}</div>`}
function validate(v){return `<div class="topline"><div><h2>Validate / Feedback</h2></div><p>Outcome observation stays separate from causal attribution.</p></div><div class="grid metrics">${metric('Experiments',v.experiments.length)}${metric('Passed / supported',v.passed_or_supported_experiments)}${metric('Feedback requests',v.feedback_requests.length)}${metric('Feedback results',v.feedback_results.length)}</div><div class="card" style="margin-top:14px"><h3>Experiments</h3>${v.experiments.length?v.experiments.map(e=>`<div class="row"><strong>${esc(e.name)}</strong>${pill(e.verdict)}<div class="meta">${esc(e.method||'')}</div><div class="meta">${esc(e.result||'')}</div></div>`).join(''):empty('No experiments yet.')}</div>`}
function bindGraph(){const input=$('#graphSearch');if(input)input.oninput=()=>{state.graphQuery=input.value;state.coverage=null;renderContent()};document.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>inspectNode(b.dataset.node))}
async function inspectNode(id){const p=state.project.project.id;const data=await api(`/api/projects/${encodeURIComponent(p)}/nodes/${encodeURIComponent(id)}/coverage?depth=1`);state.coverage=data.coverage;renderContent()}
function renderContent(){if(!state.project)return;const s=state.project.sections;let html='';if(state.tab==='overview')html=overview(s);else if(state.tab==='reality')html=reality(s.reality);else if(state.tab==='research')html=research(s.research);else if(state.tab==='graph')html=graph(s.graph);else if(state.tab==='solutions')html=solutions(s.solutions);else if(state.tab==='build')html=build(s.build);else html=validate(s.validate);$('#content').innerHTML=html;if(state.tab==='graph')bindGraph()}
async function loadProject(id){state.project=await api(`/api/projects/${encodeURIComponent(id)}?graph=1`);state.coverage=null;state.graphQuery='';$('#title').textContent=state.project.project.title||'Untitled';$('#problem').textContent=state.project.project.problem||'';$('#status').textContent=`${state.project.project.status||'active'} · unified workspace`;renderProjects();renderTabs();renderContent();history.replaceState(null,'',`?project=${encodeURIComponent(id)}`)}
async function init(){try{state.projects=await api('/api/projects');renderProjects();const id=new URLSearchParams(location.search).get('project')||state.projects[0]?.id;if(id)await loadProject(id);else{$('#title').textContent='Cite-Refinery';$('#problem').textContent='Create a project to begin.';$('#content').innerHTML=empty('No projects in this workspace.')}}catch(e){$('#content').innerHTML=empty(e.message)}}init();
</script></body></html>'''


class _Handler(BaseHTTPRequestHandler):
    workspace: ProductWorkspace

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
        return

    def _send(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, value: Any, status: int = 200) -> None:
        self._send(
            json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path in {"/", "/index.html"}:
                self._send(APP_HTML.encode("utf-8"), "text/html; charset=utf-8")
                return
            if path == "/api/health":
                self._json({"status": "ok", "product": "cite-refinery"})
                return
            if path == "/api/projects":
                self._json(self.workspace.list_projects())
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 3 and parts[:2] == ["api", "projects"]:
                project_id = parts[2]
                if len(parts) == 3:
                    include_graph = query.get("graph", ["0"])[0].lower() in {"1", "true", "yes"}
                    self._json(self.workspace.project_view(project_id, include_graph=include_graph))
                    return
                if len(parts) == 4 and parts[3] == "graph":
                    self._json(self.workspace.graph.export(project_id))
                    return
                if len(parts) == 6 and parts[3] == "nodes" and parts[5] == "coverage":
                    depth = int(query.get("depth", ["1"])[0])
                    self._json(self.workspace.node_view(project_id, parts[4], depth=depth))
                    return
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self._json({"error": f"internal error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def make_server(
    workspace: str | Path = ".cite-refinery",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    if not 0 <= int(port) <= 65535:
        raise ValueError("port must be between 0 and 65535")
    product = ProductWorkspace(JsonStore(workspace))

    class Handler(_Handler):
        pass

    Handler.workspace = product
    return ThreadingHTTPServer((host, int(port)), Handler)


def serve(
    workspace: str | Path = ".cite-refinery",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    server = make_server(workspace, host=host, port=port)
    actual_host, actual_port = server.server_address[:2]
    print(f"Cite-Refinery web: http://{actual_host}:{actual_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()
