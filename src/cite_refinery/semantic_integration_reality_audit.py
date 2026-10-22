"""Reproducible adversarial audit of actual three-atlas semantic integration.

Tests *the built offline product* against curated in-domain paraphrases,
the archived separate-model diagnostic, source identity overlap and runtime
wiring. Deliberately does not impersonate an LLM or silently upgrade evidence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import argparse
import json

SCHEMA="cite_refinery.semantic_integration_reality_audit.v1"
PILOT="cite_refinery.standalone_research_pilot.v1"
ENTAILMENT="cite_refinery.entailment_diagnostic_report.v1"
REVIEW="cite_refinery.three_layer_semantic_review_queue.v1"

# Human-chosen semantic equivalence hypotheses over already present records.
# These are explicitly *development probes*, not an independent gold eval.
# Both exact and paraphrase queries are submitted to the same current frontend
# lexical retrieval, with one source ID expected per query. No other tools,
# embeddings, models, privileged original text, or sealed holdout material.
PAIRS=[
 ("practical:reported_case:OA-da5bbdb0bf0dd0",
  "surplus food","routing unsold meals to hungry households"),
 ("practical:reported_case:EPMC-088e66a2f887",
  "Anuradhapura","stray animals immunized and sterilized over several years"),
 ("practical:reported_case:OFFICIAL-f3e30d7ac5a5",
  "Ban Kao Many","villagers receive advance alerts before river inundation"),
 ("academic:legacy_abstract:OA-2c8a36e510bc7f",
  "lithium-ion battery","whether processing discarded electric car packs pays off"),
 ("academic:legacy_abstract:OA-4f0f6d04561a0f",
  "concentration","pupils lose focus when classroom atmosphere is stale"),
 ("academic:legacy_abstract:OA-4ecb63fe5958c9",
  "coastal cities","stormwater threats to Indian seafront municipalities"),
 ("academic:legacy_abstract:OA-ba418ee71ac82d",
  "heatwaves","do extreme temperature alerts prevent deaths"),
 ("implementation:surveyed_repository:github:Mr-Fang-VLSI/EDAgent",
  "EDAgent","identify phantom wiring layer in comments on chip layout files"),
 ("implementation:surveyed_repository:github:blisspixel/recon",
  "blisspixel","classify patterns in host naming for externally visible systems"),
 ("implementation:external_historical_trial:github:WeixuanZ/flood-warning-system",
  "WeixuanZ","protect sensor monitoring from invalid river gauge readings"),
]


def _require(condition,reason):
    if not condition:raise ValueError(reason)


def _read_json(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size>15_000_000:
        raise ValueError("Missing, symlinked or oversized original benchmark data")
    return json.loads(p.read_text("utf-8"))


def frontend_match(cards, layer, query):
    """Replicate 2026-10-22 offline frontend searchable field list, verbatim.

    Assesses its real lexical functionality, *not* a simulated AI system.
    """
    tokens=query.lower().strip().split()
    matched=[]
    for row in cards:
        if row["layer"]!=layer:continue
        searchable=" ".join([
            row["id"],row["title"],row["summary"],row["group"],
            row["authority"],*row["tags"],*row["flags"],
            *(x["name"]+" "+x["value"] for x in row["facts"]),
        ]).lower()
        if all(token in searchable for token in tokens):
            matched.append(row["id"])
    return matched


def check_recorded_semantic_diagnostic(entailment,review):
    """Recalculate claimed archived counters; do not reinterpret labels as truth."""
    _require(entailment.get("schema")==ENTAILMENT and
             review.get("schema")==REVIEW and
             entailment.get("graph_promotion_allowed") is False,
             "Only archived unpromoted semantic diagnostic records permitted")
    cases=entailment.get("cases")
    _require(isinstance(cases,list) and len(cases)==24 and
             len({x["id"] for x in cases})==len(cases),
             "Archived model casebook is incomplete or duplicated")
    for row in cases:
        _require(row.get("reference") in {"entailed","contradicted","overreach","unresolved"}
                 and row.get("model_label") in
                 {"entailed","contradicted","overreach","unresolved"}
                 and row.get("human_adjudication_complete") is False
                 and row.get("commercial_or_scientific_status_promoted") is False
                 and row.get("agreement") is (
                     row["reference"]==row["model_label"]),
                 "Archived model-only case contradicts nonpromotion policy")
    agreement=sum(c["agreement"] for c in cases)
    false_entailed=sum(x["model_label"]=="entailed" and
                       x["reference"]!="entailed" for x in cases)
    _require(agreement==entailment["agreement_count"]==23 and
             false_entailed==entailment["false_entailment_count"]==0,
             "Archived model benchmark statistics conflict with rows")
    queue=review.get("semantic_review_queue")
    _require(isinstance(queue,list) and len(queue)==8 and
             review["counts"]["qualified_academic_edges_promoted"]==0 and
             review["counts"]["validated_technical_fit"]==0 and
             review["counts"]["validated_commercial_value"]==0 and
             all(x.get("promotion_allowed") is False for x in queue),
             "Archived semantic cross-source queue is not review-only")
    return {
        "archived_model_casebook_size":24,
        "archived_agreement_with_investigator_labels":agreement,
        "archived_false_entailed_vs_investigator_labels":false_entailed,
        "archived_mechanism_review_questions":8,
        "source_quote_verification_replayed_by_this_audit":False,
        "independent_human_reference_adjudication":False,
        "different_dataset_than_the_new_103_source_academic_split":True,
        "diagnostic_auto_connected_to_live_atlas":False,
        "model_semantic_reasoning_in_preexisting_codebase":True,
        "accepted_scientific_or_implementation_transitions":0,
    }


def audit(pilot, entailment, review, *, template=None, compiler_source=None):
    _require(pilot.get("schema")==PILOT and
             pilot.get("record_count")==len(pilot.get("cards",[]))==1497 and
             pilot.get("by_layer")=={
                 "practical":57,"academic":150,"implementation":1290},
             "Need 1,497 original source-bound pilot records")
    original=pilot.get("original_data",{})
    _require(original.get("academic_sealed_holdout_not_imported")==66 and
             original.get("independently_validated_scientific_findings")==0 and
             original.get("implementation_live_field_outcomes")==0 and
             original.get("implementation_original_modules_tested")==2 and
             original.get("implementation_actual_original_fixture_failures")==1 and
             original.get("practical_public_nocturnal_attached") is False,
             "Original pilot sources or scientific authority mutated")
    archived=check_recorded_semantic_diagnostic(entailment,review)
    ids={x["id"]:x for x in pilot["cards"]}
    archived_source_ids={x["source_id"] for x in entailment["cases"]}
    archived_legacy_overlap=0
    archived_new_academic_overlap=0
    for sid in sorted(archived_source_ids):
        source_url={x["source_url"] for x in entailment["cases"]
                    if x["source_id"]==sid}
        _require(len(source_url)==1,"Archived original source ID has multiple URLs")
        legacy=ids.get("academic:legacy_abstract:"+sid)
        if legacy is not None:
            _require(legacy["urls"]==list(source_url),
                     "Archived semantic source record doesn't match original published URL")
            archived_legacy_overlap+=1
        modern=ids.get("academic:development_source:"+sid)
        if modern is not None:
            _require(modern["urls"]==list(source_url),
                     "Archived semantic record not grounded in new frozen Academic identity")
            archived_new_academic_overlap+=1
    archived["archived_unique_original_source_count"]=len(archived_source_ids)
    archived["archived_source_ids_aligning_with_legacy_abstract_cards"]=archived_legacy_overlap
    archived["archived_source_ids_aligning_with_new_103_development_cards"]=archived_new_academic_overlap
    archived["archived_result_cards_actually_attached_to_workspace"]=0
    archived["source_id_possible_join_does_not_mean_semantic_model_connected"]=True
    _require(len(ids)==len(pilot["cards"]),"Repeated source index card")
    sample=[]
    for i,(target,direct,paraphrase) in enumerate(PAIRS,1):
        _require(target in ids,"Original curated semantic target missing: "+target)
        layer=ids[target]["layer"]
        direct_matches=frontend_match(pilot["cards"],layer,direct)
        semantic_matches=frontend_match(pilot["cards"],layer,paraphrase)
        sample.append({
            "id":"SEM"+str(i).zfill(2),"layer":layer,
            "reference_card_id":target,
            "literal_query":direct,"paraphrased_query":paraphrase,
            "literal_retrieves_reference":target in direct_matches,
            "paraphrase_retrieves_reference":target in semantic_matches,
            "literal_match_count":len(direct_matches),
            "paraphrase_match_count":len(semantic_matches),
            "retrieval_backend":"literal_frontend_metadata_all_tokens",
            "source_answer_entailment_evaluated":False,
            "reference_label_source":"investigator_chosen_development_pair_not_blind_gold",
        })
    literal=sum(x["literal_retrieves_reference"] for x in sample)
    paraphrase=sum(x["paraphrase_retrieves_reference"] for x in sample)
    url_to_layers=defaultdict(set)
    for card in pilot["cards"]:
        for url in card["urls"]:url_to_layers[url].add(card["layer"])
    duplicates=sorted(k for k,v in url_to_layers.items() if len(v)>1)
    if template is not None:
        _require(isinstance(template,str) and
                 'id="search"' in template and
                 'const searchable=[' in template and
                 'return term.every(t=>searchable.includes(t))' in template and
                 "invoke_semantic_llm" not in template and
                 "<script src=" not in template,
                 "Frontend source changed: cannot apply this version-specific audit")
    if compiler_source is not None:
        _require(isinstance(compiler_source,str) and
                 "def build_pilot(" in compiler_source and
                 "invoke_semantic_llm" not in compiler_source and
                 "external_semantic_discovery" not in compiler_source,
                 "Standalone research compiler changed: reevaluate live semantic path")
    limitations={
        "semantic_search_in_public_workspace":False,
        "authenticated_llm_invoked_by_workspace":False,
        "runtime_source_body_reading_for_questions":False,
        "runtime_source_entailment_or_contradiction_check":False,
        "real_semantic_link_between_independent_map_records":False,
        "practical_real_nocturnal_snapshot_attached":False,
        "academic_new_split_results_semantically_validated":False,
        "implementation_narrow_function_tests_available":True,
        "source_metadata_and_independent_provenance_visible":True,
        "semantic_engines_exist_in_separate_prior_experimental_routes":True,
        "live_multi_layer_semantic_integration_verified":False,
    }
    return {
        "schema":SCHEMA,
        "evaluation_scope":"frozen_readonly_2026_10_22_three_atlas_workspace",
        "measurement_type":"reproducible_development_smoke_not_blind_independent_gold",
        "search":{"n_pairs":len(sample),"literal_target_recall":literal,
                  "meaning_preserving_paraphrase_target_recall":paraphrase,
                  "paraphrase_trials_by_layer":dict(Counter(x["layer"] for x in sample)),
                  "cases":sample,
                  "semantic_paraphrases_not_independently_adjudicated":True,
                  "full_semantic_retrieval_quality_scored":False,
                  "precision_or_answer_correctness_scored":False},
        "source_integrity":{
            "indexed_records":len(pilot["cards"]),
            "distinct_external_source_urls":len(url_to_layers),
            "exact_same_original_urls_occurring_across_layers":len(duplicates),
            "repeated_same_URLs_are_not_independent_corroboration":True,
            "separate_practical_and_academic_record_identities_can_overlap":True,
            "sealed_66_holdout_source_ids_or_content_imported":False,
            "original_body_text_available_for_answer_entailment":False,
        },
        "historic_model_diagnostic":archived,
        "current_integration":limitations,
        "blocked_release_claims":[
            "Source index is not a semantic knowledge graph with verified meaning-based retrieval",
            "Archived 23/24 separate LLM agreement cannot measure this new browser's performance",
            "Cross-layer mechanisms and field effectiveness are not operationally verified",
            "Proof requires actual connected inference, independent gold evaluation and measured error/abstention",
        ],
        "verdict":"SOURCE_NAVIGATION_WORKS_BUT_LIVE_SEMANTIC_INTEGRATION_NOT_DEMONSTRATED",
        "readiness_gate_passed":False,
        "evaluation_promotes_scientific_or_commercial_authority":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot",required=True,type=Path)
    p.add_argument("--archived-entailment",required=True,type=Path)
    p.add_argument("--archived-semantic-queue",required=True,type=Path)
    p.add_argument("--report-out",required=True,type=Path)
    p.add_argument("--template",type=Path)
    p.add_argument("--workspace-source",type=Path)
    args=p.parse_args(argv)
    if args.report_out.exists():raise ValueError("Will not replace earlier benchmark evidence")
    template=args.template.read_text("utf-8") if args.template else None
    source=args.workspace_source.read_text("utf-8") if args.workspace_source else None
    result=audit(_read_json(args.pilot),_read_json(args.archived_entailment),
                 _read_json(args.archived_semantic_queue),
                 template=template,compiler_source=source)
    args.report_out.parent.mkdir(parents=True,exist_ok=True)
    args.report_out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
        "schema":SCHEMA,"literal_target_recall":result["search"]["literal_target_recall"],
        "paraphrase_target_recall":result["search"][
            "meaning_preserving_paraphrase_target_recall"],
        "same_original_urls_across_layers":result["source_integrity"][
            "exact_same_original_urls_occurring_across_layers"],
        "readiness_gate_passed":False}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
