from __future__ import annotations

import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from cite_refinery.repository_layer_view import render_repository_layer


class PayloadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.payload = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.scripts.append(attrs)
            self.inside = attrs.get("id") == "repo-layer-data"

    def handle_endtag(self, tag):
        if tag == "script":
            self.inside = False

    def handle_data(self, text):
        if self.inside:
            self.payload.append(text)


def fixture(count=70):
    records = [{
        "id": f"github:acme/repo{i:03d}", "full_name": f"acme/repo{i:03d}",
        "url": f"https://github.com/acme/repo{i:03d}", "description": f"Inventory repository {i}",
        "aliases": [], "languages": [], "topics": [], "domains": ["general"],
        "review_state": "unreviewed", "capabilities": [], "proposed_capabilities": [],
        "rejected_assignments": [], "unknowns": [], "observations": [{
            "source_id": "metadata-snapshot", "observed_at": "2026-11-18T00:00:00Z",
            "description": f"Inventory repository {i}", "evidence_level": "metadata_only"
        }]
    } for i in range(count)]
    for i, level in enumerate(("documented", "code_inspected", "executed")):
        if i >= count:
            break
        records[i]["review_state"] = "partially_reviewed"
        records[i]["capabilities"] = [{
            "id": f"capability-{i}", "key": f"transform-{i}", "name": "Transform a record",
            "mechanism": "Maps component graphs using onlyMechanismNeedle" if i == 0 else "Transforms a bounded fixture",
            "inputs": [{"name": "Structured netlist", "format": "DSN", "description": "Connectivity", "evidence_ids": ["source-1"]}],
            "outputs": [{"name": "Routing session", "format": "SES", "description": "Routed copper", "evidence_ids": []}],
            "requirements": [{"kind": "runtime", "name": "Java", "constraint": "Version declared by upstream", "evidence_ids": []}],
            "limitations": [{"text": "Scoped fixture only", "evidence_ids": []}],
            "evidence_level": level, "evidence_ids": ["source-1"]
        }]
    if count:
        records[0]["domains"] = ["chemistry"]
        records[0]["description"] = '</script><img src="https://attacker.invalid/pixel" onerror="window.__evil=1"> & 中文 \u2028'
    if count > 3:
        records[3]["proposed_capabilities"] = [{
            "id": "proposal-1", "name": "Unreviewed XML parser", "status": "unreviewed",
            "mechanism": "Proposed from a source mention", "evidence_ids": []
        }, {"id": "proposal-2", "name": "Rejected compiler assignment", "status": "rejected", "evidence_ids": []}]
    if count > 4:
        records[4]["source_interpretations"] = [{
            "id": "interpretation-1", "repository_id": records[4]["id"],
            "purpose": "Transform onlyInterpretationNeedle into inspectable records.",
            "inputs": ["Typed input stream"], "outputs": ["Normalized table"],
            "human_work": ["Select source fields"], "custom_glue": ["Connect the file adapter"],
            "limitations": ["Source review has no runtime receipt"],
            "authority": "source_bound_model_interpretation", "analysis_method": "llm_source_review",
            "semantic_support_verified": False, "runtime_tested": False, "evidence_ids": ["source-1"],
            "evidence": [{"source_id": "source-1", "excerpt": "<img onerror=window.__evil=1> A literal source passage.",
                          "excerpt_start": 10, "excerpt_end": 40, "byte_integrity_checked": True,
                          "semantic_support_verified": False, "runtime_tested": False}],
        }]
    if count > 6:
        records[4]["reviewed_identity"] = {"canonical_repository_id": "github:current/canonical",
            "observed_repository_ids": [records[4]["id"], "github:current/canonical"],
            "resolution_ids": ["identity-resolution-1"], "authority": "reviewed_identity"}
        records[4]["source_mapping_states"] = [{"cohort": "completed-cohort", "status": "mapped", "source_status": "captured"}]
        records[5]["technical_findings"] = [{"id": "finding-1", "title": "ApprovedInterfaceNeedle", "kind": "input_output_interface",
            "direction": "output", "format": "STEP", "description": "Exports an exact body", "status": "approved",
            "runtime_tested": False, "evidence_ids": ["source-1"], "limitations": ["Format contract remains unexecuted"],
            "evidence": [{"source_id": "source-1", "excerpt": "<img onerror=window.__evil=1> STEP export documented."}]},
            {"id": "finding-2", "title": "RejectedInterfaceNeedle", "status": "rejected", "description": "Wrong operation"}]
        records[6]["source_mapping_states"] = [{"cohort": "stopped-cohort", "status": "ready", "source_status": "captured",
            "reason": "Original source retained, review not started"}]
    return {
        "schema": "cite_refinery.repository_layer.v1", "scope": "repository_only",
        "repositories": records,
        "sources": [{"id": "source-1", "repository_id": records[0]["id"] if records else "none",
                     "kind": "documentation", "path": "README.md", "revision": "abcdef123456",
                     "url": "javascript:window.__evil=1", "excerpt": "<svg onload=window.__evil=1> Source claim only."},
                    {"id": "metadata-source", "repository_id": records[-1]["id"] if records else "none",
                     "kind": "metadata", "excerpt": "A revision lookup does not establish captured source coverage."},
                    {"id": "failed-source", "repository_id": records[-2]["id"] if len(records) > 1 else "none",
                     "kind": "documentation", "excerpt": "A mismatched capture is not source coverage.", "capture_integrity": "mismatch"}],
        "relationships": [{"id": "edge-1", "source_repository_id": records[0]["id"],
                           "target_repository_id": records[2]["id"], "kind": "proposed_handoff",
                           "description": "Candidate interface handoff", "evidence_ids": ["source-1"],
                           "scope": {"status": "not executed"}}] if count > 2 else [],
        "proposed_relationships": [{"id": "legacy-edge-1", "source_repository_id": records[0]["id"],
                                    "target_repository_id": records[-1]["id"], "kind": "legacy_handoff",
                                    "status": "unreviewed", "description": "Preserved shared-format suggestion"}] if count > 3 else [],
        "coverage": {}, "input_sources": []
    }


