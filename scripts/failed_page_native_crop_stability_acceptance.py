#!/usr/bin/env python3
"""Replay five perturbations around each original failed-page native crop.

This is a distinct robustness gate from source word matching, not a claim of
original table completeness, accounting semantics, or trusted publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA='atlas.original_failed_page_crop_robustness.v1'


def run(oracle_path:Path,pilot_path:Path,pdf_dir:Path,drive_root:Path)->dict:
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_native_crop_stability import audit_native_crop_stability
    oracle=json.loads(oracle_path.read_text())
    pilot=json.loads(pilot_path.read_text())
    if oracle.get('schema')!='atlas.operator_cropped_failed_pdf_pages.v1' or pilot.get('schema')!='atlas.real_pdf_operator_pilot.v1':
        raise ValueError('unrecognized pinned operator/source pilot')
    sources={x['id']:x for x in pilot['cases']}
    results=[]
    for item in oracle['table_cases']:
        name=item['source_id']
        original=sources[name]
        path=(pdf_dir/(name+'.pdf')).resolve(strict=True)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=original['source_sha256']:
            raise ValueError('original source PDF differs from initial heterogeneous benchmark')
        if item['physical_page'] not in original['selected_physical_pages']:
            raise ValueError('physical page outside pinned benchmark scope')
        r=audit_native_crop_stability(path,item['physical_page'],item['crop_bbox_pdf'],item['profile'],item['selected'])
        results.append({'source_id':name,'original_sha256':original['source_sha256'],
            'physical_page':item['physical_page'],
            'original_img2table_error_code':item['strict_img2table_error_code'],
            'operator_crop_bbox_pdf':item['crop_bbox_pdf'],
            'operator_profile':item['profile'],
            'selected_original_source_cells':r['selected_original_source_cells'],
            'baseline_match_count':r['baseline_match_count'],
            'perturbation_count':r['perturbation_count'],
            'successful_perturbations':r['successful_perturbations'],
            'failed_or_abstained_perturbations':r['failed_or_abstained_perturbations'],
            'all_tested_crops_match':r['all_tested_crops_match'],
            'review_state':r['review_state'],
            'source_table_completeness_verified':False,
            'trusted_source_values':0,'trials':r['trials']})
    if len(results)!=2:raise ValueError('the two pinned original table-containing failures are required')
    return {'schema':SCHEMA,'authority':'READ_ONLY_CROP_ROBUSTNESS_ONLY_NOT_DATASET_EVIDENCE',
        'tested_original_pages':len(results),
        'baseline_source_word_matches':sum(x['baseline_match_count'] for x in results),
        'total_boundary_perturbations':sum(x['perturbation_count'] for x in results),
        'all_source_words_matched_perturbations':sum(x['successful_perturbations'] for x in results),
        'failed_or_abstained_perturbations':sum(x['failed_or_abstained_perturbations'] for x in results),
        'crop_sensitive_pages':sum(not x['all_tested_crops_match'] for x in results),
        'robust_under_tested_crops_pages':sum(x['all_tested_crops_match'] for x in results),
        'perturbation_offsets_pdf_points':[-5,-2,0,2,5],
        'source_pdf_bytes_committed':False,'independent_human_review':False,
        'verified_source_table_completeness':False,'trusted_pdfscope_promotions':0,
        'auto_publish':False,'auto_register_dataset':False,
        'decision':'HOLD_CROP_SENSITIVITY_AND_UNREVIEWED_SEMANTICS',
        'cases':results}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',required=True,type=Path)
    p.add_argument('--pilot',required=True,type=Path)
    p.add_argument('--pdf-dir',required=True,type=Path)
    p.add_argument('--research-drive-root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('refusing to overwrite original crop robustness evidence')
    result=run(a.oracle,a.pilot,a.pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({key:result[key] for key in ('tested_original_pages','baseline_source_word_matches','total_boundary_perturbations','all_source_words_matched_perturbations','crop_sensitive_pages','robust_under_tested_crops_pages')}))
if __name__=='__main__':main()
