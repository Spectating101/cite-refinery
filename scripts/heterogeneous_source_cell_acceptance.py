#!/usr/bin/env python3
"""Investigate heterogeneous recovered candidate TABLE shape versus source truth.

No new table extractor: reuse Research Drive's optional parser, layout triage,
original-word source checker, and pinned manually reviewed visual oracle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA='atlas.heterogeneous_source_cell_quality_acceptance.v1'
TABLE_MAP={
    'bis106': {4:[(0,0,1)]},
    'bis116': {4:[(0,0,1),(1,0,1)],5:[(0,0,2)]},
    'bis138': {4:[(0,0,1)]},
    'arxiv2604': {7:[(0,0,1)]},
    'arxiv2506': {11:[(0,1,2)]},
}


def run(pilot_path:Path,oracle_path:Path,pdf_dir:Path,research_drive_root:Path) -> dict:
    sys.path.insert(0,str(research_drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates_partial
    from scripts.cluster_agent.optional_pdf_layout_audit import triage_numeric_table
    from scripts.cluster_agent.optional_pdf_source_check import verify_candidate_words
    pilot=json.loads(pilot_path.read_text())
    oracle=json.loads(oracle_path.read_text())
    if oracle.get('schema')!='atlas.manual_heterogeneous_source_cell_oracle.v1':
        raise ValueError('unknown operator-selected source oracle')
    cases=[];source_observation=None
    for src in pilot['cases']:
        name=src['id'];path=(pdf_dir/(name+'.pdf')).resolve(strict=True)
        original_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        if original_hash!=src['source_sha256']:
            raise ValueError('original heterogeneous PDF digest changed')
        result=extract_candidates_partial(path,src['selected_physical_pages'])
        status=[];candidates={x['page']:x['candidate'] for x in result['successful_page_candidates']}
        for page,targets in TABLE_MAP[name].items():
            if page not in candidates:raise ValueError('expected independent selected-page success missing')
            for table_index,label_column,value_column in targets:
                report=triage_numeric_table(candidates[page],page=page,table_index=table_index,
                    label_column=label_column,value_column=value_column)
                status.append({'page':page,'table_index':table_index,
                    'label_column':label_column,'value_column':value_column,
                    'row_count':report['rows_considered'],
                    'shape_reviewable_rows':report['potential_rows'],
                    'abstained_rows':report['abstained_rows'],
                    'outcomes':[x['status'] for x in report['decisions']]})
        if name==oracle['source_id']:
            if original_hash!=oracle['source_sha256'] or oracle['physical_page'] not in candidates:
                raise ValueError('manual visual source cell oracle not backed by exact original PDF')
            p=oracle['physical_page']
            selections=[{
                'page':p,'table_index':oracle['table_index'],
                'row_index':x['row_index'],'label_column':oracle['label_column'],
                'value_column':oracle['value_column'],'header_row':oracle['header_row'],
                'expected_label':x['expected_label'],'expected_numeric':x['expected_numeric'],
                'expected_header':oracle['expected_printed_header']}
                for x in oracle['source_cells']]
            verified=verify_candidate_words(path,candidates[p],selections)
            source_observation={
                'source_id':name,'page':p,'original_sha256':original_hash,
                'reviewed_cells':verified['selected'],'source_word_matches':verified['matched'],
                'source_word_abstentions':verified['abstained'],
                'source_label_and_value_flags':[
                    {'id':label['id'],'status':outcome['status'],
                        'checks':outcome['checks']}
                    for label,outcome in zip(oracle['source_cells'],verified['results'])],
                'provenance':oracle['provenance'],
                'publisher_original_verified':False,'trusted_financial_export':False,
            }
        cases.append({'source_id':name,'original_sha256':original_hash,
            'selected_pages':src['selected_physical_pages'],
            'failed_pages':result['failed_pages'],
            'pages_with_tables':[page for page,c in candidates.items() if c['tables']],
            'total_unverified_parser_cells':result['total_candidate_cells'],
            'table_shape_diagnostics':status})
    if source_observation is None:raise ValueError('selected source-cell oracle was not executed')
    return {'schema':SCHEMA,
        'authority':'ORIGINAL_SOURCE_WORD_REVIEW_NO_ISSUER_VERIFICATION',
        'documents':len(cases),
        'candidate_cells_total':sum(c['total_unverified_parser_cells'] for c in cases),
        'table_regions_triaged':sum(len(c['table_shape_diagnostics']) for c in cases),
        'candidate_rows_triaged':sum(x['row_count'] for c in cases for x in c['table_shape_diagnostics']),
        'shape_reviewable_rows':sum(x['shape_reviewable_rows'] for c in cases for x in c['table_shape_diagnostics']),
        'abstained_candidate_rows':sum(x['abstained_rows'] for c in cases for x in c['table_shape_diagnostics']),
        'manual_source_cell_acceptance':source_observation,
        'actual_second_human_adjudication':False,
        'primary_issuer_source_verified':False,
        'source_file_bytes_committed':False,
        'trusted_data_promotions':0,
        'auto_publish':False,'auto_register_dataset':False,
        'decision':'HOLD_UNVERIFIED_LAYOUTS_SECONDARY_SOURCE_AND_FAILED_PAGES',
        'cases':cases}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pilot',required=True,type=Path)
    ap.add_argument('--oracle',required=True,type=Path)
    ap.add_argument('--pdf-dir',required=True,type=Path)
    ap.add_argument('--research-drive-root',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite original-source acceptance evidence')
    out=run(a.pilot,a.oracle,a.pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as handle:json.dump(out,handle,indent=2,ensure_ascii=False);handle.write('\n')
    print(json.dumps({key:out[key] for key in ('documents','table_regions_triaged','candidate_rows_triaged','shape_reviewable_rows','abstained_candidate_rows','candidate_cells_total')}))
    print(json.dumps({key:out['manual_source_cell_acceptance'][key] for key in ('reviewed_cells','source_word_matches','source_word_abstentions','publisher_original_verified')}))
if __name__=='__main__':main()
