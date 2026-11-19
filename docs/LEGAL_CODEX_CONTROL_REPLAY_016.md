# Legal Codex 016 — Decision-time enforcement replay

**Date:** 17 November 2026. **Status:** experimental offline controls, not deployed law or observed prevention. No government operational decision logs were acquired. All event streams are explicitly synthetic; the implementation rejects a real-operational-log label.

## What advances beyond 015

015 checks whether a legal safeguard has a plausible link to a case, and its proposed precommit API accepts four Boolean verifications. 016 tests whether a corresponding **sequence of decisions remains safe as its evidence changes**. It accepts typed, content-hashed synthetic documents and ordered events, recomputes checks at the commitment step, and preserves a reproducible decision trace. Expected outcomes live in the separate tests, not in the evaluator input.

The central distinction is not simply allow versus deny. The appropriate response to missing evidence depends on **who holds the record and what harm the next action creates**.

## Legal anchors, not automatic transplants

The original Indonesian Perpres 16/2018 Article 11(1)(n) concerns PPK execution-document preservation; Article 11(2) concerns delegated expenditure/contract authority. Original pages 18–19 were read and visually inspected. The official registry records later amendments: do not present the original version as today's complete procurement law. This pilot is a newly proposed software control, not an interpretation that the regulation itself commands these exact state transitions.

- Historical text: https://jdih.lkpp.go.id/admin/uploads/documents/Peraturan%20Presiden%20Nomor%2016%20Tahun%202018_1001_1.pdf
- Version registry: https://jdih.lkpp.go.id/regulation/1001/peraturan-presiden-nomor-16-tahun-2018

In ECLI:NL:RVS:2026:1753, paragraphs 11.2–11.4 and 12, the court considered the service's missing application form and visit record, and reduced the disputed recovery to nil. In ECLI:NL:RVS:2021:1729, paragraphs 3.6–3.8, proportionality was considered but recovery was upheld. These are distinct judicial outcomes, not two observed executions of our software.

- 2026 judgment: https://www.raadvanstate.nl/uitspraken/@157254/202501843-1-a2/
- 2021 judgment: https://www.raadvanstate.nl/uitspraken/@126332/201908482-1-a2/

**Our inference/design proposal:** missing agency records should trigger a protective review before a proposed debt collection, rather than automatically make the claimant responsible. This is not a general rule that every incomplete file must lead to waiver. Equally, suspending a purchase for unverifiable authority is not a criminal-liability finding.

## Two operational models

### A. Procurement: before a binding order

The synthetic event stream registers an appointment and a proposed package. A check verifies officer identity, package scope, currency, per-order amount ceiling, effective interval and signature-date assertion. Evidence is usable only after its registration event. Successful checks produce a package-version-bound approval; the commitment step checks all constraints again.

Expiry or revocation between approval and commitment, a changed supplier/amount/package description, actor substitution, direct execution without prior approval, and unsupported override requests cannot silently pass. Reverting a changed package to its previous bytes does not revive old approval. One package cannot execute twice even through a newly issued approval. These are one-shot package models, not installment contracts or aggregate-budget accounting.

### B. Recovery: before adverse collection

The synthetic record says whether a missing application or assessment is held by the agency, claimant, or an unknown custodian. Missing agency material produces **PROTECTIVE_REVIEW**; proposed collection without a current reasoned review is held. The model does not terminate ongoing benefits, determine entitlement, or credit money.

A synthetic reviewer must be explicitly listed, distinct from the handler, give reasons, address missing record roles, and bind the decision to the exact proposal and evidence state. It can record uphold, mitigate or waive. A later changed record invalidates the old review. A review cannot claim to consider evidence first available after its stated decision time. A one-shot recovery package cannot be collected twice through a new review.

After seven synthetic days unresolved, a tick emits an escalation event: it does not automatically collect, waive or declare the applicant at fault. **Seven days, reviewer separation, and the required record roles are design assumptions, not asserted statutory deadlines.** There is no live scheduler.

## Executable challenge set and repair record

The catalogue contains **24 synthetic scenario streams** (14 procurement, 10 recovery). The tests additionally sweep **32 combinations** of authority timing, identity, scope, currency and limit; these are subcases, not 32 independent legal cases. The 36 unittest methods include actual Cite graph ingestion and the prior 015 API compatibility check in full repository CI.

Four additional adversarial tests initially failed in the first 016 implementation: issuing a second approval could repeat a purchase; restoring old package bytes could revive an approval; a review could be backdated before the evidence it claimed to consider; and issuing a second review could repeat collection. These defects were corrected with per-package completion guards, monotonic state versions, and decision-versus-evidence chronology checks. This is a software-repair observation about **this new prototype**, not a claim about real procurement systems.

Representative expected outcomes:

| Sequence | Result in proposed replay |
| --- | --- |
| Valid authority and unchanged proposal | One simulated commitment |
| Authority expires after a successful check | Hold at commitment |
| Appointment arrives only after failed attempt | Earlier hold remains; a fresh later check may proceed |
| Proposal changes after approval | Fresh review/check required |
| Agency record unavailable | Protective review; no automatic collection or claimant blame |
| Missingness addressed and reviewer records waiver | No simulated collection; no asserted cash refund |
| Complete review records recovery upheld | Simulated collection permitted once |
| Review overdue | Escalation, not silent indefinite success or automatic debt |

## Reproduce

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_control_replay_016.py' -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_control_scenarios --output /tmp/control-016.json --examples-dir /tmp/control-016-scenarios
    PYTHONPATH=src python -m cite_refinery.legal_codex_control_replay /tmp/control-016-scenarios/late_evidence_no_hindsight.json --output /tmp/late-evidence-result.json --packet /tmp/late-evidence-graph.json

The dedicated workflow requires native app, graph and 015 imports before tests, so missing repository modules cannot silently count as success. It uploads the full scenario inputs and traces under an explicitly SYNTHETIC artifact name. Graph ingestion recomputes the result, rejects edited output, and emits only candidate synthetic-sequence edges. The existing Legal Codex test-discovery pattern also runs these tests.

## Boundaries and next evidence gate

No signature authenticity, reviewer identity or quality of legal reasons is proved by these fixtures. A hash does not prevent someone authorized to rewrite both content and digest from inventing evidence. There is no transaction API, banking adapter, source-vault import, identity provider, cross-process durable lock or enforcement connection. Collection holds are proposals, not judicial orders. Real human triage capacity and appeal/escalation design require validation.

The engine deliberately refuses actual-record mode until an independently verified adapter can establish record availability times, officer authority, application scope, and complete decision logs. To establish prevention, a real pilot must show the control was mandatory, triggered before the consequential action, resisted bypass, did not cause unfair refusals or delays, and changed outcomes against a justified comparison. A 24/24 synthetic outcome match is **not** a prevention rate.

The Indonesian signed June 30 PPK instrument and matching original SD order remain unverified. Neither repository is merged, no public accusation is promoted, and no information request is sent by this work.
