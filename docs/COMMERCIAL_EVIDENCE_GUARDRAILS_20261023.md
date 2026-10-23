# Commercial evidence & competitor controls — experimental hardening (2026-10-23)

## Why

PR #123 surfaced two reproducible problems in the existing opportunity-conversion evaluator:
1. A public software bug issue could be mislabeled as a "reviewed signed contract" and, with a self-asserted execution status, advance to paid-pilot readiness.
2. Adding a direct competitor was ignored by the conversion decision.

This change **prevents silent promotion on those inputs** without deleting the underlying research leads. It does not turn Atlas into an autonomous contract-authentication service.

## Decision semantics

- `market.demand_status` is explicitly **claimed** by the case author. `buyer.verified_demand_status` is **unverified_claim** for any claimed expressed interest, funded request, or signed commitment without a valid attestation tied to that exact evidence snapshot.
- `competitive_alternatives` is a bounded list of real alternatives, each with `name`, HTTPS `url`, and `scope` in `direct|partial|adjacent`. A named substitute modifies the next test to compare buyer-specific differentiated value and switching costs.
- `competitive_review.assessment = buyer_verified_differentiation` is only eligible when a signed independent-review receipt is bound to the exact alternative list and **the same counterparty** as the demand receipt.
- A claimed `fit.verification = executed_local` or `independently_replicated` does not grant commercial readiness. A separately signed technical execution review must reference a reviewed execution artifact bound to the fit claim.
- All three independent receipts (buyer demand, comparative differentiation, technical execution) are required before a candidate can reach **candidate_for_paid_pilot_subject_to_contract_and_rights**. This state is conditional; it does not authorize procurement, deployment, reuse, or an income claim.
- Missing keys, expired reviews, missing alternatives, swapped evidence, bad signatures, mismatched buyer identity, or unreviewed claims stay at **evidence_lead_only**. Historical source-side claims can still be displayed without being trusted as facts.

## Trust boundary

The host-operated reviewer maintains a private `CITE_REFINERY_COMMERCIAL_REVIEW_KEY` at least 32 UTF-8 bytes in an authorized environment. **Never commit it to Git or share it with an LLM or supplier.** Raw case JSON, repositories and retrieved webpages are untrusted.

The attestation envelope has `payload` plus a 64-character hex HMAC-SHA256 `signature` over canonical UTF-8 JSON (sorted keys; compact separators; no ASCII coercion). Payload schema: `cite_refinery.commercial_review_attestation.v1`.

Payload must contain:
- `purpose`: `buyer_demand`, `competitive_differentiation`, or `technical_execution`
- `case_id` (exact), `subject_sha256` (digest of normalized market signals, cleaned alternatives, or fit minus its attestation)
- `buyer_id` and responsible `reviewer_id`
- `evidence_url` matching the relevant source, `evidence_sha256` as an inspected document/receipt fingerprint
- `reviewed_on` and `expires_on` (ISO dates, max 180-day validity)
- `demand_status` for demand attestations, or `assessment=buyer_verified_differentiation` for competition

The evaluator validates signature, scope, case/evidence digest, dates, purpose, and counterparty matches. **This is chain-of-custody / reviewer authorization only.** It *cannot* cryptographically establish that an attached file is a genuine signed agreement, that a bidder has eligibility, that evidence is independently sourced, or that an actual buyer has agreed to pay. Those are human/offline validation responsibilities, and must be reflected in custody records and real-world checks.

Review creation, authenticated source retrieval, secure private evidence storage, trusted key rotation, and reviewer permission management are **not implemented here**. The test fixtures use a deliberately synthetic key and documents at example.org, and MUST NOT be mistaken for authentic commercial evidence. A production release must add an independent evidence-source/identity review workflow and an append-only reviewer audit trail.

## Validation

```bash
PYTHONPATH=src python -m unittest tests.test_commercial_evidence_guardrails -v
PYTHONPATH=src python -m unittest tests.test_commercial_comparison_v1 -v
PYTHONPATH=src python -m unittest tests.test_opportunity_conversion -v
```

The full GitHub Actions suite may still surface unrelated pre-existing missing optional dependencies or model-provider environment problems. Do not merge on the strength of the targeted tests alone.

## First commercial decision after this patch

Open Food Network remains a *possible paid contribution route*, not a confirmed paid fix. PV remains a potential service hypothesis that faces Solargis and other monitoring substitutes. Kobo remains a technical component hypothesis. **None is a validated source of current revenue.**

Next critical experiment is an independently blinded and cost-matched Atlas versus general-agent comparison, followed by actual buyer interviews / paid contracts, not more unranked opportunity counts.
