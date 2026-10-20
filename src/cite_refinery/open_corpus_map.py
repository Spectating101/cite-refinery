"""Model-first open-corpus map WITHOUT preassigned source roles or modules.

Input is locally extracted publisher passage snippets. Stable hash-shards mix
collection strata, so the model does not receive topical query labels.
All generated claims require exact on-source quote checks and remain proposals.
"""
from __future__ import annotations
import hashlib
import json

ROLE_CODES={
 "practical_observation","academic_finding","academic_method",
 "program_guidance","reported_implementation","measured_program_outcome",
 "background_only","off_topic",
}
REL_CODES={"corroborates","qualifies","apparent_tension","methodological_gap"}
SCHEMA="cite_refinery.open_corpus_map_chunk.v1"

def stable_shards(corpus,max_per=9):
    if corpus.get("schema")!="cite_refinery.open_corpus.v1":raise ValueError("Unexpected raw corpus")
    if not 3<=max_per<=16:raise ValueError("Chunk size out of bounds")
    records=sorted(corpus["sources"],key=lambda x:hashlib.sha256(x["url"].encode()).hexdigest())
    shards=[records[i:i+max_per] for i in range(0,len(records),max_per)]
    return shards

def map_prompt(chunk,batch_id):
    if not chunk or len(chunk)>16:raise ValueError("Invalid mapping chunk")
    readings=[{"id":s["id"],"title":s["title"],"text":s["text"],
               "source_scope":s["source_scope"],"origin_type":s["origin_type"]}
              for s in chunk]
    return (
      "You are an epistemically cautious SEMANTIC CARTOGRAPHER exploring an "
      "UNCLASSIFIED heap of evidence. No predefined topics, ontology modules, "
      "practical/academic/program map or domain labels have been assigned. "
      "Discover thematic groupings from the actual passages. Different fields "
      "may appear in the SAME batch; avoid spurious edges just because texts "
      "both mention 'health', 'risk', or 'program'. Identify each source's real "
      "genre: observed practical problem, academic result, method, program advice, "
      "documented implemented action, or *actually measured program outcome*. "
      "A respected publisher does not prove a program was implemented. "
      "A program injury outcome is not proof of reduced toxicant burden. "
      "Quote sources verbatim from supplied passages only and label geography,"
      " time, population and what a source CANNOT show. Do not invent new "
      "sources, models or data. All claims are CANDIDATES. "
      "Respond with a SINGLE JSON object {\"batch_id\":\"...\","
      "\"readings\":[{\"source_id\":\"...\","
      "\"role\":\"practical_observation|academic_finding|academic_method|"
      "program_guidance|reported_implementation|measured_program_outcome|"
      "background_only|off_topic\","
      "\"fit\":\"relevant|context|off_topic\","
      "\"statement\":\"grounded single claim or limitation\","
      "\"quote\":\"verbatim substring 25+ characters or empty when off-topic\","
      "\"scope\":\"what population/place/period does this refer to\","
      "\"caveat\":\"what is not shown\"}],"
      "\"clusters\":[{\"name\":\"specific emergent topic\","
      "\"source_ids\":[\"ID\"],\"question\":\"specific research problem\"}],"
      "\"links\":[{\"from_source\":\"ID\",\"to_source\":\"ID\","
      "\"relation\":\"corroborates|qualifies|apparent_tension|methodological_gap\","
      "\"reason\":\"specific verified connection or limitation\"}],"
      "\"unknowns\":[{\"question\":\"actionable unresolved evidence question\","
      "\"source_ids\":[\"ID\"]}]}. "
      "Assess EVERY supplied source once. Provide 1-5 clusters and 0-6 "
      "links only when there is a justified semantic relationship; zero "
      "links is correct for unrelated sources. Include 2-6 unknowns. "
      "Assign at least one source to each cluster and do not force unrelated "
      "sources into a cluster. Role/fit/statement and source quote mandatory "
      "except off_topic, which must have empty quote. "
      "INPUT:\n"+json.dumps({"batch_id":batch_id,"source_readings":readings},
                             ensure_ascii=False,separators=(",",":"))
    )

def _text(v,k,minlen=10,maxlen=2000):
    if not isinstance(v,str) or not minlen<=len(v.strip())<=maxlen:
        raise ValueError("Invalid "+k)
    return v.strip()

