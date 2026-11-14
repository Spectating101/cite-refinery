# Global Legal Codex — Milestone 011: comparative legal-audit pilot

**Scope:** Horizon (England and Wales) vs Dutch childcare benefits (Netherlands).  
**Research cut-off:** 15 November 2026.  
**Status:** runnable, source-attributed and review-gated pilot, **not** a verified cross-border legal conclusion, original-file custody claim, published accusation or impact estimate.

This milestone returns to the broader Global Legal Codex objective after Indonesia Chromebook milestones 003–010. It compares **legal and institutional failure modes** using a reusable evaluator and typed graph, not a claim that courts, laws, causes or remedies in separate countries are equivalent.

## Research question and preliminary result

**Question:** When a government-linked system yields erroneous or discriminatory decision support, what independent channels exist to challenge the evidence, scrutinize institutional failure and remedy affected people?

**Source-attributed pattern:** Both case families illustrate problems with challenge, transparency and independent oversight around computer-assisted state-linked decisions. In the UK, the CCRC documented Horizon accounting-system defects and inadequate disclosure in criminal prosecutions. In the Netherlands, the parliamentary inquiry documented rule-of-law failures in childcare-benefit administration and the Dutch data regulator made a separate unlawful/discriminatory processing determination. Criminal conviction review and data-protection enforcement **do not confer the same legal remedy**.

### Actual comparative audit matrix

| Dimension | Horizon / England and Wales | Dutch childcare benefits / Netherlands | Legal boundary |
| --- | --- | --- | --- |
| Mechanism implicated | Bugs in accounting records and disclosure failures reported by CCRC | Unlawful/discriminatory nationality risk processing found by Dutch DPA; rigid benefits administration criticized by parliament | These are different technical failure modes and different liability regimes |
| Independent challenge / scrutiny | CCRC criminal-case review and referrals | Parliamentary investigative scrutiny; independent regulator enforcement | Review authority, evidentiary standards and individual access differ |
| Legislative or enforcement response | Post Office (Horizon System) Offences Act 2024 quashes **qualifying** convictions, not all convictions | DPA imposed **EUR 2.75m** penalty on the Tax Administration, 7 December 2021 | A regulatory fine is not claimant compensation or a quashed conviction |
| Inquiry | Statutory Horizon Inquiry, Volume 1 published 8 July 2025 (human impact/redress) | Parliament's *Ongekend onrecht* inquiry reported 17 December 2020 | Both document failures; neither alone proves later prevention |
| Outcome assessment | Case-level covered-vs-uncovered convictions and compensation completion not independently reconciled | Beneficiary-level remedies, decision/appeal logs and subsequent sanction status not independently reconciled | No ex-post effectiveness score or causal benefit is reported |

**Main falsifiable finding:** post-harm oversight and redress mechanisms are identifiable in both countries, but this data does not establish that they prevented harm, compensated all individuals or were equally effective. Proposed design tests are *independent evidence audit*, *challenge rights*, *transparent error disclosure* and *fit-for-purpose redress*. These are candidate governance principles, **not automatically transplanted foreign law**.

## Original official-source locators

All URLs below were checked as public research leads; **no source bytes are archived by this Milestone 011 module**. The module uses source-type/domain restrictions, reference validation and strict review flags to prevent a curated paraphrase from being reported as independently authenticated original evidence.

