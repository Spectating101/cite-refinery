# First evidence-qualified opportunity dossier: flood monitoring and warning

**October 22, 2026 · Development demonstration · Not operational advice or a deployment recommendation**

**Decision: LAB-ONLY FALSIFICATION PRIORITY.** The initial cross-map relation is plausible as a *research question*, but presently fails a critical source-code reliability test and lacks real local-system, alert-delivery or downstream-outcome evidence. **No deployable technology, underconverted asset, commercial demand, mortality benefit, or operational warning capability has been demonstrated.**

## 1. The actual question

Can the existing, pinned `WeixuanZ/flood-warning-system` water-level-station logic be safely adapted into a verified flood-alert workflow of the type described in WHO's Ban Kao Many account?

This is intentionally narrower than "the Atlas has found a solution for Laos." Existing source evidence belongs to **three different contexts**:

| Map | Original item and authority | What it does—and does not—establish |
|---|---|---|
| Practical/program source | WHO, 27 July 2023, *The importance of preparedness: strengthening community resilience against flash floods*, archived ID `OFFICIAL-f3e30d7ac5a5`: https://www.who.int/news-room/feature-stories/detail/the-importance-of-preparedness--strengthening-community-resilience-against-flash-floods | WHO reports advance warnings from national agencies and trained responders assisting Ban Kao Many, Laos. It does **not** identify or validate the GitHub software below, disclose controlled before/after casualty comparisons, or establish that a new supplier is needed. This is an *institutional narrative*, **not a Nocturnal approved-public case release**. |
| Academic | Luís Cea & Pierfranco Costabile (2022), *Flood Risk in Urban Areas: Modelling, Management and Adaptation to Climate Change. A Review*, DOI `10.3390/hydrology9030050`, archived ID `OA-f84a08fcbd0caa`: https://www.mdpi.com/2306-5338/9/3/50 | Genuine 2022 peer-reviewed-review source about *urban* flooding, multiple flood mechanisms and risk management. It provides general context, **not a field efficacy trial, local forecast calibration, source-code audit or causal study of Ban Kao Many**. Its archived role is `unverified_role_and_proposition`. |
| Implementation | `WeixuanZ/flood-warning-system`, source `c1c7facf2c5577a155edd93a0b7279ad7630518c`: https://github.com/WeixuanZ/flood-warning-system/tree/c1c7facf2c5577a155edd93a0b7279ad7630518c | Original upstream source advertises water-level stations, threshold ranking, LSTM/polynomial prediction and clustering. The **archived tests cover only station threshold/ranking functions**: three passes, two critical failures and one untested end-to-end outcome gate. Nothing here establishes local instrumentation, model forecast accuracy, public dissemination or field harm reduction. |

The archived `flood_candidate.json` is explicitly an **LLM-generated, unreviewed candidate**. Its two alignments cannot become validated simply by citing each other. The archived Ugandan cross-sectional research candidate (DOI `10.21203/rs.3.rs-9885849/v1`) is **not used to establish an independently verified effect** here; its original full study has not been confirmed in this development pass.

## 2. What we actually verified and what remains historical

Primary public-source checks for this dossier preparation:
- WHO original page: describes agencies, warnings, rescue teams and response plans. It includes broad claims about decreased drownings **without providing a specific causal impact estimate for this implementation in Ban Kao Many**.
- Publisher's original Hydrology (2022) review page: verifies existence, authors, title and multidisciplinary scope. Reviewing an original article is not automatically verifying each of its claims.
- Pinned original GitHub tree: source file `floodsystem/station.py` calculates station relative level; `floodsystem/flood.py` selects/sorts stations. The repository also advertises other capabilities that this dossier **does not reproduce or validate**.
- WMO/UN Early Warnings for All framework: four distinct, jointly necessary pillars of risk knowledge, detection/forecasting, dissemination and community response. Reference: https://public.wmo.int/all-activities/build-resilience/early-warnings-all

The following results **come from Cite–Refinery's existing historical synthetic test receipt, not a fresh execution**:

| Fixture | Archived result | Interpretation boundary |
|---|---|---|
| `threshold_selection` | Pass | Basic threshold selection on synthetic station values only |
| `missing_level_handling` | Pass | Missing reading exclusion on synthetic input only |
| `invalid_typical_range_handling` | Pass | Rejects zero-width typical range in the tested function |
| `nonfinite_sensor_level_is_excluded` | **Fail** | NaN entered the ranked candidates |
| `nonfinite_station_corrupts_top_one_ordering` | **Fail** | For ordered input low / NaN / high, expected top station was high but output was low |
| `local_warning_distribution_and_health_outcomes` | Not tested | No real feed, recipients, forecast lead time, response or health endpoint |

The NaN failure is a **bounded but critical** counterexample for a safety-related ranking component. It does not mean this project caused real-world warning failures, nor that an isolated fix would make it safe for deployment.

