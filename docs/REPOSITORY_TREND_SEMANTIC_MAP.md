# Repository/project semantic mapping — v0.18

Cite-Refinery is not only a Cite-Agent research product. Its core is the
three-layer clustered problem map: Practical, Academic and Program. This
standalone Program feeder turns source-pinned Git repositories, project
capabilities, and bounded development history into inspectable semantic nodes.
No AI is needed for this adapter or the map.

## Source and epistemic boundaries

For each declared repository, this importer requires an exact local GitHub
origin, immutable base and head Git commit SHAs, an ancestor relation and a
bounded commit window. It reads committed source files directly via Git show.
It never executes source code or trusts uncommitted working files.

- Repository identity becomes a Program repository node.
- A revision comparison becomes a Program event node with commit count,
  changed-path count, bounded commit history, GitHub compare link, and a
  warning that history is NOT popularity, adoption, product maturity or
  effectiveness.
- Operator-curated project capabilities become Program capability nodes with
  a source file/line URL and an exact text excerpt checked at the pinned
  Git revision. The excerpt proves only source-file presence, not working
  software, production adoption or successful validation.
- Distinct repositories mapped to a common curated topic may get CANDIDATE
  RELATED_TO edges. Shared topic does not prove equivalence or interoperability.
- Optional Program-to-Practical/Academic/neutral links require an exact,
  already existing target node in the same private project, an identified
  source capability, an allowed relation and a human-written rationale.
  Every such link remains CANDIDATE, including ADDRESSES or ADAPTABLE_TO.
  It is never automatically promoted into support, causation or deployment.

Repositories can belong to different GitHub organizations, provided the
operator has a matching trusted local checkout. The workflow limits source
file types, manifest size, commit window, number of repositories and facts;
secret-like paths and local traversal are prohibited.

## First pinned portfolio example

The tracked example manifest is at
examples/repository_portfolio_snapshot_v1.json.
It maps five version-pinned source repositories:

1. Spectating101/nocturnal-oversight
2. Spectating101/refinery
3. Spectating101/yzu-cluster (Research Drive public repo)
4. Spectating101/hardware-splicer
5. Spectating101/solarpunk-coin (Policy Lab)

The operator-assigned semantic topics are source provenance/accountability,
research data workflows, executable verification, policy constraints, plus
the project-history module.

The isolated real-source import produced 5 clusters, 20 Program nodes,
15 qualified source/history relations and 5 candidate cross-repository
topic relations. Commit counts over each explicitly pinned window were
70, 18, 12, 287 and 8 respectively. These windows use different Git
topologies and are NOT comparable productivity, popularity or adoption
metrics. In particular, merges can introduce many side-branch commits.

## Trusted local operator use

Requirements: v0.14+ local private SQLite project and an operator bearer
credential in the CITE_REFINERY_TOKEN environment variable, plus the actual
checked-out Git repositories inside a trusted portfolio root.

To preview source evidence without changing project state:

    cite-refinery-repos --db /private/research.sqlite3 --project "$PROJECT" --repo-root /path/to/project_portfolio --manifest examples/repository_portfolio_snapshot_v1.json preview

The preview reports source revisions, topics, factual evidence sources,
candidate links, proposed additions, packet digest and project revision.
After human review, enqueue the exact unchanged manifest:

    cite-refinery-repos --db /private/research.sqlite3 --project "$PROJECT" --repo-root /path/to/project_portfolio --manifest examples/repository_portfolio_snapshot_v1.json enqueue --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

A separate trusted worker applies the reviewed graph transactionally:

    cite-refinery-private --db /private/research.sqlite3 worker-once

Identical imports are idempotent. A later operator-reviewed base/head pair
creates a new historical event without rewriting the old evidence snapshot.
This is not an automatic GitHub watcher or cloud-hosted service.

## Multi-engine integration validation

Against an isolated private map with the genuine frozen Kangmei Nocturnal
case (4 Practical events), four Cite-Agent literature records and two
abstract-backed scholarly claims (6 Academic total), the five-repository
manifest plus one explicitly curated candidate Program-to-Practical
relation produced 6 clusters, 31 nodes and 36 edges. The Chrome interface
loaded six modules, displayed the expected Program topic nodes, inspected
source links and reported no JavaScript errors.

It still reports ZERO three-layer-complete modules. Kangmei has Practical
and Academic layers but no proven case-specific Program solution; the
portfolio topics have Program evidence but no independently established
Practical/Academic counterparts. This is an important epistemic safeguard,
not a defect to conceal.

## Future improvements

The next Program source should be Refinery's actual capability, realization,
experiment and run attestations, beyond code/documentation excerpts. A
timestamped remote GitHub trending connector could track source-reported
stars, forks, releases, issue patterns and adoption evidence, with sensible
normalization and uncertainty; none of those are claimed here. Optional AI
may propose topic matches but must not silently change link authority.

Private production hosting still needs PostgreSQL, production identity,
authorization and queue hardening. The protected Vercel demonstration
remains read-only and does not include this private research corpus.
