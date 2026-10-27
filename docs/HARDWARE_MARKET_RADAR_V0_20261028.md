# Hardware Market Radar v0 — first executed cross-industry opportunity loop

**Branch:** `feature/hardware-market-radar-v0-20261028`, stacked on research PR #132, NOT merged into main.
**Status:** offline curated-source prototype; **NOT an autonomous website crawler, in-stock checker, supplier-quote verifier, buyer outreach system, purchase bot, actual manufacturability test, or revenue engine.**

## What now exists

- `src/cite_refinery/hardware_market_radar.py` — stdlib-only CLI and pure evaluators with canonical SHA-256 source snapshot; strict dated, named, publicly attributed source observations.
- `research_materials/opportunity_conversion/hardware_radar_observations_seed_20261028.json` — 12 dated references from earlier market work spanning 11 cases. Price information is retailer/manufacturer *asking* information, including one HISTORICAL aquaculture figure. Zero verified live stock or transactions.
- `research_materials/opportunity_conversion/hardware_radar_capabilities_20261028.json` — explicit technical requirements of 12 cases and 13 attributed HS / external capability candidates. Draft HS PRs flagged draft, not merged. A tag overlap is only a proposed engineering-reuse investigation, never proof of component compatibility or available modules.
- `research_materials/opportunity_conversion/hardware_radar_supplier_candidates_20261028.json` — 14 source-linked vendor/manufacturer/fabrication directory entries with broad catalog tags, deliberately unqualified (no matched SKU, quote or proven market service).\n- `tests/test_hardware_market_radar_v0.py` — 13 deterministic tests including the actual 64-catalog/12-case evaluation, different current vs historical sellers, non-local global products, duplicate/future/invalid source, malicious self-certified demand, snapshot changes and no falsely computed income.
- `.github/workflows/hardware-market-radar-offline.yml` — GitHub Actions runs tests and actually calls the CLI twice, comparing stable snapshots.

## Reproduction

```sh
python -m pip install -e .
python -m unittest tests.test_hardware_market_radar_v0 -v
python -m cite_refinery.hardware_market_radar --as-of 2026-10-28 > /tmp/hardware-radar.json
python -m cite_refinery.hardware_market_radar --as-of 2026-10-28 --previous /tmp/hardware-radar.json > /tmp/hardware-radar-comparison.json
```

When market observations have been refreshed in the supplied JSON, rerun with the old saved report via `--previous` to see `new`, `revised`, and `missing_from_input_not_stockout`. A deleted row from the analyst's source file is *not* a confirmed delisted product.

The CLI `--observations`, `--catalog`, `--cases`, `--capabilities`, `--output` accept local JSON paths. No network access is attempted. It makes no file writes unless explicitly given `--output`.

Expected baseline shape:
- 64 concept hypotheses / 16 sectors
- 12 cross-industry cases, including one with no observations
- 12 individual attributed market observations (some local, some global, some historical, some supplier discovery)
- Several potential cross-sector reuse links through ESP-IDF, HS firmware, mechanical design, IoT, PCB tools, vision/simulation and instrumentation\n- 14 **unqualified** supplier/fabrication reference catalogs with deterministic candidate tag-overlap edges (NOT a qualified supplier graph)
- **Zero qualified commercial opportunities, verified supplier quotes, customer payments, physical builds or profit projections**

Every input observation is subject to validation; `buyer_verified`, `paid_sale_verified`, `stock_verified`, `supplier_qualified` declarations are REJECTED. Exact matched product functions are unverified, source URLs are attributed but not independently authenticated, and future-dated sources are rejected. Output includes provenance fingerprints, not a guarantee that a page is true or was reachable. Scores and implied ROI are deliberately omitted.

## Two independent graphs, not a universal recommender

**Market graph:** case → source observation → named seller/reference, including region, price only if recorded, evidence status, exact-variant comparability flag. Sector-wide references are not presented as local inventory.

**Engineering capability graph:** case → explicit needed tag ↔ HS feature or external technical system, preserving maturity. Shared tags across cases identify **where to investigate reuse** (e.g. microcontroller firmware across education and agriculture, sensors/telemetry across farms and monitoring), not a validated common bill of materials.\n\n**Supplier candidate graph:** case → needed tag ↔ source-linked public component vendor, manufacturer or fabrication directory. Every edge is `CATALOG_TAG_OVERLAP_ONLY`; catalog breadth cannot verify target model SKU, geographic service, MOQ, quote, right to integrate or distribution agreement. Manufacturers already selling competitor products remain distinguished in the **market graph**.

This intentionally complements rather than copies:
- Cite–Refinery market-demand screen #128 and business workbench #127 (both draft) for actual buyer qualification, experiments and money controls.
- HS commercial router #214 (draft) for specific repair/source/build financial pathways.
- HS engineering freeze #227 for electronics, firmware, mechanics and physical-evidence readiness.
- HS operator research #228 for MRO/service.
- Cross-industry research PR #132 (parent of this stack).

## Next actual verification, before autonomous monitoring

1. **Source-refresh adapter:** choose legally permissible, stable public APIs/feeds or operator curation in each target market; capture observation timestamp, original content/fingerprint, product identity, variant and seller. This prototype currently only compares input snapshots: it does **not** independently fetch fresh prices.
2. **Market completeness:** more than one independently indexed local substitute per case and clearly missing markets. Match function/warranty/retailer/subscription/availability, don't compare a bare sensor to a full installed system.
3. **Buyer signal:** at least one attributable paid acquisition or direct buyer research in each considered segment. Keep any buyer contact separately permission-gated.
4. **Supplier graph:** actual ODM/parts quote, MOQ, incoterms, importer/certification status and samples. A reference brand or component library is **not** yet a qualified vendor.
5. **Engineering test:** real functional spec against a competitor and independently measured physical outputs, plus HS revision/firmware/geometry constraints. CI success cannot satisfy this.
6. **Commercial**: feed evidenced cases to #127/#128 and HS #214 and get authorized validation budget, kill criteria, and paid contract/transaction receipts before claiming revenue.

## First data decision

For now, retain a **diverse validation portfolio** spanning companion/pet electronics, education, farm/aquaculture, industrial MRO/vision, power/cold-chain, lab instrumentation. Treat `PUBLISHED_LOCAL_OFFER_EXISTS` as proof that seller material was collected, not stock, transaction, demand, exclusivity, shortage or arbitrage margin. Any opportunity that cannot show a real reason to beat/bundle with an established product remains on `RESEARCH_MORE_OR_HOLD`.

No outbound contact, web scrape, manufacturing action, trade transaction, user device access, or automated job scheduling occurs in this implementation.
