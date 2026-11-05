#!/usr/bin/env python3
"""Reproduce the 3 strict parser failures and bounded native-crop review.

Never treat a graph as a table or successful source words as trusted data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA="atlas.failed_page_operator_cropped_native_recovery.v1"


def run(oracle_path,pilot_path,pdf_dir,drive_root):
    sys.path.insert(0,str(Path(drive_root).resolve(strict=True)/"drive"))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates_partial
    from scripts.cluster_agent.optional_native_pdf_crop_review import (
        extract_operator_cropped_native,verify_native_crop_words)
    from scripts.cluster_agent.cell_evidence import pdf_words
    from scripts.cluster_agent.optional_pdf_source_check import _witness

    oracle=json.loads(Path(oracle_path).read_text())
    pilot=json.loads(Path(pilot_path).read_text())
    if oracle.get("schema")!="atlas.operator_cropped_failed_pdf_pages.v1" or pilot.get(
        "schema")!="atlas.real_pdf_operator_pilot.v1":
        raise ValueError("operator/pilot source pins not recognized")
    originals={row["id"]:row for row in pilot["cases"]}
    cases=[]
    for config in [oracle["chart_case"],*oracle["table_cases"]]:
        name=config["source_id"];page=config["physical_page"]
        original=originals[name]
        if page not in original["selected_physical_pages"]:
            raise ValueError("physical page not in recorded heterogeneous pilot")
        path=(Path(pdf_dir)/(name+".pdf")).resolve(strict=True)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=original["source_sha256"]:
            raise ValueError("original source bytes differ from pinned pilot")
        failed=extract_candidates_partial(path,[page])
        if (failed["successful_page_count"]!=0 or failed["failed_page_count"]!=1 or
            failed["failed_pages"][0]["page"]!=page or
            failed["failed_pages"][0]["error_code"]!=config["strict_img2table_error_code"]):
            raise ValueError("strict original img2table failure was suppressed or changed")
        case={"source_id":name,"original_sha256":digest,
              "physical_page":page,"original_img2table_error_code":failed["failed_pages"][0]["error_code"],
              "trusted_values":0}
        if name=="bis138":
            original_words=pdf_words(path.read_bytes(),page)
            caption,_=_witness(original_words["words"],tuple(config["caption_bbox_pdf"]))
            if caption!=config["expected_caption"]:
                raise ValueError("graph-only source caption not in original PDF")
            case.update(original_operator_inspection=config["original_image_classification"],
                original_caption_verified=True,native_fallback_attempted=False,
                original_source_cells_checked=0,source_word_matches=0,
                page_outcome="CHART_ONLY_HOLD_NO_TABLE_RECONSTRUCTION")
        else:
            candidate=extract_operator_cropped_native(
                path,page,config["crop_bbox_pdf"],config["profile"])
            if candidate["source_sha256"]!=digest or candidate["table_count"]!=1:
                raise ValueError("original cropped table absent or ambiguous")
            checked=verify_native_crop_words(path,candidate,config["selected"])
            case.update(original_table_caption_operator_observed=config["original_table_caption"],
                native_fallback_attempted=True,operator_crop_bbox_pdf=config["crop_bbox_pdf"],
                native_profile=config["profile"],
                candidate_rows_in_crop=candidate["tables"][0]["row_count"],
                candidate_cells_in_crop=candidate["candidate_cell_count"],
                original_source_cells_checked=checked["checked"],
                source_word_matches=checked["matched"],source_word_abstentions=checked["abstained"],
                original_word_and_geometry_checks=[
                    {"source_row_index":r["row_index"],"status":r["status"],"checks":r["checks"]}
                    for r in checked["results"]],
                word_verifier_separate_library_from_detector=False,
                operator_table_context_independently_adjudicated=False,
                page_outcome=("SELECTED_SOURCE_WORDS_MATCH_REVIEW_ONLY"
                    if checked["matched"]==checked["checked"] else
                    "ABSTAIN_SOME_OPERATOR_SOURCE_WORDS_UNMATCHED"))
        cases.append(case)
    return {"schema":SCHEMA,"authority":"SOURCE_WORD_ONLY_OPERATOR_CROPS_NOT_TRUSTED_EXTRACTION",
        "original_selected_failed_pages":3,"original_img2table_errors_still_reproduced":3,
        "cropped_native_pages_attempted":sum(c["native_fallback_attempted"] for c in cases),
        "chart_only_original_pages_held":sum(not c["native_fallback_attempted"] for c in cases),
        "operator_selected_cells_checked":sum(c["original_source_cells_checked"] for c in cases),
        "source_word_matches":sum(c["source_word_matches"] for c in cases),
        "source_word_abstentions":sum(c.get("source_word_abstentions",0) for c in cases),
        "verified_original_table_semantics":False,"independent_human_adjudication":False,
        "default_img2table_parser_repaired":False,"original_pdf_bytes_committed":False,
        "trusted_source_values_promoted":0,"auto_publish":False,"auto_register_dataset":False,
        "release_decision":"HOLD_OPERATOR_SCOPED_RECOVERY_IS_NOT_DEFAULT_PARSER_FIX","cases":cases}


def main():
    ap=argparse.ArgumentParser()
    for key in ("oracle","pilot","pdf_dir","research_drive_root","out"):
        ap.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():raise FileExistsError("immutable acceptance receipt already exists")
    result=run(args.oracle,args.pilot,args.pdf_dir,args.research_drive_root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({k:result[k] for k in
        ("original_img2table_errors_still_reproduced","cropped_native_pages_attempted",
         "chart_only_original_pages_held","operator_selected_cells_checked",
         "source_word_matches","source_word_abstentions")}))
if __name__=="__main__":main()