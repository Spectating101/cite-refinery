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
