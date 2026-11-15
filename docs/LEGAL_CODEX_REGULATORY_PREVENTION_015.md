# Global Legal Codex — Milestone 015: Regulatory safeguards and prevention edges

Research snapshot: 16 November 2026. Cite–Refinery PR #143 / Nocturnal PR #115, both draft.

## Why this pilot matters

A source law linked to a failed case is not evidence that it would have prevented the case. The reusable investigative chain is:

    dated regulation or court doctrine
      → actual legal scope and possible decision point
      → a measurable compliance/detection action
      → the specific failure path the action might interrupt
      → actual implementation or breach evidence
      → documented outcome / still-unverified counterfactual

An edge can be rejected for wrong legal jurisdiction, wrong procedural stage, later effective date or absent overlapping failure mechanism. Even a fitting edge remains only a potential mechanism until there is actual evidence of implementation and effect.

## Cases and regulation instruments

The test uses seven source-attributed case contexts: UK Horizon system-dependent prosecutions; Dutch childcare recovery reconsidered in 2019 (ECLI:NL:RVS:2019:3536); a distinct 2021 Dutch child-budget appeal (ECLI:NL:RVS:2021:1729); a distinct March 2026 Dutch health/rent/child-budget recovery appeal (ECLI:NL:RVS:2026:1753); Indonesian June 2020 Chromebook PPK authority-document investigation; a synthetic Indonesian HPS-as-state-loss inference hazard; and a synthetic Indonesian trial disclosure risk with **no allegation that actual prosecutors withheld evidence**.

Seven instruments are version-pinned in the evaluator: UK Criminal Procedure and Investigations Act 1996 Section 3; Netherlands Awb Article 3:4; 2019 Dutch ECLI 3536 judicial interpretation; Indonesian Perpres 16/2018 PPK duties (Article 11); Indonesian Perpres 16/2018 Article 26(6) HPS restriction; a newly designed conditional PPK appointment/order gate; and a proposed cross-sector independent provenance audit. The last two are engineering designs, **not enacted laws**.

## Three decisive tests and their different results

### A. Preexisting UK law failed to interrupt harm

**Statute:** https://www.legislation.gov.uk/ukpga/1996/25/section/3

The disclosure regime was in force from 1 April 1997 and amended in April 2005. Historical cases must use their correct versions rather than the current consolidated wording.

**Judicial record:** https://www.judiciary.uk/wp-content/uploads/2022/07/Hamilton-Others-v-Post-Office-judgment-230421.pdf

The 2021 Court of Appeal held that relevant Horizon-dependent prosecutions suffered serious failures of investigation and disclosure. The prosecution was required to investigate reasonable lines of enquiry and disclose material undermining its case, yet it did not do so. The court allowed 39 appeals and dismissed three, demonstrating why even the eventual legal result cannot be generalized to every defendant.

**Regulation-to-case result:** preexisting duty failed to prevent. If observed compliance had been present, proper disclosure might have interrupted unreliable-evidence prosecutions. That is a conditional mechanism, not a measured counterfactual.

### B. Existing Dutch proportionality rule, later clarification, and a real negative control

**Norm:** Netherlands Awb Article 3:4, in force 1 January 1994, requires reasonable interest balancing and that adverse consequences not be disproportionate to the decision's purpose.

**Judicial interpretation:** https://www.raadvanstate.nl/uitspraken/@118142/201802802-1-a2/

On 23 October 2019, ECLI:NL:RVS:2019:3536 reinterpreted Awir Article 26: full benefits recovery was not invariably mandatory, and special circumstances could justify partial or zero recovery. The court remitted a challenged administrative decision from 2017. The 2019 precedent did not already exist before that decision, although the broader proportionality norm did.

**Actual subsequent case:** https://www.raadvanstate.nl/uitspraken/@126332/201908482-1-a2/

The Raad van State's 4 August 2021 judgment ECLI:NL:RVS:2021:1729 expressly refers to the 2019 interpretation and the 17 April 2020 implementing policy. It assessed recovery proportionality in a **different child-budget case** and still upheld the recovery: the claimant did not establish circumstances requiring mitigation. Thus legal reasoning propagated into a later case, but **did not produce the remedy requested**. This is direct legal-process reuse, not evidence of aggregate prevention effectiveness.

### B2. Same 2019 Dutch precedent, real full recovery waiver in 2026

**Official judgment:** https://www.raadvanstate.nl/uitspraken/@157254/202501843-1-a2/ — ECLI:NL:RVS:2026:1753, 25 March 2026, paragraphs 11.1–11.4, conclusion paragraph 12 and operative ruling V–VI.

