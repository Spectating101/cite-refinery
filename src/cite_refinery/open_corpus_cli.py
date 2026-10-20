"""CLI to classify shuffled corpus shards and assemble evidence-first sketch.

No source content published; sanitized model paraphrases, source IDs, evidence
hashes, and unresolved questions may be committed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .open_corpus import collect
from .open_corpus_map import stable_shards,map_prompt,validate_map
from .external_llm_runtime import invoke_semantic_llm

def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")

def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-corpus-map")
    p.add_argument("--corpus-dir",type=Path,required=True)
    p.add_argument("--map-dir",type=Path,required=True)
    sub=p.add_subparsers(dest="action",required=True)
    sub.add_parser("collect")
    batch=sub.add_parser("map-shard")
    batch.add_argument("--index",type=int,required=True)
    batch.add_argument("--provider",choices=["copilot","antigravity","codex","gemini","ollama"],default="copilot")
    batch.add_argument("--model",default=None)
    batch.add_argument("--timeout",type=int,default=240)
    batch.add_argument("--raw-output",type=Path)
    sub.add_parser("status")
    sub.add_parser("assemble")
    atlas=sub.add_parser("synthesize")
    atlas.add_argument("--provider",choices=["copilot","antigravity","codex","gemini","ollama"],default="copilot")
    atlas.add_argument("--model",default=None)
    atlas.add_argument("--timeout",type=int,default=250)
    atlas.add_argument("--raw-output",type=Path)
    atlas.add_argument("--model-output",type=Path,help="Validate previously saved response without another model call")
    args=p.parse_args(argv)
    if args.action=="collect":
        corpus,manifest=collect(args.corpus_dir)
        print(json.dumps({"count":corpus["source_count"],"origins":sorted({x["origin_type"] for x in corpus["sources"]}),
                          "errors":len(corpus["retrieval_errors"]),"local":str(args.corpus_dir/"private_corpus.json")},indent=2))
        return
    corpus=json.loads((args.corpus_dir/"private_corpus.json").read_text())
    shards=stable_shards(corpus)
    args.map_dir.mkdir(parents=True,exist_ok=True)
    if args.action=="map-shard":
        if not 0<=args.index<len(shards):raise ValueError("Shard index outside corpus")
        identifier=f"shard-{args.index:02d}"
        dest=args.map_dir/(identifier+".json")
        if dest.exists():raise ValueError("Shard already mapped; do not overwrite reviewed results")
        prompt=map_prompt(shards[args.index],identifier)
        result=invoke_semantic_llm(prompt,provider=args.provider,model=args.model,timeout_seconds=args.timeout)
        raw=result["raw"]
        if args.raw_output:save(args.raw_output,raw)
        mapped=validate_map(raw,shards[args.index],identifier)
        mapped["generation_provider"]=result["provider"]
        mapped["generation_model"]=result["model"]
        save(dest,mapped)
        print(json.dumps({"batch_id":identifier,"readings":mapped["source_count"],
                          "clusters":len(mapped["clusters"]),"links":len(mapped["links"]),
                          "unresolved":len(mapped["unknowns"]),"saved":str(dest)},indent=2))
    elif args.action=="status":
        print(json.dumps({"corpus_sources":len(corpus["sources"]),
                          "shards":len(shards),
                          "completed":[i for i in range(len(shards)) if (args.map_dir/(f"shard-{i:02d}.json")).exists()]},indent=2))
    elif args.action=="synthesize":
        from .open_corpus_atlas import synthesis_prompt,validate_synthesis
        provisional=json.loads((args.map_dir/"provisional_map.json").read_text())
        if args.model_output:
            raw=json.loads(args.model_output.read_text())
            provenance="local_saved_model_response"
        else:
            result=invoke_semantic_llm(synthesis_prompt(provisional),provider=args.provider,
                                       model=args.model,timeout_seconds=args.timeout)
            raw=result["raw"]
            provenance=result["provider"]+":"+result["model"]
        if args.raw_output:save(args.raw_output,raw)
        assembled=validate_synthesis(raw,provisional)
        assembled["generation_provenance"]=provenance
        save(args.map_dir/"global_atlas.json",assembled)
        print(json.dumps({"domain_count":len(assembled["domains"]),
                          "source_count":assembled["mapped_source_count"],
                          "links":len(assembled["cross_domain_links"]),
                          "unplaced":len(assembled["unplaced_source_ids"]),
                          "authority":"candidate_only"},indent=2))
    elif args.action=="assemble":
        gathered=[];read=set();clusters=[];edges=[];questions=[]
        for i in range(len(shards)):
            dest=args.map_dir/(f"shard-{i:02d}.json")
            if not dest.exists():raise ValueError(f"Unmapped shard {i}: do not fabricate mapping")
            record=json.loads(dest.read_text())
            # Verify input/source binding to current corpus.
            if record.get("batch_id")!=f"shard-{i:02d}" or record.get("source_count")!=len(shards[i]):
                raise ValueError("Shard record does not belong to source snapshot")
            for row in record["source_readings"]:
                if row["source_id"] in read:raise ValueError("Source reading duplicated across shards")
                match=next((s for s in shards[i] if s["id"]==row["source_id"]),None)
                if not match or row["source_sha256"]!=match["sha256"]:
                    raise ValueError("Source hash changed since mapped")
                read.add(row["source_id"])
            gathered+=record["source_readings"]
            clusters += [{"batch_id":record["batch_id"],**x} for x in record["clusters"]]
            edges += [{"batch_id":record["batch_id"],**x} for x in record["links"]]
            questions += [{"batch_id":record["batch_id"],**x} for x in record["unknowns"]]
        if read!={x["id"] for x in corpus["sources"]}:
            raise ValueError("Not every source actually mapped")
        output={
            "schema":"cite_refinery.open_corpus_provisional_map.v1",
            "source_count":len(gathered),"readings":sorted(gathered,key=lambda x:x["source_id"]),
            "emergent_clusters":clusters,"proposed_links":edges,"unknowns":questions,
            "independent_scientific_validation":False,
            "accepted_evidence":0,"no_preassigned_module_taxonomy":True,
            "all_sources_mapped":True,
            "boundary":"Mapping is model-generated from a heterogeneous dump; ontology, clusters and links still need blind review.",
        }
        save(args.map_dir/"provisional_map.json",output)
        print(json.dumps({"mapped_sources":len(gathered),"emergent_clusters":len(clusters),
                          "candidate_links":len(edges),"unknowns":len(questions),
                          "status":"neutral_unverified"},indent=2))
if __name__=="__main__":main()
