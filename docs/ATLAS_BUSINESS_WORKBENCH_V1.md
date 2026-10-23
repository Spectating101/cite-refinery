# Atlas Business Workbench v0.1 — opportunity-to-outcome operating layer

**Date:** 24 October 2026  
**Status:** local/offline MVP on a draft feature branch, not a deployed CRM, bank feed, contracted customer relationship, or autonomous revenue engine.

## Position in Atlas

The existing Practical → Academic → Implementation maps answer **what problems, mechanisms and reusable technologies are worth examining**. The existing opportunity-conversion layer answers **which rights, buyer, technical and competitor claims are actually supported**. This business layer adds the previously missing operating process:

**Source-bounded opportunity → commercial channel → falsifiable experiment → capped validation expenditure → operator-reported activity → next decision (investigate / hold / budget stop / kill).**

Neither graph discovery nor a GitHub issue can establish buyer authorization, margin, pricing, grant eligibility, sale, contract, or payment. The business layer consumes the existing evaluator and does not promote the graph.

## Included functionality

- **Opportunity register:** explicit case IDs linking to the existing evidence-reviewed opportunity JSON files. Channels: service, implementation, partnership, internal asset. These are conversion paths, not business types already proven profitable.
- **Experiment contracts:** every opportunity must specify the question, success signal and stopping signal. Avoid an infinite cycle of more research without commercial falsification.
- **Market substitutes:** the board can include named source-linked alternatives that trigger a differentiation test in the earlier commercial evaluator; examples cover Solargis and Raptor Maps, without assuming we can beat either.
- **Validation spending caps:** precise Decimal accounting in TWD or USD; mixing currencies fails. If operator-reported spend reaches or exceeds the cap, the board stops recommending further spending. This is an analytical stopping rule, not actual financial authorization.
- **Operator-reported activity:** buyer outreach, responses, pilot results, reported costs, reported payments, possible funding leads, and explicit hold/continue/kill decisions. Nothing sends email, contacts a buyer, starts a charge, creates an invoice or awards a grant.
- **Tamper-evident local receipt chain:** append-only operation IDs, prior entry hashes, aggregate head hash, pinned business plan **and source-case evidence fingerprints**, date and amount validation, duplicate rejection. If underlying evidence changes, the existing ledger refuses to silently reinterpret historical activity; an explicit reviewed migration/new plan is required. This detects accidental editing/reordering, **not** malicious rewriting by someone who can replace the entire ledger and rehash it.
- **Privacy:** actual activity receipts are not committed to GitHub. The ledger CLI demands an **absolute path outside the repository**, creates a restricted 0600 file, and uses file locks plus atomic replacement on Linux.
- **Evidence and finance separation:** signed contract / independently verified buyer stage remains owned by the existing independently attested conversion evaluator. Local reports expose amounts as **unreconciled operator reports**, never independently verified revenue, gross profit or return on investment.
- **Funding mini-lane:** record and count leads without representing a grant as awarded or its amount as payment. Grant searches, formal applications and eligibility checks are future features, not claimed now.

## Four real evidence cases, four hypothetical validation caps

The public demo plan is [examples/atlas_business_workbench_demo_v1.json](../examples/atlas_business_workbench_demo_v1.json). All caps are **fictional configuration examples**, not instructions to spend real money, quotes, cost estimates or funding approval.

| Opportunity | Revenue hypothesis | First decisive evidence | Example TWD cap |
| --- | --- | --- | ---: |
| Open Food Network | Small paid contributor/partner service | Verify issue funding and volunteer-to-certified onboarding terms | 500 |
| Foodsoft reconciliation | Narrow paid bug repair | Reproduce issue and confirm payer, not merely GitHub issue ownership | 500 |
| Independent PV audit | Fixed-fee technical diligence | Compare Solargis/Raptor Maps and obtain a prospective buyer's permission to assess operating data | 2,000 |
| Kobo dog field workflow | Institutional survey integration | Test offline photo/time/location data fidelity and confirm a real survey operator | 1,000 |

