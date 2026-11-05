#!/usr/bin/env python3
"""Check every original-source table row against independent PDF vector rules.

This does not choose a crop by score, repair img2table, or establish trusted data.
The operator rule/column and verbatim text oracle is manually scoped.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA='atlas.original_ruled_cost_table_completeness.v1'


def run(oracle_path:Path,pilot_path:Path,stability_path:Path,pdf_dir:Path,drive_root:Path)->dict:
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_ruled_inventory import verify_ruled_table_inventory
    from scripts.cluster_agent.optional_native_pdf_crop_review import extract_operator_cropped_native,verify_native_crop_words
    oracle=json.loads(oracle_path.read_text())
    pilot=json.loads(pilot_path.read_text())
    stability=json.loads(stability_path.read_text())
    if oracle.get('schema')!='atlas.operator_original_ruled_table_oracle.v1' or pilot.get('schema')!='atlas.real_pdf_operator_pilot.v1':
        raise ValueError('unexpected pinned original ruled source or pilot contract')
    source=next((x for x in pilot['cases'] if x['id']==oracle['source_id']),None)
    if source is None or source['source_sha256']!=oracle['original_sha256'] or oracle['original_physical_page'] not in source['selected_physical_pages']:
        raise ValueError('ruled source oracle differs from original heterogeneous PDF benchmark')
    if stability.get('schema')!='atlas.original_failed_page_crop_robustness.v1':
        raise ValueError('original source crop stability receipt is missing')
    stability_case=next((item for item in stability['cases'] if item['source_id']==oracle['source_id']),None)
    if (stability_case is None or stability_case['original_sha256']!=oracle['original_sha256'] or
        stability_case['operator_crop_bbox_pdf']!=oracle['baseline_operator_crop_bbox_pdf'] or
        stability_case['physical_page']!=oracle['original_physical_page'] or
        stability_case['baseline_match_count']!=4 or
        stability_case['perturbation_count']!=5 or
        stability_case['successful_perturbations']!=1):
        raise ValueError('original baseline crop instability pin differs from source review')
    p=(pdf_dir/(oracle['source_id']+'.pdf')).resolve(strict=True)
    if hashlib.sha256(p.read_bytes()).hexdigest()!=oracle['original_sha256']:
        raise ValueError('source bytes differ from pinned original PDF')
    grid=verify_ruled_table_inventory(p,source_sha256=oracle['original_sha256'],
        page=oracle['original_physical_page'],rule_bbox_pdf=oracle['ruled_source_bbox_pdf'],
        column_edges_pdf=oracle['operator_source_column_edges_pdf'],
        expected_rows=oracle['original_printed_table_rows'])
    candidate=extract_operator_cropped_native(p,oracle['original_physical_page'],
        oracle['baseline_operator_crop_bbox_pdf'],oracle['baseline_native_profile'])
    if candidate['source_sha256']!=oracle['original_sha256'] or candidate['table_count']!=1:
        raise ValueError('native crop candidate absent or source custody mismatch')
    parsed=candidate['tables'][0]
    rows=oracle['original_printed_table_rows']
    row_exactness=[{'row_index':i,
        'parser_source_row_exact_match':i<len(parsed['rows']) and parsed['rows'][i]==expected}
        for i,expected in enumerate(rows)]
    if parsed['row_count']!=len(rows):
        raise ValueError('candidate table has missing or extra native parsed rows')
    if any(not x['parser_source_row_exact_match'] for x in row_exactness):
        raise ValueError('baseline native parser differs from operator original source transcription')
    # Independently review all four originally scoped source numeric cells;
    # the complete ruled table check above covers ALL 15 source text cells.
    numbered=[{'table_index':0,'row_index':i,'label_column':0,'value_column':2,
        'header_row':0,'expected_label':row[0],'expected_numeric':row[2],
        'expected_header':rows[0][2]} for i,row in enumerate(rows) if i>0]
    word=verify_native_crop_words(p,candidate,numbered)
    if not grid['bounded_original_ruled_region_complete'] or word['matched']!=len(numbered):
        raise ValueError('original grid completeness or selected numeric source witness regressed')
    return {'schema':SCHEMA,'source_id':oracle['source_id'],
        'original_sha256':oracle['original_sha256'],
        'original_physical_page':oracle['original_physical_page'],
        'source_rule_region_pdf':oracle['ruled_source_bbox_pdf'],
        'column_edges_pdf':oracle['operator_source_column_edges_pdf'],
        'original_vector_horizontal_row_boundaries':grid['original_horizontal_rule_boundaries'],
        'bounded_original_ruled_table_rows':grid['expected_rows'],
        'bounded_original_ruled_table_columns':grid['expected_columns'],
        'original_words_in_ruled_region':grid['original_word_count_in_ruled_region'],
        'all_original_words_assigned_to_one_cell':grid['words_unassigned_to_one_operator_source_cell']==0,
        'source_rows_exact_word_inventory':grid['rows_with_exact_original_word_inventory'],
        'bounded_original_table_complete_from_original_rules':grid['bounded_original_ruled_region_complete'],
        'operator_selected_native_crop_parser_rows':parsed['row_count'],
        'operator_selected_native_crop_parser_cells':candidate['candidate_cell_count'],
        'operator_native_candidate_row_exactness':row_exactness,
        'original_native_numeric_word_witnesses':word['matched'],
        'original_native_numeric_word_abstentions':word['abstained'],
        'native_crop_boundary_stability_verified':False,
        'native_crop_matching_perturbations':stability_case['successful_perturbations'],
        'native_crop_perturbations_tested':stability_case['perturbation_count'],
        'complete_only_within_explicit_vector_rulings':True,
        'original_document_semantics_independently_reviewed':False,
        'table_prices_current_or_market_verified':False,
        'trusted_pdfscope_promotions':0,'auto_publish':False,
        'auto_register_dataset':False,
        'authority':'BOUNDED_ORIGINAL_SOURCE_RULED_TABLE_GRID_NOT_TRUSTED_DATA',
        'decision':'HOLD_CROP_FRAGILITY_AND_INDEPENDENT_SEMANTICS_REVIEW'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--pilot',type=Path,required=True)
    p.add_argument('--stability',type=Path,required=True)
    p.add_argument('--pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():raise FileExistsError('refusing to overwrite original ruled-table acceptance receipt')
    report=run(args.oracle,args.pilot,args.stability,args.pdf_dir,args.research_drive_root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
    print(json.dumps({key:report[key] for key in ('bounded_original_ruled_table_rows','bounded_original_ruled_table_columns','original_words_in_ruled_region','source_rows_exact_word_inventory','original_native_numeric_word_witnesses','decision')}))
if __name__=='__main__':main()
