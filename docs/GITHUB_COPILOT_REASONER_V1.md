# GitHub Copilot reasoning backend — Optiplex integration v1

**Cite-Refinery, October 20, 2026.** GitHub Copilot, not Codex, is the preferred execution backend for the saved semantic investigation and its adjudication/benchmark tools.

## What was found on the authorized Optiplex

The machine has **GitHub Copilot CLI 1.0.100**, installed as `copilot`, plus four additional launchers: `copilot-student`, `copilot-spectator`, `copilot-ly`, and `copilot-ly2`. These appear to select different local CLI/account configurations; do not assume that each actually has an independent usable quota.

All five launchers were tested with one minimal, isolated, tool-free JSON-response prompt. **Every invocation returned a monthly quota error.** Some account-wrapper scripts even exit with status zero despite emitting the quota message to stderr. The Cite-Refinery adapter now detects such errors and fails closed; no JSON completion is fabricated.

No OAuth tokens, credentials, configuration contents, or account identifiers are stored in this repository.

## New adapter and safety properties

The supported `copilot` provider uses an explicit locally selected launcher:

- Default binary is the installed `copilot`; optionally set `CITE_REFINERY_COPILOT_BIN` to a user-owned launcher path (e.g. `/home/phyrexian/.local/bin/copilot-student`).
- Defaults to model `auto`, and accepts `--model` only if that profile's Copilot entitlement supports the model. It does not silently downgrade to Codex or Ollama.
- Runs in an isolated temporary directory, with Copilot CLI's **available tool list empty**, built-in MCP servers disabled, streaming disabled, and memory disabled by default. No repository editing, terminal execution or arbitrary browsing is entrusted to the model. Network research source acquisition and graph persistence remain explicit operations in Cite-Refinery's controller.
- The CLI requires `--allow-all-tools` for noninteractive use; **this does not grant capabilities** because `--available-tools ''` explicitly limits the model's tool catalog to empty. Do not remove that restriction or add `--allow-all-paths`, `--allow-all-urls` or `--yolo`.
- Parses strict JSON from Copilot stdout, tolerating non-result informational banners from local wrappers, and rejects invalid or absent model output. Secrets and raw stderr are never written to error messages.
- Detects quota errors even if a wrapper mistakenly reports a successful process exit. Preserves the saved investigation stage on provider errors.

## Usage

From the repository root, with authenticated and available Copilot:

```bash
export CITE_REFINERY_COPILOT_BIN=/home/phyrexian/.local/bin/copilot-student

# Resume existing, saved evidence repair inquiry (the ID belongs only to
# the authorized Optiplex local workspace).
PYTHONPATH=src:. python3 -m cite_refinery.investigation_cli \
  --workspace /tmp/refinery-investigator-first-demo \
  step --id 49ecd664b5044b24abfc \
  --provider copilot --model auto --timeout 180

# Or explicitly use another configured launcher:
export CITE_REFINERY_COPILOT_BIN=/home/phyrexian/.local/bin/copilot-spectator

# Read status safely without invoking any LLM:
PYTHONPATH=src:. python3 -m cite_refinery.investigation_cli \
  --workspace /tmp/refinery-investigator-first-demo \
  status --id 49ecd664b5044b24abfc
```

`cite-refinery-investigate` and `cite-refinery-adjudicate` now **default to `--provider copilot`**, and `cite-refinery-external-llm` supports explicit Copilot model generation and critique. The blind-scientific benchmark runner defaults to Copilot too.

**No automatic switching among the configured Copilot launchers.** Explicit selection makes consumption and provenance auditable. In future, any source-backed, model-generated facts must still pass the same quote/source-ID constraints, source-independence safeguards and neutral graph review gates.

## What is verified, and what is not

Verified: Copilot CLI and launchers exist; actual tool-free smoke calls produced quota errors; adapter argument, output, security and quota logic passes automated tests; the complete repository regression suite passes; the existing child investigation remains at `plan` and preserves four manual source-data dependencies.

**Not verified:** a successful live Copilot inference in the current quota window; which models each Copilot profile can actually run; any real semantic judgment or new research result from this adapter. No autoruns, account cycling, subscription/quota changes, graph promotion or deployment were undertaken.

When Copilot availability is restored, the next explicit step is the saved child's planning stage, followed by a source audit before its independent dog-population/public-health evidence can be connected to research claims.