## 3. Cross-layer synthesis: four WMO pillars

| WMO pillar | What our candidate supplies | Disposition |
|---|---|---|
| Risk knowledge | General academic review and one external community account | **Insufficient** for target-catchment exposure, vulnerabilities and operational requirements |
| Monitoring, detection and forecasting | Original source-code station logic with synthetic passes and serious NaN sorting failures | **Critical blocker**; no local monitoring dataset, tuned thresholds or demonstrated forecast skill |
| Warning dissemination | No verified authorized issuing service, recipient coverage, message delivery or latency receipt | **Unverified** |
| Preparedness and response | WHO narrative describes responders in the actual community but does not connect them to the GitHub software | **Context only**, not technical integration |

It would be **incorrect** to label the WHO narrative an independent verification of GitHub functionality or to extrapolate urban hydrology review conclusions directly to rural Laos. The same problem domain does not establish engineering transfer.

## 4. Alternative opportunities already in the portfolio

Archived `conversion_qualification_with_positive_and_negative_trials_v1.json` includes candidates that might be more appropriate components of an eventual research experiment:

- `AuvroIslam/Nongor`: proposed offline/mesh warning-delivery drill. Message delivery reliability and code quality **not independently tested**.
- `soypat/lneto`: proposed timestamped microcontroller telemetry transport. Real sensor integration and timing accuracy **not independently tested**.
- `TheWillMiller/river-wise` + `sdmlua/FIMserv`: proposed threshold-to-inundation map demonstration, but integration and original source functionality **not independently tested**.

They must not be counted as integrated modules or customer-ready alternatives. Source existence and permissive license labels alone do not establish rights over data feeds, sensors, official warnings or model deployment.

## 5. Minimum reproducible next engineering experiment

**Stage A — safety regression, on pinned original revision (safe, offline, synthetic).** Fetch the exact source revision and SHA-verify files. Replay `nonfinite_sensor_level_is_excluded` and `nonfinite_station_corrupts_top_one_ordering`; randomly permute low/NaN/high input station order. Add ±infinity, missing/non-numeric values, invalid range and equal ties. First capture the unchanged original-code baseline. Fix *in a forked isolated adapter*, never silently modify upstream and call the original passed. Only advance when finite-only rankings are correct and deterministic under every preregistered case, with no change in valid station ordering. Bench performance and malformed-input handling separately.

**Stage B — field-transfer requirements.** Independently verify source permissions, an actual target station feed, station datum/units, sampling cadence, missingness, lead-time and river-specific thresholds. Compare output against authoritative local observations, with an offline safe replay first; do not connect to public warning channels.

**Stage C — warning chain.** Under consented, non-public simulation conditions, measure time to recognize, issue, deliver, acknowledge and act on warnings, including power/network outage and vulnerable-receiver cases. Official authorization and human incident-command control are prerequisites to any real dissemination.

**Stage D — Atlas versus combined specialist tools.** Give at least one independent reviewer the same task using ordinary literature search, web research, GitHub and an AI assistant. Freeze evaluation criteria beforehand: original-source identity; unsupported assertion count; correctly found code failure; actionable safe remediation; cost/time; explicit abstention. The reviewer must not be shown our selected solution or archived expected answers before comparison.

**Stop rule:** Any unresolved critical ranking defect, missing local rights/authorization, absence of a measurable real-world need or failed feasible integration keeps this as *research only*. A positive signal from synthetic tests cannot by itself promote safety or commercial outcomes.

## 6. Reproducible machine-readable decision receipt

The code at `src/cite_refinery/flood_evidence_dossier.py` reconciles the original source identities, original commit and archived result statuses, fails closed if any baseline result is silently altered, records the four missing WMO pillars, and retains alternative candidates as explicitly unqualified.

```bash
python -m cite_refinery.flood_evidence_dossier \
  --cross-layer-alignment research_materials/runtime_trials/cross_layer_20261020/flood_candidate.json \
  --functional-trials research_materials/opportunity_atlas/functional_component_trials.json \
  --conversion-queue research_materials/opportunity_atlas/conversion_qualification_with_positive_and_negative_trials_v1.json \
  --out /tmp/cite-refinery-flood-opportunity.json

python -m unittest discover -s tests -p 'test_flood_evidence_dossier_v1.py' -v
```

Machine decision: `LAB_ONLY_FALSIFICATION_PRIORITY_NO_DEPLOYMENT_RECOMMENDATION`. This is a source-artifact consistency decision, **not an AI/human-reviewed answer-quality score**.

### Status and next gate

This dossier code and tests are new draft work on a separate feature branch, stacked on #110. Neither source code replay nor GitHub Actions pass has yet been observed for this new branch. Optiplex's previously delegated original-source semantic/integration validation remains a **different** task. The frozen Atlas and sealed Academic holdout have not been changed.
