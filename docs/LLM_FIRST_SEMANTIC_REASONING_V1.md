# Cite-Refinery v1: LLM-first semantic reasoning (experimental)

**Status:** review-only integration, independent of the landscape-expansion branch. This corrects the previous reliance on TF-IDF/MiniLM similarity as a substitute for interpreting actual problem requirements and cross-field relationships.

## Design decision

Use a capable **LLM as the primary semantic reasoner**: decompose institutional and academic evidence into atomic statements, infer relevant problem requirements and examine possible bridges, counterarguments, and scope. Use **retrieval / PDFs / vector search only for finding passages**, source IDs and relevant ontology context; use programmatic checks only to catch basic invalid references, unknown modules, fabricated quotations, unsupported strong edge types and replay inconsistencies.

This pipeline does **not** claim that literal quote matching proves source entailment. It intentionally separates the generator's proposed semantic interpretation from a skeptical second LLM pass and eventual evidence/impact review. Both reasoning passes may be wrong.

## Implemented

- `src/cite_refinery/external_llm_reasoner.py`: LLM-first source-aware generation prompt; atomic propositions with explicit claim types, module mapping, scopes, limitations and quoted source evidence; typed source-qualified, cross-proposition candidate links and concrete unresolved questions. Validates module/source identities, literal excerpt existence, scope, type/strength, and missingness.
- `src/cite_refinery/external_llm_runtime.py`: opt-in model execution using local Ollama (loopback only), tool-disabled nonpersistent Claude CLI, or read-only Gemini CLI. No automatic model downgrade, no keys committed, bounded output and timeout. A **manual** mode lets ChatGPT or another capable model supply the JSON reasoning without requiring the host to authenticate a particular provider.
- `src/cite_refinery/external_llm_packets.py`: converts checked LLM outputs into isolated `cite_refinery.semantic_graph.v1` packets. **All nodes are neutral; all edges candidate; zero accepted outcome claims.** Source excerpts → atomic propositions → problem modules; model-proposed links only between specific propositions, not guessed entire field relationships.
- `build_second_pass_prompt` and `inspect_second_pass`: optional independent LLM critic checks whether a real quotation actually entails the claim, preserves scope/alternatives, and downgrades unsupported or incomplete critiques. Even `entailed` is a **reviewer opinion, not acceptance**.
- `cite-refinery-llm` CLI (also `scripts/external_llm_semantics_v1.py`): prepare a prompt, run a user-configured provider or consume an LLM JSON file, check and stage candidate graph and optional critique.

## Genuine validation and current blockers (2026-10-20)

- A **GPT-6-authored, illustrative** response to the earlier WMO HydroSOS sentence passed the new schema/quote gates: two atomic propositions, one scope-qualifying candidate connection, one unresolved question. In a **new isolated project**, the converted graph contained **6 neutral nodes and 5 candidate edges**, imported and replayed idempotently. This is a functioning **LLM response → validator → graph integration test**, **not a benchmark or autonomous discovery result**.
- Test fixtures also inject an invented 20% mortality claim, absent quotation and causal relation. The checks reject them; a quoted but false paraphrase still needs the second semantic reviewer.
- **Claude CLI cannot currently generate on the authorized host:** OAuth session expired and refresh failed; user must reauthenticate.
- **Gemini CLI cannot currently generate:** this installation reports `UNSUPPORTED_CLIENT` / individual Code Assist migration requirement. Reinstalling/migrating to an eligible client or other authorized provider is required.
- **Ollama local Qwen 1.5B** was actually called with the 2,971-character semantic prompt and failed by a hard **70-second timeout**. Previous 3B/7B/LiteLLM attempts were slow or wrong. Do not claim this branch has a dependable hosted inference runtime, nor make small CPU Ollama the default semantic judge.
- No external API key, database merge, production deployment, automatic source-side downloads or accepted graph claim was performed.

## Use it today with ChatGPT or a separate authorized model

```bash
# First prepare evidence-grounded prompt and source input:
cite-refinery-llm \
  --sources /absolute/path/sources.json \
  --modules /absolute/path/modules.json \
  --out /tmp/refinery-llm-review

# Give prompt.txt to a capable LLM. Save its JSON object as response.json:
cite-refinery-llm \
  --sources /absolute/path/sources.json \
  --modules /absolute/path/modules.json \
  --response-json /absolute/path/response.json \
  --out /tmp/refinery-llm-review

# Optional second opinion from a *different* model, ideally:
cite-refinery-llm ... --response-json response.json \
  --critic-response-json second_model_response.json
```

Source schema: JSON array of objects containing `id`, `url` (HTTPS), `text` (original cited passage), `origin_type`, and `source_scope`. Modules schema: JSON array of `id` (e.g. `WA-06`), `title`, `summary`. The CLI will produce `prompt.txt`, `input.json`, `model_response.json`, `review_result.json`, `candidate_packet.json`, and `critic_prompt.txt`. It can consume an external response without a hosted CLI model or API key.

When host authentication becomes valid, the same contract supports `--provider claude --model sonnet`, `--provider gemini`, or `--provider ollama --model MODEL`, with `--timeout`. **Do not** use the current timeout-prone local models as production defaults.

A separate configured inference provider/GPU can replace the CLI adapter without altering the semantic ontology or review policy.

## Follow-on: scientific validation

What remains is not finding enough *candidate pairs* but conducting actual evidence-constrained **semantic entailment, contradiction search, competing explanation and cross-source triangulation**, evaluated against an independently annotated holdout. A source quote, a matching embedding, two agreeing LLMs and a program website individually do not prove actual causal effectiveness or unmet need. The next useful system-level benchmark should score atomic-proposition correctness and scope, source entailment, cross-field relation precision, false causal overreach and abstention separately.

No result here should be described as improving discovery accuracy over a strong LLM until a live capable model is connected and comparatively tested.
