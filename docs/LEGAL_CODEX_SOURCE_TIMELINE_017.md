# Legal Codex 017 — source-backed decision chronology and knowledge-time boundary

## What is real, and what remains missing

Three actual official judiciary XML documents were acquired in bounded cloud execution. The new source reader rechecks raw SHA-256, native ruling extraction, paragraph hashes, ECLI identity and metadata dates. Twenty-four analyst-authored chronology entries are anchored to those bytes. These are **published judicial accounts**, not the agency's original application database, call recording, document-receipt log, decision execution log or bank records. A source hash proves the captured version, not independently certified legal authenticity or semantic correctness of the English labels.

The engine keeps four concepts separate: a recounted event day; the date of the judgment reporting it; the date the source was captured; and the actual actor-specific first-known time. The last is **unknown** in this dataset. No date, signature, claimant identity or first-known timestamp is fabricated to make the 016 synthetic engine accept real data.

## A newly recovered intermediate decision in the same proceedings

The earlier first-instance record is **ECLI:NL:RBGEL:2025:1418**, decided 24 February 2025. The later appeal is **ECLI:NL:RVS:2026:1753**, decided 25 March 2026. Their official XML metadata directly link the proceedings in both directions. The join is not made using the anonymous labels [appellant] or [eiseres]. The third source, **ECLI:NL:RVS:2021:1729**, is a separate comparator, never merged with this claimant.

Official sources:
- https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RBGEL:2025:1418
- https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2026:1753
- https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2021:1729

Reconstructed main sequence: staff-assisted application on 12 April 2023; revised advances during 2023; recovery decision on 5 January 2024; objection rejected on 18 March 2024; first-instance hearing on 10 January 2025 and dismissal on 24 February 2025; appellate hearing on 13 February 2026; partial reversal and zero-recovery order on 25 March 2026. These dates are court-reported chronology, not a recovered event stream.

## Why grounds must not be collapsed into one causal edge

The first-instance court identified a hearing-duty breach and insufficient initial reasoning, yet passed those defects and upheld recovery. The appellate court **also accepted passing the hearing-duty defect** (8.1–8.2). It did not grant the recovery waiver on that ground. The case-specific missing application form, lack of a substantive visit note, and resulting uncertainty about responsibility were considered in 11.2–11.4. The operative ruling reduced recovery to zero while otherwise upholding the reassessment. This is not a universal hearing-breach-to-waiver rule, not wholesale invalidation of the income assessment, and not proof of a cash refund.

The comparator 2021 decision retains an adverse outcome after considering proportionality. Dropping this comparator or the unsuccessful hearing ground is rejected by the reconstruction validation. The fixture also distinguishes party submissions from judicial findings; a claimant's account of a call is not an authenticated call record.

## What this says about preventive design

A proposed control could require a retrievable, versioned application record and a reasoned missing-record review before adverse collection. But the 2026 court's inability to obtain a document does not establish **when** an earlier official first knew it was unavailable, whether a record existed in January 2024, or whether a particular earlier intervention would have changed the outcome. Those questions need contemporaneous records.

Accordingly, 017 can produce an anchored chronology, separate grounds and an as-of evidence-gap view. It **refuses** conversion into authenticated operational input for 016. The existing synthetic replay remains unchanged and rejects the different source-timeline schema. No live purchase, collection, benefit decision or information request occurs.

## Software and tests

- `scripts/legal_codex_capture_017.py`: only three fixed judiciary ECLI endpoints, real hostname-verified TLS, public DNS pinning, strict byte limit, no redirects, no XML DTD/entities, no invented successes.
- `legal_codex_source_timeline.py`: exact source-version and paragraph validation, source/case/date/role boundaries, native candidate graph and operational-admission refusal.
- `legal_codex_source_timeline_catalogue.py`: transparent, analyst-authored English labels and source paragraph selections; not automatic legal entailment.
- Dedicated workflow requires **all 26 tests to execute, without skips**, with real source snapshots and native Cite graph imports. General offline suites skip the source-dependent tests when no snapshots are provided; those skips are not reported as live-source passes.

    PYTHONPATH=src python scripts/legal_codex_capture_017.py --output-dir /tmp/evidence-017
    PYTHONPATH=src LEGAL_CODEX_017_EVIDENCE=/tmp/evidence-017 python -m unittest discover -s tests -p test_legal_codex_source_timeline_017.py -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_source_timeline --evidence-dir /tmp/evidence-017 --output /tmp/timeline-017.json --packet /tmp/graph-017.json

Pinned raw hashes intentionally reject later publisher revisions until reviewed. CI source artifacts have 30-day retention and are not a permanent vault or independent signature. No new writes to the Optiplex or its private evidence vault are performed in this milestone.

## Precise next evidence requests, not submitted

For the main case: obtain a lawfully disclosed application/version history, original visit notes or retention/deletion audit, the hearing invitation/waiver/call record for the objection stage, the original January/March 2024 decisions, and separate execution/collection/refund records. The purpose is to establish who had what information at each decision, not to infer guilt from later missingness. Do not seek to deanonymize the claimant from the public judgments.

The Indonesian original signed PPK appointment and matching SD order remain unverified. Keep both PRs draft. The current result is a real source-grounded chronology, not an empirical prevention experiment.
