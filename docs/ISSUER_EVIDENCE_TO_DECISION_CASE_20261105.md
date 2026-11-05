# Manulife Q1 2024 vs Q1 2023 — end-to-end research product demonstration

**2026-11-05 | Atlas + Research Drive | Research triage, not investment advice**

## Real decision the output supports

The working question is why Manulife's issuer non-GAAP core earnings increased while net income attributed to shareholders declined in the first quarter of 2024 relative to the first quarter of 2023, and what source evidence allows a researcher to prioritize investigation.

The deliverables are now **readable finished research outputs**, not merely parser performance receipts:

- Standalone HTML: reports/manulife_1q24_vs_1q23_decision_brief_20261105.html
- GitHub-readable Markdown: reports/manulife_1q24_vs_1q23_decision_brief_20261105.md
- Machine-readable source and calculation receipt: examples/discovery/manulife_1q24_vs_1q23_decision_dossier_20261105.json
- Reproducible offline generator: scripts/issuer_financial_dossier.py

## Primary source and extraction integrity

The workflow reuses Research Drive's existing original SEC EDGAR filing witness: issuer CIK, source URL, bytes and SHA-256, original table labels, currency and unit headers, explicit reporting-period columns, and source cell values. Its two **issuer-authored original SEC HTML exhibits** are:

- Shareholder report: https://www.sec.gov/Archives/edgar/data/1086888/000119312524134354/d798617dex991.htm
- Earnings release: https://www.sec.gov/Archives/edgar/data/1086888/000119312524134343/d798735dex991.htm

The 2026-11-05 downloads were stable on an immediate repeat source fetch, but each was six bytes shorter than the earlier pinned capture. This run **explicitly reports both the old and new SHA**, retains the old immutable receipt, and independently validates the original source labels and numeric values under the new exact byte pins. The issuer HTML originals remain private and are not copied into Git.

The original 1Q24 anchors still check **8/8** against the issuer shareholder report, **7/7** in the earnings release, and **1/1** expense qualifier. Historical 1Q23 rows are then read from original labeled historical columns. Seven comparable historical metric pairs agree across the two exhibits; three more expense context pairs come from the shareholder report alone. Both documents are from the **same issuer**, not independent external auditors or reviewers.

The prior secondary arXiv figure's original PDF SHA is rechecked. Its **6/8 strict parser matches and two abstentions stay unchanged**; issuer HTML corroboration cannot silently fix the two parser errors.

## Verified decision-relevant finding

| Indicator | 1Q24 | 1Q23 | From displayed source values |
|---|---:|---:|---:|
| Net income attributable to shareholders | C$866m | C$1,406m | -38.4% |
| Core earnings (non-GAAP) | C$1,754m | C$1,531m | +14.6% |
| APE sales | C$1,883m | C$1,600m | +17.7% |
| New business CSM | C$658m | C$442m | +48.9% |
| New business value | C$669m | C$509m | +31.4% |
| Core expenses | C$1,673m | C$1,605m | +4.2% |

The core-earnings-minus-net-income *arithmetic* gap widened from C$125m to C$888m. That is a material research prioritization signal but **not proof of what caused the difference**.

The issuer's published change rates are distinct from raw nominal arithmetic and may use constant-exchange-rate or non-GAAP adjustments; for example, printed APE sales nominal growth is +17.7% whereas the issuer's change column reports **21%**. The final report keeps both, not a forced reconciliation.

**Action:** examine the MD&A's reported-to-core earnings reconciliation and currency definitions before making causal or investment claims.

## Product acceptance — no self-serving parser score

| Check | Actual result |
|---|---:|
| Original issuer-authored SEC HTML documents directly verified | 2 |
| Original 1Q24 issuer row witnesses | 8 + 7 + one context |
| 1Q23 versus 1Q24 comparisons in finished report | **10** |
| Historical metrics corroborated in second filing from same issuer | **7** |
| Expense measures from shareholder filing alone | **3** |
| End-to-end offline data processing (excluding network acquisition) | approximately 10 seconds |
| Finished reader-facing deliverables | HTML, Markdown, source JSON |
| Independently adjudicated analyst interpretation | **0** |
| Trusted PDFScope/dataset promotion | **0** |
| Auto-publishing or production deployment | **none** |

Source and math integrity tests reject changed historical denominators, forged earnings-gap arithmetic, missing source-exhibit corroboration and unsupported source URLs. Source data was verified on the authorized machine; no original issuer HTML was included in public test fixtures. No external human validated causation, investment suitability or the completeness of issuer disclosures.

## Product next step

This case demonstrates **source-to-decision research handoff** with existing integrated infrastructure, not autonomous extraction from all PDFs and not automatic financial investigation. The next valuable validation is a second issuer from a distinct filing format, with a real independent analyst evaluating the resulting report and review effort. Further PDF edge-case work should be driven by those workflow blockers, not automatic component optimization.

**Both PRs remain open drafts, unmerged and undeployed. No human-reviewed or trusted dataset claim has been made.**
