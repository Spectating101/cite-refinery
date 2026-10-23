"""Independent model output diagnostics, without repairing answers into fake passes."""
import json
from collections import Counter


REQUIRED = ("capabilities","limitations","integration_candidates",
            "competitor_substitutions","decision","decision_rationale",
            "unanswered_questions")


def diagnose(raw):
    """Distinguish serialization failure from missing or malformed dossier fields."""
    errors = []
    if not isinstance(raw, str):
        return {"parseable":False,"complete":False,"errors":["nontext_output"]}
    stripped = raw.strip()
    fenced = stripped.startswith("```")
    if fenced:
        errors.append("markdown_fence")
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1])
        else:
            errors.append("malformed_fence")
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return {"parseable":False,"complete":False,"errors":errors+["invalid_json"]}
    if not isinstance(obj, dict):
        return {"parseable":True,"complete":False,"errors":errors+["not_object"]}
    missing = [field for field in REQUIRED if field not in obj]
    if missing: errors.append("missing_fields")
    for field in REQUIRED[:4]:
        if field in obj and (not isinstance(obj[field],list)
                             or any(not isinstance(v,dict) for v in obj[field])):
            errors.append("malformed_"+field)
    complete = not missing and not any(x.startswith("malformed_") for x in errors)
    return {"parseable":True,"complete":complete,"errors":errors,
            "missing_fields":missing}


def aggregate(rows):
    classified = [diagnose(x["raw"]) for x in rows]
    return {"count":len(classified),
            "parseable_after_fence_removal":sum(d["parseable"] for d in classified),
            "structurally_complete":sum(d["complete"] for d in classified),
            "issues":dict(Counter(err for d in classified for err in d["errors"]))}
