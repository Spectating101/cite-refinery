# Cross-layer problem intelligence — reviewed graph

Source-bounded candidate interpretations, not independently verified results.

## The current local free-roaming dog population is not continuously enumerated by the periodic national survey system.

**Practical observation**
- Taiwan estimates the national free-roaming dog population every two years using a photographic capture survey method; the 2024 estimate was 141,584 dogs. [qualified]

**Academic mechanism / method**
- Free-ranging dog abundance estimates can be biased when detection probability, individual identification, registration, or population closure assumptions are inadequately handled. [qualified]
- Photographic mark-recapture and capture-recapture methods can use repeated individual observations to estimate free-roaming dog abundance under explicit assumptions. [qualified]

**Implementation / program**
- Talea is a street-survey system that records roaming animal sightings, characteristics, routes, survey areas, and geolocated observations. [candidate]

**Interpreted findings**
- **Scope qualification**: The Ministry of Agriculture cautioned that the 2024 national decline relative to 2022 was not statistically significant.
  - Why: This qualification changes how the practical observation can be interpreted.
  - Next check: Review sampling, significance and whether a causal interpretation is supported.
  - Inspect sources: https://animal.moa.gov.tw/Frontend/Know/Detail/LT00000864?parentID=Tab0000143, https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599
  - Status: source_bounded_qualification_requires_review
- **Method implementation mismatch**: Talea is a street-survey system that records roaming animal sightings, characteristics, routes, survey areas, and geolocated observations. However: ICAM's Talea guide says a sighting cannot include an animal photograph; the app can record textual notes. The scientific method requires: Repeated sightings need reliable individual reconciliation before they can support individual-aware population estimation.
  - Why: The implementation limitation interrupts a named requirement of the linked scientific method.
  - Next check: Verify whether talea can actually satisfy: Repeated sightings need reliable individual reconciliation before they can support individual-aware population estimation.
  - Inspect sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC12363366/, https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/, https://www.icam-coalition.org/talea-user-guide/, https://www.icam-coalition.org/tool/talea-street-survey-app/
  - Status: unresolved_capability_fit_not_a_proven_incompatibility

---

## Immigration and replenishment can undermine fertility-control effects in an open free-roaming dog population.

**Practical observation**
- Miaoli reported about 7,400 roaming dogs in 2025 and stated that intensified capture and inspection were still being outpaced by abandonment, free-roaming owned dogs, and reproduction. [qualified]

**Academic mechanism / method**
- In Shoushan, modelling indicated that maintaining female sterilization above 75 percent could theoretically control the dog population, while roughly 50 to 100 incoming dogs per year could severely disrupt the TNR effect. [qualified]

**Implementation / program**
- Taiwan's 2026 community free-roaming dog management program prioritizes risk hotspots, female-dog source control, pet registration, sterilization, owner responsibility, and community participation. [qualified]

**Interpreted findings**
- **Implementation outcome unestablished**: Taiwan's 2026 community free-roaming dog management program prioritizes risk hotspots, female-dog source control, pet registration, sterilization, owner responsibility, and community participation.
  - Why: The reviewed graph links a documented program to this problem but provides no outcome-evaluation edge.
  - Next check: Locate an independent intervention evaluation with a specified outcome, baseline and population.
  - Inspect sources: https://animal.moa.gov.tw/Frontend/News/Detail/N0000000002234
  - Status: absence_only_in_this_reviewed_graph

---

**Limit:** absence of evidence in this graph is not evidence of worldwide nonexistence; source-review relationships are not proof of causal effectiveness.
