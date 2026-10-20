# Persistent InvestigationController v1 — Cite-Refinery

## Purpose

This is the first **executing LLM-planned investigation loop**, not a static graph seed or an embeddings-only similarity search. It builds directly on the draft #46–#56 research and semantic infrastructure without merging or overwriting the parallel breadth-expansion branches.

The controller works through **persisted and independently resumable** stages:

1. **Plan:** ask a capable model to choose a narrow semantic question, testable hypotheses and searches against multiple evidence families. **No preselected bibliography** is supplied.
2. **Collect:** execute bounded scholarly search through Europe PMC and independent official webpage discovery through Brave Search, then retrieve and hash actual publisher excerpts. Search snippets never count as evidence.
3. **Recover evidence when needed:** if either academic or institutional sources are absent, ask the LLM to broaden searches; retain prior finds and retry at most three times. **Never invent missing source families.**
4. **Reason:** use a real LLM with the original source text and module descriptions to extract atomic, source-quoted propositions, relationships, objections and unresolved questions; preserve provenance and limitations.
5. **Critique:** ask the model to critically reconsider literal quotations, scope and competing explanations. This is still model opinion; even `entailed` means **unverified reviewer verdict**, not acceptance.
6. **Stage:** atomically ingest a strictly **neutral/candidate-only** semantic packet in its own Cite-Refinery project. Preserve the source-linked research frontier and continue into another round if configured.

The investigation frontier is populated by LLM-identified unresolved questions and used on subsequent planning passes. Later rounds can reconsider earlier sources and previous **provisional** claims. A full round can complete without affecting any existing validated research workspace.

## Real access and execution status

On the connected Optiplex machine, the original system `codex` wrapper was broken: global npm install failed with EACCES. A **separate local installation** of the official Codex CLI `0.163.0` succeeded, and `codex login status` reported an existing **ChatGPT login**. A real `gpt-6.1-sol` CLI invocation returned `INVESTIGATOR_OK` in 15.3 seconds using a read-only, ephemeral session.

Unlike the previously unavailable Claude/Gemini CLI sessions and unreliable local Ollama attempts, this means there is now a **tested strong-model backend** for the controller. The new `codex` inference adapter is entirely opt-in:

- Isolated disposable working directory;
- read-only sandbox; no write access to source code or accepted graph;
- ephemeral session; no persisted model conversation;
- explicit `Do not use any tools` instruction;
- real structured JSON result written by Codex and validated by the existing Cite-Refinery schemas;
- no injected API key, no automatic downgrade, strict timeout and **safe explicit failure**.

The controller's own orchestrator (not the model) performs **bounded source discovery** and candidate-graph writes.

## Run

```bash
# After installing this branch:
# Use an existing ontology file, not a bibliography. It must be a JSON list
# of {id,title,summary} objects. The prior five-module demo file is suitable.
D=research_materials/runtime_trials/llm_multisource_20261020

# 1. Start a new investigation:
cite-refinery-investigate --workspace /tmp/my-investigations init \
  --question 'Why do free-roaming dog population-control programs sometimes fail to improve public health?' \
  --modules "$D/modules.json" --max-rounds 2

# 2. Set your own authenticated Codex binary path (or leave unset if `codex`
# is already a functional installed binary):
export CITE_REFINERY_CODEX_BIN=/path/to/working/codex

# 3. Run the next bounded phase, supplying the ID returned above:
cite-refinery-investigate --workspace /tmp/my-investigations step \
  --id INVESTIGATION_ID --provider codex --model gpt-6.1-sol --timeout 240

# 4. Resume as often as needed, or advance at most five states at once:
cite-refinery-investigate --workspace /tmp/my-investigations run \
  --id INVESTIGATION_ID --provider codex --model gpt-6.1-sol \
  --timeout 240 --steps 5

# 5. Review state without invoking an LLM:
cite-refinery-investigate --workspace /tmp/my-investigations status \
  --id INVESTIGATION_ID
```

No automation or background watcher is created. Only explicit commands advance state. **Each LLM call may take minutes;** the controller saves after each completed stage so expensive prior work is retained. A provider failure or network error stores `last_error` without moving the stage; retry the same stage after correcting its cause.

Files live under `<workspace>/investigations/<id>.json` (complete, audit-friendly plan, sources, LLM output, critique, frontier, packet receipt) and `<workspace>/refinery/state.json` (isolated semantic project). Do not share full state files without checking source copyright and private research contents.

## Source-acquisition boundaries

**Academic lane:** Europe PMC search API with `resultType=core`. Returned **bibliographic abstracts only** are labeled `scholarly_abstract_lead`, not verified peer-reviewed full-text evidence; the DOI and retrieval endpoint are retained.

**Official lane:** Brave Search, followed when necessary by **WOAH's own searchable publisher index**, discovers URLs within a strict allowlist of official government, intergovernmental and public-health domains (WHO, WOAH, CDC, FAO and others). The controller reads **the publisher's actual HTML paragraphs**, not the search snippet. It validates redirect destinations and rejects arbitrary URLs, internal hostnames, unsupported binary formats and oversized responses. These are `official_webpage_excerpt_unverified`: normative program guidance or public-health advice is NOT proof of implementation or measured effects.

