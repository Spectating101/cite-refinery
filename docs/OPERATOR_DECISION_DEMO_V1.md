# Source-to-Solution Verification | Operator decision brief

**Question:** Which practical academic implementation links pass independent semantic review without domain-specific answer cues?

**Investigation:** `52d77ac4d5c1464f96d4`

**Decision:** No cross-layer connection has been promoted to verified outcome or commercial value. Use the following results for scoped next-step decisions, not certification.

**Publisher source receipts:** 6/6 matching reported passages. Matching a source is not proof of the report's substantive claims.

## Decision matrix

| Link | Semantic evidence | Original-code regression | Recommended action |
|---|---|---|---|
| BR-01 | semantic_fit_uncertain | 10/14 original vs 14/14 temporary candidate, NOT complete application | VALIDATE next with real application integration and an operator-defined acceptance test; a bounded repair exists, but neither mechanism-to-product nor outcome is proven. |
| BR-02 | reviewer_reports_mismatch_or_contradiction | 10/14 original vs 14/14 temporary candidate, NOT complete application | REJECT this proposed cross-layer explanation; separate component-level test evidence does not repair the academic applicability mismatch. |
| BR-03 | reviewer_reports_mismatch_or_contradiction | 6/9 original vs 9/9 temporary candidate, NOT complete application | REJECT this proposed cross-layer explanation; separate component-level test evidence does not repair the academic applicability mismatch. |

## Evidence and remaining obligations

### BR-01: semantic_fit_uncertain
Practical: `USR-P-01` · Academic: `USR-A-02` · Implementation: `USR-I-01`.

**Action:** VALIDATE next with real application integration and an operator-defined acceptance test; a bounded repair exists, but neither mechanism-to-product nor outcome is proven.

**Pinned original-code evidence:** openfoodfoundation/openfoodnetwork, Git blob `74a669690f56c15f2c15ceffe34c8f02a96d0e27`. Original scoped tests: 10/14 pass; temporary patch: 14/14 pass. **No full original application suite, upstream acceptance or field impact.**

**Next functional gate:** Connect configured instance bounds, verify valid remote locations and actual zoom in full OFN frontend tests

**Additional validation required:**
- Run the existing Jasmine specs for MapCentreCalculator and add cases with one outlier coordinate, such as Guatemala among Canadian enterprises, to reproduce the shift.
- Implement and test a robust alternative (median, trimmed bounds, or an outlier filter) and check the resulting centre and zoom against the expected country bounds.
- Check the full file, the zoom logic and the admin default lat/long handling, which the excerpt omits.
- Measure the first-view location on a real or seeded dataset with realistic geocode error rates before and after the change.

### BR-02: reviewer_reports_mismatch_or_contradiction
Practical: `USR-P-01` · Academic: `USR-A-01` · Implementation: `USR-I-01`.

**Action:** REJECT this proposed cross-layer explanation; separate component-level test evidence does not repair the academic applicability mismatch.

**Pinned original-code evidence:** openfoodfoundation/openfoodnetwork, Git blob `74a669690f56c15f2c15ceffe34c8f02a96d0e27`. Original scoped tests: 10/14 pass; temporary patch: 14/14 pass. **No full original application suite, upstream acceptance or field impact.**

**Next functional gate:** Connect configured instance bounds, verify valid remote locations and actual zoom in full OFN frontend tests

**Additional validation required:**
- Check whether the heat-warning study includes any geocoding, mapping or viewport variable. The title suggests it does not.
- Run a map-centre unit test with outlier coordinates to confirm only the viewport behaviour, not any health outcome.
- Provide independent evidence, which does not exist in the supplied sources, linking map-centre correction to heat exposure behaviour or hospital outcomes.

### BR-03: reviewer_reports_mismatch_or_contradiction
Practical: `USR-P-02` · Academic: `USR-A-02` · Implementation: `USR-I-02`.

**Action:** REJECT this proposed cross-layer explanation; separate component-level test evidence does not repair the academic applicability mismatch.

**Pinned original-code evidence:** foodcoops/foodsoft, Git blob `64567d22f2a02cd3d4b0a481ff1f8b581e90420d`. Original scoped tests: 6/9 pass; temporary patch: 9/9 pass. **No full original application suite, upstream acceptance or field impact.**

**Next functional gate:** Run complete Foodsoft Rails/RSpec and ActiveRecord precision/units tests, then obtain maintainer agreement

**Additional validation required:**
- Read the full Foodsoft issue text to see whether it describes a rounding or unit-conversion cause.
- Inspect the full `orders_helper.rb` and the actual code that computes the ordered-quantity comparison, since the excerpt shows only a link helper.
- Reproduce the balance-view mismatch with decimal quantities and check whether any precision change resolves it.
- Show that the geocoding paper's findings have any relation to quantity accounting. None is apparent.

## Proposed customer deliverable (commercial hypothesis)

**Source-to-Solution Verification Sprint:** Given a documented bug, investigation question or disputed engineering claim, produce a source-pinned report, a reproducible component test where legally/technically permitted, and a scoped go/hold/reject next-step decision. Optional implementation work must be a separately authorized engagement.

**Not a paid result:** No buyer, price acceptance, signed statement of work, real operational improvement, security certification, or revenue has been established. The near-term commercial test is a manually delivered pilot with a consenting client and measured effort/decision utility, not a speculative SaaS launch.

**Limitations:** Only available authenticated source-passage receipts and a previously curated source-pinned runtime report are joined. Original app/browser/Rails completeness, academic mechanism applicability, owner permissions and buyer demand remain distinct gates.
