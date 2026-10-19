'use strict';
// Credentials exist only in this running page's JavaScript memory.
const app={token:null,projects:[],project:null,snapshots:[],report:null,module:null,node:null};
const $=id=>document.getElementById(id);
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const count=n=>Number(n||0).toLocaleString();
function setStatus(message,failed=false){$('status').textContent=message;$('status').classList.toggle('error',failed)}
function setOptions(el,items,empty){el.replaceChildren();if(!items.length){const opt=new Option(empty||'No saved checkpoints','');el.add(opt);return}items.forEach(item=>el.add(new Option(item.label,item.value)))}
async function request(path,options={}){
  if(!app.token)throw Error('Connect with a private token first');
  const r=await fetch(path,{...options,credentials:'omit',cache:'no-store',
    headers:{'Authorization':'Bearer '+app.token,...(options.body?{'Content-Type':'application/json'}:{})}});
  if(!r.ok){let msg='Request failed ('+r.status+')';try{const data=await r.json();if(data.detail)msg+=': '+data.detail}catch(_){}throw Error(msg)}
  return r.json();
}
function safeRef(ref){
  const str=String(ref||'');let url=null;
  try{const u=new URL(str);if(u.protocol==='https:')url=u.href}catch(_){}
  return url?'<a target="_blank" rel="noopener noreferrer" href="'+escapeHtml(url)+'">'+escapeHtml(str)+'</a>':'<span class="meta">'+escapeHtml(str)+'</span>';
}
const chip=(name,cls='')=>'<span class="chip '+escapeHtml(cls)+'">'+escapeHtml(name)+'</span>';
function clearReport(){$('report').hidden=true;$('welcome').hidden=false;app.report=null;app.module=null;app.node=null}
async function connect(){
  const input=$('credential');const token=input.value.trim();
  if(!token){setStatus('Enter a bearer token.',true);return}
  app.token=token;input.value='';
  try{
    const projects=await request('/api/projects');
    app.projects=projects;
    setOptions($('project'),projects.map(p=>({value:p.id,label:p.title})), 'No accessible projects');
    $('project').disabled=!projects.length;$('disconnect').hidden=false;
    $('captureLabel').disabled=false;
    setStatus('Authenticated. Choose a project and two checkpoints.');
    if(projects.length)await chooseProject(projects[0].id);
  }catch(err){disconnect(false);setStatus(String(err.message||err),true)}
}
function disconnect(notify=true){
  app.token=null;app.projects=[];app.project=null;app.snapshots=[];
  $('credential').value='';$('disconnect').hidden=true;
  for(const id of ['project','before','after']){$(id).disabled=true;setOptions($(id),[],'Connect first')}
  for(const id of ['compare','capture','captureLabel'])$(id).disabled=true;
  clearReport();if(notify)setStatus('Disconnected. Token cleared from memory.');
}
async function chooseProject(id){
  app.project=app.projects.find(p=>p.id===id)||null;
  clearReport();
  if(!app.project)return;
  $('project').value=id;
  const snapshots=await request('/api/projects/'+encodeURIComponent(id)+'/evolution/snapshots');
  app.snapshots=snapshots;
  const entries=snapshots.map(s=>({value:s.id,label:'r'+s.revision+' · '+s.label}));
  setOptions($('before'),entries,'No checkpoints yet');
  setOptions($('after'),entries,'No checkpoints yet');
  $('before').disabled=snapshots.length<2;$('after').disabled=snapshots.length<2;
  $('compare').disabled=snapshots.length<2;
  $('capture').disabled=false;$('captureLabel').disabled=false;
  if(snapshots.length>1){
    $('before').value=snapshots[snapshots.length-2].id;
    $('after').value=snapshots[snapshots.length-1].id;
  }
  setStatus('Project selected · revision '+app.project.revision+' · '+snapshots.length+' immutable checkpoints.');
}
async function compare(){
  const old=$('before').value, newest=$('after').value;
  if(!old||!newest)throw Error('Choose two saved checkpoints');
  const pid=encodeURIComponent(app.project.id);
  app.report=await request('/api/projects/'+pid+'/evolution/compare?from_snapshot='+encodeURIComponent(old)+'&to_snapshot='+encodeURIComponent(newest));
  app.module=null;app.node=null;renderReport();setStatus('Compared source evidence from revisions '+app.report.before.revision+' → '+app.report.after.revision+'.');
}
async function capture(){
  const label=$('captureLabel').value.trim();
  if(label.length<5)throw Error('Checkpoint label must contain at least 5 characters');
  const pid=encodeURIComponent(app.project.id);
  const item=await request('/api/projects/'+pid+'/evolution/snapshots',{
    method:'POST',body:JSON.stringify({label,expected_revision:app.project.revision})});
  $('captureLabel').value='';
  await chooseProject(app.project.id);
  setStatus('Saved immutable checkpoint at project revision '+item.revision+'.');
}
function metric(label,n){return '<div class="card"><strong>'+count(n)+'</strong><span>'+escapeHtml(label)+'</span></div>'}
function renderReport(){
  const report=app.report;if(!report)return;
  $('welcome').hidden=true;$('report').hidden=false;
  const delta=report.record_delta||{};
  $('summary').innerHTML=metric('New nodes',delta.semantic_nodes?.added)+metric('Changed existing nodes',delta.semantic_nodes?.revised_existing)
    +metric('New typed edges',delta.semantic_edges?.added)+metric('Changed modules',report.module_changes?.count);
  const warnings=report.interpretation?.warnings||[];
  $('boundary').innerHTML='<h2>What this comparison cannot establish</h2><p class="warning">Comparability: not established. No performance, market adoption or production readiness estimate is inferred from graph growth.</p><ul>'
    +warnings.map(w=>'<li>'+escapeHtml(w)+'</li>').join('')+'</ul>';
  renderModules();
}
function filteredModules(){
  const q=$('search').value.trim().toLowerCase(),filter=$('filter').value;
  return(app.report?.module_changes?.items||[]).filter(m=>{
    const text=(m.title+' '+(m.external_key||'')+' '+Object.keys(m.changed_node_counts||{}).join(' ')).toLowerCase();
    if(q&&!text.includes(q))return false;
    if(filter==='all')return true;
    if(filter==='candidate')return m.changed_relations_candidate_or_unresolved>0;
    if(filter==='limitation')return (m.nodes||[]).some(n=>n.kind==='limitation');
    return(m.changed_node_counts?.[filter]||0)>0;
  });
}
function renderModules(){
  const items=filteredModules();
  $('modules').innerHTML=items.length?items.map(m=>'<button class="module '+(app.module===m.id?'active':'')+'" data-module="'+escapeHtml(m.id)+'"><strong>'+escapeHtml(m.title)+'</strong><span class="meta">'+count(m.new_nodes_total)+' new / '+count(m.revised_nodes_total)+' revised · '+count(m.changed_relations_total)+' relations</span><div class="chips">'+
    ['practical','academic','program'].filter(k=>m.changed_node_counts?.[k]).map(k=>chip(k+' '+m.changed_node_counts[k],k)).join('')+
    (m.changed_relations_candidate_or_unresolved?chip('candidate '+m.changed_relations_candidate_or_unresolved):'')+'</div></button>').join(''):
    '<p class="muted">No modules match this search or structural filter.</p>';
  $('modules').querySelectorAll('[data-module]').forEach(button=>{
    button.addEventListener('click',()=>{app.module=button.dataset.module;app.node=null;renderModules();renderDetail()})
  });
  if(app.module&&!items.some(m=>m.id===app.module)){app.module=null;app.node=null}
  if(!app.module&&items.length){app.module=items[0].id;renderDetail();
    const button=$('modules').querySelector('[data-module]');if(button)button.classList.add('active')}
  else if(!items.length){$('detail').innerHTML='<p class="muted">Select a changed semantic module.</p>'}
}
function renderDetail(){
  const module=app.report?.module_changes?.items.find(m=>m.id===app.module);
  if(!module){$('detail').innerHTML='<p class="muted">Choose a module.</p>';return}
  const title='<h2>'+escapeHtml(module.title)+'</h2><p class="muted">'+escapeHtml(module.boundary)+'</p>';
  const nodeCol=layer=>{
    const nodes=(module.nodes||[]).filter(n=>n.layer===layer);
    return '<div class="layer '+layer+'"><div class="layerhead">'+escapeHtml(layer)+' · '+count(module.changed_node_counts?.[layer])+'</div>'+
      '<div class="layerbody">'+(nodes.length?nodes.map(n=>'<button class="node '+(app.node===n.id?'active':'')+'" data-node="'+escapeHtml(n.id)+'">'+escapeHtml(n.statement)+'<br><span class="meta">'+escapeHtml(n.kind)+' · '+escapeHtml(n.change)+'</span></button>').join(''):
      '<span class="muted">No changed nodes represented.</span>')+'</div></div>';
  };
  const neutral=(module.nodes||[]).filter(n=>n.layer==='neutral');
  let body=title+'<div class="layers">'+['practical','academic','program'].map(nodeCol).join('')+'</div>';
  if(neutral.length)body+='<div class="muted">'+neutral.length+' neutral/context records changed</div>';
  const n=(module.nodes||[]).find(n=>n.id===app.node);
  if(n){
    body+='<section class="audit"><h3>'+escapeHtml(n.statement)+'</h3><p class="meta">'+escapeHtml(n.kind)+' · '+escapeHtml(n.layer)+' · '+escapeHtml(n.change)+'</p>'+
    '<div>'+((n.source_refs||[]).map(safeRef).join('')||'<span class="muted">No source link provided.</span>')+'</div>'+
    '<details><summary>Evidence scope / source receipts</summary><pre>'+escapeHtml(JSON.stringify(n.evidence_scope||[],null,2))+'</pre></details></section>';
  }
  const relations=module.relations||[];
  body+='<section class="audit"><h3>Typed relation changes · '+count(module.changed_relations_total)+'</h3>'+
    (relations.length?relations.map(e=>'<div class="relation">'+chip(e.relation)+chip(e.status)+
      (e.cross_module?chip('cross-module'):'')+'<div class="meta">'+escapeHtml(e.change)+' · '+escapeHtml(e.source_id)+' → '+escapeHtml(e.target_id)+'</div>'+
      (e.source_refs||[]).map(safeRef).join('')+'</div>').join(''):'<p class="muted">No changed relations.</p>')+'</section>';
  if(module.nodes_truncated||module.relations_truncated)body+='<p class="warning">Large module: details truncated for this view. Use the authenticated underlying project record for full evidence.</p>';
  $('detail').innerHTML=body;
  $('detail').querySelectorAll('[data-node]').forEach(b=>b.addEventListener('click',()=>{
    app.node=b.dataset.node;renderDetail()
  }));
}
function run(action){Promise.resolve().then(action).catch(err=>setStatus(String(err.message||err),true))}
$('connect').addEventListener('click',()=>run(connect));
$('disconnect').addEventListener('click',()=>disconnect(true));
$('project').addEventListener('change',e=>run(()=>chooseProject(e.target.value)));
$('compare').addEventListener('click',()=>run(compare));
$('capture').addEventListener('click',()=>run(capture));
$('search').addEventListener('input',renderModules);
$('filter').addEventListener('change',renderModules);