The controller currently searches **academic + institutional** material and can uncover local outcomes mentioned within these sources, but **an independent structured practical/field-data provider is still missing**. It must not claim complete Practical/Academic/Program coverage based merely on the two acquisition providers.

External websites are untrusted data. Citation presence is a necessary gate but not semantic entailment. All source statements must be read with geography, timeframe, population, measurement and method constraints.

## Graph semantics

Each staged packet contains:

- Neutral candidate module containers;
- original source excerpt nodes and provenance;
- model-proposed atomic claim nodes, source-quote links, and scope/limitations;
- candidate or explicitly unresolved typed semantic bridges;
- concrete unanswered questions feeding future investigation.

All nodes remain `neutral`. All edges remain `candidate` or `unresolved`. The system **never silently declares causal impact, accepts an intervention as effective or replaces an accepted Practical/Academic/Program source**. Import is idempotent and read-state checks are performed by Cite-Refinery's established semantic graph ingestion.

The single-user JSON workspace still has no cross-writer transaction protection. Production concurrent writers require proper locking/database transactions, not assumptions.

## Tests and acceptance limits

Automated tests use a fake model, injected academic/official search providers and the actual persistence/semantic graph engines. They verify:

- model-driven selection rather than fixed source IDs;
- independent academic and official search lanes;
- real-source parser contracts and domain restrictions;
- five-stage checkpoint transitions and retry behavior;
- neutral-only provenance-preserving graph import and idempotent replay;
- unresolved questions driving a second investigation round;
- read-only / ephemeral / no-tool Codex CLI contract.

The first **live** session is rooted in the user's stray-dog/public-health problem and seeded only with the existing five-module ontology. It generates its own academic and institutional searches and preserves results. Its real model output and measured stage status should be reported separately and **must not be conflated with tests using fake LLM responses**.

## Next system-level acceptance gate

After a first fully staged and critiqued live round, require a second round to **choose an unresolved question independently**, search for new counterevidence, relate it to the prior round, and revise uncertainty. Then run independent/source-level review of the material claims (including the difference between reported statistical associations, program protocols and causal health effects). **Graph growth by itself is not an accuracy score.**

## Real-world proof: LLM-discovered research and source recovery

A new isolated investigation was started **without a bibliography** using the five previously defined AW/PH ontology modules and the question: why free-roaming dog management sometimes fails to achieve public-health outcomes.

1. **Codex/GPT-6.1 planning** selected demographic turnover, durable vaccine coverage, exposure surveillance and PEP, with five queries.
2. Independent retrieval found **4 Europe PMC abstracts and 4 WHO excerpts**, each with source IDs and URLs. They remain unreviewed.
3. Actual Codex/GPT-6.1 semantic generation took about **168 seconds**, returning **36 source-quoted atomic propositions, 18 candidate semantic relationships, and 15 unresolved questions**. All literal citation checks passed; semantic validity remains unproven.
4. The **same model** reviewed these in about **79 seconds** and marked all 36 claims `entailed` and all 18 bridges `plausible`. Unanimity may reflect same-model confirmation bias: this is NOT independent scientific verification.
5. The controller staged **64 neutral nodes and 112 candidate edges** in an isolated project. Repeat ingestion was idempotent. Chromium rendered the actual graph.
6. An unresolved question drove a **second Codex planning round** about whether fewer dogs needing sterilization reflects reduced abundance or changed status/detection. Initial acquisition had insufficient institutional evidence. The LLM adjusted searches, and publisher-index recovery located relevant WOAH publications. Off-topic hits concerning rats, swine fever, governance and glanders were excluded before reasoning. The second live synthesis then generated **51 more source-quoted propositions, 23 semantic candidate bridges and 16 open questions** using both fresh sources and bounded previous context. A **bounded second-pass critique** reviewed 18 propositions and six bridges, while **33 propositions and 17 links were explicitly left uncertain rather than approved**. The second review packet imported as **79 nodes/157 edges, of which 17 edges are unresolved**. After both rounds the actual persistent project contains **134 unique nodes, 269 edges (252 candidate, 17 unresolved)** and the controller reached `done` at the configured two-round limit.

See the sanitized source-link receipt and actual browser screenshot in `research_materials/runtime_trials/investigation_controller_20261020/`. Full source paragraphs/model transcripts remain in the locally authorized workspace; do not publish them indiscriminately.

### Review budget and safety

When a round yields many model assertions, the controller initially reviews at most **18 atomic propositions and ten compatible candidate bridges**. Other assertions are explicitly represented as `uncertain` and their edges as `unresolved`, not accepted on the basis of missing review. This is a resource-budget control, not evidence that the reviewed subset is the most important. A future version should independently audit the entire queue before public release, and ideally use a separate model and human adjudication rather than the same-model critic.

The recovery provider allows Brave Search for official domains and falls back to WOAH's publisher-owned WordPress index. Search discovery may over-return adjacent topics; the publisher-index route now filters titles against topic-bearing query words. The live second round excluded four unrelated indexed articles before synthesis. The controller does not rely on domain trust as a substitute for checking scientific conclusions.
