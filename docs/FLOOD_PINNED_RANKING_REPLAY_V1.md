# Exact-original flood-station NaN replay and lab-only repair

**2026-10-23. This is an isolated engineering falsification, NOT a public flood-warning system.**

## Why this test comes next

The first flood opportunity dossier (#111) found an appealing implementation candidate but also a critical synthetic-test failure: invalid NaN river-level data can disrupt the order used to rank stations. This pass repeats the exact original source failure at a hash-verified upstream revision, implements a **separate** finite-only laboratory adapter, and tests whether normal finite-input behavior remains.

### Original upstream and integrity controls

Original repository: https://github.com/WeixuanZ/flood-warning-system

Pinned commit: c1c7facf2c5577a155edd93a0b7279ad7630518c.

The three upstream Python files are **not vendored** into Cite–Refinery, and upstream is not modified. An isolated GitHub Actions checkout pins the exact revision. Before any upstream code is imported or executed, the replay script verifies original Git blob SHA-1 identities:

| Original source file | Verified blob |
|---|---|
| floodsystem/flood.py | 467c9813043adef3593ef6dd73c9c7adca2e9618 |
| floodsystem/station.py | 00d963622dda2ec688fec6b6b1d222955e8d9a0e |
| floodsystem/utils.py | 2ebe58b654041fe461fbf47e99cdc9488e453785 |

Any altered byte is rejected. Copyright and MIT licensing stay with the original authors. No external original text, live gauge feed, public alerting endpoint, or model API is used.

## Locally reproduced source-pinned results

The exact upstream stations_highest_rel_level(stations, 1) function was executed on all six permutations of synthetic stations with low=0.2, invalid=NaN and high=1.6, all using a synthetic typical range (0, 1).

| Result | Count |
|---|---:|
| Original top station correct | 4 / 6 |
| Original top station incorrect | **2 / 6** |
| Separate finite-only adapter top station correct | **6 / 6** |
| Adapter explicitly marks NaN station rejected and input degraded | 6 / 6 |
| Adapter retains original ordering for distinct finite levels | Yes |

This is a deterministic synthetic defect on the pinned source, **not an operational failure rate** of real sensors.

The adapter also rejects NaN, positive/negative infinity, missing, text, boolean, complex and overflowing levels; invalid or reversed ranges; and invalid ranking parameters. It refuses duplicate station identities and sorts finite-score ties deterministically. It returns rejected-station diagnostics and a degraded-input flag. This is a bounded offline component; it never issues real warnings and cannot guarantee the remaining stations cover the missing hazard.

Nine Python test methods passed locally using the byte-for-byte original sources. GitHub Actions subsequently established that the exact original misranking count is not portable as a hard-coded assertion: the new acceptance gate requires at least one original misranking among all six permutations and reports the actual runtime-specific count, while still requiring 6/6 correct adapter results. These contain six NaN input permutations, 24 tie/ordering permutations and numerous adversarial subcases. Independent GitHub Actions results must be checked separately.

## Reproduce against verified original source

~~~bash
git clone https://github.com/WeixuanZ/flood-warning-system /tmp/cr-pinned-flood-upstream
git -C /tmp/cr-pinned-flood-upstream checkout c1c7facf2c5577a155edd93a0b7279ad7630518c

python -m pip install -e .
FLOOD_UPSTREAM_ROOT=/tmp/cr-pinned-flood-upstream \
  python -m unittest discover -s tests -p 'test_flood_ranking_replay_v1.py' -v

python -m cite_refinery.flood_ranking_replay \
  --upstream-root /tmp/cr-pinned-flood-upstream \
  --out /tmp/flood-pinned-ranking-receipt.json
~~~

The dedicated workflow in .github/workflows/flood-pinned-replay.yml checks out the pinned original revision, validates all three original blobs, runs the original + adapter tests and generates a scoped JSON artifact.

## Decision and next stage

**GO only for additional offline integration research.** The finite-only adapter fixes the tested ranking counterexample, but does not establish a safe flood-warning service.

The next gate requires legitimately obtained, locally relevant gauge histories, timestamp quality, sensor uncertainty and thresholds; reference comparison of detection lag and missed/false alerts; and a simulated consented notification and response chain. Public alarm channels, field efficacy assertions, health outcomes, commercialization, funding value and automated cross-map promotions remain forbidden without independent supporting evidence.

**Disposition remains LAB_ONLY_FALSIFICATION_PRIORITY_NO_DEPLOYMENT_RECOMMENDATION.**

## Separate baseline test issue

The first dossier's focused CI succeeded. Its full-project CI failed five stale tests that expected **50** installed console entry points, while the current feature stack intentionally declares **51**, including the prior Academic source-grounded semantic CLI (cite-refinery-semantic-answer). This branch updates exactly those five test counts and asserts the new CLI's canonical entrypoint target explicitly; it does **not** add or remove any actual CLI command. The complete suite requires a fresh successful CI run before being called green. This packaging-contract repair is separate from the flood source replay.
