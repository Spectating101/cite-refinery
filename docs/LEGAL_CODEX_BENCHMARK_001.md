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
