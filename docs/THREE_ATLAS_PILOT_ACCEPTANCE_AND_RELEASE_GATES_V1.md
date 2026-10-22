# Standalone Research Pilot — Verified Acceptance and Release Gates

**22 October 2026, first portable preview.** This is a reproducible, read-only research-workspace demonstration, not a hosted or production release.

## What was actually exercised

GitHub Actions at PR #106 / commit `d0909c6b3a5a9cce5fb15cf4525f94dedf0ef75d`:
- `tests`, run **39741708261**: completed **success**. **596** unit tests, one skipped, no failures.
- `Three-layer map foundations`, run **39741708265**: completed **success**. Full source-index validation, 8 Europe PMC structural checks, 44 pinned GitHub repository source checks (39 original code file samples SHA-verified), two source-pinned original code replays and prototype compilation.
- Artifact `cite-refinery-three-layer-foundations`: ZIP created by the workflow containing `standalone-research-pilot/index.html`, `standalone-research-pilot/atlas.json`, `standalone-research-pilot/README.txt`.

The generated `atlas.json` was extracted and inspected: schema `cite_refinery.standalone_research_pilot.v1`, **1,497** index records = Practical 57, Academic 150, Implementation 1,290. It reports exactly **103** Academic development documents, **66** held-out documents excluded, **2** original Implementation tested modules, **1** original test failure, **zero** independently validated scientific findings, **zero** live Implementation operational outcomes. It reports **no attached public Nocturnal matter snapshot**, so the Practical index is correctly limited to the original 9 provisional reports and 48 separate notice-context leads.

## Browser acceptance

The generated 1.36 MB `index.html` was loaded into headless Chromium using Playwright `page.set_content(html)`, because this automated container blocks direct `file://` navigation by administrative policy. The page itself has no browser `fetch`, external script or backing service.

Observed:
- Browser JavaScript execution: **no uncaught page errors**.
- Header counters: **57**, **150**, **1,290**, **2**.
- Practical tab initially shows 57 source records, Academic tab 150 and Implementation tab 1,290.
- Implementation query `blisspixel`: **1** match; the original pinned `blisspixel/recon` record opens its source dossier.
- Implementation query `Mr-Fang-VLSI/EDAgent`: **1** match; the dossier visibly retains `design_comment_is_not_real_layer: fail` with original observed `PHANTOM` output.
- Source-dossier JSON download is emitted as `cite-refinery-dossier.json`.
- Unknown search produces an explicit **zero-result** state.
- Academic evidence-class filter `development_source`: **103** entries.

The visible UI is usable on a desktop Chromium viewport and has responsive CSS for smaller screens. A separate human pass on local `file://` browsers, mobile screen readers, and shared-hosting authorization remains to be done.

## What is not validated

The browser presents source-index identities and isolated test receipts; it **does not** independently read and reason over full paper methods/results, adjudicate contradictory witnesses, prove actual practical outcomes or guarantee the suitability of repositories. It does not establish coverage representativeness. No automatic semantic synthesis or verified cross-layer connection exists. It is not a replacement for a primary-source reader and currently has no interactive correction/review-authoring workflow.

### Real release blockers

1. **Stack consolidation:** GitHub PRs **#98 → #99 → #100 → #101 → #102 → #103 → #104 → #105 → #106** form an ordered draft stack. #98 itself targets a feature branch rather than `main`. Before a mainline merge, determine and review the actual release base, then integrate/rebase sequentially, rerun focused plus full CI, inspect the resulting final diff and tag a release. Avoid silently merging one early PR with a base that does not contain the tested dependent implementation.
2. **Nocturnal source-publication boundary:** private `nocturnal-oversight` PR **#111** still has failing CI. Do not import real Nocturnal data or claim the Practical public pipeline works end-to-end until that contract passes and a separately approved publication manifest is available.
3. **Academic depth:** although 103 material records are indexed and eight original JATS structures checked, no original-text-based methods/results synthesis has yet been independently accepted as correct, and no sealed holdout source may be used for product improvement until a properly logged blind evaluation.
4. **Implementation sample size:** 44 pinned source identities / 39 inspected code samples are not the same as 44 working implementations; only 2 of 1,287 survey repositories had bounded, independently executed module fixtures.
5. **Product usability evaluation:** at least one unrelated user must perform source-finding, claim qualification and dossier-export tasks independently; record correctness, unsupported assertions, navigation time and explanation clarity.
6. **Production identity and provenance:** authentication, access control, long-lived artifact signature, hosted runtime, publication permissions and enterprise-grade durability remain absent. A standalone file is an appropriate **local pilot**, not a production multi-tenant intelligence service.

## Recommended next milestone

Rather than adding another isolated library integration: conduct a bounded **field-based usability/evidence challenge** on each map, write a source-by-source verified dossier for a selected domain (or representative source groups), and only then merge the stacked release behind the same nonpromotion gates. Retain original source failures and unreviewed records. Keep Practical, Academic and Implementation independently useful; defer cross-layer monetization or grant targeting until evidence quality is established.
