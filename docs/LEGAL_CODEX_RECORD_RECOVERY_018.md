# Legal Codex 018 — targeted original-record recovery

**Research date: 18 November 2026.** No claimant originals obtained; no identity or representative mandate established; no formal request sent; no private portal or Optiplex accessed. This milestone locates possible systems and lawful access routes rather than manufacturing a government event log.

## New primary-source lead: a historical system map

The official public archive contains **GEB Interactieve dienstverlening v1.0.1, 24 November 2021**, document markings **1881304 / 00536**. The downloaded 77-page PDF is 24,795,210 bytes, SHA-256 `034fdcdb988235b3d10ae5fd9fa2e28bbcdfe1ac158197d8471dc122cdffe430`.

Source: https://informatiepuntkinderopvangtoeslag.rijksoverheid.nl/publicaties/9ebc0f244fb97cc58dbe3fb626e92a82/183622021-24-11-geb-interactieve-dienstverlening-v101pdfpdf.pdf

The PDF distinguishes interaction services from substantive benefit source systems. Its platform table identifies **JCC** for desk service and **Genesys** for contact-center functions; the data catalogue names **KCH contact history** and notes. Printed page 33 describes **two years in user systems** for contact-history data and **seven years in an analytical environment**, with daily transfers. Separate interaction data has a stated seven-year-after-contact-year window. Benefit-source-system retention is controlled separately.

**Counterevidence:** risk 13 says active access logging/monitoring was absent and describes a target to implement it by **31 December 2023**. That is not a deployment certificate and does not negate the separate description of ordinary interaction logging. Neither the policy nor these names proves the 12 April 2023 claimant record exists, was recorded in one of these systems, or remains retrievable.

Visual review: physical PDF page 12 (risk 13); page 38 / printed 30 (platform table); page 41 / printed 33 (retention). The web screenshot endpoint failed, so actual downloaded PDF pages were rendered locally and inspected; no new OCR was run. Extracted text has pre-existing OCR imperfections and is not a substitute for those page images.

**Practical change:** a negative search in the current user interface is not the end of the inquiry. Ask for the relevant analytical/archive search, migration history and search scope—while separately requesting the original application in its substantive source system.

## A regulation edge that helps obtain evidence

CJEU **C-579/21**, judgment 22 June 2023, paragraph 83 / operative part 2, interprets Article 15 GDPR as covering the dates and purposes of consultations of a person's data. Employee identities are not automatically included; the stated exception requires necessity and balancing others' rights. The interpretation is EU data-access law, not a Finnish banking rule mechanically imported into Indonesian procurement.

https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62021CJ0579

CJEU **C-487/21**, judgment 4 May 2023, paragraph 45, supports faithful, intelligible reproduction of personal data and document/database copies when essential to exercising GDPR rights. It does **not** confer unconditional access to every document in a case file.

https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62021CJ0487

The proposed investigative edge is: **access right -> lawful subject request -> consultation/record-version evidence -> better decision-time reconstruction**. A date of consultation still does not prove comprehension or the official's first knowledge. Existing records may be limited, unavailable or lawfully withheld. No access right grants this project authority to impersonate the anonymized claimant.

## Current routes and historical limits

- Official Toeslagen privacy guidance describes a written personal-data access request and restrictions. Its BelastingTelefoon section describes 90-day recording deletion for quality purposes; this cannot automatically be applied to a February 2024 objection call of unverified channel. https://www.belastingdienst.nl/wps/wcm/connect/nl/toeslagen/content/privacyverklaring-toeslagen
- Mijn Toeslagen describes correspondence/payment views and logging of entries/clicks. This current page neither proves desk-input coverage in April 2023 nor supplies a claimant's logs. https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/mijn-toeslagen/hoe-werkt-mijn-toeslagen
- Public Woo requests can seek institutional documents held by Toeslagen. A separate general-policy draft asks about historical system/retention/implementation documents, not personal dossiers. https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive/toeslagen/hoe_werken_toeslagen/ik_wil_informatie_over_toeslagen/ik_wil_vragen_om_informatie_openbaar_te_maken
- The **14 July 2025** ministerial publication distinguishes GDPR, own-information and procedural-file routes. It also discusses proposed future changes; this document is not evidence those proposals became current law. Do not apply special childcare-remediation dossier arrangements to the separate 2023 health/rent/child-budget case. https://zoek.officielebekendmakingen.nl/kst-36708-28.html

## Eight evidence targets

1. Original April 2023 application and income-field versions.
2. Desk appointment/attendance metadata, with actual historical platform confirmed.
3. KCH notes/contact history, including preserved analytical copies where applicable.
4. Consultation dates/purposes and actual historical audit coverage.
5. Hearing invitation, waiver/contact record and any lawfully retained February 2024 audio or notes.
6. Original January/March 2024 decisions, input snapshots and approval trail.
7. Separate collection/offset/cancellation/refund ledger, not a court-order substitute.
8. Nonpersonal historical implementation, retention, migration and search documents.

Targets 1–7 require the claimant or a genuinely authorized representative and route-specific review. Target 8 can be pursued as a general public-policy request after a real sender authorizes dispatch. The prepared drafts are in `LEGAL_CODEX_ORIGINAL_RECORD_REQUESTS_018.md`; **neither was sent**.

## Implementation and results boundaries

`legal_codex_record_access.py` provides the eight-target plan, historical retention leads and observation classification. It distinguishes front-end absence, unsuccessful search, access refusal, planned control, consultation dates and court orders. It refuses to turn any into actual destruction, first knowledge or payment. Only candidate record-location/access-route graph edges are emitted.

The dedicated plan workflow runs 20 tests, including actual Cite graph ingestion, with no permitted skips. The **separate acquisition workflow remains partially unsuccessful**: five public sources were captured; both EUR-Lex pages returned HTTP 202 in cloud acquisition. They were read through public web retrieval, but no raw-byte custody is claimed for those two judgments. We did not bypass the response or silently mark it as success. Failed capture receipts are retained. A green planning test is not proof of seven-source acquisition or any claimant-original acquisition.

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_record_access_018.py' -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_record_access --output record-plan.json --packet graph.json

No step runs an information request, creditor action, benefit decision or operational replay. These records would be useful inputs to later professional review; merely identifying a source system or legal request route does not close the evidence gaps from 017. The Indonesian signed PPK instrument and original SD order also remain unresolved. Keep both PRs draft.
