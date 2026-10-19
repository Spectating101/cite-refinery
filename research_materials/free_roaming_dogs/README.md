# Free-roaming dogs — field material pack v1

**This is an evidence/source collection, not a semantic graph expansion, a completed field assessment, or a report.** It exists so we can examine a real field and decide which problem nodes and relations have source support. No acceptance-case files, infrastructure, or map records have been changed.

## Actual reusable materials

| File | Contents | Source |
| --- | --- | --- |
| county_survey_estimates_2018_2024.csv | 88 rows: county-level free-roaming dog estimates in the four documented survey years | [MOA 41771](https://data.gov.tw/dataset/41771) |
| shelter_latest_month_snapshot.csv | 23 rows: 22 counties/cities plus national total, September 2026, operational fields | [MOA 73396](https://data.gov.tw/dataset/73396) |
| sources.json | 12 linked source records, with layer, scope, limitations and candidate module tags | Various first-party source pages and scholarly abstracts |
| provenance.json | Original full-feed SHA-256 hashes, 389 county raw records / 1,541 shelter raw records, selection rules and county sums | Official MOA JSON APIs |

The two CSV files are materialized extracts of the Ministry's live JSON endpoints. The full raw feeds were inspected locally but are **not** committed here; they can be retrieved at URLs in provenance.json. Original Chinese county names and unmodified source field codes are preserved.

## Critical quality checks

- Non-survey years in the county source sometimes contain a stray_dog_count of 0. **Do not treat these zeroes as actual absence of dogs** or calculate annual rates by naive interpolation. The extract includes only 2018, 2020, 2022 and 2024.
- Comparing the sum of the 22 county records to the national press totals:

| Year | County endpoint sum | MOA national news total | Difference |
| --- | ---: | ---: | ---: |
| 2018 | 146,774 | 146,773 | +1 |
| 2020 | 155,867 | 155,869 | -2 |
| 2022 | 158,696 | 159,697 | -1,001 |
| 2024 | 141,584 | 141,584 | 0 |

The 2022 discrepancy is material; **do not silently reconcile it**. The 2024 estimate decline was explicitly described by MOA as *not statistically significant*. None of this establishes causal policy effectiveness.

- The shelter data represent intake/outflow, occupancy and similar operational measures, and may aggregate dogs and cats. **They are not a direct proxy for the free-roaming dog population.** Current extract is the latest reporting month available at retrieval; verify the source definition before analysis.
- The 2026 designated risk-village list is a 49-page annex linked in sources.json. It establishes policy targeting, not evaluated outcomes.
- Academic study settings (Shoushan, Yangmingshan, historical Taiwan household survey) differ substantially. Do not generalize untested models or owner practices across place/time.
- Talea's documented ability to export survey observations does not establish photographic individual identification, continuous dog abundance estimation, or field effectiveness. The publisher's FAQ says sighting entries do not include photographs.

## Three-layer mapping entry points

- **Population observability:** MOA county/national estimated counts, Yangmingshan repeated photographic observations, population estimation assumptions, and Talea survey data format.
- **Population replenishment:** Miaoli local account, owner-practice literature, Shoushan immigration model and the 2026 source-control program.
- **Intervention and ecological effects:** reported wildlife attacks, administrative shelter flows, geographic risk-priority areas and the missing/unknown longitudinal outcome evidence.

These are *candidate inspection neighborhoods*, not pre-approved graph relations. Let the specific source claims determine which semantic nodes and typed edges deserve review.

## Reproduction and authority

The official source pages show **Taiwan Open Government Data License v1** for the MOA datasets; source attribution and API endpoints are preserved in provenance.json. Scholarly full texts and software-provider data are **not** copied into this repository.

Collection date: October 20, 2026. The live endpoints may change; pinned SHA-256 values describe the retrieved bytes. This pack lives separately from the original free-roaming dog acceptance case and frozen v0.24 material.
