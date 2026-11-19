# Legal Codex 022 — Source-bound decision-chain and prevention-checkpoint pilot

**Pilot date:** 20 November 2026 (Taiwan). **Scope:** 2023 Dutch benefit recovery and 30 June 2020 Indonesian SD procurement. This is a forensic **research prototype**, not a verdict, a criminal accusation, or evidence that our controls were deployed.

## Actual result

The executable pilot reconstructs **7 checkpoint observations**. The Dutch side is rebuilt from **3 public court-publisher XML originals**, SHA-pinned by the existing 017 source reader, with **24 paragraph-anchored records** and reciprocal published court relationship metadata. Indonesia is rebuilt from the independently validated **008 source-attributed research ledger**: 12 reported statements, 10 original-record leads and two unresolved narrative conflicts, but **zero original signed appointments or matching purchase orders**.

There are **5 public-source actor records**, **3 reported-only actor relationships**, and **5 specific original-document targets**. A private Nocturnal test newsroom contains **two held native investigations**, with no source-record import claims, reviewer approvals, submissions or public output. **30 dedicated Cite tests** and **11 dedicated Nocturnal tests** ran with real Dutch snapshots locally; dedicated CI reacquires them before checking.

### Why this matters

**Dutch benefits (2023–2026)** — Administrative case:

| Date / checkpoint | Actual available material | What we must NOT infer |
| --- | --- | --- |
| 12 April 2023 | The 2025 district judgment recounts a staff-assisted application | That the later application record was missing or known missing on application day |
| 5 January 2024 | The 2026 appellate judgment recounts a recovery decision | That it was enforced/collected, or that the agency knew a document was unavailable |
| 18 March 2024 | The later appellate judgment recounts rejection of the objection | That a hearing-rule breach alone explains the ultimate recovery waiver |
| 24 February 2025 | District court found procedural/reasoning defects yet upheld recovery | That every procedural breach automatically cancels recovery |
| 25 March 2026 | Appellate court reduced recovery to zero; separately upheld other reassessment aspects | A cash refund, complete benefit reinstatement or causal prevention |

The 2021 Dutch comparator upholds recovery despite proportionality review. It is **not** the same claimant or a universal opposite rule. The appeal's later finding about missing agency records is not assigned to a January 2024 caseworker as contemporaneous knowledge.

Official source identities:
- ECLI:NL:RBGEL:2025:1418 — https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RBGEL:2025:1418
- ECLI:NL:RVS:2026:1753 — https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2026:1753
- Separate adverse-outcome comparator ECLI:NL:RVS:2021:1729 — https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2021:1729

**Indonesian procurement (June 2020)** — Allegation and judicial-reporting dispute:

The prosecution's 2025 account alleges that the PPK replacement resulted from refusal to carry out a ChromeOS instruction and that a new officer placed an e-catalog order on 30 June. A 2026 journalist's account of court reasoning describes a voluntary resignation and a rushed appointment without a handover memorandum. The reporting is not the original signed 2020 PPK appointment, an authenticated electronic purchase order, or an original full judicial judgment. Both competing accounts are retained, with names limited to their reported public roles:

- **Bambang Hadi Waluyo:** reported former SD PPK
- **Wahyu Haryadi:** reported replacement SD PPK
- **Sri Wahyuningsih:** reported SD KPA in case coverage

The original signed appointment, delegation scope/effective interval, exact SD e-catalog proposal/order, and precommit authority trace remain unverified. Neither the 8 June 2020 general appointment decree, a different SMP order, nor a third-party reupload can substitute for them.

Attributed source leads:
- Prosecution statement: https://kejati-kepulauanbangkabelitung.kejaksaan.go.id/conference/news/6463/read
- Reported court reasoning: https://www.hukumonline.com/berita/a/melihat-unsur-penyalahgunaan-wewenang-dan-perintah-jabatan-di-putusan-terdakwa-korupsi-chromebook-lt69f34d794ab23/

## Proposed legal-control mechanism versus observed history

The **Dutch design proposal** would preserve assistance and application field history, then require a reasoned, protective review when agency-held records cannot be supplied before an adverse collection. It does not decide entitlement or order waiver. The **Indonesian proposal** would check a signed officer appointment, time/scope, and the **proposed package** before a binding order. It must never require an already executed original purchase order before order creation (the 015 circularity bug).

These are **prospective software designs made in 2026**, not an assertion that the respective statutes mandated these exact software gates on the earlier dates. A legal analogy between countries is not a transplant of binding foreign law.

022 independently executes **nine previously implemented 016 synthetic replay streams**: valid purchase, missing authority, post-approval revocation/change, late evidence, agency-held missing documents, reasoned waiver, reasoned recovery upholding and missingness not addressed. A hold is a conditional software response, **not** evidence it happened, and certainly not evidence a corruption offense was averted.

Three distinct questions remain explicitly unresolved:
1. Were original decision inputs/authority documents actually present and usable at the original checkpoint?
2. When did the responsible official receive or consult those inputs, and which version?
3. Was an equivalent mandatory control actually deployed, correctly triggered, and resistant to bypass?

All answers currently depend on original records, not courtroom hindsight. **Observed historical prevention effect: unknown**. No test reports a prevention percentage.

## Evidence acquisition priorities — not submitted

| Priority | Original record | Access boundary |
| --- | --- | --- |
| NL 1 | 12 April application with original field/version data and staff-assistance record | Data subject or verified representative |
| NL 2 | 5 January recovery inputs, documented search and collection/offset/reversal ledger | Data subject or verified representative |
| NL 3 | February hearing communication and 18 March objection record | Data subject or verified representative |
| ID 1 | Signed June 30 replacement/authority and delegation annex | Official original-record route |
| ID 2 | Exact SD 2020 proposed package and e-catalog order/audit trail | Official original-record route |

**No personal-data, PPID, Woo or court application was dispatched.** Missing records are not evidence that they never existed or were destroyed.

## Reproduction

From Cite checkout, after lawful/ordinary public source acquisition:

```bash
PYTHONPATH=src python scripts/legal_codex_capture_017.py --output-dir /tmp/022-court
PYTHONPATH=src LEGAL_CODEX_022_EVIDENCE=/tmp/022-court python -m unittest discover -s tests -p 'test_legal_codex_decision_audit_022.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_decision_audit_022 \
  --dutch-evidence-dir /tmp/022-court \
  --indonesia-fixture examples/legal_codex_signature_chain_008.json \
  --output /tmp/022-decision-audit.json --packet /tmp/022-candidate-graph.json
```

The direct Cite semantic graph is **candidate-only**. The conversion routine requires the original byte-verified sources and re-runs the audit; an edited JSON with a recalculated checksum is insufficient. All actor relationships in the graph are attributed, not original-verified facts. Raw/capture versions are not digital signatures or independent legal translations.

The Nocturnal companion runs two real **native software case holds** in an isolated private test workspace, using a scripted source-locator callback and the native journalist journal. It exercises **no live model, external network fetch, signed evidence request or publication**. It is a case readiness rehearsal, not autonomous legal reasoning or a production deployment. Keep PRs draft pending independent source/legality review.
