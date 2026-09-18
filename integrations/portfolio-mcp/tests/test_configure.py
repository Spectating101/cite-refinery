import json
import os
import sys
from pathlib import Path
import pytest
from portfolio_mcp.configure import build_client_config, executable


def config(tmp_path):
    path = tmp_path/'integrations/mcp'; path.mkdir(parents=True)
    (tmp_path/'engine.py').write_text("raise AssertionError('Configuration must not execute engines')")
    (path/'manifest.json').write_text(json.dumps({
        'schema':'portfolio.mcp.manifest.v1','project':'fixture','mode':'native',
        'argv':['$PYTHON','engine.py'],'required_files':['engine.py']}))
    return {'runner_python':sys.executable, 'servers':{'fixture':{'root':str(tmp_path),'engine_python':sys.executable}}}


def test_configure_is_nonexecuting_and_explicit(tmp_path):
    result = build_client_config(config(tmp_path))
    entry = result['mcpServers']['fixture']
    assert entry['command'] == sys.executable
    assert '--allow-writes' not in entry['args']
    assert str(tmp_path/'integrations/mcp/manifest.json') in entry['args']


def test_missing_engine_source_fails(tmp_path):
    spec = config(tmp_path); (tmp_path/'engine.py').unlink()
    with pytest.raises(ValueError): build_client_config(spec)


def test_unknown_configuration_field_fails(tmp_path):
    spec = config(tmp_path); spec['servers']['fixture']['shell'] = 'touch unwanted'
    with pytest.raises(ValueError): build_client_config(spec)


def test_native_write_flag_never_implies_authorization(tmp_path):
    spec = config(tmp_path); spec['servers']['fixture']['allow_writes'] = True
    with pytest.raises(ValueError, match='Native permissions'): build_client_config(spec)


def test_no_relative_interpreter():
    with pytest.raises(ValueError): executable('python')


@pytest.mark.skipif(os.name != 'posix', reason='POSIX symlink semantics')
def test_venv_interpreter_symlink_is_preserved(tmp_path):
    venv = tmp_path/'venv/bin'; venv.mkdir(parents=True)
    selected = venv/'python'; selected.symlink_to(sys.executable)
    assert executable(str(selected)) == str(selected)
    assert executable(str(selected)) != str(selected.resolve())
