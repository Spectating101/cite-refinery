# Cite-Agent abstract grounding to Academic claims — v0.17

Cite-Refinery remains a three-layer clustered research map, operable without
AI. This optional bridge processes model-assisted Cite-Agent grounding receipts
without upgrading them into independent evidence of real-world events.

## Real Optiplex experiment on 19 October 2026

Two specific research claims about the Kangmei Pharmaceutical ruling were
evaluated with the actual Cite-Agent claim-grounding CLI.

- Audit insurance and market reaction, Yang et al. (2023);
  DOI 10.1080/21697213.2023.2239674.
- Difference-in-differences reporting-quality response, Cao et al. (2026);
  DOI 10.1007/s10551-026-06344-2.

Both returned a supported verdict and one quotation in a retrieved abstract,
with zero rejected quotations. These are abstract-backed findings, NOT full-text
methodological checks and NOT verified relationships to Nocturnal events.

Using the private authenticated ingestion queue, two additional Academic
claim nodes were imported into the existing Kangmei semantic module.
The actual integrated map contains Practical=4, Academic=6, Program=0,
with one neutral anchor, totaling 11 nodes and 15 typed edges.

## Contract

- A completed Cite ground schema-v1 receipt is required. Error, not-run,
  not-found or unsupported claims do not become grounded nodes.
- The DOI must already exist as an Academic Cite source inside the SAME
  provenance-verified frozen Nocturnal research module.
- The quotation must be present, as a normalized exact substring, in the
  previously imported indexed abstract for that exact DOI and title.
- An accepted scholarly claim becomes an Academic claim node with hashes of
  its quote, abstract and grounding receipt; the source and verification scope
  are inspectable.
- The claim-to-DOI paper edge is qualified DERIVED_FROM, expressing indexed
  abstract backing, not full-text or independent scientific validation.
- The claim-to-Nocturnal case context edge is RELATED_TO candidate, never
  automatically asserted SUPPORTS, CAUSES or EXPLAINS. Specific Nocturnal
  events are not considered established by scholarly topical overlap.
- A fabricated quotation, mismatched paper, off-project DOI or rejected
  quotation cannot be imported as a qualified Academic finding.

These checks do not authenticate a manually supplied JSON file as genuine
Cite-Agent output. Operator approval remains necessary. Identical quotations
can still be misleading without full-text methods and limitations.

## Local operator workflow

A v0.14+ private local workspace must already contain the v0.15 Nocturnal
case and v0.16 Cite-Agent literature, with CITE_REFINERY_TOKEN set to an
authorized short-lived bearer credential. Generate an operator-reviewed
grounding JSON file separately:

    cite-agent-research ground "Specific research claim" > /private/grounding.json

Preview its exact packet without mutation:

    cite-refinery-ground --db /private/research.sqlite3 --project "$PROJECT" --candidate china-kangmei-2020 --ground-json /private/grounding.json preview

After inspecting sources, quote, warnings, project revision and packet digest,
queue the SAME packet:

    cite-refinery-ground --db /private/research.sqlite3 --project "$PROJECT" --candidate china-kangmei-2020 --ground-json /private/grounding.json enqueue --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

Then execute the existing trusted private worker:

    cite-refinery-private --db /private/research.sqlite3 worker-once

Without model access, Cite-Refinery's map and manual research workflows still
function. A Cite-Agent grounding result of not_run must not be promoted.

## Next evidence gates

Full-text reading, sample and identification-method analysis, checks of
robustness, precise scholarly claim attribution and human-approved cross-layer
relations remain outstanding. The Program/Refinery engine is still absent from
the Kangmei cluster. The public Vercel demonstration remains unchanged and
contains no private Nocturnal, literature or grounding records.
