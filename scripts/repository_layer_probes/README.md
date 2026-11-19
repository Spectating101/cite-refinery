# Bounded repository-layer probes

These scripts produce execution receipts for explicitly scoped technical behavior.
They do not update the catalogue, wire into an existing agent, call a paid model,
or establish general production suitability.

## Environment

Use an isolated Python environment and preserve its installation report. The
reported 19 November 2026 runs used:

| Probe | Executed packages |
| --- | --- |
| Exact STEP transfer | `smlibpy==0.6.2`, `cadquery==2.7.0`, `cadquery-ocp==7.8.1.1.post1`, `numpy==2.3.5`; Python 3.12, Linux x86_64 |
| Trace integrity | `tracekit-ai==1.7.2`, `cryptography==50.0.1`, `rfc8785==0.1.4`; Python 3.13, Linux x86_64 |

For example, `python -m pip install --report install-report.json ...` preserves
the actual downloaded package URLs and hashes. Use the interpreter from that
environment for both the install and the probe. Already-installed dependencies
are identified by version in each execution receipt; they are not falsely
reported as new wheel downloads.

## Exact geometry exchange

```sh
python scripts/repository_layer_probes/probe_smlibpy.py \
  --output-dir /tmp/repository-probe-smlibpy \
  --installation-receipt /tmp/probe-environment/install-report.json
```

The script constructs two SMLib solids, exports STEP, and reads each file through
CadQuery/OpenCascade. The checks compare the imported solid with independent
analytical volume, bounds and bore positions/radii, plus BRep validity and solid
count. The second case includes corner fillets, four through bores and a recess.
The source and reader use different geometry kernels. Two passing files do not
qualify arbitrary parts, assemblies, unit conversion, manufacturing or an HS
integration.

## Trace integrity

```sh
python scripts/repository_layer_probes/probe_tracekit.py \
  --output-dir /tmp/repository-probe-tracekit \
  --installation-receipt /tmp/probe-environment/install-report.json
```

The script starts a temporary same-user signer and operator-controlled test
witness, asks permission for one harmless fixture read, performs it, records its
result, and exports a bundle. It shuts down the signer before verifying the
bundle in a fresh process. A second bundle changes the signed policy decision
from `allow` to `deny` without re-signing. Verification must accept the original
and reject the changed record.

Only the fixture, bundles, public trust configuration and receipt are retained.
The temporary signing store and socket are removed in `finally`. This requires
Unix sockets; a restricted runtime may block before capture. The 19 November
cloud runtime did so, and the executed pass was obtained in an isolated OptiPlex
environment. No persistent agent hooks or services were installed.

The test witness is classified as **operator**, so the verification assurance is
local. These checks establish the observed integrity behavior only. They do not
prove hostile-agent isolation, independent witnessing, truthful results, complete
capture, source-document preservation or Nocturnal integration.

## Outputs

Each probe writes `execution.json`, records interpreter/package versions and the
probe-script/installation-receipt hashes, and preserves its output artifacts by
SHA-256. A zero exit means the bounded checks passed. An execution receipt can be
curated into the repository layer only with its scope and limitations intact.
