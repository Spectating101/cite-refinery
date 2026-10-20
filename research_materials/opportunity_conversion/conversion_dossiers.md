# Opportunity conversion: ofn-paid-contributor-route

**Status: evidence_lead_only** — not a proven commercial arbitrage.

## Real problem
Open Food Network Canada reports a map-centering and zoom bug: one mis-geocoded enterprise can shift the map to another continent, making local sellers hard for shoppers to find.

## Existing asset
Established open-source marketplace linking growers, food hubs and purchasers across a global nonprofit network. (https://github.com/openfoodfoundation/openfoodnetwork)
Capability source: https://github.com/openfoodfoundation/openfoodnetwork/blob/master/README.md
Repository license status: copyleft
Repo adoption and willingness-to-pay have **not** been verified.

## Mechanism / opportunity fit
**Function documented:** Open Food Network includes a public /map for producer discovery and a MapCentreCalculator setting map center from enterprise coordinates.

**Operational requirement:** A robust, locale-aware map should display the intended country's sellers even if one enterprise is geocoded outside the service geography.

**Gap to verify:** Issue #14924 identifies extreme-coordinate midpoint and hard-coded zoom defects; no patch, review or measured retention impact is demonstrated in this assessment.

**Fit stage:** source_reviewed

## Buyer and conversion
Prospective buyer: Open Food Foundation engineering team or existing country instance operators (paid contractor fit to confirm)
Buyer evidence stage: problem_signal
- Self-execution: conditional_on_license_compliance_review
- Maintainer/partner service: apply_for_published_paid_contributor_process_no_contract
- Component reuse: technical_candidate_requires_integration_and_rights_check

## Concrete next action
Check whether the paid contributor application remains open and propose one bounded deliverable.

## Commercial reality
Evidence of underconversion: **not_established**.
GitHub usage counters and repository feature lists do not establish a monetization gap or economically addressable demand.
Unit economics: not_estimated (No observed selling price or total delivery cost; no revenue projection.)

## Inspect original signals
- Open issue #14924 describes a real Canadian instance problem and reports a user threatening to leave; maintainer issue text is not independent churn measurement. — https://github.com/openfoodfoundation/openfoodnetwork/issues/14924 [reported]
- A published open bug documents current engineering need but not a paid budget for this task. — https://github.com/openfoodfoundation/openfoodnetwork/issues/14924 [reported]
- The foundation publicly advertises applications for paid developer and system administrator contributions; no specific offer or contract has been received. — https://openfoodfoundation.org/become-a-contributor/ [reviewed]
- Maintainer issue names a concrete open engineering problem; it does not promise paid engagement. — https://github.com/openfoodfoundation/openfoodnetwork/issues/14924 [reported]

No outreach or deployment has been initiated.


---

# Opportunity conversion: foodsoft-food-coop-deployment

**Status: evidence_lead_only** — not a proven commercial arbitrage.

## Real problem
Foodsoft's cooperative order-balancing UI can flag false mismatches when article quantities are rounded to three decimals but the summed group-order quantities are not.

## Existing asset
Nonprofit food cooperative software for product ordering, cooperative accounting and job scheduling. (https://github.com/foodcoops/foodsoft)
Capability source: https://github.com/foodcoops/foodsoft/blob/master/README.md
Repository license status: copyleft
Repo adoption and willingness-to-pay have **not** been verified.

## Mechanism / opportunity fit
**Function documented:** Foodsoft supports member group orders and accounting/balancing views with a quantity-difference diagnostic.

**Operational requirement:** Price and quantity reconciliation must compare values consistently at the same precision without suppressing real order mismatches.

**Gap to verify:** Issue #1368 identifies a precision mismatch; a safe fix and regression fixture still need to be executed. No contract or local deployment demand is confirmed.

**Fit stage:** source_reviewed

## Buyer and conversion
Prospective buyer: Foodsoft maintainer community or cooperatives experiencing balancing errors
Buyer evidence stage: problem_signal
- Self-execution: conditional_on_license_compliance_review
- Maintainer/partner service: community_contribution_invitation_not_a_paid_service
- Component reuse: technical_candidate_requires_integration_and_rights_check

## Concrete next action
Verify the named open issue and discuss a minimal, test-backed contribution; payment is unconfirmed.

## Commercial reality
Evidence of underconversion: **not_established**.
GitHub usage counters and repository feature lists do not establish a monetization gap or economically addressable demand.
Unit economics: not_estimated (No observed selling price or total delivery cost; no revenue projection.)

## Inspect original signals
- Issue #1368 reports an explicit unit rounding discrepancy and a minimal code-location lead; this is software maintainer feedback, not proof of demand for paid consulting. — https://github.com/foodcoops/foodsoft/issues/1368 [reported]
- An unresolved published issue documents a software quality need, not spending authority or a purchase request. — https://github.com/foodcoops/foodsoft/issues/1368 [reported]
- Foodsoft publicly invites contributors and participation in its community development activities; this is not a paid implementation request. — https://github.com/foodcoops/foodsoft/blob/master/README.md [reviewed]
- Unassigned open issue #1368 is an actionable contribution candidate; the maintainer has not contracted our work. — https://github.com/foodcoops/foodsoft/issues/1368 [reported]

No outreach or deployment has been initiated.


---

# Opportunity conversion: kobo-dog-sighting-integration

**Status: evidence_lead_only** — not a proven commercial arbitrage.

## Real problem
Taiwan's periodic dog-population surveys and research on mark-recapture imply an investigation requirement for repeatable sightings with photographic identity records; this is not a confirmed local agency procurement request.

## Existing asset
Open-source form/data collection infrastructure for field operations and surveys. (https://github.com/kobotoolbox/kpi)
Capability source: https://github.com/kobotoolbox/kpi/blob/main/README.md
Repository license status: copyleft
Repo adoption and willingness-to-pay have **not** been verified.

## Mechanism / opportunity fit
**Function documented:** KoboToolbox provides offline forms and API access to survey records and attachments, potentially allowing dog sighting photos to be collected.

**Operational requirement:** Repeated dog-specific sightings with location/time/photo provenance, individual reconciliation, and valid population-estimation assumptions.

**Gap to verify:** A dog-identification model and statistical abundance estimator would remain separate; no end-to-end field proof or Taiwan authority willingness-to-pay has been established.

**Fit stage:** untested

## Buyer and conversion
Prospective buyer: Potential animal-control departments, shelters, research organizations and field survey contractors
Buyer evidence stage: none
- Self-execution: conditional_on_license_compliance_review
- Maintainer/partner service: research_upstream_fit_before_permission_request
- Component reuse: technical_candidate_requires_integration_and_rights_check

## Concrete next action
Run a minimal capability-to-requirement test before proposing deployment.

## Commercial reality
Evidence of underconversion: **not_established**.
GitHub usage counters and repository feature lists do not establish a monetization gap or economically addressable demand.
Unit economics: not_estimated (No observed selling price or total delivery cost; no revenue projection.)

## Inspect original signals
- Population estimation literature describes the importance of identification and repeat observation for free-roaming dog abundance estimation. — https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/ [reviewed]
- Taiwan's 2024 national dog estimate and periodic survey methodology do not establish a continuously tracked local population. — https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599 [reviewed]

No outreach or deployment has been initiated.


---

# Opportunity conversion: food-rescue-mvp-partner-audit

**Status: evidence_lead_only** — not a proven commercial arbitrage.

## Real problem
Surplus-food donors and recipients face coordination, pickup and handling frictions, while published redistribution interventions rarely establish long-term beneficiary outcomes.

## Existing asset
A community surplus-food listing, discovery, claim and pickup prototype with published unverified feature claims. (https://github.com/still-trying/food-rescue)
Capability source: https://github.com/still-trying/food-rescue/blob/main/README.md
Repository license status: no_license_detected
Repo adoption and willingness-to-pay have **not** been verified.

## Mechanism / opportunity fit
**Function documented:** README claims authentication, listings, geo-discovery, atomic claiming and pickup completion.

**Operational requirement:** Reliable donor-to-recipient posting, collection and traceability without unsafe food handling or identity/access failures.

**Gap to verify:** No observed real adoption, business/organization onboarding, operator safety verification, food safety liability assessment or external buyer commitment. Public README mentions MIT despite no detected root license file.

**Fit stage:** untested

## Buyer and conversion
Prospective buyer: Potential food-rescue nonprofits or local institutions
Buyer evidence stage: none
- Self-execution: blocked_until_rights_resolved
- Maintainer/partner service: research_upstream_fit_before_permission_request
- Component reuse: blocked_until_rights_resolved

## Concrete next action
Ask maintainer about license/permission; do not copy, deploy or sell the code yet.

## Commercial reality
Evidence of underconversion: **not_established**.
GitHub usage counters and repository feature lists do not establish a monetization gap or economically addressable demand.
Unit economics: not_estimated (No observed selling price or total delivery cost; no revenue projection.)

## Inspect original signals
- A scoping review discusses surplus-food redistribution models and structural limitations, not demonstrated buyer demand for this particular MVP. — https://doi.org/10.1111/nbu.70053 [reported]

No outreach or deployment has been initiated.
