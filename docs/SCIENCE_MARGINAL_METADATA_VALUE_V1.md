# Does Science actually add useful evidence beyond our frozen GitHub survey?

**2026-10-23 — preregistered matched/unmatched development experiment. No graph promotion.**

## Question and boundary

We have **1,287** frozen Implementation GitHub identities, of which **398** match existing projects in ecosyste.ms Science and **889** do not, as established by 52 successful bulk calls on [the source-verified CI run](https://github.com/Spectating101/cite-refinery/actions/runs/39928095138). The question is no longer merely *does Science know the source URL?* but whether it gives a tangible additional metadata signal that saves us reimplementing discovery.

This pass is a **metadata field-availability and provenance** experiment, not a semantic performance study, software correctness benchmark, blinded quality evaluation or independent staff-hours savings measurement.

## Precommitted original-source comparison

The independently generated original full census artifact is downloaded directly from its immutable GitHub Actions run with read-only permissions. We do not requery and replace the baseline sample under different results. Inputs remain the two frozen GitHub survey files whose combined SHA-256 census digest is:

`b8bb8c733801c04e8c6f07f0c9a99f4016edd8e677343c93ffe13612aea450d2`

We select exactly 20 matches and 20 nonmatches in the original full-census result, using ascending SHA-256 of the exact original GitHub URL with fixed seed `refinery-science-incremental-context-v1`. The identities and Science IDs are committed to the bounded preregistration file. CI independently **recomputes the selection** from the full historic census, and fails if the sample or source fingerprint differs.

Each of the 20 matched software projects gets **one** read-only original Science API request to:

`GET https://science.ecosyste.ms/api/v1/projects/<original_project_id>/search_context`

The response's exact original project ID and expected arrays are checked. We measure available secondary descriptions, languages, package records, and directly indexed dependency records with a timestamp. The 20 nonmatched repositories are benchmark **original GitHub snapshot-only controls**, because there is no known Science project ID to retrieve; these are not a randomized controlled trial or statistical precision estimate.

Every failure, missing context, or source ID mismatch is recorded as **unknown/unavailable**, not replaced by zero metadata. Fetched catalog information is **not** accepted as working functionality or scientifically substantiated implementation.

## Reuse-versus-build decision rule

- **Keep** the Science adapter if it supplies traceable additional structured project/package/dependency/description information for recognized repos, with acceptable provider reliability.
- **Do not** retire the underlying frozen GitHub source discovery because 889/1287 sources were not in the Science identity catalog.
- **Do not** build another package relationship index until we have evaluated whether Science, ecosyste.ms Repos, and Software Heritage already suffice.
- **Do not** count more description records as improved correctness or "saved hours" without a controlled researcher-workflow evaluation.
- **Retain** our original tests of source SHA, code function, requirement compatibility, commercial rights and adoption; none are outsourced to Science's existence, score or descriptions.

No new private Nocturnal import, original fulltext redistributions, sealed 66 Academic records, automated entity merging, field deployment or validated funding claim occurs.

## ORKG and Nocturnal side gates

ORKG's public source implementation selects between a legacy and v2 paper controller through HTTP content negotiation. We changed the adapter to send `Accept: application/vnd.orkg.paper.v2+json`, using a host-pinned bounded response and no redirects. A prior anonymous generic-JSON request resulted in HTTP 400, **not zero scholarly sources**. Live status can only be declared successful once its independent API smoke passes.

Nocturnal's original `src/nocturnal_product/identity.py` already recognizes FTM, OpenSanctions, and yente candidate identities; FollowTheMoney data is a compatible external schema, not grounds to replace Nocturnal or publish real named actors. OpenAleph is an independent service candidate, not a current requirement.

## Reproduction / authoritative execution

The source-bound CI workflow is `.github/workflows/science-marginal-metadata.yml`. It downloads the **original full census artifact**, reruns the original-source and corruption tests, retrieves at most 20 live contexts, prints only aggregate availability metrics, and stores a JSON review-only receipt.

Local usage requires the unmodified full census artifact:

```sh
SCIENCE_FULL_CENSUS_PATH=/path/to/original/science-full-1287.json \
  python -m unittest discover -s tests -p test_science_marginal_metadata_v1.py -v

python -m cite_refinery.science_marginal_metadata \
  --sample research_materials/external_landscape/science_marginal_context_sample_v1.json \
  --census /path/to/original/science-full-1287.json \
  --primary research_materials/opportunity_atlas/github_repository_survey.json \
  --frontier research_materials/opportunity_atlas/github_frontier_repository_survey.json \
  --out /tmp/refinery-marginal-science-value.json
```

**Report values are deliberately omitted here until an executed independent live job is checked.** A successful job would qualify source metadata reuse for research; it would not prove commercial product differentiation.
