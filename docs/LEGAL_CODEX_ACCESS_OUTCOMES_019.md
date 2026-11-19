# Legal Codex 019 — cross-sector access outcomes, not a single win/loss label

**Research date: 18 November 2026.** We followed the 018 access-law leads into new published cases rather than claiming access to the Dutch benefits claimant's private records. Purposeful case selection is not a representative effectiveness study, and curated outcome labels are not a classifier accuracy benchmark.

## A concrete cross-case chain

The underlying rule is EU GDPR access law, interpreted in C-579/21 (Pankki S; a Finnish banking reference) and C-487/21. Its use in Dutch healthcare is shared EU law, not automatic transplantation of a Finnish domestic banking rule. The Dutch 2026 hospital decision explicitly cites the 2024 hospital appeal and both CJEU lines. The implementation extracts literal citations from source text automatically; the outcomes below are separately attributed human-readable interpretations.

### Hospital appeal, 26 August 2024 — ECLI:NL:GHARL:2024:5384

The court ordered intelligible log overviews within a month, respecting others' privacy, and accepted role descriptions without general disclosure of staff names. It imposed a conditional EUR 100/day penalty capped at EUR 1,000 per separate order. This is a conditional enforcement order, not proof that a penalty accrued, was paid or that later disclosure actually happened.

Official snapshot: https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:GHARL:2024:5384
Key extracted blocks p0113, p0141, p0143; original numbered reasoning 4.11–4.12, 4.16 and operative 6.3–6.4 should be checked in the complete ruling.

### Hospital decision, 30 September 2026 — ECLI:NL:RBMNE:2026:7063

The judgment records the claimant confirming receipt of log overviews and a medical-file copy on **7 September 2026**. It nevertheless orders clearer explanations of which personal data staff accessed and for what purpose. A separate order requires further specification of staff linked to certain logged activities where not already done, subject to privacy rights. The source does not support either 'all names automatically disclosable' or 'no identification can ever be required'.

It also distinguishes the requested NEN 7513 format from the rights established under Article 15 in this proceeding, and declines the requested conditional penalty. **Receipt, intelligibility, identity scope and enforcement are four distinct dimensions.** Subsequent compliance with the September order has not been verified. The private logs themselves were not acquired by this project.

Official snapshot: https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RBMNE:2026:7063
The official metadata distinguishes decision **30 September** from publication **15 October 2026**. Important source blocks: p0057, p0059, p0067, p0079–p0081, p0091, p0100 and p0102. Footnotes p0117–p0121 explicitly cite the 2024 hospital decision.

### Ministry employee identities, 16 July 2025 — ECLI:NL:RVS:2025:3260

The appeal concerns staff identities, not wholesale rejection of all access rights. The court found no access logs available for the earlier period and limited the identity issue to the later period. It ruled that staff acting under the controller's authority and instructions were not recipients in the relevant sense, and their names were not necessary for the stated rights in this case. It reversed the lower identity-disclosure requirement. The identity exception discussed by the CJEU is preserved, not replaced with a blanket rule.

Official source: https://www.raadvanstate.nl/uitspraken/@152256/202306121-1-a3/
Official XML: https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2025:3260
Source blocks p0035–p0038 and p0051. A missing log is not proof of deliberate destruction or an individual's misconduct.

## A useful new failure mechanism — Finnish tax case (web-reviewed lead)

Finlex publishes decision **TSV/238/2022 of 23 October 2026**. Paragraphs 63–65 describe partial log disclosure following C-579/21, but older requested periods remained unavailable after delayed reconsideration. Paragraph 30 records the controller's explanation that retention was six years. The regulator says timely reconsideration after the 2023 remittal could still have enabled access to part of the earlier period. The publication explicitly says the decision is **not final**; no later appeal status was established.

Primary source: https://www.finlex.fi/fi/viranomaiset/tietosuojavaltuutettu/2026/37

**Acquisition boundary:** the official indexed text was readable through web retrieval, but this run's bounded HTML capture did not expose the expected case identity and was rejected. It is not one of the four hash-rechecked core snapshots, and the source-bound graph does not pretend to include its raw decision file. The Finnish legal reading remains provisional and requires independent language/legal review.

**Design implication, not an established general retention mandate:** when a verified request or judicial remittal concerns expiring records, consider a lawful, access-controlled and scope-limited preservation review promptly. Separate preservation from disclosure: protecting an existing record while access is decided does not mean automatically publishing staff identities. Do not preserve all personal data indefinitely or equate a retention schedule with actual deletion. This paper does not implement a real retention hold or claim one was in force in the studied case.

## Newer implementation research does not close the old deployment gap

The official **Advies Modernisering Contact Center** publication, dated 1 June 2026 on its page, describes procurement in dialogue and not yet awarded at the time of the report. It concerns modernization for the Belastingdienst, Douane and Dienst Toeslagen and recommends changes before award. This is a genuine newer institutional source, not evidence that the specific access-monitoring measure proposed in the 2021 assessment was implemented by December 2023. Nor should the June description be presented as independently verified current status in November.

https://www.adviescollegeicttoetsing.nl/documenten/2026/05/29/advies-modernisering-contact-center

## Code, auditability and rejected shortcuts

- `scripts/legal_codex_capture_019.py` fetches only five fixed public endpoints using TLS and public DNS pinning; failures remain failures. It submits no requests and uses no personal credentials.
- `legal_codex_access_outcomes.py` rehashes four exact core source snapshots and re-extracts their text before emitting 13 explicitly scoped observations. Three are judicial sources; one is institutional advice.
- Literal citations are discovered automatically rather than hardcoded as edges. A citation is not proof of causation, same proceedings or legal applicability. The two references printed as `ECLI:EU:C:2023:50` in the 2026 judgment are preserved as unresolved literal references—not silently repaired to `...:501` even though complete references occur elsewhere.
- The graph contains 17 nodes and 14 candidate edges: 13 scoped observations and one unique 2026-to-2024 citation link. Automatic extraction is separate from the curated English interpretation of legal outcomes.
- Original operational replay remains refused. Courts can record that a litigant received logs while this project still has none of those logs. Conditional penalties are not fines collected. Program plans are not executed safeguards.

The source-acquisition job and core-validation job are separate. **A successful core-validation job must not conceal an incomplete five-source discovery capture.** The Finnish failed lead remains explicit. No personal file, private portal, Optiplex or local source vault is accessed. No formal request is sent, no execution outcome is invented, and the Indonesia PPK/SD-order originals remain unresolved. Keep existing PRs draft.

Reproduce against the captured source archive:

    PYTHONPATH=src LEGAL_CODEX_019_EVIDENCE=evidence-019 python -m unittest discover -s tests -p test_legal_codex_access_outcomes_019.py -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_access_outcomes --evidence-dir evidence-019 --output outcomes.json --packet graph.json

The dedicated job requires all actual-source tests without skips. Offline repository suites explicitly skip source-dependent tests when no snapshots are available; those are not acquisition passes. CI archives have 30-day retention, not durable vault status. English/Finnish interpretations and decision finality remain subject to independent review.
