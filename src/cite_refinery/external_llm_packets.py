"""Stage LLM-reasoned source claims as neutral, review-only Cite-Refinery data."""
from __future__ import annotations
import hashlib


def _key(prefix, value):
    return prefix+"_"+hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:20]


def llm_review_packet(review_input, inspected, second_opinion=None):
    if inspected.get("status")!="LLM_PROPOSITIONS_REQUIRING_INDEPENDENT_SEMANTIC_REVIEW":
        raise ValueError("Only inspected LLM review results are accepted")
    if second_opinion is not None and second_opinion.get("state") != "CRITICAL_SECOND_PASS_NOT_AUTHORITY":
        raise ValueError("Only a checked second-pass critique can annotate the graph")
    critic_props={p["proposition_id"]:p for p in (second_opinion or {}).get("propositions",[])}
    critic_bridges={(e["from"],e["to"]):e for e in (second_opinion or {}).get("bridges",[])}
    modules={m["id"]:m for m in review_input["modules"]}
    sources={s["id"]:s for s in review_input["sources"]}
    clusters=[{"key":"llm_review_root","title":"LLM-assisted evidence review (not accepted)",
               "tags":["source_backed_hypotheses","unverified"]}]
    nodes=[];edges=[];modulekeys={};sourcekeys={};propkeys={}
    for mid,m in modules.items():
        mk=_key("module",mid);modulekeys[mid]=mk
        clusters.append({"key":mk,"title":f"{mid} — {m['title']}",
                         "parent":"llm_review_root","tags":["problem_ontology"]})
        nodes.append({
            "key":mk,"statement":m["title"]+" — "+m["summary"],
            "kind":"research_question","layer":"neutral","clusters":[mk],
            "tags":["candidate_problem_module"],
            "provenance":{"source_system":"preexisting_module_registry",
                          "boundary":"Problem-module topic only; not a verified real-world fact."},
        })
    for sid,s in sources.items():
        sk=_key("source",sid+s["text_sha256"]);sourcekeys[sid]=sk
        nodes.append({
            "key":sk,"statement":"Institutional excerpt for review: "+s["text"][:1100],
            "kind":"source","layer":"neutral","clusters":["llm_review_root"],
            "source_refs":[s["url"]],
            "tags":["source_excerpt_unverified_claims"],
            "provenance":{"source_id":sid,"text_sha256":s["text_sha256"],
                          "source_scope":s["source_scope"],
                          "parent_source_url":s.get("parent_source_url", ""),
                          "same_study_as_parent":s.get("same_study_as_parent",False),
                          "boundary":"Source text was supplied; source content authentication is separate from this packet."},
        })
    for p in inspected["propositions"]:
        key=_key("proposition",p["id"]+p["statement"]);propkeys[p["id"]]=key
        refs=sorted({e["source_url"] for e in p["support"]})
        nodes.append({
            "key":key,"statement":p["statement"],
            "kind":"concept","layer":"neutral",
            "clusters":[modulekeys[mid] for mid in p["module_ids"]],
            "source_refs":refs,
            "tags":["llm_semantic_atom","literal_quote_found","not_validated_entailment",p["claim_type"]],
            "provenance":{"review_status":p["review_status"],"claim_type":p["claim_type"],
                          "scope":p["scope"],"limitation":p["limitation"],
                          "quote_receipts":p["support"],
                          "second_pass_verdict":critic_props.get(p["id"],{}).get("reviewer_verdict","not_run"),
                          "second_pass_rationale":critic_props.get(p["id"],{}).get("rationale",""),
                          "boundary":"Quotation matches source excerpt; proposition not independently checked for entailment."},
        })
        for evidence in p["support"]:
            edges.append({
                "source":sourcekeys[evidence["source_id"]],"target":key,
                "relation":"CONTEXT_FOR","status":"candidate",
                "evidence_refs":[evidence["source_url"]],
                "provenance":{"quoted_passage":evidence["quote"],
                              "quote_sha256":_key("quote",evidence["quote"]),
                              "boundary":"Literal quote associated with model proposition; human/independent entailment review required."},
            })
        for mid in p["module_ids"]:
            edges.append({
                "source":key,"target":modulekeys[mid],
                "relation":"CONTEXT_FOR","status":"candidate",
                "evidence_refs":refs,
                "provenance":{"boundary":"LLM maps this atomic topic to a module; entire module is not thereby evidenced.",
                              "scope":p["scope"],"limitation":p["limitation"]},
            })
    by_id={p["id"]:p for p in inspected["propositions"]}
    for b in inspected["bridges"]:
        if b["from"] not in by_id or b["to"] not in by_id:
            raise ValueError("Missing proposition reference")
        refs=sorted({
            s["source_url"] for pid in (b["from"],b["to"])
            for s in by_id[pid]["support"]
        })
        verdict=critic_bridges.get((b["from"],b["to"]),{}).get("reviewer_verdict","not_run")
        status="unresolved" if verdict in {"uncertain","unsupported","contradicted"} else "candidate"
        edges.append({
            "source":propkeys[b["from"]],"target":propkeys[b["to"]],
            "relation":b["relation"],"status":status,"evidence_refs":refs,
            "provenance":{"reason":b["reason"],"limitations":b["limitations"],
                          "second_pass_verdict":verdict,
                          "second_pass_rationale":critic_bridges.get((b["from"],b["to"]),{}).get("rationale",""),
                          "review_status":b["review_status"],
                          "boundary":"LLM-proposed association between two atomized statements. Sources have not been independently checked for the relationship."},
        })
    for question in inspected["open_questions"]:
        qkey=_key("question",question["question"])
        nodes.append({
            "key":qkey,"statement":question["question"],
            "kind":"research_question","layer":"neutral",
            "clusters":[modulekeys[mid] for mid in question["module_ids"]] or ["llm_review_root"],
            "tags":["unresolved_llm_question_not_evidence"],
            "provenance":{"why_unresolved":question["why_unresolved"],
                          "boundary":"An LLM identified an information gap. Missing from source excerpt is not absent in the world."},
        })
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"external_llm_reasoner_v1",
        "clusters":clusters,"nodes":nodes,"edges":edges,
        "conversion_metadata":{
            "status":"CANDIDATE_LLM_REASONING_REQUIRES_ENTAILMENT_REVIEW",
            "propositions":len(inspected["propositions"]),
            "bridges":len(inspected["bridges"]),
            "critic_reviewed_propositions":len(critic_props),
            "critic_reviewed_bridges":len(critic_bridges),
            "critic_flagged_unresolved_bridges":sum(e["status"]=="unresolved" for e in edges),
            "rejected_proposals":len(inspected["rejected"]),
            "verified_effectiveness_claims":0,
            "authoritative_graph_unchanged":True,
            "boundary":"All nodes remain neutral and edges are candidate or unresolved; this is not accepted Practical, Academic, Program evidence.",
        },
    }
