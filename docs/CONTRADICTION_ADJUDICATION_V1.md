# Contradiction-driven semantic adjudication — v1

## Scope and reason

Cite-Refinery's first persistent investigator autonomously generated source-quoted claims and connections, but its GPT-6.1 self-critic frequently endorsed those claims. A second pass from the same model does not independently verify source meaning or real-world causal effects.

This branch adds a durable, **falsification-oriented evidence challenge** for an existing saved investigation. It uses independently selected source searches, rather than merely re-reading the generator's original citations. All judgments are provisional and no existing graph claim or relationship is automatically promoted, reversed or deleted.

## Five stages

1. **Blind claim selection.** The LLM challenge planner sees up to 14 existing atomic claims with scope and limitations, but **does not see** the original source quotations, explanatory bridge rationales or any prior favorable self-critic verdict. It picks one or two claims to falsify and proposes alternative explanations plus academic and official search queries.
2. **Independent source discovery.** Academic search uses Europe PMC abstracts; institutional search retrieves real WHO/WOAH or other allowed publisher pages from discovered URLs. The controller excludes previously used source URLs, deduplicates identical excerpts, rejects off-topic institutional documents and requires both evidence families. One bounded replanning attempt is allowed before it blocks with insufficient evidence.
3. **Blind-to-prior-verdict judgment.** The LLM judge receives original source quotes, the claim wording and the newly retrieved passages—but not the first model's positive verdict or its elaborated reasoning. It must explicitly distinguish measurement denominator, population, method, time period, mechanism and outcome. Each judgment must be one of supporting, conflicting, scope_qualified or inconclusive.
4. **Strict evidence validation.** A positive, conflicting or qualifying label requires an exact new-source quotation, source ID and evidence role. Fabricated quotes and invalid IDs downgrade the model decision to **inconclusive**. Literal passage matching alone does not prove semantic entailment.
5. **Non-destructive review graph.** Newly retrieved evidence and unresolved challenge nodes are added alongside existing neutral claims. Proposed CONTRADICTS, SUPPORTS, QUALIFIES or RELATED_TO links are **always marked unresolved** regardless of the LLM's classification. The old graph nodes and all earlier edge statuses remain unchanged, with idempotent packet import.

### Meaning of independence

**Source independence** means the planner was not shown the existing evidence bibliography and the new challenge corpus excludes the original URLs. It does not establish study independence, population independence, model independence or correctness.

**Model independence is not established.** The authenticated Codex environment successfully runs GPT-6.1. Testing GPT-5.6 as an alternate judge returned an explicit unsupported-model error for ChatGPT-connected Codex. A separate GPT-6.1 session still shares model biases. Full adjudication needs an independently evaluated model and human/source-level review.

### Known limitations

- Europe PMC provides scholarly abstract *leads*, not verified complete academic papers. Institutional websites contain normative advice, not necessarily implemented outcomes.
- Search engines can produce irrelevant pages from otherwise reputable domains. The controller applies subject filtering and retains a list of exclusions. The filter is conservative and may exclude unusual but useful evidence.
- A new source may simply be about a different population or measurement. Such a source does not establish a genuine contradiction with a number from the original study.
- Genuine causal attribution, clinical effectiveness and local field impact are **not certified** by LLM or graph edges.
- The underlying state uses a local single-user JSON store. It is not a concurrent research database.

## How to use

Prerequisites: the prior investigation is present in the same workspace, has at least one staged candidate graph, and an authenticated Codex binary or supported LLM provider is configured. The adjudicator does not generate an initial research project.

Use the installed CLI:

    cite-refinery-adjudicate --workspace /tmp/my-investigations start --investigation-id ORIGINAL_ID

Then advance one stage at a time:

    export CITE_REFINERY_CODEX_BIN=/path/to/authenticated/codex
    cite-refinery-adjudicate --workspace /tmp/my-investigations step --id ADJUDICATION_ID --provider codex --model gpt-6.1-sol --timeout 180

Or inspect the saved state without calling a model:

    cite-refinery-adjudicate --workspace /tmp/my-investigations status --id ADJUDICATION_ID

A bounded run can advance up to five stages. An inference failure keeps the previous durable checkpoint. The controller never launches background work.

The full local audit is under workspace/adjudications/ID.json, including original claim IDs, separate sources, rejected/off-topic records, verdicts, exact quote receipts, and the graph ingestion receipt.

## Validation and next gate

Automated tests verify original-source reuse rejection, challenge-claim identity, missing evidence stopping rules, off-topic source rejection, fabricated-quote downgrades, isolation of accepted graph records, idempotent challenge import and provider failure recovery. They use injected model responses, and are distinct from the real Codex demonstration.

Next steps after this v1 are to:
- Expand full-text academic extraction and explicit operational/practical data;
- run actual independently authored contrast cases including matched and mismatched outcomes;
- adjudicate with a different model where authorized, then independent human verification;
- evaluate precision, recall, abstention, false contradictions and source-scope errors on independently labeled test cases.

## Live first adversarial investigation (20 October 2026)

On the existing **completed two-round** GPT-6.1 stray-dog/public-health investigation, a new blind source-planning session chose two precise claims from round two:

- **R2:P4:** 1,368 (2021) versus 484 (2025) free-roaming dogs *requiring sterilization* — not necessarily total canine abundance.
- **R2:P6:** a reported statistically significant male population buffer-zone intervention effect in zone 1 — not proof of causal rabies or human-health improvement.

The LLM selected four challenge searches across scholarly and official sources **without the first model's citations or review verdict**. On initial search, the purported institutional leads were WHO articles on human population ageing and health literacy; the controller rejected all three as off-topic. The planner reformulated the searches. On its bounded second retrieval it obtained **three new source leads** (one Europe PMC scholarly abstract concerning animal welfare programs and two WHO vaccination-related pages), excluding one previously used source. Neither novel corpus directly remeasured the two numerical/statistical outcomes.

A distinct GPT-6.1 model invocation then classified **both claims as inconclusive**. It explicitly recognized that the 2021/2025 subset counts could not be independently checked from the novel sources, nor could the sex/zone-specific statistical result. **No contrary results or quotes were invented.** The challenge packet added five neutral nodes and two unresolved review edges; original graph statuses were not changed. The persistent Cite-Refinery project now contains **139 unique nodes and 271 relationships**, including the new unresolved review context. The browser-rendered visualization was tested in Chromium; the sanitized live report and screenshot accompany this branch.

This is a **successful abstention and provenance demonstration**, not a successful falsification or externally validated claim. The proper next step is original-method full-text retrieval, independent field population observation and statistical replication, not raising the LLM's confidence score.
