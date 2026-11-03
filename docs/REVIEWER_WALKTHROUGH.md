# Reviewer walkthrough: source-reviewed research map

This is a short, reproducible way to inspect what Cite-Refinery does with one real, bounded research question. It uses public Taiwanese sources and scholarly material already cited in the repository. It does not call an AI model or claim that a population intervention has been tested.

## Run it

From the repository root, with Python 3.11 or newer:

```bash
python3 scripts/preview_public_demo.py
```

Open the `127.0.0.1` address printed in the terminal. The command verifies the SHA-256 digests of the public pilot and source-review file, builds an isolated snapshot in a temporary directory, and serves it on loopback. It needs no account, API key, package installation, or network access to start. Stop with `Ctrl+C`.

The generated snapshot contains 4 clusters, 15 nodes, and 16 relationships. The original pilot remains unchanged.

## Inspect the question

Select **Population observability** and compare the records in the three layers:

- **Practical:** Taiwan's periodic national estimate and a local Miaoli report.
- **Academic:** population-estimation methods and a site-specific Shoushan model.
- **Program:** documentation for the Talea street-survey system and Taiwan's 2026 management program.

Select nodes to inspect their citations and provenance. Follow the represented relations and note the difference between `qualified`, `candidate`, and `unresolved` links. A relation in the map describes what this reviewed packet records; it is not automatically a causal or effectiveness claim.

## Check the evidence boundaries

The source review preserves several distinctions that are easy to lose in a polished summary:

- The Ministry's lower 2024 national point estimate was **not statistically significant**.
- The Shoushan population model is site-specific and does not establish nationwide effects.
- Talea's cited documentation does not establish an individual-photo workflow or a validated local population estimator.
- The repository did not run a dog survey, field intervention, or local population estimator for this case.
- The 2026 Ministry program is documented policy intent, not measured effectiveness.

In the packet, unsupported connections remain candidate or unresolved rather than being represented as proven links. The case builder validates the input digests and adds explicit source-scope and limitation records before the graph is rendered.

## What this demonstrates

- A typed graph that keeps practical observations, academic methods, programs, and requirements distinguishable.
- Provenance attached to records and relationships, with uncertainty visible in the interface.
- A repeatable transformation from two frozen public JSON inputs into the same map-first UI used by the local product.
- A read-only public-data surface isolated from private workspaces and model credentials.

## What this does not demonstrate

This is a bounded research-mapping example. It does not establish a field-ready dog-management system, independent scientific review, human usability, customer adoption, production readiness, or the real-world effectiveness of a policy. The broader acceptance-case rationale and limitations are in [Product acceptance case 02](PRODUCT_ACCEPTANCE_FREE_ROAMING_DOGS_02.md); the public deployment boundary is in [Public Atlas Preview](PUBLIC_ATLAS_PREVIEW.md).

## Relevant implementation

- [`scripts/preview_public_demo.py`](../scripts/preview_public_demo.py) — one-command, loopback-only preview launcher.
- [`scripts/build_public_preview.py`](../scripts/build_public_preview.py) — builds the isolated read-only snapshot.
- [`scripts/acceptance_free_roaming_dogs.py`](../scripts/acceptance_free_roaming_dogs.py) — verifies source digests and applies the case-specific review overlay.
- [`examples/free_roaming_dog_semantic_pilot.json`](../examples/free_roaming_dog_semantic_pilot.json) — original public research map.
- [`examples/acceptance_free_roaming_dog_source_review_v1.json`](../examples/acceptance_free_roaming_dog_source_review_v1.json) — frozen review of the public source set.