This **different** case concerns provisional **2023 health, rent and child-budget benefits**, recalculated in 2024. The court explicitly cited the 2019 recovery interpretation, applied proportionality and referred to the *later codification in Awir Article 13b*. The administrative service could not supply its own original application form or a meaningful visit record; the resulting uncertainty about who entered the estimated income should not be assigned entirely to the claimant.

**Actual adjudicated remedy:** the Administrative Jurisdiction Division reduced the disputed repayment by **100% and set it at zero** (operative paragraph 12 and ruling V–VI), reversing the recovery element of the administrative decision while otherwise upholding the eligibility adjustments. The court additionally ordered litigation-cost/court-fee reimbursements, but their actual subsequent payment is unverified. This **does not prove an earlier payment had been returned**.

The 2021 no-relief and 2026 full-waiver cases therefore show the same 2019 doctrinal reference **applied to different facts with opposite outcomes**. One legal edge is documented_rule_considered_no_relief; the other is documented_rule_considered_court_ordered_relief. Both remain distinct from demonstrated prevention or a general causal success rate. In the 2026 decision the court also relied on **Awir Article 13b** and factual record failures, so the 2019 precedent cannot be credited as the single causal factor.

**Primary-source archive:** Nocturnal fetched, re-extracted and byte-hash-checked both public ECLI XML records. The operator private vault stores them as separately identified publisher snapshots, without asserting a certified signed judgment, independently reviewed legal translation or a cash-remedy event.

### C. Indonesian procurement duties as auditability controls, not automatic guilt findings

**Historical law:** https://peraturan.bpk.go.id/Details/73586/perpresno-16-tahun-2018 (effective 22 March 2018). Original text: https://peraturan.bpk.go.id/Download/64076/Perpres%20Nomor%2016%20Tahun%202018.pdf.

Article 11 assigns PPK procurement duties, including preserving execution documents. Article 26(6) forbids treating HPS price estimates as the basis for calculating the magnitude of state loss. These safeguards may help make an investigation reviewable or stop an unsupported analytical inference. **Neither proves that a named officer had lawful purchasing authority, that the 2020 appointment was invalid, or that a particular damage estimate was wrongful.**

The missing signed June 30, 2020 PPK replacement and the corresponding SD e-purchase order remain the central Indonesian record gap.

**Proposed new operational control, not a 2020 rule:** test a system that requires all four checks before simulated authorization: original appointment, effective date, delegation scope, and matching original purchase order. Missing verification causes a hold for documentary review, not a determination of criminal wrongdoing.

## Cross-jurisdiction transfer policy

A general Horizon lesson — independently verify critical machine-generated evidence before a serious decision — is a candidate **process design** for e-catalog procurement. The tool marks it nonbinding, not UK law applied to Indonesia.

Separately, a UK criminal disclosure rule is tested against an explicitly hypothetical Indonesian trial-evidence scenario. Because the jurisdictions differ, the engine reports a possible research analogy but no domestic legal force. It rejects other transfers where risk mechanisms or operating stages fail to match.

## Files and execution

- src/cite_refinery/legal_codex_prevention_edges.py: chronology, statute source, country, legal arena, required stage and enforcement-status gates; graph export and a deliberately synthetic appointment gate.
- examples/legal_codex_prevention_edges_015.json: six cases, seven instruments, fourteen proposed regulation-to-case edges with explicit missing evidence and source URLs.
- tests/test_legal_codex_prevention_edges_015.py: positive, negative, historical-version, spoofed-source, synthetic-authorization and real Cite graph-ingestion tests.

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_prevention_edges_015.py' -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_prevention_edges \
      examples/legal_codex_prevention_edges_015.json \
      --output /tmp/legal-prevention-015-result.json \
      --packet /tmp/legal-prevention-015-graph.json

Mismatched proposals are preserved in the evaluation JSON but never emitted as candidate failure-interruption edges. Valid analogies and candidate controls become neutral Cite semantic graph nodes/edges. None become proven causation, a legal finding about individual wrongdoing, or a published allegation.

## Evidence necessary to advance a prevention claim

For a real causal prevention assessment: authenticated applicable historic law, proof of actual operational enforcement before the decision, source-linked triggering evidence, documented change to a consequential action, a defensible comparison group/counterfactual, and independent professional legal review. No success probability is invented by this pilot.

Next phase: compare a second genuinely held-out case family, recover the operational implementation evidence that would make the edge falsifiable, and formally review statutory versions and new court opinions before promoting findings. No Indonesian PPID requests were submitted.
