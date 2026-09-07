# Cite-Refinery

**Cite knows. Refinery builds. Cite-Refinery closes the loop.**

Cite-Refinery is the orchestration layer between empirical research and solution construction. A project begins as a real problem, accumulates explicit claims and evidence, acquires or builds capabilities in a project-local Refinery overlay, records implementation artifacts and experiments, and promotes validated capabilities into a shared registry for reuse by later projects.

It is intentionally not another chat surface and not a replacement for either upstream system:

- **Cite-Agent** owns research, grounding, evidence and citation semantics.
- **Refinery** owns capability discovery, implementations and reusable solution components.
- **Cite-Refinery** owns the cross-project lifecycle, provenance chain and promotion loop.

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
 implementation artifacts
          |
          v
 experiments / validation
          |
          v
 promote reusable capability
          |
          +----------------------> shared registry -> next project
```

Each project is an **overlay**, not a fork of the entire platform. Project-local `rcap:*` capabilities and `rimpl:*` implementations remain private to that branch while they are being developed. After validation they can be promoted to global capabilities, where every later project can discover them.

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

### Refinery

This repository contains a small persistence-backed `rcap / rimpl` kernel with the same capability-first boundary needed by the fusion. It deliberately does not hard-wire the orchestrator to historical internal paths from `alpha-platform`; a future/current Refinery execution backend can be attached behind this boundary without rewriting project state.

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

cite-refinery artifact-add rproject:... "detector-v1" \
  --kind software --description "First working implementation" --reusable

cite-refinery experiment-add rproject:... "holdout validation" \
  --method "frozen holdout" --result "passed acceptance threshold" \
  --verdict passed --metrics-json '{"precision": 0.91, "recall": 0.87}'

cite-refinery promote rproject:... rcap:... --experiment-id rexp:...
cite-refinery dossier rproject:... --format markdown --out dossier.md
```

State lives in `.cite-refinery/state.json` by default. Writes are atomic and the event ledger is append-only at the application level, making the lifecycle inspectable without requiring a database for the first integration layer.

## Machine IDs

| Prefix | Meaning |
| --- | --- |
| `rproject:*` | project / problem branch |
| `rclaim:*` | explicit claim to audit |
| `revidence:*` | attached evidence record |
| `raudit:*` | Cite-Agent grounding run |
| `rcap:*` | reusable capability |
| `rimpl:*` | implementation of a capability |
| `rart:*` | build artifact |
| `rexp:*` | experiment / validation |
| `revt:*` | lifecycle event |

## Design constraints

1. **Evidence is not a decoration.** Claims stay unverified unless a grounding/validation step actually runs.
2. **Machine IDs survive UI changes.** Human labels can change without breaking references.
3. **Branches compound instead of fragment.** Local work is isolated during development, then explicitly promoted into shared capability state.
4. **Build and research remain separate authorities.** Refinery does not invent empirical support; Cite does not pretend a paper is an implementation.
5. **Outputs are auditable.** The dossier joins problem, claims, audits, evidence, capabilities, artifacts, experiments and lifecycle events.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The test suite covers the full project lifecycle, branch isolation/promotion, local-over-global resolution, and the no-fabricated-evidence failure path.

## Next adapters

The kernel is deliberately small so the next work can concentrate on real backends rather than migration:

- direct Cite-Agent structured/MCP result ingestion (preserving evidence locators rather than only audit output),
- current Refinery/`alpha-platform` execution-provider adapter,
- GitHub branch/artifact ingestion,
- project templates and reusable capability packs,
- evaluator/acceptance-policy gates for promotion.
