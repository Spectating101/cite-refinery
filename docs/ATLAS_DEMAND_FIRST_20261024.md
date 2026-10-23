# Atlas Demand-First Commercial Test — 2026-10-24

Status: source-linked public-opportunity screening, not outreach, a submitted bid, payment, signed client or autonomous prospecting.

## Purpose

The Business Workbench already tracks four internally identified source-bounded opportunities. Demand-first screening asks the reverse question: **when a real institution or competition advertises money, does Atlas have any rational way to capture it?** The engine must be able to reject a large tender or an attractive prize rather than treating its advertised budget as user revenue.

## Three public leads, as checked October 24

| Lead | Source and claimed value | Commercial barrier | Decision |
| --- | --- | --- | --- |
| Cognee Mergetober | Official event at https://www.wemakedevs.org/hackathons/mergetober with a top US$2,000 prize and a separate random draw of twenty US$100 rewards | Competition, not a paid contract; official rules require an assigned issue, a solo original contribution, submission steps and an accompanying post. AI-assisted study allowed but AI-generated PRs prohibited. No eligibility, authorship, assignment or payment is validated | HOLD: eligibility/originality first; do not count prizes |
| Taiwan Ministry of National Defense | Third-party tender reference https://www.beraniq.com/publicbid/biddetail?bid=3774067 with project ID CD15004L254, reported NT$60m budget, November 5 deadline | Selective procedure, supplier company/tax conditions, project/security/implementation capacity; no authoritative tender pack checked | VERIFY OFFICIAL: no bid authorization |
| NCKU Hospital | Third-party listing https://www.tendersontime.com/tenders-details/first-and-second-level-next-generation-data-analysis-system-902d8bf/ reports an NT$3.94m analysis-system purchase, October 29 deadline | This is not shown to be an Atlas software-service order; specialized supply, clinical fit and eligibility are not established | REJECT: scope mismatch |

Official Cognee rules: https://www.wemakedevs.org/hackathons/mergetober/rules.

No prospective user bid eligibility, work permit conditions, purchase orders, prizes awarded, profits, ROI or revenue can be inferred from these figures. Secondary government listing claims are subject to official government procurement confirmation and full tender document checks.

## Execution

Offline reproduction from the repository:

    python -m unittest tests.test_market_demand_screen_v1 -v
    cite-refinery-business board --plan examples/atlas_business_workbench_demo_v1.json --demand-scan research_materials/opportunity_conversion/public_demand_scan_20261024.json --as-of 2026-10-24 --format json

The standalone demand screen validates ISO dates, source authority, eligibility and capability declarations, monetary type, advertized prize vs procurement budget, and stops against deadlines. The combined board keeps internal conversion opportunities and external public demand leads in separate fields.

## Decision gates

- Expired lead => not currently actionable.
- Scope mismatch or ineligible => reject irrespective of amount.
- Third-party or stale listing => verify official primary notice before any follow-through.
- Unknown eligibility => hold.
- Unknown technical delivery ability => investigate a small capability test, not full implementation.
- Conditional prize => no guaranteed income; even successful delivery may produce no award.
- Seemingly qualified tender => human review of complete contracting terms and eligibility, not automatic bid.

The business workbench's private expense and outcome log does not accept advertised procurement amounts as money received.


## Original GitHub bounty: first external payout due-diligence experiment

A separate source-backed paid-work scanner now accepts *original issues only* alongside published payments terms. As of 2026-10-24 the frozen casebook `research_materials/opportunity_conversion/paid_work_original_issues_20261024.json` reports five examples:

| Original issuer | Advertised reward | Original-issue fact | Commercial decision |
| --- | ---: | --- | --- |
| [Claude Builders hook #3](https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3) | US$100 | Open, about 1,886 issue comments; issuer promises automatic payment upon merge, **contradicted by** [Opire's direct payment arrangement terms](https://docs.opire.dev/rewards/pricing) | REJECT pending independently confirmed funded/payout and acceptance process |
| [Tenstorrent #56290](https://github.com/tenstorrent/tt-metal/issues/56290) | US$500 | Original issue closed and assigned; a crawler copy can still look open | REJECT closed issue |
| [Tenstorrent #56908](https://github.com/tenstorrent/tt-metal/issues/56908) | US$3,000 | Approved bounty but currently assigned to someone else and requires Wormhole hardware regressions | REJECT already assigned |
| [Local AI Registry #216](https://github.com/sybil-solutions/local-ai-registry/issues/216) | US$50 | Original task open with six acceptance tests requiring actual Intel Arc B580, and payment arranged by sponsor after merge | HOLD unavailable/unverified hardware and unverified payout |
| [Solana Pay Kit #354](https://github.com/solana-foundation/pay-kit/issues/354) | **No offered reward** | Technically relevant issue, but no published paid assignment or budget | REJECT as revenue opportunity; potentially useful unpaid open-source contribution |

These original-source examples show why job/bounty board volumes are not the same as earnable money. The issue's comment count is a **competition/congestion proxy**, *not a count of submitted competing PRs*. Even allegedly independent payment metadata remains unverified operator input; this module **never authorizes starting work** without separate manual permission.

Run the combined screen:

```bash
python -m unittest tests.test_market_demand_screen_v1 tests.test_paid_work_preflight_v1 -v
cite-refinery-business board \
  --plan examples/atlas_business_workbench_demo_v1.json \
  --demand-scan research_materials/opportunity_conversion/public_demand_scan_20261024.json \
  --paid-work-scan research_materials/opportunity_conversion/paid_work_original_issues_20261024.json \
  --as-of 2026-10-24 --format json
```

### Economic conclusion

All five developer-bounty leads fail at least one essential precondition, so **the right commercial move is to invest nothing in implementing these tasks as paid work**. The purpose of this gate is preserving development effort for genuine, confirmed paid client requests or for our own differentiated reusable assets. Even the lowest-cost bounty deserves evidence of a payer, payment mechanism, acceptance criteria, hardware availability, competition, time constraints and lawful payment eligibility.

## Commercial lesson and next milestone

These leads are **negative-control examples**, not income prospects confirmed for the operator. Their utility is avoiding investments based on large headline budgets and uncertain contests.

Next positive-result target: one current first-party fixed-scope paid task or buyer inquiry fitting an existing capability, with clear legal eligibility, payment basis and delivery requirements, no lengthy speculative development. Confirm source, alternatives, customer demand and costs before investing more than a bounded research allowance.

No third-party outreach, account registration, competition submission, payment, grant application or model execution was performed in this experiment.
