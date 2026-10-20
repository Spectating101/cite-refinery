"""Independent *invocation* of a same-family critic for evidence-role scope.

A second call can identify mistakes, but is not independent human or model
verification. Any upgrade is prohibited; critic can only downgrade/exclude.
"""
from __future__ import annotations
import json
from .cross_domain_roles import ROLES,coverage_matrix

def critique_prompt(review,sources):
    lookup={x["id"]:x for x in sources}
    rows=[]
    for a in review["results"]:
        x=lookup[a["source_id"]]
        rows.append({"source_id":a["source_id"],"role":a["role"],"fit":a["fit"],
                     "quote":a["quote"],"why":a["why"],"limitations":a["limitations"],
                     "text":x["text"]})
    return (
      "You are a skeptical SOURCE GENRE AND ENTAILMENT CRITIC, checking a prior "
      "language model's classifications. The first reviewer could be wrong. "
      "A source hosted on WHO/CDC/UN pages is NOT automatically a deployed "
      "public intervention. A published risk association is not automatically "
      "an effect evaluation. Test whether EXACT quoted wording establishes "
      "academic study vs program guidance vs implemented practice vs a measured "
      "program outcome. You may only AFFIRM, DOWNGRADE, or EXCLUDE, never "
      "upgrade. If a source is merely recommending actions, a label of "
      "documented implementation/measured outcome MUST be downgraded to "
      "program guidance. Distinguish outcomes attributed to an actually "
      "implemented program from general outcomes in observational studies. "
      "For any ambiguity, downgrade. Do not invent facts or quotes. "
      "Return JSON only: {\"assessments\":[{\"source_id\":\"...\","
      "\"decision\":\"affirm|downgrade|exclude\","
      "\"safe_role\":\"one of the evidence roles or off_topic\","
      "\"reason\":\"at least 20 chars explaining whether evidence warrants label\"}]}."
      " Exactly one review per source; an affirmed safe_role must equal prior "
      "role. A downgraded role must be weaker, never stronger. INPUT:\n"+
      json.dumps(rows,ensure_ascii=False,separators=(",",":"))
    )

ORDER={
 "off_topic":0,"background_only":1,
 "practical_problem_report":2,"academic_method":2,
 "academic_finding":3,
 "program_guidance_or_proposal":2,
 "documented_implementation":4,
 "measured_program_outcome":5,
}
def validate_critique(raw,review,modules):
    if not isinstance(raw,dict) or not isinstance(raw.get("assessments"),list):
        raise ValueError("Role critic needs complete array")
    rlookup={x["source_id"]:x for x in review["results"]}
    if len(raw["assessments"])!=len(rlookup):raise ValueError("Incomplete role critic")
    checked=[];seen=set()
    for row in raw["assessments"]:
        if not isinstance(row,dict):raise ValueError("Malformed critic item")
        sid=row.get("source_id");decision=row.get("decision");new=row.get("safe_role")
        if sid not in rlookup or sid in seen:raise ValueError("Duplicate or unknown critic ID")
        seen.add(sid)
        if decision not in {"affirm","downgrade","exclude"} or new not in ROLES:
            raise ValueError("Invalid review or safe evidence role")
        old=rlookup[sid]["role"]
        if (decision=="affirm" and new!=old or
            decision=="downgrade" and (new==old or ORDER[new]>=ORDER[old]) or
            decision=="exclude" and new!="off_topic"):
            raise ValueError("Critic may not upgrade a source role")
        reason=row.get("reason")
        if not isinstance(reason,str) or len(reason.strip())<20:
            raise ValueError("Missing rationale")
        source=dict(rlookup[sid])
        source["pre_critique_role"]=old
        source["role"]=new
        source["critic_action"]=decision
        source["critic_reason"]=reason
        if new=="off_topic":
            source["fit"]="off_topic";source["module_ids"]=[];source["quote"]=""
        checked.append(source)
    return {
      "schema":"cite_refinery.cross_domain_role_critique.v1",
      "results":checked,
      "coverage":coverage_matrix(modules,checked),
      "critic_independence":"separate_call_same_model_family_not_independent_validation",
      "authority":"neutral_role_candidates_no_scientific_promotion",
      "inference_limitation":"Critic-reviewed role is not independent verification of a source statement, actual program implementation, causal attribution or measured intervention benefit.",
    }
