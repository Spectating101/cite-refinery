# Refinery supply layers

Cite-Refinery treats Refinery as two distinct solution-supply authorities.

## 1. Canonical Commons / operational supply

Canonical `refinery search` exposes curated capability and implementation state. A hit here can describe a reusable capability or an operational implementation, subject to Refinery's own validation, rights and execution policies.

Cite-Refinery does not weaken those gates. Adoption remains project-local until the existing run/experiment/promotion rules are satisfied.

## 2. Reviewed market supply

When `REFINERY_MARKET_DB` points to a reviewed market-graph database and `refinery-market-search` is installed, Cite-Refinery also queries that directory.

A reviewed-market result means only that a resolved product/repository entity has audited accepted descriptive relations whose text overlaps the requirement. It does **not** mean:

- the product is recommended or high quality;
- the capability is admitted to Commons;
- source or software rights are cleared;
- an implementation is executable;
- a market or demand claim has been established;
- the candidate is validated for the current problem.

The solution map records candidate authority separately. Typical authority values are:

- `commons`
- `operational`
- `reviewed_market_graph`
- `unspecified`

`reviewed_market_graph` candidates can inform an explicit `cap-adopt` decision, but adoption still creates only a project-local capability. An implementation must still be registered, executed and validated before it can be promoted.

## Configuration

Canonical Refinery remains the default and requires no new configuration.

To add the broader reviewed directory:

```bash
export REFINERY_MARKET_DB=/path/to/current-reviewed-market-graph.db
# optional override if the command is installed under another entry point
export REFINERY_MARKET_COMMAND=refinery-market-search
```

If the database or reviewed-market command is absent, the market lane reports `not_run` and the canonical lane continues normally. If market search errors while canonical search succeeds, the layered result reports `partial`; the failure is not silently hidden.

## Why the split matters

Refinery's broader market graph is valuable because it maps more programs and repositories than the small reusable Commons. But descriptive market evidence and reusable implementation authority answer different questions:

```text
reviewed market graph:  "what products/repos are evidenced as doing something related?"
canonical Commons:       "what reusable capability/implementation is admitted here?"
Cite-Refinery project:   "which candidate should we evaluate for this problem?"
experiment/promotion:    "what did we actually prove reusable?"
```

Keeping those layers visible lets Cite-Refinery expand solution recall without turning a directory hit into a claim that software is safe, reusable or effective.
