"""Bounded, auditable portfolio decision evaluation.

This evaluates externally supplied decisions against independently sealed tasks.
It does NOT generate judgments, validate human gold, or establish model autonomy.
Only opaque evidence IDs and public URLs are accepted in public evaluation inputs.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

VERDICTS = {"supported", "refuted", "insufficient"}
SCHEMA = "cite_refinery.portfolio_decision_eval.v2"


class EvaluationError(ValueError):
    pass


def _require(ok, msg):
    if not ok:
        raise EvaluationError(msg)


def _unique_ids(rows, name):
    _require(isinstance(rows, list) and rows, name + " must be a nonempty list")
    ids = [r.get("id") for r in rows]
    _require(all(isinstance(x, str) and x and len(x) <= 100 for x in ids),
             name + " invalid IDs")
    _require(len(ids) == len(set(ids)), name + " duplicate IDs")


def _public_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        return False
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.hostname in
            {"github.com", "api.github.com", "raw.githubusercontent.com"}
            and not parsed.username and not parsed.password and not parsed.fragment)


def evaluate(tasks, answers):
    """Tasks are sealed evaluator-provided labels; answers are candidate output.

    Expected task:
      {id, gold, allowed_evidence_ids, evidence_urls, family}
    Expected answer:
      {id, verdict, evidence_ids, rationale}
    Explicitly declared allowed evidence is *not* proof of entailment.
    """
    _unique_ids(tasks, "tasks")
    _unique_ids(answers, "answers")
    task_by_id = {t["id"]: t for t in tasks}
    answer_by_id = {a["id"]: a for a in answers}
    _require(set(answer_by_id) == set(task_by_id),
             "Missing or extraneous candidate answers")
    results = []
    for task in tasks:
        tid = task["id"]
        gold = task.get("gold")
        _require(gold in VERDICTS, tid + ": invalid sealed gold verdict")
        family = task.get("family")
        _require(isinstance(family, str) and family and len(family) <= 80,
                 tid + ": invalid family")
        allowed = task.get("allowed_evidence_ids")
        urls = task.get("evidence_urls")
        _require(isinstance(allowed, list) and len(allowed) == len(set(allowed))
                 and all(isinstance(e, str) and e for e in allowed),
                 tid + ": invalid evidence allowlist")
        _require(isinstance(urls, list) and all(_public_url(url) for url in urls),
                 tid + ": nonpublic or invalid source URL")
        answer = answer_by_id[tid]
        verdict = answer.get("verdict")
        _require(verdict in VERDICTS, tid + ": invalid candidate verdict")
        cited = answer.get("evidence_ids")
        _require(isinstance(cited, list) and len(cited) == len(set(cited))
                 and all(isinstance(e, str) for e in cited),
                 tid + ": invalid cited evidence")
        rationale = answer.get("rationale")
        _require(isinstance(rationale, str) and len(rationale.strip()) >= 12,
                 tid + ": missing substantive rationale")
        unauthorized = sorted(set(cited) - set(allowed))
        unsupported_positive = verdict == "supported" and (not cited or bool(unauthorized))
        wrong = verdict != gold
        # Gold insufficient must never become an asserted positive. This is a
        # high-consequence failure even when an apparently plausible URL exists.
        false_approval = gold != "supported" and verdict == "supported"
        false_refutation = gold != "refuted" and verdict == "refuted"
        proper_abstention = gold == "insufficient" and verdict == "insufficient"
        results.append({
            "id": tid, "family": family, "gold": gold, "verdict": verdict,
            "correct": not wrong, "proper_abstention": proper_abstention,
            "false_approval": false_approval, "false_refutation": false_refutation,
            "unsupported_positive": unsupported_positive,
            "unauthorized_evidence_ids": unauthorized,
            "rationale_present_not_entailment_verified": True
        })
    n = len(results)
    counts = Counter(r["gold"] for r in results)
    insuff = counts["insufficient"]
    approvals = sum(r["verdict"] == "supported" for r in results)
    correct = sum(r["correct"] for r in results)
    bad_approval = sum(r["false_approval"] for r in results)
    scope = sum(bool(r["unauthorized_evidence_ids"]) for r in results)
    unsupported = sum(r["unsupported_positive"] for r in results)
    abstain = sum(r["proper_abstention"] for r in results)
    by_family = {}
    for fam in sorted({r["family"] for r in results}):
        subset = [r for r in results if r["family"] == fam]
        by_family[fam] = {"n": len(subset),
                          "correct": sum(r["correct"] for r in subset),
                          "false_approvals": sum(r["false_approval"] for r in subset)}
    return {
        "schema": SCHEMA, "task_count": n, "correct_count": correct,
        "accuracy": correct / n,
        "insufficient_gold_count": insuff,
        "proper_abstention_count": abstain,
        "insufficient_abstention_rate": abstain / insuff if insuff else None,
        "candidate_approval_count": approvals,
        "false_approval_count": bad_approval,
        "false_approval_rate": bad_approval / approvals if approvals else None,
        "unsupported_positive_count": unsupported,
        "source_scope_violation_count": scope,
        "by_family": by_family, "decisions": results,
        "release_gate_pass": bad_approval == 0 and unsupported == 0 and scope == 0
                             and abstain == insuff and correct == n,
        "release_gate_is_only_frozen_task_performance": True,
        "does_not_certify_autonomous_assessment_or_source_entailment": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    _require(not args.out.exists(), "Cannot overwrite existing evaluation receipt")
    result = evaluate(json.loads(args.tasks.read_text("utf-8")),
                      json.loads(args.answers.read_text("utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "task_count", "accuracy", "false_approval_count",
        "insufficient_abstention_rate", "source_scope_violation_count",
        "release_gate_pass")}, sort_keys=True))
    return 0 if result["release_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
