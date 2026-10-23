# Paid-work commercial diligence — sample deliverable

**Case:** Claude Builders Bounty, destructive-command pre-tool-use hook (original issue #3)  
**Evidence snapshot:** October 24, 2026 (Taipei).  
**Conclusion:** **Do not undertake this as compensated work before verifying payout and acceptance in writing.**

## 1. The offer actually advertised

- [Original issue #3](https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3) is open and advertises **US$100** for a Python/bash Claude Code hook that blocks destructive commands and logs them while allowing ordinary commands. The issue requests `/opire try`, a pull request and implies automatic payment on merge. At our Oct 24 original-issue inspection, it had **1,886 comments**.
- That reward is **nominal and conditional**. There is no published signed engagement with our operator, no accepted assignment, no earned invoice and no independently authenticated payment.

## 2. Disconfirming evidence and authority reconciliation

- [Opire's official Costs & Payments documentation](https://docs.opire.dev/rewards/pricing) explicitly states that **creating or claiming a bounty does not create automatic payment**. After a developer submits a PR, *each bounty creator* decides whether the work meets criteria and **arranges payment for their own bounty**.
- The issuer's phrase *“Payment is released automatically on merge”* therefore conflicts with the documented provider flow. The mismatch is not resolved by a GitHub `bounty` label, public fork count or a maintainer emoji.
- High issue-comment volume **does not equal** a verified count of competing PRs; nevertheless it flags a heavily contested/automated issue discussion. We did not verify acceptance rate or successful payouts on this issue.
- A currently open GitHub issue is an engineering problem statement, not sufficient proof of funding, payment rails, exclusivity, adjudication, acceptance or enforceability.

## 3. Technical and commercial feasibility

| Dimension | Result | What would move the gate |
| --- | --- | --- |
| Requirements | Documented | No major feature ambiguity; hook format and logging are explicit |
| Capability match | Potential | Local tests needed; no implementation executed for this bounty |
| Active issue | Yes | Recheck immediately before attempting |
| Unclaimed/exclusive slot | Not established | Direct evidence from issuer's actual accepted attempt |
| Competition | Heavy issue discussion | Current PR/claim review, not just comment counts |
| Payment custody and route | **Disputed/unverified** | Provider-compatible written payout agreement and evidence of escrow or credible past settlement |
| Recipient payout eligibility | Unverified | Verify available country/region and permitted payment arrangements |
| Revenue | **None verified** | Only actual independently reconciled settlement counts |

## 4. Economic decision

An advertised **US$100 gross conditional bounty** is not a receivable, contract, expected value or realized profit. Without a defensible settlement probability, acceptance rules and measured hours, an ROI formula would be invented.

**Recommended action:** reject for now, preserve the source discrepancy, do not claim or write a submission solely for the bounty. Reopen only if primary-source payment terms and recipient eligibility can be authenticated, if the issuer confirms a realistic unclaimed scope, and if any additional code has independent reuse value.

This result is a **negative commercial outcome** in the valuable sense: Atlas declined a questionable opportunity rather than generating persuasive but unrecoverable engineering work.

## 5. Evidence and reproduction

- [Original issue](https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3)
- [Opire primary payment policy](https://docs.opire.dev/rewards/pricing)
- Source-stamped casebook: `research_materials/opportunity_conversion/paid_work_original_issues_20261024.json`.
- Engine: `src/cite_refinery/paid_work_preflight.py` with zero automatic write, outreach, claims or invoices.
- Executable tests: `python -m unittest tests.test_paid_work_preflight_v1 -v`.

**Commercial service hypothesis:** This document illustrates a narrow independent source/authenticity-and-economics verification service for operators evaluating open-source paid-work invitations or technology adoption. It does **not** establish customers, a saleable rate, a competitive moat or procurement eligibility. Those require a verified buyer and test engagement before offering the service commercially.
