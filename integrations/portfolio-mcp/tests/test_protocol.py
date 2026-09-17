"""Real SDK/stdio tests. Skipped, never counted as passed, without the SDK."""
import asyncio
import json
import os
import sys
from pathlib import Path
import pytest
pytest.importorskip('mcp')
from mcp import Client, StdioServerParameters


def test_real_stdio_discovery_call_and_error(tmp_path):
    (tmp_path / 'engine.py').write_text('import sys; print(sys.stdin.read())')
    doc = {'schema':'portfolio.mcp.manifest.v1','project':'wire-fixture','mode':'bridge',
           'tools':[{'name':'fixture_echo','description':'Transport test double, not a portfolio engine.',
                     'effect':'compute','argv':['$PYTHON','engine.py'],
                     'input_schema':{'type':'object','properties':{'ref':{'type':'string'}},
                                     'required':['ref'],'additionalProperties':False}}]}
    path = tmp_path / 'manifest.json'; path.write_text(json.dumps(doc))
    params = StdioServerParameters(command=sys.executable,
        args=['-m','portfolio_mcp.cli','serve','--manifest',str(path),'--root',str(tmp_path)], env=dict(os.environ))
    async def exercise():
        async with asyncio.timeout(30):
            async with Client(params) as client:
                listed = await client.list_tools()
                assert [t.name for t in listed.tools] == ['fixture_echo']
                result = await client.call_tool('fixture_echo', {'ref':'dataset:test'})
                assert not result.is_error
                assert result.structured_content['result']['ref'] == 'dataset:test'
                bad = await client.call_tool('fixture_echo', {'unexpected':True})
                assert bad.is_error
    asyncio.run(exercise())


def test_native_cite_refinery_dossier_over_stdio(tmp_path):
    """Native application + real stdio MCP; not a mocked application."""
    pytest.importorskip('cite_refinery')
    from cite_refinery.orchestrator import CiteRefinery
    root = Path(__file__).resolve().parents[3]
    workspace = tmp_path / 'workspace'
    app = CiteRefinery(workspace)
    project = app.init_project('MCP integration test', 'Verify native dossier transport')
    env = dict(os.environ, CITE_REFINERY_WORKSPACE=str(workspace))
    params = StdioServerParameters(command=sys.executable,
        args=['-m','portfolio_mcp.cli','serve','--manifest',str(root/'integrations/mcp/manifest.json'),
              '--root',str(root)], env=env)
    async def exercise():
        async with asyncio.timeout(30):
            async with Client(params) as client:
                listed = {t.name for t in (await client.list_tools()).tools}
                assert 'cite_refinery_dossier' in listed
                assert 'cite_refinery_create_project' not in listed
                result = await client.call_tool('cite_refinery_dossier', {'project_id':project.id})
                assert not result.is_error
                assert result.structured_content['result']['project']['id'] == project.id
                denied = await client.call_tool('cite_refinery_create_project', {'title':'No','problem':'No'})
                assert denied.is_error
    asyncio.run(exercise())