1. **UK independent reviewer:** CCRC, 3 January 2024, [The CCRC and Post Office/Horizon cases](https://ccrc.gov.uk/news/the-ccrc-and-post-office-horizon-cases/). Source for review mechanism and documented risk of bug-induced shortfalls plus disclosure concerns. Does not establish who is personally guilty or when the CCRC was first created.
2. **UK enacted statute:** [Post Office (Horizon System) Offences Act 2024](https://www.legislation.gov.uk/ukpga/2024/14/enacted), Royal Assent 24 May 2024, especially sections 1–4. Quashes a specified class of convictions in England and Wales and Northern Ireland. It **does not** cover Scotland; the Scottish legislative response is separate and outside this pilot. Conditions must be checked individually before any person's conviction can be classified as automatically quashed.
3. **UK statutory inquiry:** [Horizon Inquiry final report Volume 1 landing record](https://www.postofficehorizoninquiry.org.uk/inq00002037-volume-1-post-office-horizon-it-inquirys-final-report), published 8 July 2025, human impact and redress focus. **The full 166-page report is not captured or independently page-anchored in this pilot**.
4. **Netherlands parliamentary report:** Tweede Kamer, [*Ongekend onrecht* original parliamentary document](https://www.tweedekamer.nl/kamerstukken/detail?did=2020D52975&id=2020Z25233), 17 December 2020. Institutional, rule-of-law and proportionality critique. Parliamentary findings must not be represented as a judicial judgment against named officials.
5. **Netherlands regulator:** Autoriteit Persoonsgegevens, [Tax Administration fined for discriminatory and unlawful data processing](https://autoriteitpersoonsgegevens.nl/en/current/tax-administration-fined-for-discriminatory-and-unlawful-data-processing), 7 December 2021. Its EUR 2.75m penalty concerns discriminatory/unlawful (dual) nationality use; not a measured figure for compensation received by affected parents.

The fixture stores short **paraphrased institutional statements**, not original judicial or statutory passage hashes. Dates for official actions in this **snapshot** must match source publication dates; the 2024 CCRC source's date is an **observation date**, not its founding date. Case failure windows use calendar-year boundaries to cover research periods, not exact first/last victim dates.

## Components actually implemented

- **Five typed official source locators**: source class, domain, jurisdiction, date and explicit unarchived custody.
- **Two case scopes and seven institutions**: offices and organizations, not inferred individual wrongdoing.
- **Five attributed findings and five documented interventions**: each bound to an official source, jurisdiction, act of institutional authority and publication-date gate.
- **Three comparative questions**: contestability, individualized redress and institutional oversight. Two are analogy-only and one is explicitly **non-equivalent remedies**.
- **Four open evidence-acquisition questions**: actual case-level treatment and compensation records, plus Dutch risk/appeal logs and claimant recovery outcomes.
- **Candidate-only Cite–Refinery semantic graph**: case, source, institution, finding, intervention, and cross-case *comparable-mechanism* links; no legal-effect, personal-guilt or monetary-causation edge.
- **Adversarial tests**: reject fabricated archive status and review approval, source-class impersonation, cross-case actor/source mix-up, backdated remedies, invented foreign applicability, a fine presented as individual compensation and spurious effect sizes.

Reproducibility:

~~~bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_comparative_audit_011.py' -v
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_comparative_audit \
  examples/legal_codex_comparative_audit_011.json \
  --output /tmp/legal-codex-comparative-011-result.json \
  --packet /tmp/legal-codex-comparative-011-graph.json
~~~

All graph links are **candidates** even if the source is an official body: a domain check is not authentication of the original file, an institutional assertion is not proof of causal mechanism, and a dated legislative act is not a verified individual case outcome.

## Nocturnal handoff and gates before publication

1. **Acquire and preserve original official texts** via an authorized, bounded Nocturnal capture. Save durable raw files, per-file SHA-256 and extracted page/section references, independent of 30-day CI artifacts. Record access failures rather than working around blocks.
2. **Build a fuller institutional relation timeline.** Actor identities and roles must stay limited to contemporaneous record-supported powers. Distinguish Post Office prosecutor and software operator, statutory court/CCRC, legislators and inquiry; in the Netherlands, distinguish tax administrator, court, legislature, DPA, individual claimants and ministers. No graph-proximity guilt.
3. **Reconstruct concrete counterfactual questions**, not claims: when could a challenge have been raised, what information was available, what legal authority and procedural remedy existed at that date? Require contemporaneous law and decision records. Legal rules from the other country can motivate questions but cannot be directly applied.
4. **Measure outcome denominators separately**: UK qualifying convictions and actual quashing notifications vs nonqualifying cases and cash redress paid; Netherlands affected claimant decisions, contested/overturned outcomes and restitution status. Do not equate regulator fines, administrative recovery claims, criminal acquittals or total spending.
5. **Commission independent bilingual legal/technical editorial review** before publishing accountability conclusions. Demand disconfirming evidence, appeals and defense positions, source custody audit, sampling method and uncertainty analysis.

### Handoff to the ongoing Indonesia procurement case

The same stage-gated workflow can later test the June 30, 2020 PPK authority and purchase order question, but this pilot **does not verify that transaction**. Original signed appointment, audit logs, purchase order, authentic judicial files and individual-authority crosswalk remain blocked under Milestones 008–010. Formal PPID requests remain **prepared, not sent**.

**Next acceptance target (012):** original-byte capture and independent clause/page anchors for at least one source in each jurisdiction, then re-run the comparative packet with reviewed sources and adversarial disconfirming evidence. The comparison itself stays candidate-only until peer/legal review and an actual evaluation design exist.
