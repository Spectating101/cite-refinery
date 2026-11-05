#!/usr/bin/env python3
"""Execute immutable prospective PDF holdout, retaining all failures.

Never edits parser thresholds or selects fixtures. Original PDFs and candidate
row text stay private. Only metadata and aggregate outcomes may enter Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

SCHEMA='atlas.locked_external_pdf_first_page_scan.v1'
LOCKED_ENGINE_SHA='2f5bd7f'


def private_write(path:Path,data:bytes):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as output:output.write(data)


def run(manifest_path:Path,drive_root:Path,private_dir:Path)->dict:
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_blind_scan import scan_first_page_ruled_rows
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='atlas.preregistered_untouched_pdf_holdout.v1' or len(manifest['selected_source_files'])!=16:
        raise ValueError('locked evaluation manifest invalid')
    import subprocess
    sha=subprocess.check_output(['git','-C',str(drive_root),'rev-parse','HEAD'],text=True).strip()
    if not sha.startswith(LOCKED_ENGINE_SHA):
        raise ValueError('cannot change frozen source scanner in locked evaluation')
    out=[]
    for row in manifest['selected_source_files']:
        fname=row['filename']
        pdf=(private_dir/fname).resolve()
        entry={'filename':fname,'stratum':row['predeclared_stratum'],
               'upstream_committed_url':row['original_source_url'],
               'physical_page':1,'original_sha256':None,
               'original_size_bytes':None,
               'scan_status':'NOT_EXECUTED',
               'source_table_regions_proposed':0,'source_row_regions_proposed':0,
               'reference_row_annotation_available':False,
               'externally_verified_true_positive_rows':None,
               'externally_verified_false_positive_rows':None,
               'externally_verified_false_negative_rows':None,
               'row_precision':None,'row_recall':None,
               'trusted_published_rows':0}
        try:
            if pdf.exists():
                raw=pdf.read_bytes()
            else:
                request=urllib.request.Request(row['original_source_url'],
                    headers={'User-Agent':'spectating101-locked-holdout-evaluation'})
                with urllib.request.urlopen(request,timeout=30) as f:raw=f.read(8*1024*1024+1)
                if not raw.startswith(b'%PDF-') or len(raw)>8*1024*1024:
                    raise ValueError('downloaded upstream file not bounded original PDF')
                private_write(pdf,raw)
            entry['original_sha256']=hashlib.sha256(raw).hexdigest()
            entry['original_size_bytes']=len(raw)
            prediction=scan_first_page_ruled_rows(pdf,source_sha256=entry['original_sha256'],page=1)
            entry['source_table_regions_proposed']=prediction['candidate_table_regions']
            entry['source_row_regions_proposed']=prediction['candidate_row_regions']
            entry['scan_status']='ORIGINAL_SOURCE_ROW_PROPOSALS_UNREVIEWED' if prediction['candidate_row_regions'] else 'ABSTAIN_NO_SOURCE_RULED_ROWS'
            private_write(private_dir/(fname+'.private-row-proposals.json'),
                (json.dumps(prediction,ensure_ascii=False,indent=2)+'\n').encode())
        except Exception as ex:
            entry['scan_status']='ERROR_NO_SOURCE_AUTHORITY'
            entry['error_type']=type(ex).__name__
        out.append(entry)
        print(fname,entry['scan_status'],'rows',entry['source_row_regions_proposed'],flush=True)
    return {'schema':SCHEMA,
        'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'locked_engine_commit':sha,
        'upstream_git_commit':manifest['upstream_commit'],
        'intent_to_test_pages':16,'attempted_pages':len(out),
        'source_pages_with_row_proposals':sum(x['source_row_regions_proposed']>0 for x in out),
        'source_pages_abstained':sum(x['scan_status']=='ABSTAIN_NO_SOURCE_RULED_ROWS' for x in out),
        'source_pages_errors':sum(x['scan_status']=='ERROR_NO_SOURCE_AUTHORITY' for x in out),
        'total_source_row_proposals':sum(x['source_row_regions_proposed'] for x in out),
        'independently_scored_row_pages':0,
        'precision_unknown_without_independent_oracle':True,
        'recall_unknown_without_independent_oracle':True,
        'all_failures_kept_in_denominator':True,
        'external_reviewers_accepted':0,
        'original_pdf_bytes_committed':False,
        'original_pdf_full_row_proposals_committed':False,
        'trusted_pdfscope_promotions':0,
        'auto_publish':False,'auto_register_dataset':False,
        'decision':'HOLD_EXTERNAL_ORACLE_ROW_TRUTH_REQUIRED',
        'cases':out}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True,type=Path)
    ap.add_argument('--research-drive-root',required=True,type=Path)
    ap.add_argument('--private-dir',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    if a.out.exists():raise FileExistsError('locked evaluation receipt already exists')
    result=run(a.manifest,a.research_drive_root,a.private_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in (
        'intent_to_test_pages','attempted_pages','source_pages_with_row_proposals',
        'source_pages_abstained','source_pages_errors','total_source_row_proposals')}))


if __name__=='__main__':main()
