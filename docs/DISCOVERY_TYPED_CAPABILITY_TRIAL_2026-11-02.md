# Atlas Discovery Challenge 003 — Typed Capability Mapping

**Date:** November 2, 2026 (Asia/Taipei)
**Status:** Experimental, original-source documentation claims only.
**Depends on:** #139 → #138 → #137 → #130. No merged changes to existing project repositories or authority.

## Question

Can Atlas avoid making invalid substitutions when projects share broad words but differ in required **operations, artifact modalities and input/output contracts**? Challenges #001–#002 revealed that web-archiving indexes, web captures, web replay, PDF extraction and source-cell validation were being conflated. Policy Lab also needs *PV plant time-series* anomaly evidence rather than merely any *photovoltaic cell image anomaly* dataset.

## What is implemented

`src/cite_refinery/typed_capability_map.py` consumes explicitly selected external records, declared capability rules and concrete portfolio requirement links. The rulebook defines, as separate typed candidates:

- **Nocturnal:** web capture (URL → saved web artifact), archive replay (saved artifact → reconstructed page), archival crawling (seed URLs → collections) and evidence custody (capture → provenance/hash receipt).
- **Research Drive:** PDF table extraction (PDF → rows/columns) versus keyed source-cell validation (original table + assertions → mismatches).
- **Policy Lab:** PV plant/inverter time-series data versus PV cell-image anomaly data. Only the former is mapped to the *plant-level* requirement.
- **Cite-Agent / Atlas:** citation-to-scientific-claim review and research reproducibility screening.

A source is considered for a type only when a fixed-size passage in its **original author documentation or official metadata** contains the required concept groups. Candidate evidence includes exact source identity, original blob/hash receipt, passage offset/snippet, declared input/output and the source-claims-only authority.

A compiled `candidate_edges` relation has the exact authority `MAY_SUPPORT_REQUIREMENT_REVIEW_ONLY`. It is **not** a verified implementation, match of live function signatures, security clearance, reproducibility certificate, or permission to adopt anything. A curated `awesome-...` repository is classified as a **discovery index**, not an operative archiver. Missing or rate-limited records remain unavailable, not negative evidence.

## Reproducible private run

The source records came from the existing relevance-ranked 11-query trial in Challenge #002. The original observations are kept in Optiplex's private directory. To replicate with a fresh source query:

    PYTHONPATH=src python -m cite_refinery.multi_source_discovery \
      --manifest examples/discovery/focused_relevance_sources.json \
      --out ~/.local/share/atlas-discovery/typed-source-snapshot

Then run typed inspection on a bounded selected set:

    PYTHONPATH=src python -m cite_refinery.typed_capability_map \
      --collection ~/.local/share/atlas-discovery/typed-source-snapshot/collection.json \
      --rules examples/discovery/typed_capability_rules.json \
      --needs examples/discovery/typed_project_needs.json \
      --cases examples/discovery/typed_relevance_trial_cases.json \
      --out ~/.local/share/atlas-discovery/typed-mapping-snapshot

The fixed case list refers to public original-source identities that **may not appear in a subsequent top-N search**. If absent, select available cases explicitly and record coverage; don't invent a missing result or silently substitute a different project.

## Result interpretation

The first live trial examined 12 source records in an explicit set and produced 10 candidate links and a correctly separate index result. After tightening the false cell-validation attribution, the second live replay yielded 9 candidate links: 8 sources with documented candidate types, 1 curated index, 1 source with no typed documentary match, and 2 unavailable originals. However, it also initially assigned the `pdf_cell_validation` type to `img2table` using weak "cell/check" keyword coincidence. That was **a false capability attribution**. The rulebook now requires stronger source/row-key or original-cell assertions and has a negative fixture requiring an extraction-only README not to satisfy cell validation. This issue demonstrates the importance of testing typed labels against counterexamples, rather than counting graph edges.

Source descriptions contain incidental references, badges and linked tool lists, and cannot guarantee executable behavior. The compiler therefore treats every positive as an author-documentation claim and stores the specific excerpt supporting it. A capability can be genuinely present yet missed if its README lacks our exact concepts; negative or unavailable classifications must not be converted into external technology absence.

## Read-only and evidence boundaries

- No repo cloning, package installation, untrusted code execution, source graph writing, schedule, merge or deployment.
- Official source metadata constrained by prior PR #139, with bounded bytes, fixed hosts, timeouts and evidence hashes. Source full text remains outside public Git.
- No output can promote Policy Lab's experimental claims or Nocturnal's allegations.
- The explicit requirement link is a hypothesis for **owner-led benchmarking**. The next real gate requires checking actual inputs/outputs against fixtures with known expected results and an independently labeled held-out selection.

## Next step

Improve type hierarchy beyond simple passage matching, handle linked code/docs, and measure false type attribution plus missed compatible functions against a representative held-out corpus. Compare typed Atlas candidates with manually verified discovery and GitHub-only baselines; prioritize actual replacement value, not number of edges.
