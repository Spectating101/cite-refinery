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
from urllib.parse import urlsplit

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
                      "evidence_repair_lineage":state.get("lineage"),
                      "user_supplied_materials_unverified":[
                          {"id":x["id"],"family":x["source_family"],
                           "text_excerpt":x["text"][:360],
                           "source_scope":x["source_scope"]}
                          for x in state.get("supplied_sources",[])],
                      "user_supplied_is_independent_corroboration":False},
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


SUPPLIED_EVIDENCE_SCHEMA = "cite_refinery.supplied_evidence.v1"
_SOURCE_FAMILIES = {
    "practical": "P",
    "academic": "A",
    "implementation": "I",
}
_MAX_SUPPLIED = 6


def validate_supplied_evidence(document):
    """Locally supplied TEXT only; never fetch URL, trust title, or promote it.

    A source URL is a user-provided locator, not retrieval verification.
    A source hash identifies exact submitted bytes, not semantic truth.
    """
    if not isinstance(document, dict) or set(document) != {"schema", "sources"} or (
        document["schema"] != SUPPLIED_EVIDENCE_SCHEMA
    ):
        raise ValueError("Expected exact cite_refinery.supplied_evidence.v1 document")
    items = document["sources"]
    if not isinstance(items, list) or not 1 <= len(items) <= _MAX_SUPPLIED:
        raise ValueError("Evidence intake accepts 1-6 supplied passages per session")
    normalized = []
    ids, urls = set(), set()
    for source in items:
        if not isinstance(source, dict) or set(source) != {
            "id", "family", "url", "title", "text", "scope"
        }:
            raise ValueError("Supplied passage needs id, family, url, title, text, scope exactly")
        family = source["family"]
        sid = source["id"]
        if family not in _SOURCE_FAMILIES or not isinstance(sid, str) or (
            not re.fullmatch(r"USR-[PAI]-[0-9]{2,3}", sid)
        ) or not sid.startswith("USR-" + _SOURCE_FAMILIES[family] + "-"):
            raise ValueError("Supplied source ID must match its declared family")
        if sid in ids:
            raise ValueError("Duplicate supplied source ID")
        ids.add(sid)
        url = source["url"]
        if not isinstance(url, str) or not 12 <= len(url) <= 500:
            raise ValueError("Every passage needs bounded HTTPS provenance URL")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or (
            parsed.port not in (None, 443)
        ) or any(ord(c) < 33 for c in url):
            raise ValueError("Supplied source locator must be a clean HTTPS URL")
        if url in urls:
            raise ValueError("Repeated supplied source URL cannot be counted as another independent record")
        urls.add(url)
        title, text, scope = source["title"], source["text"], source["scope"]
        if not isinstance(title, str) or not 5 <= len(title.strip()) <= 160:
            raise ValueError("Passage title must be 5-160 characters")
        if not isinstance(text, str) or not 40 <= len(text.strip()) <= 5000:
            raise ValueError("Passage text must be 40-5000 characters")
        if not isinstance(scope, str) or not 12 <= len(scope.strip()) <= 400:
            raise ValueError("Scope must explicitly explain origin or measurement limitations")
        normalized.append({
            "id": sid,
            "url": url,
            "title": title.strip(),
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "source_family": family,
            "origin_type": "user_supplied_" + family + "_unverified",
            "source_scope": (
                "User-submitted material, independently UNVERIFIED; URL has NOT "
                "been fetched or authenticated. Supplied scope: " + scope.strip()
            ),
            "provenance_status": "user_supplied_url_not_retrieved",
            "evidence_authority": "NONE_ACCEPTED",
        })
    return normalized


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

    def start(self,question,modules,*,max_rounds=2,fulltext_enrichment=False,
              evidence_document=None):
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
        supplied = (validate_supplied_evidence(evidence_document)
                    if evidence_document is not None else [])
        project=self.app.init_project("Investigation: "+question[:65],question)
        ident=uuid.uuid4().hex[:20]
        session={
            "schema":"cite_refinery.investigation.v1",
            "id":ident,"project_id":project.id,"question":question,"focus":question,
            "modules":modules,"max_rounds":max_rounds,"stage":"plan",
            "fulltext_enrichment":bool(fulltext_enrichment),
            "rounds":[],"frontier":[],"visited_questions":[],
            "supplied_sources":supplied,
            "source_authority":"user_supplied_not_independently_verified",
            "source_authentication":[],
            "cross_layer_assessments":[],
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

    def attach_supplied_evidence(self, ident, document):
        """Attach to an unreviewed stage, atomically, without silently replacing.

        A different text or URL under an existing source ID is an explicit
        conflict, never a silently updated citation. A retry is idempotent.
        """
        incoming = validate_supplied_evidence(document)
        s = self.load(ident)
        if s["stage"] not in {"plan", "collect", "needs_sources", "reason"}:
            raise ValueError("Source intake closed after reasoning/critique begins; start new session")
        previous = list(s.get("supplied_sources", []))
        existing = {x["id"]: x for x in previous}
        for item in incoming:
            if any(old["id"] != item["id"] and old["url"] == item["url"]
                   for old in previous):
                raise ValueError("Repeated provenance URL must not masquerade as independent evidence")
            old = existing.get(item["id"])
            if old is not None and old != item:
                raise ValueError("Supplied source ID changed source content or provenance")
            if old is None:
                previous.append(item)
                existing[item["id"]] = item
        if len(previous) > _MAX_SUPPLIED:
            raise ValueError("Total supplied source quota exceeded")
        if previous != s.get("supplied_sources", []):
            s["supplied_sources"] = previous
            self.save(s)
        return s

    def authenticate_supplied_evidence(self, ident, *, github_fetch=None, epmc_fetch=None):
        """Read-only verification of submitted text at supported publishers.

        Checkpoint every receipt and preserve authority NONE_ACCEPTED even for
        matched texts. User-submitted URLs remain untrusted until comparison.
        """
        from .source_authentication import audit_sources, _gh_api, _epmc
        state=self.load(ident)
        if state["stage"] not in {"plan", "collect", "needs_sources", "reason"}:
            raise ValueError("Publisher checks require a pre-critique investigation state")
        supplied=state.get("supplied_sources",[])
        if not supplied:raise ValueError("No supplied evidence to authenticate")
        receipts=audit_sources(supplied,github_fetch=github_fetch or _gh_api,
                               epmc_fetch=epmc_fetch or _epmc)
        existing=state.get("source_authentication",[])
        old_by_id={x["id"]:x for x in existing}
        for result in receipts:
            previous=old_by_id.get(result["id"])
            if previous and previous["text_sha256"]!=result["text_sha256"]:
                raise ValueError("Publisher receipt disagrees with stored source text digest")
        state["source_authentication"]=receipts
        state["authority"]="candidate_neutral_only"
        self.save(state)
        return state

    def assess_cross_layer_links(self, ident, proposals, *, critic=None, model_metadata=None):
        """Read-only three-layer source fit review in the existing investigation.

        Store a separate audit receipt. Never grant graph authority, including
        when the model says mechanism and source excerpts are aligned.
        """
        from .cross_layer_review import assess
        state=self.load(ident)
        if not state.get("supplied_sources"):
            raise ValueError("No user-supplied sources for cross-layer comparison")
        result=assess(state,proposals,critic=critic,model_metadata=model_metadata)
        prior=list(state.get("cross_layer_assessments",[]))
        if len(prior)>=12:
            raise ValueError("Cross-layer investigation review receipt limit reached")
        prior.append(result)
        state["cross_layer_assessments"]=prior
        state["authority"]="candidate_neutral_only"
        self.save(state)
        return result

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
                scholarly=any(x.startswith("scholarly_") for x in origins)
                official=any(x.startswith("official_") for x in origins)
                rnd["independently_retrieved_scholarly_material"]=scholarly
                rnd["independently_retrieved_official_material"]=official
                rnd["supplied_source_count"]=len(s.get("supplied_sources",[]))
                rnd["independent_source_family_coverage_complete"]=scholarly and official
                if scholarly and official:
                    rnd["state"]="sources_retrieved"
                    s["stage"]="reason"
                elif len(s.get("supplied_sources",[]))>=2 and len({
                    x["source_family"] for x in s["supplied_sources"]
                })>=2:
                    # Offline/user-material-only mode: permitted for *neutral
                    # review*, NOT for independent source validation. The
                    # missing source families remain explicit and unverified.
                    rnd["state"]="supplied_materials_ready_unverified"
                    rnd["missing_independent_families"]=[
                        x for x,found in (("scholarly",scholarly),("official",official))
                        if not found
                    ]
                    s["stage"]="reason"
                else:
                    rnd["state"]="incomplete_source_families"
                    s["stage"]="needs_sources" if rnd["source_attempts"]<3 else "blocked"

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
                supplied=s.get("supplied_sources", [])
                receipts={x["id"]:x for x in s.get("source_authentication",[])}
                if supplied:
                    # The user passage itself is the text supplied to the model.
                    # A publisher match is recorded as provenance only, not
                    # independent truth, field measurement or effect.
                    supplied=[{
                        **item,
                        "source_scope":item["source_scope"]+
                            " Publisher text match: "+
                            receipts.get(item["id"],{}).get("status","not_checked")+
                            "; source semantic claim UNREVIEWED."
                    } for item in supplied]
                    # Allocate the original academic and official evidence at
                    # least one slot each. User text does NOT satisfy either
                    # independent source discovery requirement.
                    limit=12-len(supplied)
                    mandatory=[]
                    for prefix in ("scholarly_", "official_"):
                        for item in combined:
                            if item["origin_type"].startswith(prefix):
                                if item["id"] not in {x["id"] for x in mandatory}:
                                    mandatory.append(item)
                                break
                    kept=list(mandatory)
                    for item in combined:
                        if len(kept)>=limit:break
                        if item["id"] not in {x["id"] for x in kept}:
                            kept.append(item)
                    # A supplied ID must never masquerade as a found citation.
                    if set(x["id"] for x in kept) & set(x["id"] for x in supplied):
                        raise ValueError("Supplied source identity conflicts with discovered source")
                    combined=kept+supplied
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
