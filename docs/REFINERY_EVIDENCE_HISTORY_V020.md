# Refinery evidence-history comparison (v0.20)

Cite-Refinery is a three-layer semantic map of Practical, Academic and Program
records, not simply a literature tool. v0.20 begins representing *changes in
project evidence* across distinct evaluations without fabricating performance
uplift. It is a manually reviewed private import, not background synchronization.

## Real pinned evidence episodes

Repository: `Spectating101/refinery`, Git commit
`2b03ad20f8ab3d55462adb38852855b940194c94`.

**October 13, 2026 — broad privacy-gate assessment**
(`evidence/refinery-privacy-gate-20261013/`):
- Three pinned source candidates: Offsend, CloakPipe and ESYS.
- `REVIEW_REQUIRED`, reuse=false, execution_ready=false, 12 open gaps.
- ESYS detector fixture had mixed results: secret 10/12, PII 7/8,
  clean 10/10. It did **not** validate provider-level protection.
- The comparison was not fully preregistered before detailed inspection.
- Source-file integrity checked against committed `MANIFEST.sha256`.

**October 16, 2026 — narrow CloakPipe core**
(`evidence/cloakpipe-core-20261016/`, original v0.19 adapter):
- Pinned `rohansx/cloakpipe` upstream commit
  `5186e543056cc59c1f680afe3de2e68514ea89c7`.
- 27/27 bounded preregistered required checks passed;
  4/4 broader limitation probes leaked.
- `REUSE_CANDIDATE`, execution_ready=false, scratch-only,
  no production-admission change.

The two episodes have the **same pinned CloakPipe source revision** but
different objects of evaluation: a broad multi-candidate provider privacy
problem versus a bounded core-library test. There is no matched test
population, common metric denominator, verified quality improvement, or
proof the broad gate is satisfied. The earlier gaps remain historically valid.

## Mapping contract

The October 13 adapter emits 7 Program nodes:
one broad capability, three pinned implementations, one mixed ESYS fixture,
one limitations node containing all 12 gaps, and one REVIEW_REQUIRED outcome.
Its 6 source-qualified edges record candidate implementation mapping,
fixture evaluation and limitations.

The comparison adapter requires the *same exact pinned Refinery commit*,
previously ingested and source-verified v0.19 narrow implementation and
reuse-decision nodes in the **same authorized private project**, and the same
CloakPipe upstream revision. It then emits a second comparison module with
one Program comparison node and three qualified source-lineage relations:
two COMPARES_WITH relationships and one SHARES_PINNED_SOURCE.

Qualified here means the evidence episodes are linked by auditable source
identity. It is **not** a verified improvement or production recommendation.
The earlier verdict is never overwritten, and neither episode is marked
execution-ready. Uncommitted modifications to source files are not trusted.

## Tested local private workflow

Install the latest version and use a private project containing the v0.19
CloakPipe case. Place an authorized owner/editor token in
`CITE_REFINERY_TOKEN`. Preview:

    cite-refinery-history --db /private/research.sqlite3 --project "$PROJECT" --refinery-repo /path/to/refinery --ref 2b03ad20f8ab3d55462adb38852855b940194c94 preview

Inspect the two source verdicts, explicit no-comparability warning,
revision/digest and proposed objects. To queue **the same reviewed packet**:

    cite-refinery-history --db /private/research.sqlite3 --project "$PROJECT" --refinery-repo /path/to/refinery --ref 2b03ad20f8ab3d55462adb38852855b940194c94 enqueue --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_PACKET_DIGEST

Apply through the existing operator-owned ingestion worker:

    cite-refinery-private --db /private/research.sqlite3 worker-once

In an isolated real-source test, the narrow case plus earlier historical
review and comparison yielded 3 clusters, 15 nodes, and 16 edges. Source
provenance and the distinct verdicts were verified; no Academic claims were
invented. Chrome displayed the version-scoped comparison and clickable
GitHub evidence references without JavaScript errors.

## Limitations

This is a **two-episode, source-contract-specific adapter**, not yet a generic
schema for all Refinery experiments or run-history analytics. It verifies
recorded source receipts, not a fresh binary execution or signer identity.
It does not track market popularity, releases, usage or operational adoption.
The Vercel public-data demo remains unchanged; private evidence stays local.

Next: normalize more Refinery experiment/run envelopes under a generic
typed evidence-history contract, add exact-subject cross-run comparisons,
and independently review semantic applicability to real problems.
