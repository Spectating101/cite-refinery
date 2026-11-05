#!/usr/bin/env python3
"""Old frozen ruled-only scanner on exact SAME 12-page Tabula cohort.

Post-hoc same-sample diagnostic, not another untouched prospective holdout.
"""
from __future__ import annotations
from collections import Counter
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from score_tabula_multi_engine_20261104 import norm,parse_gold

SCHEMA='atlas.tabula_same_cohort_frozen_ruled_diagnostic.v1'

def run(manifest,source_base,private,engine_root):
    sys.path.insert(0,str(engine_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_blind_scan import scan_first_page_ruled_rows
    rel='drive/scripts/cluster_agent/optional_pdf_blind_scan.py'
    before=subprocess.check_output(['git','-C',str(engine_root),'show','2f5bd7f:'+rel])
    now=(engine_root/rel).read_bytes()
    if before!=now:raise ValueError('old frozen ruled-only scanner was modified')
    m=json.loads(manifest.read_text())
    b=json.loads(source_base.read_text())
    base={c['filename']:c for c in b['cases']}
    if len(m['files'])!=12 or len(base)!=12:raise ValueError('cohort differs')
    out=[];totals=Counter()
    for case in m['files']:
        name=case['filename'];pin=base[name]['original_sha256']
        file=private/name
        if hashlib.sha256(file.read_bytes()).hexdigest()!=pin:
            raise ValueError('original source bytes differ between engine comparisons')
        status='ABSTAIN_NO_RULES';pred=[]
        try:
            r=scan_first_page_ruled_rows(file,source_sha256=pin,page=1)
            pred=[norm(row['unverified_source_row_text']) for t in r['tables'] for row in t['rows']]
            if pred:status='SOURCE_ROW_PROPOSALS_UNVERIFIED'
        except Exception as exc:
            status='SCANNER_ERROR_'+type(exc).__name__
        entry={'filename':name,'source_sha256':pin,
            'source_status':status,'proposed_rows':len(pred),
            'reference_status':'NO_COMPARABLE_CSV'}
        csvpath=private/(name+'.reference.csv')
        if case['independent_published_csv_url'] and csvpath.exists():
            if base[name]['original_pdf_pages']==1:
                gold=parse_gold(csvpath)
                if gold:
                    want=Counter(gold);got=Counter(pred)
                    tp=sum(min(count,want[row]) for row,count in got.items())
                    fp=len(pred)-tp;fn=len(gold)-tp
                    entry['reference_status']='ONE_PAGE_REFERENCE'
                    entry.update({'expected':len(gold),'tp':tp,'fp':fp,'fn':fn})
                    totals.update({'tp':tp,'fp':fp,'fn':fn,'scored_pages':1})
            else:entry['reference_status']='MULTIPAGE_CSV_NOT_COMPARABLE'
        out.append(entry)
    return {'schema':SCHEMA,'comparison_kind':'POSTHOC_FROZEN_OLD_SCANNER_SAME_NEW_COHORT',
        'old_engine_commit':'2f5bd7f',
        'new_engine_first_pass_sha256':hashlib.sha256(source_base.read_bytes()).hexdigest(),
        'same_original_pdf_sha_verified':True,
        'attempted_pages':len(out),
        'pages_with_ruled_row_proposals':sum(x['proposed_rows']>0 for x in out),
        'row_proposals_total':sum(x['proposed_rows'] for x in out),
        'scored_pages':totals['scored_pages'],
        'true_positive_rows':totals['tp'],'false_positive_rows':totals['fp'],
        'false_negative_rows':totals['fn'],
        'conditional_precision':totals['tp']/(totals['tp']+totals['fp']) if totals['tp']+totals['fp'] else None,
        'conditional_recall':totals['tp']/(totals['tp']+totals['fn']) if totals['tp']+totals['fn'] else None,
        'not_originally_preregistered_as_primary':True,
        'publisher_truth_not_adjudicated':True,
        'trusted_rows':0,'auto_publish':False,'auto_register_dataset':False,
        'cases':out}

def main():
    p=argparse.ArgumentParser()
    for key in ('manifest','first-pass','private-dir','research-drive-root','out'):
        p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('immutable comparison already exists')
    d=run(a.manifest,a.first_pass,a.private_dir,a.research_drive_root)
    with a.out.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
    print(json.dumps({k:d[k] for k in (
       'attempted_pages','pages_with_ruled_row_proposals','row_proposals_total',
       'scored_pages','true_positive_rows','false_positive_rows','false_negative_rows',
       'conditional_precision','conditional_recall')}))
if __name__=='__main__':main()
