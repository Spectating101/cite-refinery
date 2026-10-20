"""Persistent, bounded LLM InvestigationController for Cite-Refinery.

The model chooses research direction/searches, interprets independently
discovered evidence, and criticizes claims. All graph writes are isolated,
neutral candidate review data, never accepted evidence or causal outcomes.
Each durable stage is checkpointed so a failed provider call can be resumed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .app import CiteRefinery
from .semantic import SemanticGraph
from .external_llm_reasoner import (
    build_prompt, make_input, inspect_answer, build_second_pass_prompt,
    inspect_second_pass,
)
from .external_llm_packets import llm_review_packet
from .investigation_sources import collect_sources


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="inv-",suffix=".json",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2)
            f.write("\n")
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def _questions(rows):
    return [{"question":str(r["question"])[:1200],
             "module_ids":list(r.get("module_ids") or [])[:15],
             "why_unresolved":str(r.get("why_unresolved") or "")[:1500]}
            for r in rows if isinstance(r,dict) and r.get("question")]


def planning_prompt(state):
    history=[{"focus":r.get("focus"),
              "source_ids":[s["id"] for s in r.get("sources",[])],
              "open_questions":[q["question"] for q in r.get("open_questions",[])[:8]]}
             for r in state["rounds"][-3:]]
    focused=state["focus"]
    return (
        "You are the active INVESTIGATION PLANNER of a semantic research agent. "
        "Decide what to investigate, not merely what words are similar. "
        "You have no preselected literature or source URLs. Prioritize independent "
        "academic evidence AND official practice/program documents. Choose your "
        "own relevant searches to test at least one plausible mechanism, potential "
        "counterargument and an empirical measurement gap. Avoid repeated searches; "
        "do not invent citations. Keep the focus narrower than a whole field, "
        "and state a concrete reason to compare the evidence families. "
        "If this is an evidence-repair investigation, distinguish public scholarly "
        "methods from author-held unpublished data; never imply a web search "
        "can independently reproduce data that are only available upon request. "
        "Do not treat an audit discrepancy as proof of misconduct or program failure. "
        "Return JSON object ONLY with fields "
        "{\"focus\":str,\"reason\":str,\"hypotheses\":[str],"
        "\"queries\":[{\"lane\":\"academic|official\",\"query\":str}]}. "
        "Supply between 2 and 5 queries covering BOTH lanes, and 1-4 hypotheses. "
        "DO NOT supply model answers or assume an intervention worked.\n\n"
        +json.dumps({"original_question":state["question"],"current_focus":focused,
                      "modules":state["modules"],"previous_rounds":history,
                      "remaining_frontier":state["frontier"][:8],
                      "evidence_repair_lineage":state.get("lineage")},
                     ensure_ascii=False,separators=(",",":"))
    )


def recovery_prompt(state):
    rnd=state["rounds"][-1]
    found=[{"title":x.get("title"),"origin_type":x.get("origin_type"),
            "source_url":x.get("url")} for x in rnd.get("sources",[])]
    return (
        "You are the LLM INVESTIGATION SOURCE-RECOVERY PLANNER. "
        "Your first search attempt failed to collect both academic evidence "
        "and independent institutional practice/program material. Do not make "
        "claims from absent evidence. Adjust search terms; try broader search "
        "phrases and relevant institutional terminology. Prefer queries that "
        "will add a MISSING evidence family rather than repeating retrieved titles. "
        "Produce one JSON object with fields focus, reason, hypotheses and "
        "2-5 queries, each with lane 'academic' or 'official'. Do NOT invent URLs. "
        "The controller will independently verify any resulting pages.\nINPUT:\n" +
        json.dumps({"focus":rnd["focus"],"last_plan":rnd["plan"],
                    "sources_obtained":found,"failures":rnd.get("source_failures",[]),
                    "excluded_off_topic_sources":rnd.get("excluded_off_topic_sources",[])},
                   ensure_ascii=False))


def validate_plan(value):
    if not isinstance(value,dict):
        raise ValueError("Planner must return a JSON object")
    focus=value.get("focus");reason=value.get("reason")
    queries=value.get("queries");hypotheses=value.get("hypotheses")
    if not isinstance(focus,str) or not 12<=len(focus)<=650 or not isinstance(reason,str) or len(reason)<15:
        raise ValueError("Planner focus/reason invalid")
    if not isinstance(queries,list) or not 2<=len(queries)<=5:
        raise ValueError("Planner must supply 2-5 searches")
    if not isinstance(hypotheses,list) or not 1<=len(hypotheses)<=4 or not all(isinstance(x,str) and len(x)>10 for x in hypotheses):
        raise ValueError("Planner hypotheses invalid")
    seen=set()
    for q in queries:
        if not isinstance(q,dict) or q.get("lane") not in {"academic","official"} or not isinstance(q.get("query"),str) or not 4<=len(q["query"])<=190:
            raise ValueError("Search must identify lane and bounded query")
        key=(q["lane"],q["query"].lower())
        if key in seen:raise ValueError("Duplicate search")
        seen.add(key)
    if {x["lane"] for x in queries}!={"academic","official"}:
        raise ValueError("Planning requires academic AND official source discovery")
    return {"focus":focus,"reason":reason[:1800],
            "hypotheses":hypotheses,"queries":queries}


class InvestigationController:
    STAGES={"plan","collect","needs_sources","reason","critique","stage","ready_next","blocked","done"}
    def __init__(self,workspace,*,reasoner,academic_search=None,official_search=None):
        self.root=Path(workspace).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.app=CiteRefinery(self.root/"refinery")
        self.graph=SemanticGraph(self.app.store)
        self.reasoner=reasoner
        self.academic_search=academic_search
        self.official_search=official_search

    def start(self,question,modules,*,max_rounds=2,fulltext_enrichment=False):
        if not isinstance(question,str) or not 15<=len(question)<=1200:
            raise ValueError("Investigation question must be 15-1200 characters")
        if not 1<=max_rounds<=8:raise ValueError("max_rounds must be 1-8")
        # Reuse schema validation without supplying any source at setup.
        if not isinstance(modules,list) or not 1<=len(modules)<=100:
            raise ValueError("1-100 problem modules must be known before investigation")
        ids=set()
        for m in modules:
            if not isinstance(m,dict) or not re.fullmatch(r"[A-Z]{2,5}-[0-9]{2,3}",str(m.get("id") or "")) or m["id"] in ids or not m.get("title") or not m.get("summary"):
                raise ValueError("Each problem module needs unique ID, title, summary")
            ids.add(m["id"])
        project=self.app.init_project("Investigation: "+question[:65],question)
        ident=uuid.uuid4().hex[:20]
        session={
            "schema":"cite_refinery.investigation.v1",
            "id":ident,"project_id":project.id,"question":question,"focus":question,
            "modules":modules,"max_rounds":max_rounds,"stage":"plan",
            "fulltext_enrichment":bool(fulltext_enrichment),
            "rounds":[],"frontier":[],"visited_questions":[],
            "created_at":_utc(),"updated_at":_utc(),
            "last_error":None,"authority":"candidate_neutral_only",
        }
        self.save(session)
        return session

    def path(self,ident):
        if not re.fullmatch(r"[0-9a-f]{20}",ident):
            raise ValueError("Invalid investigation ID")
        return self.root/"investigations"/(ident+".json")

    def load(self,ident):
        state=json.loads(self.path(ident).read_text(encoding="utf-8"))
        if state.get("id")!=ident or state.get("schema")!="cite_refinery.investigation.v1":
            raise ValueError("Unexpected investigation state schema")
        return state

    def save(self,state):
        if state["stage"] not in self.STAGES:raise ValueError("Invalid stage")
        state["updated_at"]=_utc()
        _atomic(self.path(state["id"]),state)

    def step(self,ident):
        s=self.load(ident)
        if s["stage"] in {"done","blocked"}:
            return s
        try:
            if s["stage"]=="ready_next":
                if len(s["rounds"])>=s["max_rounds"] or not s["frontier"]:
                    s["stage"]="done"
                else:
                    q=s["frontier"].pop(0)
                    s["focus"]=q["question"]
                    s["stage"]="plan"
                self.save(s)
                return s

            if s["stage"]=="plan":
                answer=self.reasoner(planning_prompt(s))
                plan=validate_plan(answer)
                s["rounds"].append({
                    "number":len(s["rounds"])+1,"focus":plan["focus"],
                    "plan":plan,"sources":[],"source_failures":[],"open_questions":[],
                    "state":"planned","source_count":0,"source_attempts":0,
                })
                s["visited_questions"].append(s["focus"])
                s["stage"]="collect"

            elif s["stage"]=="collect":
                rnd=s["rounds"][-1]
                kwargs={"per_query":2,"max_sources":8}
                if self.academic_search is not None:kwargs["academic_search"]=self.academic_search
                if self.official_search is not None:kwargs["official_search"]=self.official_search
                acquired=collect_sources(rnd["plan"]["queries"],**kwargs)
                existing_urls={x["url"] for x in rnd["sources"]}
                for item in acquired["sources"]:
                    if item["url"] not in existing_urls and len(rnd["sources"])<8:
                        rnd["sources"].append(item)
                        existing_urls.add(item["url"])
                rnd.setdefault("source_failures",[]).extend(acquired["failures"])
                if s.get("fulltext_enrichment"):
                    # Scholar and original fulltext are ONE study; store the
                    # explicit parent relation, not duplicate confirmations.
                    from .fulltext_audit import enrich_academic_abstract_with_fulltext
                    enhanced=[]
                    candidates=[x for x in rnd["sources"] if x.get("origin_type")=="scholarly_abstract_lead"
                                and x.get("pmcid")]
                    for source in candidates[:2]:
                        if any(x.get("parent_source_url")==source["url"] for x in rnd["sources"]):
                            continue
                        try:
                            extra=enrich_academic_abstract_with_fulltext(source)
                            if extra and extra["id"] not in {x["id"] for x in rnd["sources"]}:
                                enhanced.append(extra)
                        except Exception as e:
                            rnd.setdefault("fulltext_enrichment_failures",[]).append({
                                "pmcid":source.get("pmcid"),"kind":type(e).__name__,
                                "boundary":"Original abstract retained; JATS enrichment failed"})
                    rnd["sources"].extend(enhanced[:2])
                rnd["source_attempts"]=rnd.get("source_attempts",0)+1
                rnd["source_count"]=len(rnd["sources"])
                origins={x["origin_type"] for x in rnd["sources"]}
                if (rnd["source_count"]<2 or
                    not any("scholarly_" in x for x in origins) or
                    not any("official_" in x for x in origins)):
                    rnd["state"]="incomplete_source_families"
                    s["stage"]="needs_sources" if rnd["source_attempts"]<3 else "blocked"
                else:
                    rnd["state"]="sources_retrieved"
                    s["stage"]="reason"

            elif s["stage"]=="needs_sources":
                rnd=s["rounds"][-1]
                new_plan=validate_plan(self.reasoner(recovery_prompt(s)))
                rnd.setdefault("recovery_plans",[]).append(new_plan)
                rnd["plan"]=new_plan
                rnd["state"]="recovery_search_planned"
                s["stage"]="collect"

            elif s["stage"]=="reason":
                rnd=s["rounds"][-1]
                # In a source-audit repair investigation, stop obvious topic
                # mismatches before treating any official website as practice
                # evidence. This is only a narrow relevance prefilter; it
                # does not establish semantic entailment or source validity.
                if s.get("lineage",{}).get("source_audit_digest") and (
                    "dog" in rnd["focus"].lower() or "rabies" in rnd["focus"].lower()
                ):
                    from .investigation_adjudication import source_topic_fit
                    retained=[]
                    excluded=rnd.setdefault("excluded_off_topic_sources",[])
                    for source in rnd["sources"]:
                        if source["origin_type"].startswith("official_") and not source_topic_fit(
                            [{"statement":rnd["focus"]}],source
                        ):
                            entry={"source_id":source["id"],"url":source["url"],
                                   "reason":"No study-topic reference in retrieved official excerpt"}
                            if entry not in excluded:excluded.append(entry)
                            continue
                        retained.append(source)
                    rnd["sources"]=retained
                    rnd["source_count"]=len(retained)
                    if not any(x["origin_type"].startswith("official_") for x in retained):
                        rnd["state"]="incomplete_source_families"
                        s["stage"]="needs_sources" if rnd.get("source_attempts",0)<3 else "blocked"
                        self.save(s)
                        return s
                # Later rounds examine new evidence alongside bounded previously
                # retrieved sources, rather than starting from scratch. Previous
                # *model claims* remain provisional until re-evaluated.
                combined=list(rnd["sources"])
                ids={x["id"] for x in combined}
                for previous in reversed(s["rounds"][:-1]):
                    for old in previous.get("sources",[])[:4]:
                        if old["id"] not in ids and len(combined)<12:
                            combined.append(old);ids.add(old["id"])
                review_input=make_input(combined,s["modules"])
                provisional=[{
                    "statement":p["statement"],
                    "source_ids":[x["source_id"] for x in p["support"]],
                    "critic_verdict":next((v["reviewer_verdict"] for v in prev.get("critique",{}).get("propositions",[])
                                           if v["proposition_id"]==p["id"]),"not_reviewed"),
                } for prev in s["rounds"][:-1][-2:]
                  for p in prev.get("inspected",{}).get("propositions",[])[:8]]
                prompt=build_prompt(review_input)
                if provisional:
                    prompt+=("\nPRIOR MODEL HYPOTHESES ONLY, NOT ESTABLISHED FACTS; "
                             "re-examine against the exact source texts before retaining or contradicting:\n"
                             +json.dumps(provisional,ensure_ascii=False))
                output=self.reasoner(prompt)
                inspected=inspect_answer(review_input,output)
                rnd["review_input"]=review_input
                rnd["generated"]=output
                rnd["inspected"]=inspected
                rnd["state"]="reasoned"
                s["stage"]="critique"

            elif s["stage"]=="critique":
                rnd=s["rounds"][-1]
                full=rnd["inspected"]
                # Review bandwidth is finite. First consider candidate semantic
                # links, then additional atomic statements up to this bounded
                # model request. Anything NOT reviewed is explicit uncertainty,
                # never automatically "entailed" or "plausible".
                selected=[]
                for bridge in full["bridges"][:6]:
                    for pid in (bridge["from"],bridge["to"]):
                        if pid not in selected and len(selected)<18:selected.append(pid)
                for proposition in full["propositions"]:
                    if proposition["id"] not in selected and len(selected)<18:
                        selected.append(proposition["id"])
                sampled={**full,
                         "propositions":[p for p in full["propositions"] if p["id"] in selected],
                         "bridges":[e for e in full["bridges"] if e["from"] in selected and e["to"] in selected][:10]}
                critics=self.reasoner(build_second_pass_prompt(rnd["review_input"],sampled))
                critique=inspect_second_pass(rnd["review_input"],sampled,critics)
                prop_ids={p["proposition_id"] for p in critique["propositions"]}
                bridge_ids={(b["from"],b["to"]) for b in critique["bridges"]}
                for proposition in full["propositions"]:
                    if proposition["id"] not in prop_ids:
                        critique["propositions"].append({"proposition_id":proposition["id"],
                            "reviewer_verdict":"uncertain","literal_span_matched":False,
                            "rationale":"Not independently reviewed within the bounded LLM critique budget",
                            "scope_risks":"pending a further source entailment review", "authority":"NONE_ACCEPTED"})
                for bridge in full["bridges"]:
                    if (bridge["from"],bridge["to"]) not in bridge_ids:
                        critique["bridges"].append({"from":bridge["from"],"to":bridge["to"],
                            "reviewer_verdict":"uncertain",
                            "rationale":"Not reviewed within bounded LLM critique budget",
                            "authority":"NONE_ACCEPTED"})
                rnd["critique_raw"]=critics
                rnd["critique"]=critique
                rnd["review_coverage"]={"propositions_in_model_review":len(sampled["propositions"]),
                     "total_propositions":len(full["propositions"]),
                     "bridges_in_model_review":len(sampled["bridges"]),
                     "total_bridges":len(full["bridges"]),
                     "unreviewed_are_explicitly_uncertain":True}
                rnd["state"]="critiqued_with_explicit_pending_items"
                s["stage"]="stage"

            elif s["stage"]=="stage":
                rnd=s["rounds"][-1]
                packet=llm_review_packet(rnd["review_input"],rnd["inspected"],rnd["critique"])
                # Critic verdicts are NOT empirical validations. No external
                # program gets automatically marked deployed or effective.
                receipt=self.graph.ingest_packet(s["project_id"],packet,
                    packet_ref=f"investigation:{ident}:round:{rnd['number']}")
                rnd["packet_digest"]=hashlib.sha256(
                    json.dumps(packet,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                rnd["packet"]=packet
                rnd["graph_receipt"]=receipt
                rnd["state"]="staged_candidates"
                rnd["open_questions"]=_questions(rnd["inspected"]["open_questions"])
                for q in rnd["open_questions"]:
                    if q["question"] not in s["visited_questions"] and all(x["question"]!=q["question"] for x in s["frontier"]):
                        s["frontier"].append(q)
                s["stage"]="ready_next"

            s["last_error"]=None
        except Exception as e:
            # Persist failure without losing valid previous stages, allowing
            # user to fix provider/network and resume the SAME stage.
            s["last_error"]={"stage":s["stage"],"kind":type(e).__name__,
                             "message":str(e)[:400],"at":_utc()}
            self.save(s)
            raise
        self.save(s)
        return s

    def run(self,ident,*,max_steps=6):
        if not 1<=max_steps<=50:raise ValueError("max_steps must be 1-50")
        state=self.load(ident)
        for _ in range(max_steps):
            if state["stage"] in {"blocked","done"}:break
            state=self.step(ident)
        return state
