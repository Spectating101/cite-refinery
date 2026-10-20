"""Explicit, non-interactive opportunity decision dossier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .opportunity_conversion import evaluate


def render(report: dict) -> str:
    if report.get("schema") != "cite_refinery.opportunity_decision.v1":
        raise ValueError("invalid opportunity result")
    repo = report["candidate_asset"]
    fit = report["cross_layer_fit"]
    buyer = report["buyer"]
    routes = report["conversion_routes"]
    lines = [
        "# Opportunity conversion: " + report["case_id"], "",
        "**Status: " + report["readiness"] + "** — not a proven commercial arbitrage.", "",
        "## Real problem",
        report["problem"]["statement"], "",
        "## Existing asset",
        f"{repo['description']} ({repo['repository_url']})",
        f"Capability source: {repo['capability_reference']}",
        "Repository license status: " + repo["license_state"],
        f"Repo adoption and willingness-to-pay have **not** been verified.", "",
        "## Mechanism / opportunity fit",
        "**Function documented:** " + fit["documented_capability"], "",
        "**Operational requirement:** " + fit["required_mechanism"], "",
        "**Gap to verify:** " + fit["unverified_gap"], "",
        "**Fit stage:** " + fit["fit_status"], "",
        "## Buyer and conversion",
        "Prospective buyer: " + buyer["segment"],
        "Buyer evidence stage: " + buyer["demand_status"],
        "- Self-execution: " + routes["self_execution"],
        "- Maintainer/partner service: " + routes["maintainer_service"],
        "- Component reuse: " + routes["reuse_as_component"], "",
        "## Concrete next action",
        report["recommended_next_test"], "",
        "## Commercial reality",
        "Evidence of underconversion: **" + report["underconversion"]["status"] + "**.",
        report["underconversion"]["why"],
        "Unit economics: " + report["unit_economics"]["status"] + " (" + report["unit_economics"]["limitation"] + ")", "",
        "## Inspect original signals",
    ]
    for entry in [*report["problem"]["sources"], *buyer["signals"], *report["upstream"]["signals"]]:
        lines.append("- " + entry["claim"] + " — " + entry["url"] + " [" + entry["status"] + "]")
    lines.extend(["", "No outreach or deployment has been initiated.", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-opportunities")
    parser.add_argument("cases", type=Path, nargs="+", help="One or more explicitly reviewed opportunity JSON cases")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    results = [evaluate(json.loads(path.read_text(encoding="utf-8"))) for path in options.cases]
    if options.format == "markdown":
        payload = "\n\n---\n\n".join(render(r) for r in results)
    else:
        payload = json.dumps({"schema": "cite_refinery.opportunity_batch.v1",
                              "results": results}, indent=2, ensure_ascii=False) + "\n"
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(payload, encoding="utf-8")
        print(options.output)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
