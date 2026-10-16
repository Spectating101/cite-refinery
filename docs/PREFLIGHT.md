# Cite-Refinery preflight

Run a local, non-network readiness check before starting a project:

```bash
cite-refinery preflight
```

The report distinguishes **core readiness** from **full broad-supply readiness**.

Core readiness requires:

- a writable Cite-Refinery workspace;
- Cite-Agent grounding (`cite-agent tool ground`);
- Cite-Agent deterministic deep research (`cite-agent-research deep`);
- canonical Refinery search (`refinery search`).

The broader reviewed-market lane is reported separately. It is ready when:

- `refinery-market-search` is installed; and
- a reviewed-market database is available either through `REFINERY_MARKET_DB` or at the canonical snapshot-restore path:

```text
~/.local/share/refinery/reviewed-market-search.db
```

To require that broader lane in automation:

```bash
cite-refinery preflight --require-reviewed-market
```

The command exits nonzero when the requested readiness level is not met and includes a recovery action for every missing surface.

## What preflight does not prove

Preflight intentionally performs no live research. It does not validate API credentials, source accessibility, network availability, empirical source fidelity, literature quality, or whether a specific project will find useful solutions. It only verifies that the local orchestration interfaces and restored state needed to attempt the workflow are present.
