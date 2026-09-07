# Cite-Refinery

**Cite knows. Refinery builds. Cite-Refinery closes the loop.**

Cite-Refinery is the orchestration layer between empirical research and solution construction. A project begins as a real problem, accumulates explicit claims and evidence, acquires or builds capabilities in a project-local Refinery overlay, executes implementations, records validation, and promotes proven capabilities into a shared registry for reuse by later projects.

It is intentionally not another chat surface and not a replacement for either upstream system:

- **Cite-Agent** owns research, grounding, evidence and citation semantics.
- **Refinery** owns capability discovery, implementations and reusable solution components.
- **Cite-Refinery** owns the cross-project lifecycle, provenance chain, execution record and promotion loop.

## Architecture

```text
problem / external challenge
          |
          v
   claims + questions
          |
          v
  Cite-Agent ground_claims  <---- empirical evidence
          |
          v
 project Refinery overlay   <---- shared capability registry
          |
          v
  implementation execution
          |
          v
   run record + artifacts
          |
          v
 experiments / validation
          |
          v
 promote proven capability
          |
          +----------------------> shared registry -> next project
```

Each project is an **overlay**, not a fork of the entire platform. Project-local `rcap:*` capabilities and `rimpl:*` implementations remain private while they are being developed. A later project cannot discover or execute them. After a passed/supported experiment, a capability can be promoted to shared state; executable capabilities additionally require a successful linked `rrun:*` before promotion.

## Current integration

### Cite-Agent

The production adapter calls Cite-Agent's real grounding surface:

```bash
cite-agent tool ground "<claim or paragraph>"
```

That command delegates to `ground_claims`. Set `CITE_AGENT_COMMAND` when Cite-Agent is invoked another way, for example:

```bash
export CITE_AGENT_COMMAND="python -m cite_agent.cli"
```

If Cite-Agent is absent or fails, Cite-Refinery records that grounding did **not** run. It never converts an unavailable research backend into fabricated evidence or a "supported" claim.

### Refinery execution

The fusion has a provider boundary for implementations. The built-in `subprocess` provider executes an explicitly registered argv vector with `shell=False`. Runtime project input is serialized to JSON stdin by default rather than interpolated into a shell command. Runs record status, structured stdout when JSON is returned, stderr, exit code and duration.

This repository keeps the `rcap / rimpl` contract independent of historical internal paths in `alpha-platform`. A current/historical Refinery or MCP execution plane can therefore be connected as another provider without changing project state or machine IDs.

## Quick start

```bash
python -m pip install -e .

cite-refinery init "Pilot project" --problem "A real unresolved problem"
# -> copy the returned rproject:* id

cite-refinery claim-add rproject:... "Intervention X improves outcome Y."
cite-refinery ground rproject:...

cite-refinery cap-add rproject:... "Anomaly detector" \
  --description "Detect anomalous observations before downstream analysis" \
  --tag anomaly --tag validation

cite-refinery cap-search rproject:... "anomaly validation"

cite-refinery impl-add rproject:... rcap:... subprocess \
  --invocation-json '{"argv":["python","detector.py"]}'

cite-refinery invoke rproject:... rimpl:... \
  --input-json '{"dataset":"fixtures/holdout.json"}'
# -> returns rrun:...

cite-refinery artifact-add rproject:... "detector-v1" \
  --kind software --description "First working implementation" --reusable \
  --capability-id rcap:...

cite-refinery experiment-add rproject:... "holdout validation" \
  --method "frozen holdout" --result "passed acceptance threshold" \
  --verdict passed --metrics-json '{"precision": 0.91, "recall": 0.87}' \
  --run-id rrun:...

cite-refinery promote rproject:... rcap:... --experiment-id rexp:...
cite-refinery dossier rproject:... --format markdown --out dossier.md
```

State lives in `.cite-refinery/state.json` by default. Writes are atomic and the event ledger is append-only at the application level, making the lifecycle inspectable without requiring a database for the integration layer.

## Machine IDs

| Prefix | Meaning |
| --- | --- |
| `rproject:*` | project / problem branch |
| `rclaim:*` | explicit claim to audit |
| `revidence:*` | attached evidence record |
| `raudit:*` | Cite-Agent grounding audit |
| `rcap:*` | reusable capability |
| `rimpl:*` | implementation of a capability |
| `rrun:*` | recorded implementation execution |
| `rart:*` | build artifact |
| `rexp:*` | experiment / validation |
| `revt:*` | lifecycle event |

## Promotion invariant

Promotion is intentionally asymmetric:

1. A project-local capability must have a **passed** or **supported** experiment.
2. If the capability has executable implementations, the experiment must link at least one **successful run of that capability**.
3. Implementations proven by those runs are marked validated before being cloned into shared state.
4. The promoted global capability records the originating local capability, project, experiment, metrics and successful run IDs in provenance.

This prevents a project from turning an unexecuted implementation into a globally reusable capability by metadata alone.

## Design constraints

1. **Evidence is not a decoration.** Claims stay unverified unless a grounding/validation step actually runs.
2. **Machine IDs survive UI changes.** Human labels can change without breaking references.
3. **Branches compound instead of fragment.** Local work is isolated during development, then explicitly promoted into shared capability state.
4. **Build and research remain separate authorities.** Refinery does not invent empirical support; Cite does not pretend a paper is an implementation.
5. **Execution is provenance.** Runs are persisted and can be cited by experiments instead of relying on an informal assertion that code worked.
6. **Outputs are auditable.** The dossier joins problem, claims, audits, evidence, capabilities, implementations, runs, artifacts, experiments and lifecycle events.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers the full evidence-to-build lifecycle, real subprocess execution, structured input/output, failure capture, branch isolation, cross-project execution denial, validation-gated promotion, reuse of a promoted implementation by a later project, local-over-global resolution, and the no-fabricated-evidence Cite fallback.

## Next adapters

The core lifecycle is backend-neutral. Remaining work is integration depth rather than another architecture rewrite:

- direct Cite-Agent structured/MCP result ingestion so evidence locators can flow into `revidence:*` automatically,
- current/historical Refinery/`alpha-platform` and MCP execution-provider adapters,
- GitHub artifact/commit ingestion for code provenance,
- richer evaluator policies for domain-specific promotion gates,
- UI/project templates on top of the stable machine-ID lifecycle.
