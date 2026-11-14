# Global Legal Codex — Milestone 012: judicial decision reconstruction

**Study date:** 15 November 2026  
**State:** primary court-hosted texts consulted via public web view; three identifiers and twelve paragraph-specific paraphrases seeded; original downloaded bytes, per-page hashes, certified judicial orders and independent bilingual legal review **not** acquired by this pipeline. This is an investigative research candidate, not a published determination of foreign legal applicability or causation.

## Why this differs from Milestone 011

011 compared **institutional responses** (CCRC, UK legislation, UK Inquiry, Dutch parliament/DPA), not judicial ratios or individual holdings. 012 separately models a criminal appellate judgment on Horizon-dependent unsafe prosecutions and **two distinct** Dutch administrative rulings from the same day: one on childcare-benefit **entitlement**, one on **recovery** of payments.

An action occurring in 2024 cannot supply a 2021 court's reasoning. The Dutch 2019 judgments **do not adjudicate nationality-based profiling**, the 2021 DPA fine, or which claimants later received compensation. UK abuse-of-process doctrine does not automatically govern Dutch benefit determinations.

## Primary judicial opinions and paragraphs

### A. Hamilton & Others v Post Office Limited

[Official judgment PDF](https://www.judiciary.uk/wp-content/uploads/2022/07/Hamilton-Others-v-Post-Office-judgment-230421.pdf)

- **Jurisdiction:** England and Wales, Court of Appeal (Criminal Division).
- **Neutral citation:** **[2021] EWCA Crim 577**, decided **23 April 2021**; 42 linked appeals, individually assessed.
- **Paras 120–123:** The court accepted that Horizon defects could generate apparent shortfalls without actual losses. The relevant prosecutions lacked independent loss evidence and suffered serious investigation and disclosure failures.
- **Paras 127–138:** The court distinguished *category 1* abuse (unfair trial) and *category 2* abuse (affront to conscience of court) and held that both applied to the relevant Horizon-dependent prosecutions.
- **Paras 357–446:** Three contested appeals demanded case-specific review. At **para 440**, Neelam Hussain's prosecution was not dependent on Horizon's general reliability in the required sense; her appeal failed.
- **Para 447, operative disposition:** **39 appeals allowed**, with all those appellants' respective convictions quashed; appeals of **Wendy Cousins, Stanley Fell and Neelam Hussain dismissed**. The 39/42 ratio is the *appeal* denominator within this 2021 judgment, not the total prosecutions ever undertaken or later statutory relief.
- **Not decided here:** individual compensation paid, quantified preventive effect, or application of the **Post Office (Horizon System) Offences Act 2024** enacted years later.

The [court-published explanatory summary](https://www.judiciary.uk/wp-content/uploads/2022/07/Hamilton-Others-v-Post-Office-summary-230421.pdf) confirms the paragraph structure and split but expressly states that the full judgment alone is authoritative.

### B. Dutch ECLI:NL:RVS:2019:3535

[Official Raad van State decision](https://www.raadvanstate.nl/uitspraken/@118143/201900753-1-a2/)

- **Case:** 201900753/1/A2, decided **23 October 2019**.
- **Paras 8.7–8.11:** The previous rigid all-or-nothing entitlement interpretation could be disproportionate. The court reinterpreted *Wet kinderopvang* articles **1.7 and 1.52** to permit nonzero benefit after partly paid childcare costs, requiring individualized balancing under **Awb 3:4**.
- **Para 8.13:** The agency's asserted grounds for inflexible denial were insufficient in the case.
- **Paras 9–10, outcome:** Appeal granted; administrative decision of **7 November 2017 annulled** (Awb 3:4 and 7:12). New decision required within **26 weeks**. The court did not itself award a final compensation amount.
- **Scope:** **Entitlement and advance calculation**; not automatically a ruling on recoupment or nationality profiling.

### C. Dutch ECLI:NL:RVS:2019:3536

[Official Raad van State decision](https://www.raadvanstate.nl/uitspraken/@118142/201802802-1-a2/)

- **Case:** 201802802/1/A2, decided **23 October 2019**.
- **Para 5.6:** The third-party joint-liability rule, **Awir article 33(3)**, applicable from **2014**, cannot retroactively apply to a **2010** benefit year. This is distinct from the proportional-recovery holding.
- **Para 5.12:** **Awir article 26** does not require full recovery in every case; the agency can reduce or refrain from recovery under exceptional circumstances when **Awb 3:4** proportionality requires it.
- **Paras 5.14–5.16:** On these specific facts, the claimant did not receive the funds directly and was victimized by relevant criminal conduct; requiring full repayment was disproportionate. This is not a blanket repayment waiver.
- **Paras 6–7, outcome:** Relevant part of administrative decision of **24 March 2017 annulled**, with reconsideration and a **26-week** deadline. No definite cash reimbursement amount was set.

The [Raad van State's official 23 October 2019 press explanation](https://www.raadvanstate.nl/@118168/belastingdienst-maatwerk-bij-toeslagen/) makes the **two** changes explicit, but is explanatory context rather than an additional judgment.

## Comparative audit results: legally bounded

| Comparison | Court mechanism | Material difference |
| --- | --- | --- |
| Evidence and institutional challenge | Hamilton paras 121/137 vs 3535 para 8.11 | Criminal disclosure and abuse of process versus administrative entitlement and proportionality |
| Judicial remedy | Hamilton para 447 vs 3536 para 6 | Criminal convictions quashed in 39 appeals versus annulment of an administrative decision and remittal |
| Domestic Dutch split | 3535 para 8.11 vs 3536 para 5.12 | Recalculating original entitlement differs from reducing or waiving **recovery** |

**Testable design hypothesis:** independent review, access to accurate evidence and individualized decision-making may prevent some institutional harms. These judgments do **not** quantify prevention or prove a remedy's transferability across legal systems. The three unsuccessful UK appeals are necessary counterevidence to any automatic claim that all Horizon-linked convictions were unsafe.

## Files and reproducibility

- examples/legal_codex_judgment_reconstruction_012.json — pinned court URLs, dockets, judicial dispositions, twelve paragraph-holding records, three bounded comparison questions, four unresolved primary-record gaps.
- src/cite_refinery/legal_codex_judgment_reconstruction.py — fail-closed evaluator; jurisdiction, docket, legal basis, paragraph and disposition gates; candidate-only semantic graph export.
- tests/test_legal_codex_judgment_reconstruction_012.py — adversarial checks for fake original hashes, misdated or foreign law, incorrect denominators, erased UK exceptions, paragraph swaps, false financial remedies and stale graphs.

Reproduce:

~~~bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_judgment_reconstruction_012.py' -v
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_judgment_reconstruction \
  examples/legal_codex_judgment_reconstruction_012.json \
  --output /tmp/legal-codex-judgments-012.json \
  --packet /tmp/legal-codex-judgments-012-graph.json
~~~

Each semantic edge remains **candidate**. Court-hosted text found in public web viewing is not the same as byte-level archived original-file custody, machine-proven textual entailment, an independent Dutch-English legal review or a verified subsequent individual payout.

## Acceptance gate for Milestone 013

1. Acquire original decision bytes by authorized Nocturnal capture for the Hamilton PDF and Dutch 3535/3536 pages. Maintain raw hashes and stable paragraph/page references in durable, controlled archive storage; 30-day CI artifacts are inadequate for permanent evidence custody.
2. Conduct bilingual paragraph-by-paragraph verification, including negative findings in the dismissed UK appeals and Dutch non-retroactivity holding. Preserve defense arguments and alternative explanations.
3. Separately reconstruct **later individual remedies**, without backdating: the UK's 2024 statutory intervention cannot become a 2021 ratio; the Netherlands' later administrative decisions and claimant compensation must be separately sourced.
4. Continue independent requests for the Indonesian Chromebook 2020 PPK appointment and matching purchase order; none of these foreign judgments resolve the missing administrative original.
5. Obtain independent legal/editorial review before publishing cross-jurisdiction findings, individual liability or causal effectiveness claims.

**Current status:** a narrower, defensible court-holding comparison can be reproduced. It is not yet a validated global-law effectiveness audit.
