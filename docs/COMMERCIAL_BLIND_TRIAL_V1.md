# Commercial Atlas vs. general AI: independently generated blinded trial harness

**Status (23 October 2026):** The benchmark *harness and offline tests* exist. The authenticated model trial has **not** been run in this branch. Therefore there are **no independently generated head-to-head results or Atlas wins** from this work yet.

## Hypothesis

With the same publicly attributed evidence, is an Atlas-assisted decision process better than an unaided but equally instructed modern general AI model at recognizing a potentially convertible asset, its buyer uncertainty, obvious substitutes, rights constraints and the lowest-cost commercial experiment?

The prior 18/18 comparison in PR #123 was an **unblinded, researcher-authored calibration**, not the answer. This is the first executable route to an independent model comparison.

## Trial design

- **One proposer model for BOTH arms.** Default `gemini-3.8-flash-medium` via the locally authenticated `agy` adapter. Running separate provider families in the candidate arms would confound model quality with Atlas assistance.
- **The same attributed, bounded source packet** appears word-for-word in both model prompts. No browsing/tools enabled through the existing CLI adapter.
- **Control:** source packet and regular commercial investigation instructions.
- **Atlas:** identical source packet plus `evaluate()`'s deterministic three-layer/rights/demand/competition reasoning. It is an additional input and computational step. Prompt lengths differ; no matched-token, response-token, cost, or effort equivalence is claimed.
- **Blind judge:** different model family, default `claude-opus-5-5-medium` via `agy`. Candidate answers are labeled `X` and `Y` in shuffled order. The judge receives only source packet plus anonymous decision output, never which one used Atlas. Candidate outputs identifying their own arm are rejected before judging.
- Record per-case source fingerprint, arm order, prompts' character lengths, model IDs/families, model wall times, structured reply receipts, failures, judge preference and anonymization mapping (exposed only in final run receipt).
- **No token or monetary usage metrics:** the existing CLI integration does not expose reliable usage/billing receipts. Wall clock and character counts are **not** a valid replacement for paid token spend, human labor cost or commercial unit economics. The public benchmark must not overclaim cost parity.
- No cross-provider fallback; a failed request stays a failed request and no score is generated. No account rotation.

## Frozen casebook

`research_materials/opportunity_conversion/blind_casebook_development_v1.json` contains **four already researched development scenarios**, not a new held-out set:

1. **Open Food Network Canada map:** first-party user issue + paid-contributor pathway + volunteer/certification hurdle
2. **Foodsoft cooperative balancing:** first-party fractional quantity mismatch with no demonstrated paid assignment
3. **Commercial rooftop PV audit:** technical reuse candidate plus directly competing Solargis PV Performance Assessment
4. **Taiwan free-roaming dog field survey:** academic identity requirements, ministry survey context, and Kobo field-data component

All source IDs, URLs, short paraphrased extracts, split classification, and source fingerprints are captured. Claims are source-bound research inputs, not automatically freshly reverified independent source truth or confirmed purchase decisions.

All four cases were selected **after** seeing development results in Atlas. They are suitable for a first genuine model-call rehearsal, but not final evidence of out-of-sample commercial superiority. A sealed test set, independent annotation and real buyer outcomes are a separate experiment.

## Offline verification (CI and any trusted machine)

```bash
PYTHONPATH=src python -m unittest tests.test_commercial_blind_trial_v1 -v
PYTHONPATH=src python -m cite_refinery.commercial_blind_trial plan
```

`plan` performs **zero model calls** and emits `ready_for_authenticated_opt_in_not_executed`, case IDs, source hashes and per-arm prompt lengths. No artificial scorer output is recorded as production evidence.

## Authenticated model execution on authorized Optiplex

The existing `cite_refinery.external_llm_runtime.invoke_semantic_llm` integration is reused. Use the machine's already-authenticated Antigravity session with the exact model IDs that were previously observed by `agy models`. Do not place credentials in this repository, the model prompts, logs, or chat.

First one case only to validate API/formats and independent-family response:

```bash
PYTHONPATH=src python -m cite_refinery.commercial_blind_trial run \
  --provider antigravity --model gemini-3.8-flash-medium \
  --judge-provider antigravity --judge-model claude-opus-5-5-medium \
  --max-cases 1 \
  --output /tmp/commercial_blind_smoke_PRIVATE.json
```

Then complete the four-case development run, **only if authentication, model quotas and reply schema permit**:

```bash
PYTHONPATH=src python -m cite_refinery.commercial_blind_trial run \
  --provider antigravity --model gemini-3.8-flash-medium \
  --judge-provider antigravity --judge-model claude-opus-5-5-medium \
  --output /tmp/commercial_blind_full_PRIVATE.json
```

The four-case run requests 8 independent candidate replies and up to 4 blind judge replies. It must only be initiated explicitly on an authorized machine. Model receipts are written outside the checkout, with restrictive file permissions, and are **not committed or uploaded by default**. The standalone runner has no outbound buyer-contact, price quotation, contract modification or deployment actions.

## Interpretation rule

A valid run can establish whether *a different-family AI judge prefers one anonymous decision workflow over the other on these development cases*. It **cannot** by itself establish independent correctness, customer demand, signed contracts, a defensible commercial moat or return on investment.

Mark candidate and judge calls that fail to produce acceptable evidence-bound JSON as failures, not wins/losses or implicit ties. Do not compute numerical superiority based on three or four contaminated development examples.

## External execution limitation / why not GitHub hosted model APIs

[GitHub Models retired on 2026-07-30](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/); the old Actions `GITHUB_TOKEN` inference service is unavailable. GitHub Actions can execute **offline deterministic tests**, not these third-party authenticated model calls without separately authorized credentials. Do not add personal tokens to public Actions runners without explicit authorization.

## Gates before commercialization

1. **Blind out-of-sample replication:** a truly sealed 10–20+ casebook not curated with knowledge of Atlas outputs, independent source authentication, one general-model family equal in both arms, and a distinct judge family.
2. **Expert gold:** at least one independent evaluator blind to tool origin, explicit accuracy/error-severity rubric and reference context, not solely a preference from an AI judge.
3. **Competitive economics:** measured source-collection, model/runtime, expert verification and acquisition effort; count proposals rejected for confirmed substitutes, not only discovered ideas.
4. **Real conversion:** an identifiable prospective client, documented permission/budget and a paid or declined pilot. Capture negative outcomes equally.

**Go/no-go:** keep Atlas an internal investigatory asset until there is reproducible decision improvement at defensible cost; do not productize as a licensed SaaS platform on the strength of model preferences.
