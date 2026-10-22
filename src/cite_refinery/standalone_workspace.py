"""Build an offline, read-only, three-map research atlas from existing receipts.

No ingestion, model call, browser network request, graph write, hidden holdout
source identity, unsupported scientific claims or cross-layer matching.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

FOUNDATION="cite_refinery.layer_foundations.v1"
ACADEMIC="cite_refinery.academic_evidence_atlas.v1"
IMPLEMENTATION="cite_refinery.implementation_evidence_atlas.v1"
PRACTICAL="cite_refinery.nocturnal_practical_atlas.v1"
SCHEMA="cite_refinery.standalone_research_pilot.v1"
MAX_ROWS=10000
MAX_OUTPUT=14_000_000


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _text(value, limit=3500):
    if value is None:
        return ""
    if not isinstance(value, (str, int, float, bool)):
        raise ValueError("Invalid untrusted text field")
    return str(value)[:limit]


def _url(value):
    parts=urlsplit(value) if isinstance(value,str) else None
    if (not parts or parts.scheme!="https" or not parts.hostname or
        parts.username is not None or parts.password is not None):
        raise ValueError("External evidence URL must be HTTPS without embedded credentials")
    return value


def _safe_urls(values):
    if not isinstance(values,(tuple,list)):
        raise ValueError("Source URLs must be a collection")
    return list(dict.fromkeys(_url(x) for x in values))[:45]


def _item(layer, group, key, *, title, summary="", urls=(), tags=(),
          facts=(), authority="", flags=(), details=None):
    label=layer+":"+group+":"+str(key)
    _require(0<len(label)<=500 and len(title or "")>0,"Invalid source record title or ID")
    return {
        "id":label,"layer":layer,"group":group,
        "title":_text(title,1200),"summary":_text(summary,2300),
        "urls":_safe_urls(urls),
        "tags":sorted({_text(x,130) for x in tags if x is not None}),
        "authority":_text(authority,350),
        "flags":sorted({_text(x,180) for x in flags}),
        "facts":[{"name":_text(k,170),"value":_text(v,1200)}
                 for k,v in facts],
        "details":[{"heading":_text(k,170),"text":_text(v,2800)}
                   for k,v in (details or [])],
    }


def build_pilot(foundation, academic, implementation, public_practical=None):
    """Assemble independent browse records; no inferred matches or ranking."""
    _require(foundation.get("schema")==FOUNDATION and
             foundation.get("cross_layer_edges_generated")==0,
             "Original three-layer foundation required, no joins allowed")
    _require(academic.get("schema")==ACADEMIC and
             academic.get("provenance",{}).get("development_partition_only") is True and
             academic["provenance"].get("heldout_source_id_or_text_imported") is False and
             academic.get("coverage",{}).get("sealed_holdout_documents_not_imported")==66,
             "Academic source map is not a frozen, sealed development split")
    _require(implementation.get("schema")==IMPLEMENTATION and
             implementation.get("cross_layer_edges_generated")==0 and
             implementation["coverage"].get("survey_repository_leads")==1287 and
             implementation["coverage"].get("underconverted_assets_proven")==0,
             "Implementation independent source census/scope altered")
    _require(implementation["coverage"].get("live_operational_implementations_verified")==0,
             "Claim of live Implementation outcomes contradicts source scope")
    _require(foundation.get("implementation",{}).get("unique_repositories")==1287,
             "Original Implementation foundation inventory changed")
    _require(len(academic.get("sources",{}))==
             academic["coverage"]["development_documents"]==103,
             "Academic development sources incomplete")
    _require(len(implementation.get("surveyed_repositories",{}))==1287,
             "Implementation source index incomplete")
    _require(len(foundation["academic"]["source_abstracts"])==47,
             "Legacy abstract-source inventory must stay separately labeled")
    if public_practical is not None:
        _require(public_practical.get("schema")==PRACTICAL and
                 public_practical.get("provenance",{}).get("approved_public_release_only") is True,
                 "Nocturnal snapshot not publication-authorized")
        origin=public_practical["provenance"]
        _require(origin.get("fictional") is True or
                 origin.get("trusted_manifest_sha256_pinned") is True,
                 "Nonfictional public Nocturnal release must have out-of-band manifest pin")
    cards=[]
    p=foundation["practical"]
    for row in p["reported_cases"]:
        cards.append(_item(
            "practical","reported_case",row["id"],
            title=row["title"],summary=row["provisional_model_statement"],
            urls=[row["url"]],
            tags=[row["provisional_model_role"],row["reporting_channel"]],
            facts=[("Recorded source type",row["origin_type"]),
                   ("Original text SHA-256",row["retrieved_text_sha256"]),
                   ("Scope",row["provisional_model_scope"])],
            authority="Unverified reported observation; NOT firsthand field evidence",
            flags=["reported_not_field_validated","provisional_model_reading"],
            details=[("Caveat",row["provisional_model_caveat"])]))
    for row in p["published_procurement_notices_as_separate_context"]:
        cards.append(_item(
            "practical","published_notice",row["id"],
            title=row["title"],summary="Published procurement notice metadata, not validated actual demand.",
            urls=[row["url"]],tags=["procurement_notice"],
            facts=[("Buyer",row["buyer"]),("Publication date",row["published"])],
            authority="Published notice metadata only; eligibility/current status unknown",
            flags=["eligibility_unverified","demand_unconfirmed"]))
    if public_practical is not None:
        is_fictional=public_practical["provenance"]["fictional"]
        for mid,row in sorted(public_practical["matters"].items()):
            modules=[public_practical["modules"][x] for x in row["module_ids"]]
            entity_names=[public_practical["entities"][x].get("name")
                          for x in row["entity_ids"]]
            timelines=[" • ".join(filter(None,[
                _text(m.get("observed_at"),60),_text(m.get("title"),120),
                _text(m.get("status_stage"),80)]))
                for m in modules]
            cards.append(_item(
                "practical","public_nocturnal_matter",mid,
                title=(modules[0].get("title") or mid) if modules else mid,
                summary="Publication-approved Nocturnal matter; original-source assertions are not independently adjudicated.",
                urls=row["source_urls"],
                tags=["nocturnal_matter",*(("fictional_pilot",) if is_fictional else ("public_release",))],
                facts=[("Matter ID",mid),
                       ("Reported current stage",row["current_stage_reported_by_nocturnal"]),
                       ("Source domains",", ".join(row["source_domains_not_independent_witnesses"])),
                       ("Modules in timeline",len(modules)),
                       ("Publicly listed entities",", ".join(filter(None,entity_names))[:500])],
                authority=("Fictional pilot data; not a real-world case" if is_fictional else
                           "Approved public snapshot; Nocturnal source claims, not independent truth"),
                flags=["published_snapshot","unresolved_dispute_reported" if
                       row["unresolved_dispute_reported"] else "dispute_not_flagged"],
                details=[("Public module timeline","\n".join(timelines)[:2600])]))
    for row in foundation["academic"]["source_abstracts"]:
        cards.append(_item(
            "academic","legacy_abstract",row["id"],title=row["title"],
            summary=row["provisional_model_statement"],urls=[row["url"]],
            tags=[row["origin_type"],*row["provisional_research_areas"]],
            authority="Earlier abstract/bibliographic lead; not a validated full-text finding",
            flags=["bibliographic_not_scientific_finding"],
            facts=[("Original excerpt SHA-256",row["retrieved_text_sha256"]),
                   ("Publication year",row["publication_year"] or "Unknown")],
            details=[("Provisional methodological caveat",row["provisional_model_caveat"])]))
    claims_by_source={}
    for row in academic["claims"].values():
        claims_by_source.setdefault(row["source_id"],[]).append(row)
    for sid,row in sorted(academic["sources"].items()):
        claims=claims_by_source.get(sid,[])
        cards.append(_item(
            "academic","development_source",sid,
            title=row["title"],summary="Frozen Academic development source index; extracted original text is not redistributed in this workspace.",
            urls=[row["url"]],tags=[row["origin_genre"]],
            authority="Indexed source identity; scientific claims are NOT independently validated",
            flags=["development_only","dataset_metadata_not_observations" if
                   row["origin_genre"]=="dataset_metadata" else
                   "methods_and_results_not_independently_validated"],
            facts=[("Original source genre",row["origin_genre"]),
                   ("Text SHA-256",row["text_sha256"]),
                   ("Extracted word count",row["reported_extracted_words"]),
                   ("Reported source-span claim count",row["source_anchored_claim_count"]),
                   ("Source-span review count",row["operator_checked_anchor_count"]),
                   ("Document date",row["date"] or "Unknown")],
            details=[("Analyst supplied, source-span anchored statements (not verified findings)",
                      "\n".join(c["role_operator_supplied"]+": "+c["statement_operator_supplied"]
                                for c in claims) if claims else
                      "No source-span-anchored findings have been submitted.")]))
    source_reports=implementation.get("original_source_function_replay_receipts",{})
    for rid,row in sorted(implementation["surveyed_repositories"].items()):
        cats=[x["category"] for x in row["categories"]]
        code=row["source_code_structure_audits"]
        historical=row.get("bounded_independent_original_module_replay")
        receipt=source_reports.get(rid)
        stage=("bounded_original_function_test" if historical else
               "original_code_sample_checked" if any(
                   x.get("status")=="source_files_sha_verified" for x in code) else
               "original_commit_checked" if row["source_identity_state"]==
                   "original_commit_and_root_checked" else "survey_metadata_only")
        details=[]
        if receipt:
            details.append(("Original source fixture outcomes",
                "\n".join(x["id"]+": "+x["status"]+
                          (": "+str(x.get("actual"))[:100] if x["status"]!="pass" else "")
                          for x in receipt["cases"])))
        for x in code[:2]:
            if x.get("status")=="source_files_sha_verified":
                details.append(("Pinned original source files (identity not functional proof)",
                    "\n".join(f["path"]+" @ "+f["blob_sha"] for f in
                              x.get("source_file_samples",[]))))
        cards.append(_item(
            "implementation","surveyed_repository",rid,
            title=row["name"],
            summary=row["publisher_description_not_capability_proof"] or
                    "No descriptive publisher metadata available.",
            urls=[row["url"]],tags=[*cats,stage],
            authority=("Bounded synthetic original-source functions tested; NOT full product"
                       if historical else "Original source inspection only; no tested capability"),
            flags=[stage,"adoption_unverified","reuse_rights_unverified"],
            facts=[("Source identity stage",stage),
                   ("Categories",", ".join(cats[:12])),
                   ("Reported prior source commits",", ".join(sorted(
                       {x.get("original_commit","") for x in row["pinned_source_checks"]
                        if x.get("original_commit")})) or "Not inspected"),
                   ("Independent synthetic fixture passes",historical.get(
                       "successful_preregistered_synthetic_cases",0) if historical else 0),
                   ("Independent synthetic fixture failures/errors",historical.get(
                       "failing_or_error_cases",0) if historical else 0)],
            details=details))
    for rid,row in sorted(implementation.get("external_tested_assets_not_in_survey",{}).items()):
        cards.append(_item(
            "implementation","external_historical_trial",rid,
            title=rid.removeprefix("github:"),
            summary=_text(row.get("relevant_scope_operator_supplied")),
            urls=[row["upstream_source_url"]],tags=["prior_historical_probe",row.get(
                "technology_type_operator_supplied","")],
            authority="Prior recorded synthetic/static test outside 1,287 GitHub survey; NOT replayed here",
            flags=["outside_survey","historical_receipt","operational_fit_unverified"],
            facts=[("Original upstream pinned commit",row["upstream_commit"]),
                   ("Earlier test-status counts",json.dumps(row["case_counts"],sort_keys=True))],
            details=[("Historical synthetic failures/untested items",
                      "\n".join(row["experimental_blockers"]))]))
    _require(len(cards)<=MAX_ROWS,"Offline pilot record count too high")
    ids=[x["id"] for x in cards]
    _require(len(ids)==len(set(ids)),"Source record names collide after namespacing")
    counts=dict(Counter(x["layer"] for x in cards))
    _require(counts.get("academic")==150 and
             counts.get("implementation")==1287+len(
                 implementation.get("external_tested_assets_not_in_survey",{})),
             "Standalone map counts changed unexpectedly")
    result={
        "schema":SCHEMA,
        "mode":"offline_readonly_local_pilot",
        "record_count":len(cards),
        "by_layer":counts,
        "original_data": {
            "practical_public_nocturnal_attached":public_practical is not None,
            "practical_real_public_release_claim":public_practical is not None and
                public_practical["provenance"]["fictional"] is not True,
            "practical_legacy_reported_not_firsthand":p["reported_case_count"],
            "separate_procurement_notices":len(p["published_procurement_notices_as_separate_context"]),
            "academic_development_source_count":103,
            "academic_legacy_bibliographic_leads":47,
            "academic_sealed_holdout_not_imported":66,
            "independently_validated_scientific_findings":academic["coverage"][
                "independently_validated_scientific_findings"],
            "implementation_survey_count":1287,
            "implementation_original_modules_tested":implementation["coverage"].get(
                "original_pinned_modules_with_executed_fixture_receipts",0),
            "implementation_actual_original_fixture_failures":implementation["coverage"].get(
                "actual_original_function_fixtures_failing",0),
            "implementation_live_field_outcomes":implementation["coverage"][
                "live_operational_implementations_verified"],
            "world_coverage_complete":False,
        },
        "limitations":[
            "All three indexes remain independent. No cross-layer joins, rankings or confirmed solutions.",
            "Search is literal within each layer; no semantic retrieval or autonomous verified answer.",
            "Practical legacy reports are unverified secondary observations; procurement notices are not confirmed operator demand.",
            "Academic 103 development records exclude 66 sealed holdout documents; source titles and texts do not prove scientific conclusions.",
            "Original-code synthetic trials are narrow tests, not deployed systems or rights clearance.",
            "No original document bodies, private ledgers or heldout source identifiers are redistributed.",
        ],
        "cards":cards,
    }
    return result


def _encode_for_script(value):
    # Avoid closing the script or HTML injection by untrusted original metadata.
    raw=json.dumps(value,ensure_ascii=True,separators=(",",":"))
    return (raw.replace("<","\\u003c").replace(">","\\u003e")
               .replace("&","\\u0026"))


def write_pilot(pilot, out_dir):
    _require(pilot.get("schema")==SCHEMA,"Original verified pilot data required")
    path=Path(out_dir)
    if path.exists():
        raise ValueError("Will not overwrite existing pilot directory")
    template=Path(__file__).with_name("standalone_atlas_template.html").read_text("utf-8")
    _require(template.count("<!-- ATLAS_JSON_SLOT -->")==1,
             "Single embedded source dataset slot required")
    data=json.dumps(pilot,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    _require(len(data.encode("utf-8"))<=MAX_OUTPUT,"Offline research packet exceeds size limit")
    digest=sha256(data.encode("utf-8")).hexdigest()
    html=template.replace("<!-- ATLAS_JSON_SLOT -->",_encode_for_script(pilot))
    path.mkdir(parents=True,exist_ok=False)
    (path/"index.html").write_text(html,encoding="utf-8")
    (path/"atlas.json").write_text(json.dumps(pilot,ensure_ascii=False,indent=2)+"\n",
                                   encoding="utf-8")
    (path/"README.txt").write_text(
        "Cite-Refinery offline independent research pilot\n"
        "Open index.html locally; no server, network model or login required.\n"
        "The data is source metadata and scoped test receipts, not validated world facts.\n"
        "atlas.json canonical SHA-256: "+digest+"\n",
        encoding="utf-8")
    return {"schema":SCHEMA,"records":pilot["record_count"],"layers":pilot["by_layer"],
            "atlas_canonical_sha256":digest,"directory":str(path),
            "output_files":["index.html","atlas.json","README.txt"],
            "no_cross_layer_edges":True}


def main(argv=None):
    p=argparse.ArgumentParser(description="Build single-file offline research browser from sealed source-qualified atlas artifacts")
    p.add_argument("--foundation",required=True,type=Path)
    p.add_argument("--academic",required=True,type=Path)
    p.add_argument("--implementation",required=True,type=Path)
    p.add_argument("--approved-practical",type=Path,
                   help="Optional, already release-approved Nocturnal Practical Atlas JSON")
    p.add_argument("--out-dir",required=True,type=Path)
    args=p.parse_args(argv)
    sources=[args.foundation,args.academic,args.implementation]
    if args.approved_practical:sources.append(args.approved_practical)
    for file in sources:
        if not file.is_file() or file.is_symlink() or file.stat().st_size>14_000_000:
            raise ValueError("Source map missing, symlinked or unbounded")
    inputs=[json.loads(x.read_text("utf-8")) for x in sources]
    result=write_pilot(build_pilot(*inputs),args.out_dir)
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
