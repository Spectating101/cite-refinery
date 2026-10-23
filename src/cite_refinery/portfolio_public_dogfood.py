"""Execute Cite–Refinery's real SemanticGraph on original public portfolio snapshots.

This first dogfood exposes what the Atlas can do, and what it CANNOT do.
Original public GitHub READMEs and CI run metadata only; no private repository
data, external model secrets, automatic proof of function, or graph promotion.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import argparse
import base64
import json
import re
import tempfile

from .app import CiteRefinery
from .semantic import SemanticGraph, SEMANTIC_PACKET_SCHEMA
from .workspace import ProductWorkspace

SCHEMA="cite_refinery.real_portfolio_dogfood.v1"
ALLOWLIST={
    "hardware-splicer","yzu-cluster","gauntlet-blowback","animal-charity",
    "live-presenter","cite-refinery","Invisible-ledger","citation-engine"
}
QUESTION_SET=(
    ("hardware-splicer","Which project checks electronic schematics and board fabrication designs before bench measurement?"),
    ("yzu-cluster","Which project helps a university lab find, approve and register external datasets?"),
    ("gauntlet-blowback","Which system prepares job, fellowship and grant applications with guarded submission?"),
    ("animal-charity","Which project diagnoses public-good delivery failures and disaster aid capacity constraints?"),
    ("live-presenter","Which project makes live speech into continuously changing visual presentation aids?"),
    ("cite-refinery","Which product maps an unresolved practical problem to scientific research and usable technology?"),
    ("Invisible-ledger","Which empirical thesis investigates gaps between platform revenue and economic transaction flows?"),
    ("citation-engine","Which common software kernel tracks provenance, authority transitions and justification receipts?"),
)
NEGATIVE_QUESTIONS=(
    "Which project has completed independent powered physical tests of a fabricated PCB?",
    "Which project has verified profitable institutional commercial adoption?",
    "Which project has an independently verified complete empirical review of every claim?",
)
MAX_BYTES=120_000


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _origin_readme_sha(raw):
    return sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()


def _canonical(data):
    return json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def _fetch_json(url, token=None):
    """Only the two fixed GitHub REST endpoint families are permitted."""
    from urllib.parse import urlsplit
    u=urlsplit(url)
    _require(u.scheme=="https" and u.hostname=="api.github.com" and u.port is None
             and u.username is None and u.password is None and not u.fragment,
             "GitHub API host violation")
    # The caller constructs URLs only from validated pinned repo fields.
    _require(u.path.startswith("/repos/Spectating101/") and
             (u.path.endswith("/contents/README.md") or
              u.path.endswith("/actions/runs")), "Unsupported GitHub endpoint")
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            raise ValueError("Redirect blocked")
    headers={"Accept":"application/vnd.github+json","User-Agent":"CiteRefineryPortfolioDogfood/0.1",
             "X-GitHub-Api-Version":"2022-11-28"}
    if token:
        headers["Authorization"]="Bearer "+token
    with build_opener(NoRedirect()).open(Request(url,headers=headers),timeout=15) as resp:
        _require(resp.status==200, "Source API did not return HTTP 200")
        raw=resp.read(MAX_BYTES+1)
    _require(len(raw)<=MAX_BYTES,"Source API response oversized")
    return json.loads(raw)


def validate_manifest(manifest):
    _require(manifest.get("schema")=="cite_refinery.public_portfolio_dogfood_sources.v1"
             and manifest.get("owner")=="Spectating101"
             and manifest.get("public_only") is True
             and manifest.get("never_publish_private_files") is True
             and manifest.get("independent_gold_available") is False,
             "Not the original bounded public portfolio manifest")
    records=manifest.get("repositories")
    _require(isinstance(records,list) and len(records)==8,"Wrong public portfolio scope")
    _require({r.get("repo") for r in records}==ALLOWLIST, "Unexpected/private repo")
    for r in records:
        _require(re.fullmatch(r"[a-zA-Z0-9_.-]{2,90}",r.get("repo","")) and
                 re.fullmatch(r"[0-9a-f]{40}",r.get("head_sha","")) and
                 re.fullmatch(r"[0-9a-f]{40}",r.get("readme_blob_sha","")) and
                 re.fullmatch(r"[a-z_]{4,60}",r.get("operator_declared_category","")),
                 "Original pinned source incomplete")
    _require(manifest.get("private_repositories_excluded_by_allowlist") is True,
             "Private/public scope collision")
    return records


def fetch_repo(record, fetch_json=_fetch_json, token=None):
    from urllib.parse import quote
    repo=record["repo"]
    # Pin by exact source COMMIT and verify Git's original BLOB hash. Neither
    # default-branch drift nor fabricated source text may enter this run.
    url=("https://api.github.com/repos/Spectating101/"+repo+"/contents/README.md?ref="
         +record["head_sha"])
    data=fetch_json(url,token=token)
    _require(isinstance(data,dict) and data.get("encoding")=="base64"
             and isinstance(data.get("content"),str)
             and data.get("sha")==record["readme_blob_sha"],
             "GitHub returned nonpinned README blob")
    raw=base64.b64decode(data["content"],validate=False)
    _require(len(raw)<=85_000 and _origin_readme_sha(raw)==record["readme_blob_sha"],
             "Original README data or Git blob hash changed")
    src=raw.decode("utf-8")
    _require(src.lstrip().startswith("# ") and len(src)>100,
             "Original maintainer README invalid")
    return {
        "repo":repo,"category":record["operator_declared_category"],
        "head_sha":record["head_sha"],
        "readme_blob_sha":record["readme_blob_sha"],
        "readme_sha256":sha256(raw).hexdigest(),
        "pinned_source_url":("https://github.com/Spectating101/"+repo+
                             "/blob/"+record["head_sha"]+"/README.md"),
        "readme":src,
    }


def fetch_ci(source, fetch_json=_fetch_json, token=None):
    from urllib.parse import urlencode
    url=("https://api.github.com/repos/Spectating101/"+source["repo"]+
         "/actions/runs?"+urlencode({"branch":"main","per_page":1}))
    try:
        data=fetch_json(url,token=token)
        runs=data.get("workflow_runs",[]) if isinstance(data,dict) else []
        if not runs:
            return {"status":"not_observed","interpretation":"not_a_test_failure"}
        r=runs[0]
        _require(isinstance(r,dict) and isinstance(r.get("id"),int),
                 "Malformed CI run")
        return {
            "status":"observed","run_id":r["id"],
            "workflow_name":r.get("name"),
            "conclusion":r.get("conclusion"),
            "head_sha":r.get("head_sha"),
            "same_source_commit":r.get("head_sha")==source["head_sha"],
            "url":r.get("html_url"),
            "provider_scope":"one_last_default_branch_workflow_only",
            "not_a_full_release_gate":True,
        }
    except (HTTPError,URLError,TimeoutError,ValueError,OSError,TypeError,KeyError):
        return {"status":"provider_unavailable",
                "interpretation":"unknown_not_a_missing_or_failed_test"}


def _source_quote(readme):
    # This uses plain source extraction, NOT LLM reasoning. It explicitly
    # selects self-reported boundaries and cannot certify their factual truth.
    text=" ".join(readme.split())
    phrases=re.split(r"(?<=[.!?])\s+",text)
    pattern=re.compile(r"\b(?:not|never|no|pending|paused|shelved|unproven|unverified|untested)\b",re.I)
    selected=[x for x in phrases if 24<len(x)<450 and pattern.search(x)]
    return selected[0][:440] if selected else text[:380]


def build_packet(sources, ci_records):
    clusters=[{"key":"portfolio","title":"Portfolio source claims and current verification"},
              {"key":"readiness","title":"Implementation and external proof boundaries"},
              {"key":"reuse","title":"Reuse and evidence authority"}]
    nodes,edges=[],[]
    for row in sources:
        name=row["repo"]
        clean=re.sub(r"[^a-z0-9]+","_",name.lower()).strip("_")
        source=row["pinned_source_url"]
        # This is the repository's OWN claim, not an externally verified result.
        intro=" ".join(row["readme"].split())[:520]
        nodes.append({
            "key":"repo_"+clean,"kind":"repository","layer":"program",
            "statement":name+": "+intro,
            "clusters":["portfolio","readiness"],
            "source_refs":[source],
            "provenance":{"source_commit_sha":row["head_sha"],
                          "readme_git_blob_sha":row["readme_blob_sha"],
                          "authority":"maintainer_description_not_independent_code_test",
                          "category_operator_supplied":row["category"]},
        })
        quote=_source_quote(row["readme"])
        nodes.append({
            "key":"quote_"+clean,"kind":"source","layer":"neutral",
            "statement":quote,"clusters":["readiness"],
            "source_refs":[source],
            "provenance":{"readme_git_blob_sha":row["readme_blob_sha"],
                          "authority":"verbatim_maintainer_boundary_not_verified_outcome"},
        })
        edges.append({"source":"quote_"+clean,"relation":"QUALIFIES",
                      "target":"repo_"+clean,"status":"candidate",
                      "provenance":{"authority":"maintainer_self_report_only",
                                    "source_url":source}})
        ci=ci_records[name]
        if ci.get("status")=="observed":
            nodes.append({
                "key":"ci_"+clean,"kind":"observation","layer":"practical",
                "statement":("GitHub Actions last main-branch observed workflow "+
                             str(ci.get("workflow_name"))+" conclusion "+
                             str(ci.get("conclusion"))+" on commit "+str(ci.get("head_sha"))),
                "clusters":["readiness"],
                "source_refs":[ci["url"]],
                "provenance":{"run_id":ci["run_id"],
                              "source_commit_tested":ci["same_source_commit"],
                              "authority":"one_github_workflow_metadata_not_product_quality"},
            })
            edges.append({"source":"repo_"+clean,"relation":"EVALUATED_BY",
                          "target":"ci_"+clean,"status":"qualified",
                          "provenance":{"boundary":"one CI workflow does not certify deployed functionality"}})
    # The research repository is scholarly *work-in-progress*, not an
    # independently peer-reviewed accepted conclusion.
    il=next(r for r in sources if r["repo"]=="Invisible-ledger")
    nodes.append({
        "key":"research_portfolio","kind":"research_question","layer":"academic",
        "statement":"The Invisible Ledger investigates platform revenue recognition versus transaction activity and reporting boundaries in Indonesia.",
        "clusters":["portfolio","reuse"],
        "source_refs":[il["pinned_source_url"]],
        "provenance":{"authority":"research_question_from_maintainer_readme_not_verified_answer"},
    })
    edges.append({"source":"research_portfolio","relation":"RELATED_TO",
                  "target":"repo_invisible_ledger","status":"candidate",
                  "provenance":{"boundary":"Self-described research, no independent published claim validation"}})
    # The original source explicitly claims generic integration into many
    # projects; these are candidates, not proof of package interoperability.
    ce=next(r for r in sources if r["repo"]=="citation-engine")
    for name in ("hardware-splicer","yzu-cluster","cite-refinery"):
        target="repo_"+re.sub(r"[^a-z0-9]+","_",name.lower()).strip("_")
        edges.append({"source":"repo_citation_engine","relation":"ADAPTABLE_TO",
                      "target":target,"status":"candidate",
                      "provenance":{"source_url":ce["pinned_source_url"],
                                    "authority":"maintainer_claim_not_independently_tested"}})
    return {"schema":SEMANTIC_PACKET_SCHEMA,
            "source_system":"public_github_pinned_readme_ci_dogfood_v1",
            "clusters":clusters,"nodes":nodes,"edges":edges}


def _clean_for_output(row):
    return {key:row[key] for key in (
        "repo","category","head_sha","readme_blob_sha","readme_sha256",
        "pinned_source_url")}


def run_public_portfolio(manifest, *, fetch_json=_fetch_json, token=None):
    rows=validate_manifest(manifest)
    sources=[fetch_repo(r,fetch_json=fetch_json,token=token) for r in rows]
    ci={r["repo"]:fetch_ci(r,fetch_json=fetch_json,token=token) for r in sources}
    packet=build_packet(sources,ci)
    # The actual Cite–Refinery core is executed in a clean ephemeral workspace.
    with tempfile.TemporaryDirectory(prefix="cite-refinery-public-portfolio-dogfood-") as tmp:
        app=CiteRefinery(tmp)
        proj=app.init_project("Eight public portfolio repository evaluation",
            "Map original repo claims, CI observations and bounded evidence uncertainty")
        graph=SemanticGraph(app.store)
        original_ingest=graph.ingest_packet(proj.id,packet,
                packet_ref="research_materials/portfolio_dogfood/public_source_manifest_2026_10_23.json")
        atlas=graph.cluster_map(proj.id)
        exported=graph.export(proj.id)
        # Core read-only product projection is exercised too.
        product=ProductWorkspace(app.store).project_view(proj.id)
        _require(len(exported["nodes"])==len(packet["nodes"]) and
                 len(exported["edges"])==len(packet["edges"]),
                 "Real graph changed original source packet totals")
        _require(len(atlas["clusters"])>=3 and product["atlas"]["clusters"],
                 "Actual ProductWorkspace map failed to render clusters")
    _require(all(e["status"] in {"candidate","qualified"} for e in packet["edges"]),
             "Promoted evidence edge detected in source-only audit")
    _require(sum(n["layer"]=="academic" for n in packet["nodes"])==1,
             "Unqualified research claims falsely promoted into Academic map")
    _require(all(x["readme_blob_sha"] in {r["readme_blob_sha"] for r in rows}
                 for x in sources),"Source claim escaped manifest identity")
    return {
        "schema":SCHEMA,"corpus":"8_original_public_github_repositories",
        "source_manifest_sha256":sha256(_canonical(manifest).encode()).hexdigest(),
        "source_snapshots":[_clean_for_output(r) for r in sources],
        "ci_read_only_observations":ci,
        "atlas_actual_semantic_graph_ingested":True,
        "atlas_actual_product_workspace_rendered":True,
        "source_nodes":len(packet["nodes"]),
        "source_edges":len(packet["edges"]),
        "layers":dict(Counter(n["layer"] for n in packet["nodes"])),
        "edges_by_status":dict(Counter(e["status"] for e in packet["edges"])),
        "same_commit_ci_observed":sum(x.get("status")=="observed" and x.get("same_source_commit") is True for x in ci.values()),
        "maintainer_claims_independently_verified":0,
        "external_technical_code_executions_by_this_run":0,
        "scientific_findings_verified_by_this_run":0,
        "independent_commercial_proof_records":0,
        "accepted_cross_repo_compatibility":0,
        "source_only_candidate_links":sum(e["status"]=="candidate" for e in packet["edges"]),
        "private_repositories_included":0,
        "original_nocturnal_case_imported":False,
        "frozen_academic_holdout_accessed":False,
        "autonomous_semantic_understanding_demonstrated":False,
        "no_automatic_portfolio_investment_or_deployment_authority":True,
        "source_claims_prove_source_exists_not_claim_truth":True,
        "programmatic_graph_not_an_independent_ai_dossier":True,
        "benchmark_limitations":[
            "Public only; private owned projects are excluded from GitHub Actions",
            "Maintainer README assertions are not independent technical verification",
            "One last CI run is neither full release status nor human field outcomes",
            "Manually declared project categories and source links, not AI-discovered labels",
            "Selected review questions are not independent blind relevance gold",
            "No automatic inference model or objective competitor output executed in this structural graph run",
        ],
        "packet":packet,
    }


def lexical_bm25_baseline(names, docs, queries):
    """Plain README BM25 baseline (no external model or prior repo labels)."""
    from collections import Counter
    from math import log
    def tokens(x):
        return re.findall(r"[a-z][a-z0-9]+",x.casefold())
    series=[tokens(doc) for doc in docs]
    _require(bool(series) and all(series),"Empty source descriptions")
    N=len(series)
    df=Counter(t for x in series for t in set(x))
    average=sum(map(len,series))/N
    results=[]
    for query in queries:
        qs=set(tokens(query))
        values=[]
        for doc in series:
            c=Counter(doc)
            k1,b=1.5,0.75
            length_factor=k1*(1-b+b*len(doc)/average)
            score=sum(log(1+(N-df[t]+0.5)/(df[t]+0.5))
                      * c[t]*(k1+1)/(c[t]+length_factor)
                      for t in qs if t in c)
            values.append(score)
        ranking=sorted(range(N),key=lambda i:(-values[i],names[i]))
        results.append([names[i] for i in ranking])
    return results


def run_queries(report):
    # A real pretrained *retrieval* test. No answer-synthesis or truth status
    # inferred from cosine similarities.
    import numpy as np
    from fastembed import TextEmbedding
    names=[r["repo"] for r in report["source_snapshots"]]
    source_nodes={n["key"].removeprefix("repo_"):n["statement"]
                  for n in report["packet"]["nodes"] if n["layer"]=="program"}
    # Repository identity is removed from vector text to reduce trivial identity
    # matches. The source statement itself remains exact original README prose.
    texts=[]
    for n in names:
        key=re.sub(r"[^a-z0-9]+","_",n.lower()).strip("_")
        text=source_nodes[key]
        texts.append(text.split(": ",1)[-1])
    prompts=[q for _,q in QUESTION_SET]+list(NEGATIVE_QUESTIONS)
    bm25_ranks=lexical_bm25_baseline(names,texts,prompts)
    model=TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2",threads=2)
    vectors=np.asarray(list(model.embed(texts+prompts,batch_size=16)),dtype=np.float32)
    if vectors.shape[0]!=len(texts)+len(prompts) or not np.isfinite(vectors).all():
        raise ValueError("Real pretrained embedding failure")
    norms=np.linalg.norm(vectors,axis=1)
    if np.any(norms==0) or np.any(~np.isfinite(norms)):
        raise ValueError("Malformed embedding norms")
    normalized=vectors/norms[:,None]
    docs=normalized[:len(texts)]
    records=[]
    for i,(target,question) in enumerate(QUESTION_SET):
        sim=docs@normalized[len(texts)+i]
        ranked=sorted(range(len(names)),key=lambda k:(-float(sim[k]),names[k]))
        rank=ranked.index(names.index(target))+1
        records.append({
            "query":question,
            "developer_selected_repository":target,
            "target_rank":rank,
            "top3":[names[x] for x in ranked[:3]],
            "top3_cosine":[round(float(sim[x]),5) for x in ranked[:3]],
            "source_grounded_answer_generated":False,
            "reference_gold_independent":False,
        })
    lexical_comparison=[
        {"developer_selected_repository":x[0],
         "bm25_target_rank":bm25_ranks[i].index(x[0])+1,
         "bm25_top3":bm25_ranks[i][:3],
         "minilm_target_rank":records[i]["target_rank"]}
        for i,x in enumerate(QUESTION_SET)
    ]
    negatives=[]
    for i,question in enumerate(NEGATIVE_QUESTIONS):
        sim=docs@normalized[len(texts)+len(QUESTION_SET)+i]
        top=max(range(len(names)),key=lambda k:float(sim[k]))
        negatives.append({
            "question":question,"nearest_source":names[top],
            "score":round(float(sim[top]),5),
            "answerability_verified":False,
            "nearest_neighbor_does_not_prove_positive_answer":True,
            "requires_abstention_or_extra_evidence":True,
        })
    return {
        "model":"sentence-transformers/all-MiniLM-L6-v2",
        "model_load_executed":True,
        "selected_target_count":len(records),
        "selected_target_top1_hits":sum(x["target_rank"]==1 for x in records),
        "selected_target_top3_hits":sum(x["target_rank"]<=3 for x in records),
        "selected_target_ranks":records,
        "same_corpus_BM25_baseline":{
            "selected_target_top1_hits":sum(x["bm25_target_rank"]==1 for x in lexical_comparison),
            "selected_target_top3_hits":sum(x["bm25_target_rank"]<=3 for x in lexical_comparison),
            "same_source_texts":True,
            "queries_with_correct_source":lexical_comparison,
            "note":"Standard local BM25 retrieval, not a commercial competitor or independently validated answer-quality control.",
        },
        "deliberately_unanswerable_questions":negatives,
        "independent_gold_available":False,
        "source_verification_or_cross_layer_reasoning_generated":False,
        "model_weight_sha_pinned":False,
        "warning":"Embedding retrieval over maintainer source text is not an independent capability, adoption, or scientific assessment.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--semantic",action="store_true",help="Actually run pretrained MiniLM ONNX over public repo evidence")
    args=p.parse_args(argv)
    _require(not args.out.exists(),"Refuse to overwrite prior user portfolio source audit")
    _require(args.manifest.is_file() and args.manifest.stat().st_size<=16_000,
             "Original source manifest missing or too large")
    m=json.loads(args.manifest.read_text("utf-8"))
    import os
    result=run_public_portfolio(m,token=os.environ.get("GITHUB_TOKEN"))
    if args.semantic:
        result["neural_retrieval"]=run_queries(result)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PORTFOLIO_ATLAS_DOGFOOD",json.dumps({
        "repos":len(result["source_snapshots"]),
        "source_nodes":result["source_nodes"],
        "edges":result["source_edges"],
        "layers":result["layers"],
        "same_commit_ci_observed":result["same_commit_ci_observed"],
        "actual_graph":result["atlas_actual_semantic_graph_ingested"],
        "actual_workspace":result["atlas_actual_product_workspace_rendered"],
        "autonomous_reasoning_established":False,
        "retrieval":result.get("neural_retrieval",{}).get("selected_target_top3_hits")
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
