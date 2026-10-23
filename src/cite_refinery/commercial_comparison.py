"""Small commercial decision comparison: same-case Atlas evaluator vs unblinded GPT-6 notes.

Not an independent LLM benchmark, not a fresh discovery system, and not buyer
validation. Uses existing source-bounded opportunity cases and keeps the
comparison's methodological limitations in the printed receipt.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from .opportunity_conversion import evaluate

ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / "research_materials" / "opportunity_conversion"
BENCH = CASE_ROOT / "commercial_comparison_v1.json"
SCHEMA = "cite_refinery.commercial_comparison.v1"

_ACTIONS = {
    "check whether the paid contributor application": "verify_paid_contributor",
    "verify volunteer onboarding": "verify_paid_contributor",
    "interview an identifiable buyer/operator": "interview_buyer",
    "compare the existing substitutes": "verify_competitive_advantage",
    "run a minimal capability-to-requirement test": "test_component_fit",
}


def _action(text: str) -> str:
    for needle, action in _ACTIONS.items():
        if needle in text.lower():
            return action
    return "other"


def atlas_decision(case: dict[str, Any]) -> dict[str, Any]:
    """Project existing opportunity evaluator onto modest, verifiable decision checks."""
    report = evaluate(case)
    return {
        "documented_problem_evidence": bool(report["problem"]["sources"]),
        "end_to_end_technical_fit_verified": report["cross_layer_fit"]["fit_status"] == "independently_replicated",
        "funded_or_signed_buyer": report["buyer"]["verified_demand_status"] in {"funded_request", "signed_commitment"},
        "authorized_for_deployment": bool(case["compliance"]["rights_reviewed"] and case["compliance"]["deployment_authorized"]),
        "realized_revenue_established": False,
        "next_test": _action(report["recommended_next_test"]),
        "readiness": report["readiness"],
        "input_sha256": report["input_sha256"],
    }


def run_benchmark(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = json.loads(BENCH.read_text(encoding="utf-8")) if spec is None else spec
    if spec.get("schema") != SCHEMA:
        raise ValueError("unrecognized comparison schema")
    rows = []
    for item in spec["cases"]:
        case_file = (CASE_ROOT / item["case_filename"]).resolve()
        if case_file.parent != CASE_ROOT:
            raise ValueError("cases must be existing top-level opportunity files")
        case = json.loads(case_file.read_text(encoding="utf-8"))
        if case["case_id"] != item["id"]:
            raise ValueError("case identity mismatch")
        atlas = atlas_decision(case)
        baseline = item["generic_gpt6_unblinded"]
        reference = item["reference_checks"]
        checked = list(reference)
        row = {
            "id": item["id"],
            "atlas": atlas,
            "generic_gpt6_unblinded": baseline,
            "checks": checked,
            "atlas_correct": sum(atlas.get(k) == reference[k] for k in checked),
            "baseline_correct": sum(baseline.get(k) == reference[k] for k in checked),
            "checks_total": len(checked),
        }
        rows.append(row)

    # Red-team: forged evidence *classification* reusing a real public issue URL.
    # A URL and a caller's "reviewed" flag do not make that issue a signed contract.
    original = json.loads((CASE_ROOT / spec["adversarial_case_filename"]).read_text(encoding="utf-8"))
    forged = copy.deepcopy(original)
    forged["fit"]["verification"] = "executed_local"  # unsupported self-report
    forged["market"]["demand_status"] = "signed_commitment"
    forged["market"]["signals"] = [{
        "url": "https://github.com/openfoodfoundation/openfoodnetwork/issues/14924",
        "claim": "Test-only false assertion: a public bug report is a signed customer contract.",
        "status": "reviewed",
        "kind": "signed_contract",
    }]
    adversarial = atlas_decision(forged)
    return {
        "schema": SCHEMA,
        "kind": "unblinded_proof_of_mechanics_not_independent_agent_trial",
        "cases": rows,
        "total_checks": sum(r["checks_total"] for r in rows),
        "atlas_correct": sum(r["atlas_correct"] for r in rows),
        "baseline_correct": sum(r["baseline_correct"] for r in rows),
        "adversarial": {
            "tamper": "Caller relabels a public issue URL as reviewed signed contract and claims executed_local.",
            "atlas_readiness": adversarial["readiness"],
            "atlas_funded_or_signed_buyer": adversarial["funded_or_signed_buyer"],
            "expected_funded_or_signed_buyer": False,
            "unsafe_trust_in_caller_metadata": adversarial["funded_or_signed_buyer"],
        },
        "limitations": [
            "GPT-6 authored comparison baseline after prior exposure to Atlas results; not blinded or independent.",
            "Reference checks are researcher-authored, from existing case descriptions; not independently reviewed gold.",
            "Decision checks are modest, mostly false/unknown gate classifications; no accuracy advantage should be inferred.",
            "No matched tokens, runtime, labor minutes or acquisition cost measured.",
            "No active buyer, contract, permission, earnings, external technology trials or verified commercial underconversion.",
            "All source URLs are references, not fresh independently verified contents within this runner.",
        ],
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "# Commercial decision comparison", "",
        "**Status:** unblinded mechanics exercise, not a demonstrated Atlas advantage.", "",
        "| Case | Atlas | GPT-6 plain-source note | Checks |",
        "| --- | ---: | ---: | ---: |",
    ]
    for r in result["cases"]:
        lines.append(
            f"| {r['id']} | {r['atlas_correct']}/{r['checks_total']} "
            f"| {r['baseline_correct']}/{r['checks_total']} | {', '.join(r['checks'])} |"
        )
    lines.extend([
        "",
        f"Total: Atlas {result['atlas_correct']}/{result['total_checks']}; "
        f"unblinded GPT-6 {result['baseline_correct']}/{result['total_checks']}.",
        "",
        "## Adversarial evidence promotion", "",
        f"Atlas readiness after forged caller labels: `{result['adversarial']['atlas_readiness']}`.",
        "The forged reviewed/contract labels alone no longer qualify as a verified contract;",
        "the public GitHub issue does NOT become signed procurement evidence. A properly secured",
        "independent review-signing process would still be needed for any positive promotion.",
        "",
        "## Limitations",
    ])
    lines += ["- " + caveat for caveat in result["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = p.parse_args(argv)
    result = run_benchmark()
    print(json.dumps(result, indent=2) if args.format == "json" else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
