#!/usr/bin/env python3
"""Score frozen Camelot output vs earlier-authored Tabula CSV references.

Never choose better per-document engine after seeing gold. Do not infer
ground truth from Camelot or original pdfplumber word matches.
"""
from __future__ import annotations
from collections import Counter
import argparse,csv,hashlib,json,unicodedata
from pathlib import Path

SCHEMA='atlas.tabula_existing_engine_csv_reference_score.v1'
FLAVORS=('hybrid','network','lattice')


def norm(s):
    return ' '.join(unicodedata.normalize('NFKC',str(s)).casefold().split())


def parse_gold(file):
    with file.open(encoding='utf-8-sig',newline='') as stream:
        return [norm(' '.join(x for x in row if x)) for row in csv.reader(stream)]


def run(manifest_path,baseline_path,private):
    manifest=json.loads(manifest_path.read_text())
    baseline=json.loads(baseline_path.read_text())
    if (manifest['schema']!='atlas.preregistered_tabula_external_engine_holdout.v1'
        or baseline['schema']!='atlas.tabula_existing_engine_first_pass.v1'
        or len(baseline['cases'])!=12
        or baseline['frozen_research_drive_commit'][:7]!='9b502d8'):
        raise ValueError('unfrozen or incomplete original engine baseline')
    records={x['filename']:x for x in baseline['cases']}
    cases=[]
    totals={f:Counter() for f in FLAVORS}
    for f in manifest['files']:
        name=f['filename'];row=records[name]
        e={'filename':name,'original_sha256':row['original_sha256'],
           'original_pdf_pages':row['original_pdf_pages'],
           'reference_csv_sha256':None,'reference_status':'NO_COMPARABLE_REFERENCE',
           'engine_scores':{}}
        csvfile=private/(name+'.reference.csv')
        if f['independent_published_csv_url'] and csvfile.exists():
            raw=csvfile.read_bytes();e['reference_csv_sha256']=hashlib.sha256(raw).hexdigest()
            if row['original_pdf_pages']!=1:
                e['reference_status']='UNSCORED_REFERENCE_COVERS_MULTIPAGE_DOCUMENT'
            else:
                gold=parse_gold(csvfile)
                if not gold:
                    e['reference_status']='EMPTY_OR_UNSUPPORTED_REFERENCE'
                else:
                    e['reference_status']='REFERENCE_SCORABLE_SINGLE_ORIGINAL_PAGE'
                    e['expected_rows_in_csv']=len(gold)
                    want=Counter(gold)
                    for flavor in FLAVORS:
                        status=row['engines'][flavor]['status']
                        privatecandidate=private/(name+'.'+flavor+'.private-candidates.json')
                        rows=[];word_verified=[]
                        if status=='SOURCE_REVIEW_ONLY' and privatecandidate.exists():
                            payload=json.loads(privatecandidate.read_text())
                            if payload['original_source_sha256']!=row['original_sha256']:
                                raise ValueError('original source candidates do not match baseline')
                            for table in payload['tables']:
                                for r in table['rows']:
                                    rows.append(norm(r['camelot_row_text_unverified']))
                                    word_verified.append(r['all_cells_literal_source_matched'])
                        elif status=='SOURCE_REVIEW_ONLY' and row['engines'][flavor]['candidate_rows']!=0:
                            raise ValueError('private original candidate missing')
                        if len(rows)!=row['engines'][flavor]['candidate_rows']:
                            raise ValueError('candidate denominator changed after first pass')
                        counts=Counter(rows)
                        tp=sum(min(n,want[k]) for k,n in counts.items())
                        fp=len(rows)-tp;fn=len(gold)-tp
                        witnessed=Counter(r for r,flag in zip(rows,word_verified) if flag)
                        evidence_tp=sum(min(n,want[k]) for k,n in witnessed.items())
                        totals[flavor].update({'tp':tp,'fp':fp,'fn':fn,
                            'proposed':len(rows),'source_and_csv_tp':evidence_tp,
                            'source_witnessed_proposals':sum(word_verified)})
                        e['engine_scores'][flavor]={'expected_csv_rows':len(gold),
                            'proposed_rows':len(rows),'exact_full_row_tp':tp,
                            'unmatched_proposed_fp':fp,'missed_expected_fn':fn,
                            'matched_rows_with_original_word_witness':evidence_tp}
        cases.append(e)
    summaries={}
    for flavor,v in totals.items():
        summaries[flavor]={'scored_pages':sum(c['reference_status']=='REFERENCE_SCORABLE_SINGLE_ORIGINAL_PAGE' for c in cases),
          'exact_full_row_tp':v['tp'],
          'source_and_csv_exact_row_matches':v['source_and_csv_tp'],
          'source_witnessed_candidate_rows':v['source_witnessed_proposals'],
          'unmatched_proposed_fp':v['fp'],
          'missed_expected_fn':v['fn'],'proposed_rows_on_scored_pages':v['proposed'],
          'conditional_precision':v['tp']/(v['tp']+v['fp']) if v['tp']+v['fp'] else None,
          'conditional_recall':v['tp']/(v['tp']+v['fn']) if v['tp']+v['fn'] else None}
    return {'schema':SCHEMA,
      'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
      'first_pass_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
      'scored_rows_policy':'published_Tabula_CSV_literal_NFKC_casefold_whitespace_multiset',
      'total_first_pages':12,
      'pages_with_comparable_published_csv':summaries['hybrid']['scored_pages'],
      'pages_without_comparable_published_csv':12-summaries['hybrid']['scored_pages'],
      'frozen_primary':'hybrid','diagnostic_not_selected':['network','lattice'],
      'primary_summary':summaries['hybrid'],'diagnostic_summaries':{
          'network':summaries['network'],'lattice':summaries['lattice']},
      'independent_human_adjudication':False,
      'original_PDF_source_word_match_is_not_row_truth':True,
      'trusted_rows':0,'source_files_committed':False,
      'auto_publish':False,'auto_register_dataset':False,
      'decision':'HOLD_NO_TRUSTED_PUBLICATION',
      'cases':cases}


def main():
    p=argparse.ArgumentParser()
    for k in ('manifest','baseline','private-dir','out'):
        p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite locked first-pass score')
    result=run(a.manifest,a.baseline,a.private_dir)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'scored':result['pages_with_comparable_published_csv'],
        'primary':result['primary_summary'],
        'diagnostic':result['diagnostic_summaries']}))


if __name__=='__main__':main()
