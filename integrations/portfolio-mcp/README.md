# Portfolio MCP adapters

A small stdio transport for existing project engines. This package adds no domain
engine, database, model provider, capability ontology, or automatic agent loop.

A reviewed `integrations/mcp/manifest.json` selects either an existing MCP server
(`native`) or fixed calls to the project's current CLI (`bridge`). Native servers
are executed unchanged; their tools are not duplicated into another registry.

## Install and connect

Use a separate Python 3.11+ environment for this runner:

```bash
python -m venv .venv-mcp
.venv-mcp/bin/pip install -e integrations/portfolio-mcp
.venv-mcp/bin/portfolio-mcp validate \
  --manifest /checkout/PROJECT/integrations/mcp/manifest.json --root /checkout/PROJECT
.venv-mcp/bin/portfolio-mcp probe \
  --manifest /checkout/PROJECT/integrations/mcp/manifest.json --root /checkout/PROJECT \
  --engine-python /checkout/PROJECT/.venv/bin/python
```

`validate` checks configuration/source-file presence, not functionality. `probe`
performs a real initialize and tools/list handshake, not a domain workflow.
The owning project must already be installed in `--engine-python`'s environment.
Do not combine legacy MCP v1 applications with the runner's MCP v2 dependencies.
For Cite and Research Drive, retain a compatible v1 engine environment; the two
processes communicate over the negotiated protocol, not shared Python imports.

Example client configuration (replace absolute paths):

```json
{"mcpServers":{"nocturnal":{"command":"/checkout/cite-refinery/.venv-mcp/bin/portfolio-mcp","args":["serve","--manifest","/checkout/nocturnal-oversight/integrations/mcp/manifest.json","--root","/checkout/nocturnal-oversight","--engine-python","/checkout/nocturnal-oversight/.venv/bin/python"]}}}
```

Cite-Refinery additionally requires the operator-owned `CITE_REFINERY_WORKSPACE`
environment variable. Each server receives only the manifest's explicit variable
allowlist plus a small base environment. Extend that list explicitly for required
provider/storage settings. No credential belongs in a committed manifest.

## Application-side use

`portfolio_mcp.client.StdioConnection`, `inspect_server`, and `invoke` allow another
application to use any configured server. Always check `is_error`; a returned
object is not proof of success. Preserve native evidence IDs and statuses.

Bridge results contain the unchanged native result plus input/output/manifest
hashes and the process exit code. These are execution receipts only, not proof
of an exact source revision, scientific validity, permission, or source truth.
Native MCP servers preserve their own result contracts instead of gaining this
envelope. Consumers must adapt those contracts explicitly.

## Boundaries

Manifests and executables are trusted operator configuration. This is not an OS
sandbox. Caller data never chooses an executable, arbitrary command, working
directory, environment variable name, or file path. JSON file inputs are staged
in private temporary directories and removed after use. Calls are serialized per
bridge process, time-limited, and limited to one megabyte per input/output stream.
Persistent writes are hidden and rejected unless `--allow-writes` is supplied.
There is no submit/send, blockchain transfer, device actuation, or trade tool in
the bridge manifests. Native servers retain their existing authorization model;
`--allow-writes` is not a filter or an authority override for native mode.

This release is local stdio only. Do not expose it through an unauthenticated
public HTTP gateway. Remote auth, per-user storage isolation, deployment, and
long-running durable jobs are separate work. Repeated application-client calls
start new server processes; persistent state must live in a configured store.

## Tests and evidence

```bash
python -m pip install -e 'integrations/portfolio-mcp[dev]'
python -m pytest integrations/portfolio-mcp/tests -q
```

The runtime tests use clearly identified subprocess fixtures. Protocol tests
require the real MCP SDK; absence is a skip, not a pass. The native Cite-Refinery
test uses the actual project lifecycle and a real stdio connection. No mocked
transport result establishes another portfolio application's deployment or
complete product-surface coverage.