class RepositoryLayerViewTests(unittest.TestCase):
    def test_complete_payload_roundtrips_without_creating_html_from_sources(self):
        catalog = fixture(2048)
        rendered = render_repository_layer(catalog)
        parser = PayloadParser()
        parser.feed(rendered)
        self.assertEqual(json.loads("".join(parser.payload)), catalog)
        self.assertEqual(len(parser.scripts), 2)
        self.assertTrue(all("src" not in s for s in parser.scripts))
        self.assertNotIn('<img src="https://attacker.invalid/', rendered)
        self.assertIn("connect-src 'none'", rendered)

    def test_rejects_wrong_scope_and_duplicate_identity(self):
        catalog = fixture(1)
        catalog["scope"] = "mixed_opportunity_graph"
        with self.assertRaises(ValueError):
            render_repository_layer(catalog)
        catalog["scope"] = "repository_only"
        catalog["repositories"].append(copy.deepcopy(catalog["repositories"][0]))
        with self.assertRaises(ValueError):
            render_repository_layer(catalog)

    def test_empty_inventory_is_preserved(self):
        catalog = fixture(0)
        rendered = render_repository_layer(catalog)
        parser = PayloadParser()
        parser.feed(rendered)
        self.assertEqual(json.loads("".join(parser.payload))["repositories"], [])

    def test_dom_executes_filters_pagination_provenance_and_lossless_export(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is an optional UI execution-test dependency")
        module = os.environ.get("REPOSITORY_LAYER_JSDOM_PATH")
        if not module:
            found = subprocess.run([node, "-e", "process.stdout.write(require.resolve('jsdom'))"], capture_output=True, text=True)
            if found.returncode:
                self.skipTest("jsdom is an optional UI execution-test dependency")
            module = found.stdout
        script = r'''
const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM,ResourceLoader,VirtualConsole}=require(process.argv[1]);
const errors=[],requests=[];let exported=null;
class OfflineResources extends ResourceLoader{fetch(url){requests.push(url);return null}}
const console=new VirtualConsole();console.on('jsdomError',e=>errors.push(String(e)));
const dom=new JSDOM(fs.readFileSync(0,'utf8'),{url:'https://offline.invalid/catalog.html',runScripts:'dangerously',resources:new OfflineResources(),virtualConsole:console,beforeParse(w){
 w.matchMedia=()=>({matches:false});w.HTMLElement.prototype.scrollIntoView=function(){};
 w.Blob=class{constructor(parts){exported=parts.join('')}};w.URL.createObjectURL=()=> 'blob:offline';w.URL.revokeObjectURL=()=>{};
 const original=w.HTMLAnchorElement.prototype.click;w.HTMLAnchorElement.prototype.click=function(){if(!this.download)original.call(this)};
}});
const w=dom.window,d=w.document,$=id=>d.getElementById(id);
function set(id,value,type='change'){$(id).value=value;$(id).dispatchEvent(new w.Event(type,{bubbles:true}))}
assert.equal(d.querySelectorAll('.repo-row').length,24);assert.equal($('result-count').textContent,'70 / 70');
assert.equal(w.__evil,undefined);assert.equal(d.querySelectorAll('#inspector img,#inspector svg').length,0);
assert.equal(d.querySelectorAll('#inspector a[href^="javascript:"]').length,0);
assert.match($('metrics').textContent,/3reviewed capability claims/);
assert.match($('metrics').textContent,/1source-based interpretations/);
$('next').click();assert.equal(d.querySelector('.repo-row').dataset.repositoryId,'github:acme/repo024');
d.querySelector('[data-repository-id="github:acme/repo025"]').click();assert.equal($('selected-repo-title').textContent,'acme/repo025');
assert.equal(w.location.hash,'#repo=github%3Aacme%2Frepo025');
set('search','onlyMechanismNeedle','input');assert.equal($('result-count').textContent,'1 / 70');
assert.equal($('selected-repo-title').textContent,'acme/repo000');assert.match($('inspector').textContent,/Structured netlist/);assert.match($('inspector').textContent,/Routing session/);
assert.match($('inspector').textContent,/Preserved connection proposals \(1\)/);assert.equal(d.querySelectorAll('.neighbor-button').length,1);
assert.match($('inspector').textContent,/acme\/repo000 → acme\/repo002/);
assert.match($('inspector').textContent,/Proposed handoff/);d.querySelector('.neighbor-button').click();assert.equal($('selected-repo-title').textContent,'acme/repo002');
set('evidence-filter','metadata_only');assert.equal($('result-count').textContent,'66 / 70');d.querySelector('[data-repository-id="github:acme/repo003"]').click();
const proposals=[...d.querySelectorAll('details')].find(x=>x.querySelector('summary').textContent.includes('Preserved capability proposals'));proposals.open=true;proposals.dispatchEvent(new w.Event('toggle'));
assert.match($('inspector').textContent,/Rejected assignment/);assert.match($('inspector').textContent,/Unreviewed assignment/);
set('evidence-filter','executed');assert.equal($('result-count').textContent,'1 / 70');assert.equal($('selected-repo-title').textContent,'acme/repo002');
set('evidence-filter','source_interpreted');assert.equal($('result-count').textContent,'1 / 70');assert.equal($('selected-repo-title').textContent,'acme/repo004');
assert.equal(d.querySelectorAll('.source-interpretation').length,1);assert.equal(d.querySelectorAll('.capability').length,0);
assert.match($('inspector').textContent,/Typed input stream/);assert.match($('inspector').textContent,/Normalized table/);assert.match($('inspector').textContent,/Semantic support and runtime behavior remain unverified/);
assert.equal(d.querySelectorAll('#inspector img').length,0);
set('evidence-filter','all');set('search','onlyInterpretationNeedle','input');assert.equal($('result-count').textContent,'1 / 70');set('search','','input');
set('evidence-filter','source_captured');assert.equal($('result-count').textContent,'1 / 70');assert.equal($('selected-repo-title').textContent,'acme/repo000');
set('evidence-filter','all');set('search','github:current/canonical','input');assert.equal($('result-count').textContent,'1 / 70');
assert.match($('inspector').textContent,/Reviewed canonical repository: github:current\/canonical/);
assert.match($('inspector').textContent,/Historical listing IDs and their captured evidence remain separate/);
assert.equal(d.querySelectorAll('.capability').length,0);
set('search','ApprovedInterfaceNeedle','input');assert.equal($('result-count').textContent,'1 / 70');
const findings=[...d.querySelectorAll('details')].find(x=>x.querySelector('summary').textContent.includes('Source-reviewed technical findings'));
findings.open=true;findings.dispatchEvent(new w.Event('toggle'));assert.match($('inspector').textContent,/runtime behavior remains untested/);assert.equal(d.querySelectorAll('#inspector img').length,0);
set('search','RejectedInterfaceNeedle','input');assert.equal($('result-count').textContent,'0 / 70');
set('search','','input');set('evidence-filter','mapping_ready');assert.equal($('result-count').textContent,'1 / 70');assert.equal($('selected-repo-title').textContent,'acme/repo006');
assert.match($('inspector').textContent,/Original source retained, review not started/);
set('evidence-filter','mapping_mapped');assert.equal($('result-count').textContent,'1 / 70');assert.equal($('selected-repo-title').textContent,'acme/repo004');
set('evidence-filter','unreviewed');assert.equal($('result-count').textContent,'67 / 70');
set('evidence-filter','all');set('domain-filter','chemistry');assert.equal($('result-count').textContent,'1 / 70');
set('search','unique-unknown-token','input');assert.equal(d.querySelectorAll('.repo-row').length,0);assert.match($('inspector').textContent,/adjusting the filters/);
$('export-json').click();const saved=JSON.parse(exported);assert.equal(saved.repositories.length,70);assert.match(saved.repositories[0].description,/<\/script>/);
assert.equal(requests.length,0);assert.deepEqual(errors,[]);dom.window.close();process.stdout.write('DOM execution checks passed');
'''
        result = subprocess.run([node, "-e", script, module], input=render_repository_layer(fixture()), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DOM execution checks passed", result.stdout)

    def test_real_browser_pagination_search_evidence_navigation_export_and_xss(self):
        node = shutil.which("node")
        chromium = shutil.which("chromium") or shutil.which("chromium-browser")
        if not node or not chromium:
            self.skipTest("Node and Chromium are optional local browser-test dependencies")
        discovery = subprocess.run([node, "-e", "process.stdout.write(require.resolve('playwright'))"], capture_output=True, text=True)
        if discovery.returncode:
            self.skipTest("Playwright is an optional local browser-test dependency")
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "catalog.html"
            html.write_text(render_repository_layer(fixture()), encoding="utf-8")
            script = r'''
const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.argv[1]);
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.argv[2],args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1360,height:1000},acceptDownloads:true});
 const errors=[],network=[];page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 await page.goto(process.argv[3]);
 assert.equal(await page.locator('.repo-row').count(),24);
 assert.equal(await page.locator('#result-count').textContent(),'70 / 70');
 assert.equal(await page.evaluate(()=>window.__evil),undefined);
 assert.equal(await page.locator('#inspector img,#inspector svg').count(),0);
 assert.equal(await page.locator('#inspector a[href^="javascript:"]').count(),0);
 assert.match(await page.locator('#metrics').textContent(),/3reviewed capability claims/);
 await page.locator('#next').click();
 assert.equal(await page.locator('.repo-row').first().getAttribute('data-repository-id'),'github:acme/repo024');
 await page.locator('[data-repository-id="github:acme/repo025"]').click();
 assert.match(page.url(),/#repo=github%3Aacme%2Frepo025$/);
 await page.reload();assert.equal(await page.locator('#selected-repo-title').textContent(),'acme/repo025');
 assert.equal(await page.locator('#page-label').textContent(),'Page 2 of 3');
 await page.locator('#search').fill('onlyMechanismNeedle');
 assert.equal(await page.locator('#result-count').textContent(),'1 / 70');
 assert.equal(await page.locator('#selected-repo-title').textContent(),'acme/repo000');
 assert.match(await page.locator('#inspector').textContent(),/Structured netlist/);
 assert.match(await page.locator('#inspector').textContent(),/Routing session/);
 assert.match(await page.locator('#inspector').textContent(),/Proposed handoff/);
 assert.doesNotMatch(await page.locator('#inspector').textContent(),/Tested handoff claims/);
 await page.locator('.neighbor-button').click();
 assert.equal(await page.locator('#selected-repo-title').textContent(),'acme/repo002');
 await page.locator('#evidence-filter').selectOption('metadata_only');
 assert.equal(await page.locator('#result-count').textContent(),'66 / 70');
 await page.locator('[data-repository-id="github:acme/repo003"]').click();
 await page.locator('summary').filter({hasText:'Preserved capability proposals'}).click();
 assert.match(await page.locator('#inspector').textContent(),/Rejected assignment/);
 assert.match(await page.locator('#inspector').textContent(),/Unreviewed assignment/);
 await page.locator('#evidence-filter').selectOption('executed');
 assert.equal(await page.locator('#result-count').textContent(),'1 / 70');
 assert.equal(await page.locator('#selected-repo-title').textContent(),'acme/repo002');
 await page.locator('#evidence-filter').selectOption('all');await page.locator('#domain-filter').selectOption('chemistry');
 assert.equal(await page.locator('#result-count').textContent(),'1 / 70');
 await page.locator('#search').fill('no-such-record-unique-token');assert.equal(await page.locator('.repo-row').count(),0);
 assert.match(await page.locator('#inspector').textContent(),/adjusting the filters/);
 const downloadPromise=page.waitForEvent('download');await page.locator('#export-json').click();const download=await downloadPromise;
 const exported=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(exported.repositories.length,70);
 assert.match(exported.repositories[0].description,/<\/script>/);
 await page.locator('#search').fill('');await page.locator('#domain-filter').selectOption('all');
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.equal(network.length,0);assert.deepEqual(errors,[]);await browser.close();console.log('Browser checks passed');
})().catch(error=>{console.error(error);process.exit(1)});
'''
            result = subprocess.run([node, "-e", script, discovery.stdout, chromium, html.as_uri()], capture_output=True, text=True, timeout=60)
            if "browserType.launch" in result.stderr and "socket() failed: Operation not permitted" in result.stderr:
                self.skipTest("managed environment blocks Chromium's Unix process socket")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Browser checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
