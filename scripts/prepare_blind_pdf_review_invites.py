#!/usr/bin/env python3
"""Two blank, separate operator source-review invitations per original PDF.

ISSUES NO REVIEW, obtains NO actual independent-human testimony, and records
no source-semantic approvals. Reviewer private session packets stay off Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

SCHEMA='atlas.blind_original_pdf_review_invitations.v1'


def run(oracle_path:Path,pdf_dir:Path,drive_root:Path,private_output_dir:Path):
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates
    from scripts.cluster_agent.optional_pdf_blind_review import issue_blind_packet
    from scripts.cluster_agent.optional_pdf_source_check import _canonical_label
    oracle=json.loads(oracle_path.read_text())
    if oracle.get('schema')!='atlas.operator_reviewed_financial_cells.v1':
        raise ValueError('wrong original source oracle')
    private_output_dir=private_output_dir.expanduser().resolve()
    if any((parent/'.git').exists() for parent in (private_output_dir,*private_output_dir.parents)):
        raise ValueError('private reviewer packages cannot be created in public Git')
    private_output_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    reports=[]
    for source in oracle['sources']:
        if source['id'] not in ('apple_fy25q1','apple_fy25q4'):
            continue
        path=(pdf_dir/(source['id']+'.pdf')).resolve(strict=True)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('original financial PDF digest mismatch: '+source['id'])
        candidate=extract_candidates(path,[source['physical_page']])
        target=next(t for t in source['targets'] if t['row_label']=='Total net sales (1)' and t['period_key']=='current_quarter')
        index=target['table_index'];table=candidate['tables'][index]
        matching=[i for i,row in enumerate(table['rows']) if row and
            _canonical_label(row[0])==_canonical_label(target['row_label'])]
        if len(matching)!=1:raise ValueError('ambiguous original source review row')
        scope={'page':source['physical_page'],'table_index':index,'row_index':matching[0],
               'label_column':0,'value_column':source['column_map'][target['period_key']]['optional']}
        packets=[]
        for slot in ('A','B'):
            packet=issue_blind_packet(path,candidate,[scope])
            destination=private_output_dir/(source['id']+'-blank-session-'+slot+'.json')
            fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as out:
                json.dump(packet,out,indent=2,ensure_ascii=False);out.write('\n')
            packets.append(packet)
        if (packets[0]['case_set_sha256']!=packets[1]['case_set_sha256'] or
            packets[0]['review_session_id']==packets[1]['review_session_id'] or
            packets[0]['contains_prior_reviewer_decisions'] or
            packets[1]['contains_prior_reviewer_decisions']):
            raise ValueError('blind source-review invitation isolation failed')
        reports.append({'source_id':source['id'],'original_source_sha256':source['sha256'],
            'official_publisher_url':source['url'],'source_physical_page':source['physical_page'],
            'source_cell_id':target['id'],'scope_case_id':packets[0]['cases'][0]['case_id'],
            'case_set_sha256':packets[0]['case_set_sha256'],
            'empty_review_invitations_created':2,
            'private_review_session_ids_committed':False,
            'operator_annotations_submitted':0,'second_human_review_completed':False,
            'source_word_semantic_links_approved':0,
            'automation_authority':False})
    return {'schema':SCHEMA,'source_count':len(reports),
        'invitation_count':sum(r['empty_review_invitations_created'] for r in reports),
        'actual_independent_human_reviewer_count':0,
        'source_semantics_independently_adjudicated':0,
        'source_pdf_bytes_committed':False,
        'review_session_secrets_committed':False,
        'auto_publish':False,'auto_register_dataset':False,
        'status':'INVITATIONS_PREPARED_AWAITING_SEPARATE_HUMAN_REVIEWS',
        'cases':reports}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--private-packet-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('blind review readiness receipt already exists')
    report=run(a.oracle,a.pdf_dir,a.research_drive_root,a.private_packet_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as out:
        json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'source_count':report['source_count'],
        'blank_invitations':report['invitation_count'],
        'actual_reviewers':report['actual_independent_human_reviewer_count'],
        'approval':report['source_semantics_independently_adjudicated']}))
if __name__=='__main__':main()
