# Global Legal Codex — Integration Benchmark 001

**Status:** reviewed code candidate, not a completed legal-audit engine. This is the first reusable integration into Cite-Refinery's existing typed semantic graph.

## Three independent case families

1. **Jieyang, China (June 2026):** documented juvenile institutional response to an animal-cruelty incident, with an England/Wales animal-welfare statutory alternative.
2. **Horizon, England and Wales:** unreliable accounting evidence and post-conviction review; independent review is an institutional mechanism, not a proven prevented-convictions estimate.
3. **Childcare benefits, Netherlands:** unlawful and discriminatory nationality-data processing, parliamentary findings and the need for accountable administrative review.

## Execute

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_benchmark_001.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_benchmark \
  examples/legal_codex_benchmark_001.json \
  --output /tmp/legal-codex-result.json --packet /tmp/legal-codex-graph.json
```

The graph output uses the existing `cite_refinery.semantic_graph.v1` schema. Review it through `SemanticGraph.preview_packet(project_id, packet)`; do not automatically publish or upgrade it.

## What the code really verifies

- Per-source URLs, stated publication dates, frozen *excerpt* digests, exact quote inclusion, unique IDs and case provenance.
- Alternative mechanism retrieval by overlapping **human-labeled** failure modes.
- Whether a proposed mechanism was available before the case's anchor date.
- Foreign statutes cannot silently become domestic applicable law.
- Claims about causal effect, personal culpability, publication approval and full-document custody fail closed.
- All exported nodes are neutral and all relationships remain **candidate**, including relations named SUPPORTS.

## What is **not** demonstrated

The source URLs were researched, but original document bytes were **not** archived or cryptographically authenticated by this runner. Exact quote containment is not semantic entailment. Legal effective dates, foreign-law comparability and the interpretations in source statements still require independent verification. Matching uses curated tags, not autonomous retrieval. No causal estimator or named-official responsibility inference runs.

**Milestone gate:** runnable three-case seed-data workflow and schema export **implemented**; live source discovery, Nocturnal signed evidence ingestion, independent original-text authentication, blind holdout, causal reproduction and lawyer/editor sign-off **not passed**.

Next integration should reuse the frozen Nocturnal source bridge and the existing InvestigationController to acquire original documents and seek disconfirming evidence, keeping the human editorial gate intact.


## Integration Benchmark 002 — blinded candidate retrieval and Nocturnal capture verification

**Two explicitly separate tests:**

1. \`legal_codex_blind.py\` retrieves candidate legal mechanisms by plain lexical overlap from nine supplied candidate documents. The matcher receives only an incident question, anchor date and candidate descriptions/source locators; the earlier manually-labelled failure-mode tags are stripped from the request. A hidden answer key exists only in acceptance tests. This is **candidate-library retrieval**, not autonomous discovery from the world or proof of actual effectiveness.
2. \`legal_codex_nocturnal.py\` calls Nocturnal's real \`src.nocturnal_engine.source_capture.load_verified_capture\` against an existing local capture. That loader rechecks identity, raw response bytes, re-extracted text and exact quote proposal integrity. The adapter rejects injected-test fetchers or unverified TLS captures. It still does **not** claim source authenticity, fact truth, or permission to publish.

Run:

\`\`\`bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_blind \
  examples/legal_codex_benchmark_001.json \
  examples/legal_codex_candidate_library_001.json --output /tmp/blind.json

# Only if Nocturnal is installed and actual saved captures exist:
PYTHONPATH=src python -m cite_refinery.legal_codex_nocturnal \
  examples/legal_codex_benchmark_001.json /path/to/nocturnal-capture-references.json \
  --output /tmp/nocturnal-result.json
\`\`\`

A capture-reference file is a JSON array. Each item has \`source_id\` from the benchmark plus \`state_dir\`, \`case_id\`, \`capture_id\` and \`proposal_id\` for a real Nocturnal capture. The benchmark's synthetic/example capture objects do not pass the real loader. No live capture of these three cases has been performed by this PR.

### Evidence and evaluation limitations

- The three case questions and nine candidate descriptions were curated for development. The top-one retrieval result is an **in-sample, small-set engineering check**, not an independent blind holdout or a generalization score.
- The blind matcher has no semantic entailment, statutory hierarchy, multilingual reasoning, or causal evaluation; its lexical scores are relevance heuristics only.
- The Nocturnal private repository and any real case capture state are *not* bundled with Cite-Refinery. Tests inject simulated captures solely to exercise fail-closed policy and mark those receipts \`test_double_untrusted\`; they do not count as real verified sources.
- Even a real Nocturnal capture confirms archived-byte/extraction integrity rather than the truth of the source, the legal meaning of a statute or whether the proposed mechanism works.
- Publication, named-person responsibility and policy causal-effects estimates remain explicitly blocked.

**Next acceptance gate:** perform an actual Nocturnal capture of at least one official legal source in an authorized environment, verify it in the bridge, then run leave-one-case-family-out retrieval on an independently assembled and reviewed candidate corpus. An independent reviewer must adjudicate relevance and legal applicability before any real performance claim.


## Integration Benchmark 003 — actor names, court roles, and actual Nocturnal interop

Implemented in \`legal_codex_actors.py\`, seeded in \`examples/legal_codex_indonesia_actor_register_001.json\`, tested by \`tests/test_legal_codex_actors_003.py\` and separately by the actual private Nocturnal engine at [Nocturnal PR #115](https://github.com/Spectating101/nocturnal-oversight/pull/115).

The input register contains two distinct Indonesian trial-court records, twelve *source-named* entities (ten people plus two court-case nodes), and ten explicit **pending** observations about defendants, prosecutors and judge-panel roles. Each observation has a recorded case source and date. Four cross-case same-name pairs are listed as **unresolved possible identities**, not merged actors. The official court-directory HTML is a source locator, not yet an independently archived and authenticated original-document capture.

### Rules enforced

- Reuse Nocturnal's \`analyze_relationships\` at runtime; do not copy its identification or review logic into Cite.
- Nocturnal's pending, reported, rejected and direct-reviewed observations remain distinct. Only *direct-record accepted* relationships can project as graph edges, and even these appear as **candidate** edges in Cite, never automatic assertions.
- Exact names/aliases alone cannot merge people across cases. Cross-case accepted relationships require an independently reviewed identity crosswalk (not yet implemented).
- The approved link types are procedural (defendant, prosecutor, judge, testimony, documented appointment and similar); no claim of bribery, conspiracy, guilt or common control is created from graph proximity.
- The same named role observed in a court decision is not proof the person held a different administrative power at an earlier procurement date.
- No direct-review relationships have been accepted from the real register; its ten links are **pending**.
- Nocturnal's external source truth, provenance, reviewer identity and publication requirements remain separate gates.

### Real cross-repository software acceptance

The private Nocturnal \`test/legal-codex-actor-interop\` branch checks out the public Cite–Refinery feature branch and invokes Nocturnal's actual relation analyzer. On the pending real-world register it checks ten pending observations and four unmerged identity candidates. It then applies one **synthetic** accepted review solely to exercise the review-to-candidate graph transition. This is a real source-code integration test, **not** a real-world fact verification or legal ruling.

Run the Cite side:
\`\`\`bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
# Only when the private Nocturnal distribution is installed in the same environment:
PYTHONPATH=src python -m cite_refinery.legal_codex_actors \
  examples/legal_codex_indonesia_actor_register_001.json \
  --output /tmp/legal-actors.json
\`\`\`

### Next hard acceptance gate

Acquire and revalidate the actual source documents through Nocturnal's capture/case-reconstruction workflows, review the source-quoted case roles, and separately resolve cross-case identity and dates of authority before mapping procurement choices. Do not treat a lawyer's or investigator's allegation as a sourced direct-record relationship; attach defense and appeal material before any substantive judicial or institutional conclusion.


## Procurement investigation — source-first authority and utilization audit

Original-source reconstruction is implemented in \`legal_codex_authority.py\` and
\`examples/legal_codex_chromebook_source_audit_v1.json\`. At the current revision
there are **9 source records, 14 named actors or institutions, 18 sourced
observations and 7 unresolved questions**, ingested as neutral, candidate-only
\`REPORTS\` graph edges.

The December 2025 and January 2026 prosecutor pages, and the December 2023
ministry letter, have been **fetched through Nocturnal's real bounded network
source capture and raw/text SHA checks**, not just JSON fixture tests. See the
private Nocturnal PR #115, the \`legal-codex-official-source-capture\` CI
workflow and its ephemeral private (7-day retention) artifacts. These live
captures are not independent assessments of source truth. The February 2026
prosecutor report and AP witness account remain source locators only.

Important distinctions:

- The prosecution's account of 2020 technical-review revisions and subsequent
  reuse by directorates is explicitly attributed, not certified as a finding.
- Budget delegation to named KPA officials and technical influence by advisers
  are distinct; original appointment, sign-off, technical review/redlines and
  contract authorizations are still missing.
- The ministry's Dec 2023 98.82% APBN and 61.27% DAK figures concern **inventory
  mapping** and cannot be represented as device utilization percentages.
- An original **August 2020 junior-secondary education ministry guide**
  (\`https://repositori.kemendikdasmen.go.id/19935/1/Pemanfaatan%20Peralatan%20TIK%20Bantuan%202020.pdf\`)
  identifies **Drs. Mulyatsyah, M.M.** as director in its foreword and discusses
  online and offline Chromebook teaching uses. The recorded source date is
  month precision, not a manufactured exact day. This establishes contemporaneous
  ministry documentation, **not** that every school could configure/use the
  devices or that the procurement complied with the law.
- Permendikbud 5/2021's recorded effective date is 2021-02-11; its DAK
  Fisik FY2021 scope does not automatically govern 2020 purchases or every
  APBN-funded activity. The BPK page returned HTTP 403 to Nocturnal; its
  original text remains unarchived in this investigation.
- Prosecution, defense, independent witness accounts and trial-index outcomes
  stay in different epistemic lanes. Full court judgments, trial exhibits,
  ministerial authority delegations, procurement records and independent
  on-site usage measurements must be acquired before conclusions about
  institutional breach or any individual's culpability.

The original 2020 ministry manual is also being attempted via Nocturnal's
bounded PDF capture in the private CI branch; a locator/indexed PDF is not
equal to a successfully archived one. Do not substitute offline **capability**
for independent evidence of offline **use** in affected schools.