Total demo validation **cap**: TWD 4,000, not observed expense. No experiments with these organizations have been performed by this feature branch.

## Quick start

From the checkout with the package installed:

    python -m pip install -e .
    cite-refinery-business board \
      --plan examples/atlas_business_workbench_demo_v1.json \
      --format markdown

The board without a ledger is a **read-only hypothetical scenario** showing zero recorded spend, zero recorded payment, unverified buyers and the immediate blockers. It does not modify source cases.

For an authorized private experiment, choose an absolute writable local path outside the checkout:

    cite-refinery-business init \
      --plan examples/atlas_business_workbench_demo_v1.json \
      --ledger /tmp/atlas-business-private.json

An example *synthetic* event saved outside Git could be:

    {
      "event_id": "buyer_check_001",
      "case_id": "ofn-paid-contributor-route",
      "on": "2026-10-24",
      "kind": "buyer_contact_reported",
      "note": "TEST RECORD ONLY: sample of how a future outreach attempt would be logged."
    }

Then, only with an actual authorized local event JSON file at /tmp/synthetic-event.json:

    cite-refinery-business record \
      --plan examples/atlas_business_workbench_demo_v1.json \
      --ledger /tmp/atlas-business-private.json \
      --event /tmp/synthetic-event.json

    cite-refinery-business board \
      --plan examples/atlas_business_workbench_demo_v1.json \
      --ledger /tmp/atlas-business-private.json \
      --format json

This is not an instruction to contact any particular organization. Event strings are user/operator assertions, not independently authenticated customer records. Do not store personally identifying contacts, contracts or private bank data inside this public repository. Encrypted storage and accounting integration are not implemented.

## Gate definitions

**Research validation only:** existing practical/research/repository evidence, potentially viable service channel, no independently verified buyer/technical/competitive gate. This remains a **hypothesis**, no financial claim.

**Rights blocked:** source has unverified/no recognized license; do not reuse third-party code.

**Budget stop:** costs recorded at or above the plan's stated cap; no further expenditure recommended. Unreported costs would make the board incomplete.

**Hold / kill:** explicit human choices, retained in a sequential chain and reproducible from event records.

**Reviewed paid-pilot candidate:** only inherited from the existing strict three-attestation conversion evaluator, subject to independently verifying real contract authenticity, rights, delivery scope and costs. No board event can upgrade this condition.

**Observed revenue:** deliberately **not implemented**. Logged payments are unresolved operator assertions. Reconciliation requires an external trusted accounting source, bank statements reviewed by an independent authorized person, or another secure verified receipt process. An invoice or GitHub issue is not a payment.

## What this first slice disproves and what it does not

The workbench establishes a falsifiable experimentation process across **four distinct possible conversion paths**. It prevents model reports and freely editable logs from becoming revenue assertions, and stops unlimited spending on the example project budgets. It cannot prove the opportunities are profitable, buyers want the service, the independent-model Atlas benchmark wins, or that the documents on other sites are genuine.

The next meaningful product phase is **permissioned buyer validation and measured time-to-decision / discovery-versus-implementation cost**, starting with the smallest real operator problem. The separate [blinded Atlas-vs-general-AI benchmark](COMMERCIAL_BLIND_TRIAL_V1.md) is required before claiming the intelligence system provides an advantage over generic research agents.

## Reproduction

    PYTHONPATH=src python -m unittest tests.test_business_workbench_v1 -v
    PYTHONPATH=src python -m cite_refinery.business_cli board \
      --plan examples/atlas_business_workbench_demo_v1.json \
      --format json

The isolated Actions workflow atlas-business-workbench-offline executes the same without model tokens or private files. The broad repo suite has other historically failing optional dependency/provider tests and must not be represented as green until fixed.
