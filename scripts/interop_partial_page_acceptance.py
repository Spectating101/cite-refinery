#!/usr/bin/env python3
"""Re-run page-isolated optional parser against pinned heterogeneous originals."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA='atlas.heterogeneous_pdf_partial_page_acceptance.v1'


def run(oracle_path:Path,pdf_dir:Path,research_drive_root:Path):
    sys.path.insert(0,str(research_drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates_partial
    oracle=json.loads(oracle_path.read_text(encoding='utf-8'))
    cases=[]
    for o in oracle['cases']:
        source_id=o['id'];p=(pdf_dir/(source_id+'.pdf')).resolve(strict=True)
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest!=o['source_sha256']:
            raise ValueError('heterogeneous original source bytes changed: '+source_id)
        result=extract_candidates_partial(p,o['selected_physical_pages'])
        if result['source_sha256']!=digest:
            raise ValueError('page-isolated source hash mismatch')
        successful=[{'page':child['page'],
            'table_count':len(child['candidate']['tables']),
            'candidate_cells':child['candidate']['cell_count']}
            for child in result['successful_page_candidates']]
        cases.append({'source_id':source_id,'original_sha256':digest,
            'selected_physical_pages':o['selected_physical_pages'],
            'status':result['status'],
            'successful_pages':[child['page'] for child in result['successful_page_candidates']],
            'successful_page_details':successful,
            'failed_pages':result['failed_pages'],
            'successful_page_count':result['successful_page_count'],
            'failed_page_count':result['failed_page_count'],
            'candidate_cell_count':result['total_candidate_cells'],
            'candidate_trust':'UNVERIFIED_PARSER_HYPOTHESES',
            'trusted_csv_export':False})
    return {'schema':SCHEMA,'document_count':len(cases),
        'requested_pages':sum(len(c['selected_physical_pages']) for c in cases),
        'successful_pages':sum(c['successful_page_count'] for c in cases),
        'failed_pages':sum(c['failed_page_count'] for c in cases),
        'documents_with_any_candidate_page':sum(any(x['table_count']>0 for x in c['successful_page_details']) for c in cases),
        'pages_with_table_candidates':sum(x['table_count']>0 for c in cases for x in c['successful_page_details']),
        'documents_with_all_requested_pages':sum(c['failed_page_count']==0 for c in cases),
        'candidate_cells':sum(c['candidate_cell_count'] for c in cases),
        'source_pdf_bytes_committed':False,'numeric_cell_truth_checked':False,
        'auto_publish':False,'auto_register_dataset':False,
        'release_decision':'HOLD_INCOMPLETE_COVERAGE_AND_SEMANTIC_REVIEW',
        'cases':cases}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--oracle',required=True,type=Path)
    parser.add_argument('--pdf-dir',required=True,type=Path)
    parser.add_argument('--research-drive-root',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    a=parser.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite acceptance receipt')
    result=run(a.oracle,a.pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('requested_pages','successful_pages','failed_pages','documents_with_any_candidate_page','documents_with_all_requested_pages','pages_with_table_candidates','candidate_cells')}))
if __name__=='__main__':main()
