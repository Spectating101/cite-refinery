"""Turn reviewed source atoms into *discriminating observations*, not causal verdicts.

No research sample is created; a model designs tests and a strict validator
checks exact evidence quotes, comparison logic and unavailable data status.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .investigation_controller import InvestigationController
from .external_llm_packets import _key

MECHANISMS={"immigration_abandonment","survey_detectability","local_recruitment"}
OBSERVATION_TYPES={"capture_recapture","individual_tracking","transect_detection","ownership_history","reproductive_history","sampling_effort"}
EVIDENCE_STATUS="not_identifiable_from_available_sources"


def review_material(workspace, investigation_id):
    ctrl=InvestigationController(workspace,reasoner=None)
    state=ctrl.load(investigation_id)
    if len(state["rounds"])<2 or state["stage"]!="done":
        raise ValueError("Requires a completed two-round investigation")
    rnd=state["rounds"][-1]
    if rnd.get("state")!="staged_candidates" or not rnd.get("critique") or not rnd.get("graph_receipt"):
        raise ValueError("Requires staged source-provenance and critical review")
    # Later-round propositions may cite earlier retained sources. Validate
    # against the full persisted ledger instead of only new round material.
    sources={}
    for prior in state["rounds"]:
        for source in prior.get("sources",[]):
            sid=source["id"]
            if sid in sources:
                if sources[sid]["url"]!=source["url"]:
                    raise ValueError("Source ID collision across different URLs")
                # Same URL may have independently fetched nonidentical excerpt
                # selections in different rounds. Merge as ONE source family
                # while preserving both verbatim passage variants and digests.
                previous=sources[sid]
                newhash=hashlib.sha256(source["text"].encode()).hexdigest()
                if newhash not in previous["variant_sha256"]:
                    combined=previous["text"]+"\n\n[ADDITIONAL_EXCERPT_SAME_URL]\n"+source["text"]
                    if len(combined)>24000:
                        raise ValueError("Source alias excerpt accumulation exceeds evidence size limit")
                    previous["text"]=combined
                    previous["variant_sha256"].append(newhash)
            else:
                sources[sid]={**source,"variant_sha256":[hashlib.sha256(source["text"].encode()).hexdigest()]}
    if not sources or not rnd["inspected"]["propositions"]:
        raise ValueError("No reviewed source material")
    evidence=[]
    for proposition in rnd["inspected"]["propositions"]:
        for support in proposition["support"]:
            src=sources.get(support["source_id"])
            if src is None or support["quote"] not in src["text"]:
                raise ValueError("Source excerpt changed since previous verified round")
        evidence.append({
            "id":proposition["id"],"statement":proposition["statement"],
            "scope":proposition["scope"],"limitation":proposition["limitation"],
            "support":proposition["support"],
        })
    return state,{
        "schema":"cite_refinery.discriminating_test_input.v1",
        "target_investigation":investigation_id,
        "source_digest":hashlib.sha256(json.dumps(
            [{"id":key,"url":src["url"],"text":src["text"]} for key,src in sorted(sources.items())],
            sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        "propositions":evidence,
        "sources":[{"id":src["id"],"url":src["url"],"origin_type":src["origin_type"],
                    "text":src["text"],"source_scope":src.get("source_scope",""),
                    "parent_source_url":src.get("parent_source_url"),
                    "same_study_as_parent":src.get("same_study_as_parent",False),
                    "variant_sha256":src["variant_sha256"]}
                   for src in sources.values()],
        "target_question":rnd["focus"],
        "boundary":"Source assertions and methodological analogies only: no matched field dog tracking / census in Sri Lanka, no matched bite/PEP/rabies trends.",
    }


def design_prompt(review):
    if review.get("schema")!="cite_refinery.discriminating_test_input.v1":
        raise ValueError("Unrecognized review input")
    # All significant exact evidence is supplied; model must reason about
    # observational implications, not fabricate numerical results.
    return (
        "You are designing FALSIFIABLE MECHANISM-DISCRIMINATION TESTS for a "
        "semantic research agent, not a word similarity engine or automated "
        "claim promoter. The research question asks what explains increases "
        "in observed free-roaming dog counts during CNVR campaigns. Compare "
        "three distinct hypotheses: (1) immigration/abandonment, (2) changed "
        "sighting probability/detectability, (3) local births/recruitment. "
        "You MUST preserve the fact that these causes can co-occur. "
        "The supplied sources include studies/reviews in other geographies "
        "and institution-hosted descriptions, NOT a matched Sri Lankan "
        "longitudinal dog dataset. These are design rationales, not measured "
        "mechanism shares. Produce observable measures distinguishing at least "
        "two rival hypotheses per test, including a contrast expectation, "
        "an alternative explanation, and what evidence would FALSIFY a "
        "mechanism-dominance interpretation. Require reproducible animal-ID "
        "histories and explicit detection/sampling-effort adjustments where "
        "appropriate. Unknown data is NOT zero; do not claim a causal estimate "
        "from abstractions, author guidance, or program participation counts. "
        "For observations, use ONLY 2-5 strings selected from these exact "
        "IDs, no paraphrases: capture_recapture, individual_tracking, "
        "transect_detection, ownership_history, reproductive_history, "
        "sampling_effort. For each test choose distinct IDs. "
        "Only cite a source quote if it appears VERBATIM in the supplied "
        "source text. Same-paper JATS plus abstract are ONE study. "
        "Return JSON only: {"
        '"mechanisms":[{"id":"immigration_abandonment|survey_detectability|local_recruitment",'
        '"mechanism":"...", "rationale":"...",'
        '"source_receipts":[{"source_id":"EPMC-...","quote":"verbatim substring"}]}],'
        '"tests":[{"id":"T1","title":"...",'
        '"compares":["immigration_abandonment","survey_detectability"],'
        '"observations":["capture_recapture","individual_tracking"],'
        '"unit_of_observation":"...","timing":"...",'
        '"expected_if_first":"...", "expected_if_second":"...",'
        '"nonidentifying_pattern":"...", "falsification_condition":"...",'
        '"confounders":"...", "data_required":"...",'
        '"source_receipts":[{"source_id":"EPMC-...","quote":"verbatim substring"}]}],'
        '"current_identifiability":"not_identifiable_from_available_sources",'
        '"missing_input":["..."],"next_decision":"..."} '
        "Provide exactly 3 mechanisms, all three mechanisms each once, "
        "3-5 discriminating tests, at least one test comparing each pair "
        "of mechanisms, and 2-6 concrete missing inputs. No invented "
        "field data, numerical effect sizes, implementation claims, or "
        "unsupported trial confirmations.\n"
        "EVIDENCE:\n"+json.dumps(review,ensure_ascii=False,separators=(",",":"))
    )


def _receipt_list(value,sources):
    if not isinstance(value,list) or not 1<=len(value)<=4:
        raise ValueError("Every reason/test requires 1-4 exact source receipts")
    receipts=[]
    for r in value:
        if not isinstance(r,dict) or not isinstance(r.get("source_id"),str) or not isinstance(r.get("quote"),str):
            raise ValueError("Invalid source receipt")
        source=sources.get(r["source_id"])
        if source is None or not r["quote"].strip() or r["quote"] not in source["text"]:
            raise ValueError("Unverified, invented, or missing source quote")
        receipts.append({"source_id":r["source_id"],"source_url":source["url"],
                         "quote":r["quote"],"quote_sha256":hashlib.sha256(r["quote"].encode()).hexdigest()})
    return receipts


def _bounded(d,key,*,min_chars=12,max_chars=1600):
    val=d.get(key)
    if not isinstance(val,str) or not min_chars<=len(val.strip())<=max_chars:
        raise ValueError("Invalid or missing substantial research field: "+key)
    return val.strip()


def validate_design(raw,review):
    if not isinstance(raw,dict) or raw.get("current_identifiability")!=EVIDENCE_STATUS:
        raise ValueError("Source-only study cannot be automatically identified as causal")
    sources={s["id"]:s for s in review["sources"]}
    ms=raw.get("mechanisms");ts=raw.get("tests")
    if not isinstance(ms,list) or len(ms)!=3 or {m.get("id") for m in ms}!=MECHANISMS:
        raise ValueError("Must compare exactly the three explicit alternative mechanisms")
    if not isinstance(ts,list) or not 3<=len(ts)<=5:
        raise ValueError("Must specify 3-5 distinct discriminating tests")
    mechanisms=[]
    for m in ms:
        mechanisms.append({"id":m["id"],"mechanism":_bounded(m,"mechanism"),
                           "rationale":_bounded(m,"rationale"),
                           "source_receipts":_receipt_list(m.get("source_receipts"),sources)})
    seen_ids=set();pairs=set();tests=[]
    for t in ts:
        if not isinstance(t,dict):
            raise ValueError("Malformed mechanism test")
        ident=t.get("id")
        if not isinstance(ident,str) or not ident.startswith("T") or not ident[1:].isdigit() or ident in seen_ids:
            raise ValueError("Unique short test ID required")
        seen_ids.add(ident)
        compared=t.get("compares")
        if not isinstance(compared,list) or len(compared)!=2 or len(set(compared))!=2 or not set(compared)<=MECHANISMS:
            raise ValueError("A discriminating test must compare exactly two distinct mechanisms")
        pairs.add(frozenset(compared))
        observations=t.get("observations")
        if not isinstance(observations,list) or not 2<=len(observations)<=5 or not set(observations)<=OBSERVATION_TYPES:
            raise ValueError("Requires 2-5 concrete observation types from the allowed data ontology")
        tests.append({
            "id":ident,"title":_bounded(t,"title",min_chars=8,max_chars=160),
            "compares":compared,"observations":observations,
            **{key:_bounded(t,key) for key in (
                "unit_of_observation","timing","expected_if_first","expected_if_second",
                "nonidentifying_pattern","falsification_condition","confounders","data_required")},
            "source_receipts":_receipt_list(t.get("source_receipts"),sources),
            "classification":"unexecuted_field_protocol_not_observation",
        })
    if len(pairs)!=3:
        raise ValueError("All three competing mechanism pairs must be explicitly discriminated")
    missing=raw.get("missing_input")
    if not isinstance(missing,list) or not 2<=len(missing)<=6 or any(not isinstance(x,str) or not 12<=len(x)<=600 for x in missing):
        raise ValueError("Missing data list must be specific and bounded")
    return {
        "schema":"cite_refinery.mechanism_discrimination_plan.v1",
        "origin_investigation":review["target_investigation"],
        "source_digest":review["source_digest"],
        "mechanisms":mechanisms,"tests":tests,
        "current_identifiability":EVIDENCE_STATUS,
        "missing_input":missing,"next_decision":_bounded(raw,"next_decision"),
        "authority":"neutral_unexecuted_protocol_only",
        "limits":["No original Anuradhapura dog-level, independently sampled community abundance, immigration or detection histories.",
                  "Different countries' source statements are methodological design input, NOT replicating outcomes.",
                  "No estimates of mechanism shares, intervention causality or human-health reduction are justified.",
                  "The generated tests themselves have not been independently expert-validated or field-executed."],
    }


def graph_packet(plan):
    if plan["schema"]!="cite_refinery.mechanism_discrimination_plan.v1":
        raise ValueError("Invalid plan for graph conversion")
    base=plan["source_digest"]
    source_urls={r["source_url"] for m in plan["mechanisms"] for r in m["source_receipts"]}
    mkeys={}
    nodes=[{"key":_key("measurement_gap",base),"statement":
            "Available cross-study methodological sources do not identify the proportions attributable to immigration, local births or survey detectability.",
            "kind":"limitation","layer":"neutral","tags":["causal_identifiability_not_established"],
            "source_refs":sorted(source_urls),
            "provenance":{"status":EVIDENCE_STATUS,
                          "boundary":"Missing original measured data, not proof no field data exists."}}]
    edges=[]
    for m in plan["mechanisms"]:
        mid=_key("mechanism_hypothesis",base+m["id"]);mkeys[m["id"]]=mid
        nodes.append({"key":mid,"statement":m["mechanism"],"kind":"mechanism",
                      "layer":"neutral","tags":["alternative_explanation_not_causally_identified"],
                      "source_refs":sorted({r["source_url"] for r in m["source_receipts"]}),
                      "provenance":{"rationale":m["rationale"],
                                    "source_receipts":m["source_receipts"],
                                    "boundary":"Plausible mechanism only; no estimated effect."}})
        edges.append({"source":mid,"target":nodes[0]["key"],"relation":"REQUIRES",
                      "status":"unresolved","provenance":{
                          "boundary":"Testable hypothesis lacks local discriminating measurements."}})
    for t in plan["tests"]:
        key=_key("discriminating_test",base+t["id"])
        nodes.append({"key":key,"statement":t["title"]+": "+t["data_required"],
                      "kind":"requirement","layer":"neutral",
                      "source_refs":sorted({r["source_url"] for r in t["source_receipts"]}),
                      "tags":["unexecuted_discriminating_test"],
                      "provenance":{k:v for k,v in t.items() if k!="title"},
                      })
        for comp in t["compares"]:
            edges.append({"source":key,"target":mkeys[comp],"relation":"CONTEXT_FOR",
                          "status":"unresolved","provenance":{
                              "boundary":"Proposed field test contrasts hypotheses; no observations collected.",
                              "expected":t["expected_if_first"] if comp==t["compares"][0]
                                         else t["expected_if_second"]}})
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"mechanism_discrimination_v1",
            "clusters":[],"nodes":nodes,"edges":edges,
            "conversion_metadata":{"status":"UNEXECUTED_RESEARCH_DESIGN",
                                   "accepted_effect_claims":0,
                                   "constraints":plan["limits"],
                                   "boundary":"This plan is a research requirement, not evidence a mechanism occurred."}}


def stage_plan(workspace,plan):
    controller=InvestigationController(workspace,reasoner=None)
    state=controller.load(plan["origin_investigation"])
    if state["stage"]!="done":
        raise ValueError("Original source investigation must be completed")
    packet=graph_packet(plan)
    before=controller.app.store.load()
    preview=controller.graph.preview_packet(state["project_id"],packet)
    if preview["changed_existing_edge_statuses"]:
        raise ValueError("Candidate staging would change existing edge state")
    receipt=controller.graph.ingest_packet(state["project_id"],packet)
    after=controller.app.store.load()
    if any(after["semantic_edges"][k]["status"]!=v["status"]
           for k,v in before["semantic_edges"].items()):
        raise RuntimeError("Original edge statuses changed unexpectedly")
    return {"receipt":receipt,"preview":preview,"nodes_declared":len(packet["nodes"]),
            "edges_declared":len(packet["edges"])}
