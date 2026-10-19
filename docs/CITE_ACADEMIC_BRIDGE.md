# Cite-Agent → Academic layer bridge (v0.16)

This is the second actual engine integration. It **attaches retrieved scholarly
records to an existing Nocturnal source-case semantic cluster**, preserving the
original Practical evidence and source authority. It is not a new standalone
literature workbench, or a claim-verification system.

## First case and source records

Target: Nocturnal's frozen China Kangmei matter, already ingested by v0.15.
Run the existing structured Cite-Agent command with a deliberately scoped query:

    cite-agent-research search "Kangmei Pharmaceutical securities fraud special representative litigation investor compensation China" --limit 8

The 19 October 2026 Optiplex search returned four DOI-bearing papers (the
provider was Semantic Scholar; OpenAlex separately reported rate limiting).
Two papers were independently located on their journal publishers' websites:

- Yang et al. (2023), China Journal of Accounting Studies,
  DOI 10.1080/21697213.2023.2239674
- Cao et al. (2026), Journal of Business Ethics,
  DOI 10.1007/s10551-026-06344-2

The remaining two are retrieval candidates, not independently publisher-verified
through this integration. No search JSON, abstracts, or private Nocturnal records
are committed into this repository.

## Exact mapping

- Require a real source-provenanced Nocturnal cluster and its neutral case anchor.
- Reuse exactly the same cluster's external key and title: **one module**, not
  a duplicated academic project.
- Each DOI becomes an Academic SOURCE node with indexed title, authors, venue,
  year, DOI URL, retrieval provider/query/digest and an indexed abstract in its
  provenance receipt (private project only). The abstract is not scientific
  verification of any underlying factual claim.
- Create an explicitly CANDIDATE RELATED_TO edge from each paper to the
  Nocturnal case's neutral anchor. These edges are intentionally excluded from
  verified cross-layer trace paths.
- No Program nodes, scientific claims, citations-as-proof, contradiction or
  causal edge is asserted from bibliographic search alone.

## Local authenticated operation

Requirements: v0.14 private local DB and ingestion worker; a v0.15 Nocturnal
Kangmei case already imported into the intended project; installed Cite-Agent's
structured literature command. Use a trusted operator and a short-lived bearer
credential stored in CITE_REFINERY_TOKEN. Obtain PROJECT from the authenticated
private project list.

Preview using fresh Cite-Agent retrieval (no graph mutation):

    cite-refinery-cite --db /private/research.sqlite3 --project "$PROJECT" --candidate china-kangmei-2020 --query "Kangmei Pharmaceutical special representative litigation investor compensation" preview

For reproducible operator review, capture the CLI's search JSON outside Git
and optionally substitute `--search-json /private/cite-search-output.json`
for the `--query` flag. The JSON is locally operator-submitted data and must
not be treated as cryptographically authenticated source identity.

Review the reported packet digest, project revision and candidate-link counts.
Only then enqueue an unchanged packet:

    cite-refinery-cite --db /private/research.sqlite3 --project "$PROJECT" --candidate china-kangmei-2020 --search-json /private/cite-search-output.json enqueue --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

Finally:

    cite-refinery-private --db /private/research.sqlite3 worker-once

The private project's atlas should have Practical=4, Academic=4, Program=0
for the first Kangmei pilot if using the cited four-paper retrieval snapshot.

## Boundaries and follow-up

Retrieval isn't full-text access. Retrieved abstracts are *not* automatically
grounded claims, and even apparently topical citations may be wrong or misleading.
Future work must inspect paper-level evidence, extract carefully attributed
academic claims, review relation types against exact Practical nodes, and never
promote candidate links without a separately accountable review.

This milestone does NOT launch a hosted private service, autonomous live
synchronization, third-party integrations, or the missing Program layer.
The protected public Vercel pilot remains unchanged and contains none of the
private Kangmei/Nocturnal/Cite records.
