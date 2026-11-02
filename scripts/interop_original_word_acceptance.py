#!/usr/bin/env python3
"""Replay Research Drive's real independent PDF-word witness on a pinned oracle.

Imports the existing Research Drive optional parser and source-word verifier;
no new OCR, table detector, dataset registration or autonomous promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA='atlas.original_pdf_word_witness_acceptance.v1'


def run(oracle_path:Path, original_pdfs:Path, drive_root:Path) -> dict:
    root=drive_root.resolve(strict=True)
    sys.path.insert(0,str(root/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates
    from scripts.cluster_agent.optional_pdf_source_check import verify_candidate_words,_canonical_label
    oracle=json.loads(oracle_path.read_text())
    if oracle.get('schema')!='atlas.operator_reviewed_financial_cells.v1':raise ValueError('unrecognized manual oracle')
    if len(oracle['sources'])!=5:raise ValueError('expected five original financial PDFs')
    cases=[]
    for source in oracle['sources']:
        path=(original_pdfs/(source['id']+'.pdf')).resolve(strict=True)
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('original financial PDF has changed')
        candidate=extract_candidates(path,[source['physical_page']])
        scopes=[]
        for target in source['targets']:
            table=candidate['tables'][target['table_index']]
            label=_canonical_label(target['row_label'])
            row_ids=[i for i,row in enumerate(table['rows']) if row and _canonical_label(row[0])==label]
            if len(row_ids)!=1:raise ValueError('manually declared row is missing or ambiguous: '+target['id'])
            header=source['word_witness_header_contract']
            scopes.append({'page':source['physical_page'],'table_index':target['table_index'],'row_index':row_ids[0],
                'label_column':0,'value_column':source['column_map'][target['period_key']]['optional'],
                'expected_label':target['row_label'],'expected_numeric':target['expected_printed_numeric'],
                'header_row':header['row_index'],
                'expected_header':header['period_key_to_printed_text'][target['period_key']]})
        receipt=verify_candidate_words(path,candidate,scopes)
        if receipt['selected']!=len(source['targets']):raise ValueError('source scope mismatch')
        cases.append({'source_id':source['id'],'source_sha256':source['sha256'],
                      'selected':receipt['selected'],'matched':receipt['matched'],'abstained':receipt['abstained'],
                      'cell_checks':[{'source_cell_id':target['id'],'status':result['status'],'checks':result['checks']}
                          for target,result in zip(source['targets'],receipt['results'])]})
    return {'schema':SCHEMA,'date':'2026-11-03',
        'authority':'REVIEW_ONLY_NO_TRUSTED_EXPORT',
        'independent_word_engine':'ResearchDrive.cell_evidence.pdf_words',
        'candidate_engine':'ResearchDrive.optional_pdf_candidates.extract_candidates',
        'original_pdf_files_committed':False,'operator_period_group_reviewed':False,
        'trust_promotion':False,'document_count':len(cases),
        'selected_cells':sum(c['selected'] for c in cases),
        'source_word_matches':sum(c['matched'] for c in cases),
        'abstentions':sum(c['abstained'] for c in cases),
        'cases':cases}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',required=True,type=Path)
    p.add_argument('--pdf-dir',required=True,type=Path)
    p.add_argument('--research-drive-root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args()
    if args.out.exists():raise FileExistsError('immutable receipt already exists')
    receipt=run(args.oracle,args.pdf_dir,args.research_drive_root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as dest:json.dump(receipt,dest,indent=2);dest.write('\n')
    print(json.dumps({'selected':receipt['selected_cells'],'matched':receipt['source_word_matches'],'abstentions':receipt['abstentions']}))
if __name__=='__main__':main()