def _ids(items,allowed):
    if not isinstance(items,list) or not items or len(set(items))!=len(items) or any(x not in allowed for x in items):
        raise ValueError("Unknown or repeated source in cluster/question")
    return list(items)

def validate_map(raw,chunk,batch_id):
    if not isinstance(raw,dict) or raw.get("batch_id")!=batch_id:
        raise ValueError("Mapping output batch mismatch")
    sources={s["id"]:s for s in chunk}
    rows=raw.get("readings")
    if not isinstance(rows,list) or len(rows)!=len(sources):
        raise ValueError("Every source must be assessed exactly once")
    seen=set();readings=[]
    for r in rows:
        if not isinstance(r,dict):raise ValueError("Source reading malformed")
        sid=r.get("source_id")
        if sid not in sources or sid in seen:raise ValueError("Unknown or duplicated reading ID")
        seen.add(sid)
        role=r.get("role");fit=r.get("fit");quote=r.get("quote")
        if role not in ROLE_CODES or fit not in {"relevant","context","off_topic"}:
            raise ValueError("Unrecognized source role/fit")
        if (role=="off_topic")!=(fit=="off_topic"):
            raise ValueError("Off-topic label/fit inconsistency")
        source=sources[sid]
        if fit=="off_topic":
            if quote not in ("",None):raise ValueError("Off-topic source cannot cite supporting quote")
            quote=""
        else:
            if not isinstance(quote,str) or len(quote.strip())<25 or quote not in source["text"]:
                raise ValueError("Generated source quote fails exact passage test")
        reading={"source_id":sid,"source_url":source["url"],
                 "source_sha256":source["sha256"],
                 "role":role,"fit":fit,
                 "statement":_text(r.get("statement"),"statement",12,1500),
                 "quote_sha256":hashlib.sha256(quote.encode()).hexdigest() if quote else None,
                 "scope":_text(r.get("scope"),"scope",5,1100),
                 "caveat":_text(r.get("caveat"),"caveat",12,1800),
                 "epistemic_status":"unverified_role_and_proposition",
                 "publisher_is_not_authority":True}
        readings.append(reading)
    valid={r["source_id"] for r in readings if r["fit"]!="off_topic"}
    groups=raw.get("clusters");links=raw.get("links");gaps=raw.get("unknowns")
    if not isinstance(groups,list) or not 1<=len(groups)<=5:
        raise ValueError("Need 1-5 emergent groups")
    if not isinstance(links,list) or len(links)>6:
        raise ValueError("Too many or malformed links")
    if not isinstance(gaps,list) or not 2<=len(gaps)<=6:
        raise ValueError("Need bounded unresolved questions")
    clusters=[];unique=set()
    for g in groups:
        if not isinstance(g,dict):raise ValueError("Invalid emergent cluster")
        name=_text(g.get("name"),"cluster name",8,180)
        if name.lower() in unique:raise ValueError("Duplicate group label")
        unique.add(name.lower())
        clusters.append({"name":name,
                         "source_ids":_ids(g.get("source_ids"),valid),
                         "question":_text(g.get("question"),"cluster research question",15,450),
                         "status":"proposed_cluster_not_confirmed"})
    edges=[]
    for e in links:
        if not isinstance(e,dict) or e.get("relation") not in REL_CODES:raise ValueError("Invalid edge relation")
        a=e.get("from_source");b=e.get("to_source")
        if a not in valid or b not in valid or a==b:raise ValueError("Unsupported edge endpoints")
        edges.append({"from_source":a,"to_source":b,"relation":e["relation"],
                      "reason":_text(e.get("reason"),"edge reasoning",20,1000),
                      "status":"proposed_unverified_semantic_relation"})
    unknowns=[]
    for g in gaps:
        if not isinstance(g,dict):raise ValueError("Malformed unknown")
        unknowns.append({"question":_text(g.get("question"),"research gap",15,600),
                         "source_ids":_ids(g.get("source_ids"),valid),
                         "status":"unknown_not_evidence_of_absence"})
    return {"schema":SCHEMA,"batch_id":batch_id,
            "source_readings":readings,"clusters":clusters,"links":edges,"unknowns":unknowns,
            "authority":"neutral_provisional",
            "source_count":len(chunk),
            "accepted_scientific_conclusions":0,
            "note":"No predefined module/topic labels, no fact verification or independent adjudication."}

def public_map_chunk(full):
    if full.get("schema")!=SCHEMA:raise ValueError("Bad map output")
    return full # only model paraphrases and quote SHA, no full source passages
