"""Cross-shard semantic atlas; model-derived candidate domains, never verified outcomes."""
from __future__ import annotations
import json
import re
from collections import Counter

def synthesis_prompt(provisional):
    readings=[{"id":r["source_id"],"role":r["role"],"statement":r["statement"],
               "scope":r["scope"],"caveat":r["caveat"]}
              for r in provisional["readings"]]
    clusters=[{"name":c["name"],"source_ids":c["source_ids"],
               "question":c["question"]}
              for c in provisional["emergent_clusters"]]
    return (
      "You are building a semantic ATLAS OF PROBLEMS using shuffled, previously "
      "unclassified scholarly and public sources. No predefined ontology "
      "modules or labels exist. Source role labels below are unverified "
      "model proposals even though initial source quotes were checked. "
      "Create 6-14 emergent substantive problem clusters, ideally covering "
      "the actual heterogeneous topics; not vague repeated clusters on 'health' "
      "or 'risks'. Each area must specify the concrete problem node, "
      "measurement or academic evidence node, real or proposed intervention "
      "node, and main evidence gaps. If there is no intervention or outcome "
      "in the supplied evidence, say only NOT FOUND IN THESE RETRIEVED SOURCES. "
      "Never infer worldwide nonexistence from a limited search; absence "
      "from this corpus is not absence in the field. Distinguish measured "
      "observational associations from verified causal effects; injury "
      "endpoints do not transfer to toxicant burden. Use only real source IDs from input, "
      "not original collection query labels or invented sources. Sources may "
      "belong to two linked areas maximum. Leave off-topic/unusable passages "
      "in unplaced_source_ids. Cross-domain links must not claim causality "
      "across unrelated geographies or fields. "
      "Return only JSON with EXACT keys: "
      '{"domains":[{"label":"specific emergent focus area",'
      '"problem_node":"source-grounded specific problem or unknown",'
      '"source_ids":["existing source ID"],'
      '"measurement_node":"measurement evidence and limitations",'
      '"intervention_node":"program action or lack of verified implementation",'
      '"evidence_limit":"missing critical perspectives or lack of independence",'
      '"questions":["specific follow-up question"]}],'
      '"cross_domain_links":[{"from_label":"exact domain label",'
      '"to_label":"other exact domain label",'
      '"relation":"methodological_analogy|shared_constraint|contrasting_outcome",'
      '"rationale":"source-specific limited relation"}],'
      '"unplaced_source_ids":["remaining source IDs"],'
      '"map_limit":"limits of 63-source non-exhaustive dump"} '
      "Each domain needs >=2 source IDs. Each input source must be placed "
      "in at least one domain or explicitly unplaced. Aim for 0-8 real "
      "cross-area links, zero is fine. Make gaps actionable. "
      "INPUT:\n"+json.dumps({"readings":readings,"local_themes":clusters},
                             ensure_ascii=False,separators=(",",":"))
    )

def _txt(v,key,n=10):
    if not isinstance(v,str) or not n<=len(v.strip())<=1700:
        raise ValueError("Missing "+key)
    return v.strip()

_ABSOLUTE_ABSENCE = re.compile(r"\bno\s+(?:verified|measured|independently validated)\b", re.I)
_SOURCE_SCOPED = re.compile(
    r"\b(?:within|among|in)\s+(?:the\s+|these\s+|this\s+)?"
    r"(?:(?:retrieved|supplied|sampled|provided|mapped|current)\s+)?"
    r"(?:sources|corpus|sample|records)\b", re.I,
)


def reject_unscoped_absence(text: str) -> str:
    """Reject absolute absence claims unless explicitly scoped to the selected source set.

    This is a narrow safety contract, not a semantic entailment or causality test.
    """
    if _ABSOLUTE_ABSENCE.search(text) and not _SOURCE_SCOPED.search(text):
        raise ValueError("Unscoped absence of intervention/outcome asserted from incomplete corpus")
    return text


def validate_synthesis(raw,provisional):
    ds=raw.get("domains") if isinstance(raw,dict) else None
    if not isinstance(ds,list) or not 5<=len(ds)<=16:
        raise ValueError("Expected 5-16 distinct discovered domains")
    refs={r["source_id"]:r for r in provisional["readings"]}
    labels=set();out=[];counts=Counter()
    for d in ds:
        if not isinstance(d,dict):raise ValueError("Bad domain")
        label=_txt(d.get("label"),"label",8)
        if label in labels:raise ValueError("Duplicate domain label")
        labels.add(label)
        ids=d.get("source_ids")
        if (not isinstance(ids,list) or not 2<=len(ids)<=25 or
            len(set(ids))!=len(ids) or any(i not in refs for i in ids)):
            raise ValueError("Unanchored domain evidence")
        counts.update(ids)
        questions=d.get("questions")
        if (not isinstance(questions,list) or not 1<=len(questions)<=6 or
            any(not isinstance(q,str) or len(q.strip())<14 for q in questions)):
            raise ValueError("Missing actionable followups")
        out.append({
          "label":label,"source_ids":ids,
          "problem_node":_txt(d.get("problem_node"),"problem node",15),
          "measurement_node":_txt(d.get("measurement_node"),"measurement node",15),
          "intervention_node":reject_unscoped_absence(_txt(d.get("intervention_node"),"intervention node",15)),
          "evidence_limit":_txt(d.get("evidence_limit"),"evidence limit",18),
          "questions":questions,
          "candidate_role_distribution":dict(Counter(refs[i]["role"] for i in ids)),
          "status":"provisional_semantic_domain","independent_empirical_validation":False,
        })
    if any(n>2 for n in counts.values()):raise ValueError("Source over-assigned")
    unplaced=raw.get("unplaced_source_ids")
    if not isinstance(unplaced,list) or len(set(unplaced))!=len(unplaced) or any(i not in refs for i in unplaced):
        raise ValueError("Unplaced invalid")
    if set(unplaced)&set(counts):raise ValueError("Source both placed/unplaced")
    if set(unplaced)|set(counts)!=set(refs):raise ValueError("Some source records silently omitted")
    links=raw.get("cross_domain_links")
    if not isinstance(links,list) or len(links)>16:raise ValueError("Invalid cross-topic link list")
    result_links=[]
    for e in links:
        if (not isinstance(e,dict) or e.get("from_label") not in labels or
            e.get("to_label") not in labels or e["from_label"]==e["to_label"] or
            e.get("relation") not in {"methodological_analogy","shared_constraint","contrasting_outcome"}):
            raise ValueError("Unsupported cross-domain relationship")
        result_links.append({**e,"rationale":_txt(e.get("rationale"),"edge justification",20),
                             "status":"provisional_cross_domain_comparison"})
    return {"schema":"cite_refinery.open_corpus_atlas.v1",
            "mapped_source_count":len(refs),"domains":out,
            "cross_domain_links":result_links,"unplaced_source_ids":unplaced,
            "exhaustive_coverage":False,"blind_human_validation":False,
            "accepted_scientific_claims":0,
            "map_limit":_txt(raw.get("map_limit"),"mapping limitation",20),
            "boundary":"The map emerged from unstructured sources, but remains a generative proposal with no independent role/causality benchmark."}
