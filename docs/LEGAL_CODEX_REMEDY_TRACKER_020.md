# Legal Codex 020 — track the remedy actually evidenced

Research checked: **18 November 2026**. This addition builds on the three Dutch decisions captured in 019 and newly recovers the Finnish decision through its documented public XML endpoint.

## What changed

The new tracker evaluates **12 separately scoped remedy components and 27 source-bound events across four cases**. It distinguishes an access decision, a recipient's reported receipt, the adequacy of the material, fulfillment of a particular order, and penalty execution. A generic receipt cannot close a later explanation order or an obligation in a different case.

The real example contains **three components that a court or regulator expressly treated as fulfilled**: the 2026 hospital medical-file copy, that hospital's other-personal-data overview, and the later Finnish log period. These are attributed public findings, not possession of the underlying records. They are not a success rate: the components and cases were purposefully selected and are not comparable independent observations.

The Finnish source was a failed raw-capture lead in 019. It is now a separately successful 020 acquisition. The earlier failed workflow and its five-target result remain unchanged.

## Source findings

| Source | Component and result | What remains unverified |
|---|---|---|
| [ECLI:NL:GHARL:2024:5384](https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:GHARL:2024:5384), 26 August 2024 | Orders 6.2 and 6.3 require remaining personal data and intelligible log overviews within one month. Order 6.4 attaches a conditional EUR100 per day, capped at EUR1,000 per separate order. | Later delivery, adequacy, penalty accrual and payment. |
| [ECLI:NL:RBMNE:2026:7063](https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RBMNE:2026:7063), 30 September 2026 | Reasoning 4.4 records prior log receipt on 7 September. Reasoning 4.8 treats the medical-file copy as fulfilled; 4.14 accepts the other-personal-data overview. Orders 5.1 and 5.2 require further data/purpose explanations and qualified MiroView staff specification. | Subsequent fulfillment of those two orders. The assurance of cooperation in 4.16 is not execution evidence. |
| [ECLI:NL:RVS:2025:3260](https://www.raadvanstate.nl/uitspraken/@152256/202306121-1-a3/), 16 July 2025 | Section 10 reports a new 9 February 2024 access decision. The appeal reverses only the individual-employee-name requirement. | The decision passage does not establish actual receipt of all nonidentity records. |
| [TSV/238/2022](https://www.finlex.fi/fi/viranomaiset/tietosuojavaltuutettu/2026/37), 23 October 2026 | Paragraphs 44–45 and 53–54 distinguish the unfulfilled 1 January 2017–13 May 2019 period from the later period considered fulfilled. No further order is made for records reported no longer available. Paragraph 64 identifies the historical remittal delay. | Original taxpayer logs, an independently inspected deletion history, and any subsequent appeal/finality change. The published decision expressly says it is not final. |

### Why the Finnish recovery matters

The regulator reports that the request remitted on 28 November 2023 was not reconsidered before the regulator's office contacted the controller. The regulator also finds incomplete access to older records. Those findings support a concrete distinction between a judicial or administrative remedy and its timely performance. They do not establish a general statutory preservation period, intentional destruction, individual guilt, or the effect of a proposed control system. [Finlex, paragraphs 44–45, 53–54 and 63–67](https://www.finlex.fi/fi/viranomaiset/tietosuojavaltuutettu/2026/37).

Two discrepancies are retained in the source coding:

- Paragraph 30 ends the first disclosed interval on **31 December 2021**, while paragraphs 27 and 52 use **28 November 2021**. The tracker does not silently repair the text, combine intervals or infer an additional gap.
- Paragraph 65's counterfactual ends on **13 April 2019**; the missing-period finding elsewhere ends on **13 May 2019**. Both strings remain visible.

The representative's reported **24 May 2025** receipt and the controller's **23 May 2025** disclosure are attributed to their respective speakers. They are not automatically treated as a contradiction: dispatch and receipt can differ. The difference in claimed coverage remains a review flag.

## Acquisition and version controls

The public Finlex endpoint is:

`https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/judgment/data-protection-ombudsman-decision/2026/37/fin%40`

Finlex documents an unauthenticated Akoma Ntoso REST API through its [open-data service](https://www.finlex.fi/fi/avoin-data). The production fetch uses its required User-Agent, standard certificate and hostname verification, a fixed endpoint, no redirects, and byte/time limits. It verifies the canonical work URI, exact diary identifier, Finnish expression and decision date, all 67 numbered paragraphs, and the nonfinality statement.

The recovered XML is **63,164 bytes**, SHA-256:

`aa73bd6c9e220e235fb1d27b275c6b0be3769dde4ac8815d2738ff8a1688848f`

The XML's **10 November 2026 production date is not treated as a publication date**. Its source blocks cover numbered paragraph elements and the finality statement; unnumbered quotation/list continuations remain in the complete raw XML. The extraction is not represented as a complete text edition.

The new Dutch-source loader validates the three existing judicial pins and re-extracts their original XML. It can reuse the earlier capture receipt without rewriting it or acquire the three same official documents for a new run. Local fresh Dutch acquisition encountered a DNS resolution failure; local source integration used the previously captured exact bytes. The dedicated cloud workflow independently attempts all four case sources and fails if acquisition or verification fails.

Receipt hashes and validated TLS document the capture process. They do not independently prove the truth of a publisher's assertions. Changed raw judicial bytes require substantive review before updating a pin.

## Tracker behavior

`legal_codex_remedy_tracker.evaluate(ledger, sources, as_of)` consumes a reviewed event ledger and validated source documents. The real example binds every event to an exact source paragraph hash and separately scopes each obligation. The engine does not discover legal meaning or independently validate the analyst's translation or classification.

The report keeps separate dimensions for disposition, receipt, adequacy, fulfillment, remedial decision, unavailable records, assurance, penalty authority, accrual and payment. Unknown evidence remains unknown. A favorable decision, silence after judgment, an assurance, elapsed time, or an unsuccessful follow-up search cannot establish execution.

For a later fulfillment event to close an order, it must explicitly reference that order. Multiple unsuperseded orders remain unresolved until the analyst separates their scopes or supplies an explicit supported supersession. Conflicting positive and negative assertions remain contested; chronological recency and majority voting do not resolve them.

Every deadline has a source binding. Any manually entered calendar-month date is an **analyst review checkpoint**, not a legal computation of service, stays, enforceability or penalty conditions. Passing it can set `review_due`; it cannot infer breach or accrued money.

The real example uses the verified capture dates of the exact source versions. Earlier publication metadata alone does not show that a subsequently revised text was available historically. A filter can exclude later evidence without rewriting an earlier view. It cannot reconstruct what an actor actually knew at the time. Hidden source events do not expose later deadline details or discrepancy flags.

Native graph export recomputes from the validated inputs and uses only candidate source-to-event and event-to-obligation relationships. Literal citations never automatically join two cases or establish causal effect. There is no new Nocturnal runtime claim in this addition.

## Verification and reproduction

Local validation passed **54 new tests and all 21 source-dependent/regression tests from 019, with zero skips**. The new tests include actual-source identity and re-extraction, HTML-shell rejection, source mutation, wrong-case attribution, late evidence, source finality, disputed dates, multiple orders, deadline visibility, nonreceipt conflicts, and native graph preview/ingestion. Synthetic behavioral fixtures are identified as such; test counts are not a legal accuracy estimate.

Run a fresh acquisition:

```bash
PYTHONPATH=src python -m cite_refinery.legal_codex_remedy_sources --capture-dutch evidence-020/dutch
python scripts/legal_codex_capture_020.py --output-dir evidence-020/finlex
```

Run the source-dependent checks:

```bash
PYTHONPATH=src \
LEGAL_CODEX_020_DUTCH=evidence-020/dutch \
LEGAL_CODEX_020_FINLEX=evidence-020/finlex \
python -m unittest discover -s tests -p 'test_legal_codex_*020.py' -v
```

Generate the report and graph, supplying the intended evidence cutoff:

```bash
PYTHONPATH=src python -m cite_refinery.legal_codex_remedy_sources \
  --dutch-evidence-dir evidence-020/dutch \
  --finlex-evidence-dir evidence-020/finlex \
  --ledger examples/legal_codex_remedy_020.json \
  --as-of 2026-11-18 \
  --output remedy-020-report.json --packet remedy-020-graph.json
```

The new dedicated workflow records its own acquisition receipts, test count and graph. Source-dependent tests skip when their inputs are absent in ordinary offline runs; the dedicated workflow rejects any skipped test.

## Follow-up research boundary

Exact-ECLI and case-number searches, official-domain checks, and Dutch appeal/compliance/enforcement terms did not locate a later official execution record for these cases as of 18 November 2026. Finnish searches checked the diary number, title and appeal/finality terms on Finlex, the data-protection authority and court domains. No later official finality update was located. These are bounded search observations, not proof of noncompliance or absence of further proceedings.

The project holds published decisions, not original medical, tax or benefits logs. No claimant identity, staff responsibility, guilt, lawful mandate for a personal-data request, or operational enforcement is inferred. Existing request drafts remain unsent. The draft PR remains separate from any merge or deployment.
