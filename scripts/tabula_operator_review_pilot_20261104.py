#!/usr/bin/env python3
"""Original-PDF checked row operator review bundles from fixed Camelot hybrid.

Creates private self-contained HTML preview + source row packet for every
non-error first-page PDF. Commits only sanitized counts and reason codes.
No operator decisions are invented and no trusted rows are produced.
"""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
import sys

SCHEMA='atlas.original_pdf_operator_review_pilot.v1'

def run(manifest:Path,baseline:Path,original_dir:Path,private_out:Path,drive_root:Path):
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_camelot_row_review import produce_packet
    from scripts.cluster_agent.optional_camelot_review_sheet import html_review_sheet,safe_write
    m=json.loads(manifest.read_text())
    b=json.loads(baseline.read_text())
    if (m.get('schema')!='atlas.preregistered_tabula_external_engine_holdout.v1' or
        b.get('schema')!='atlas.tabula_existing_engine_first_pass.v1' or
        len(m['files'])!=12 or len(b['cases'])!=12):
        raise ValueError('fixed original-source cohort differs')
    byname={x['filename']:x for x in b['cases']}
    out=[]
    for spec in m['files']:
        name=spec['filename'];record=byname[name]
        info=record['engines']['hybrid']
        item={'source_file':name,'original_sha256':record['original_sha256'],
              'frozen_primary':'hybrid','first_pass_candidate_rows':info['candidate_rows'],
              'operator_ready_rows':0,'blocked_review_rows':0,
              'reason_codes':{},'review_sheet_created':False,
              'reviewer_actions_submitted':0,'trusted_rows':0}
        original=original_dir/name
        if hashlib.sha256(original.read_bytes()).hexdigest()!=record['original_sha256']:
            raise ValueError('source original bytes changed from frozen result')
        if info['status']!='SOURCE_REVIEW_ONLY':
            item['state']='ENGINE_ERROR_STILL_BLOCKED'
            out.append(item);continue
        candidate_path=original_dir/(name+'.hybrid.private-candidates.json')
        if not candidate_path.exists():
            raise ValueError('frozen source candidate missing')
        candidate=json.loads(candidate_path.read_text())
        packet=produce_packet(original,candidate)
        if packet['candidate_rows_seen']!=info['candidate_rows']:
            raise ValueError('source packet denominator differs from frozen engine')
        item['operator_ready_rows']=packet['source_witnessed_operator_review_rows']
        item['blocked_review_rows']=packet['blocked_rows_count']
        item['source_packet_digest_sha256']=packet['packet_digest_sha256']
        item['reason_codes']=dict(sorted(Counter(reason for r in packet['blocked_rows']
                                              for reason in r['reasons']).items()))
        item['state']='UNREVIEWED_OPERATOR_BUNDLE'
        stem=name.replace('.pdf','')
        private=private_out/(stem+'.source-review')
        safe_write(str(private)+'.packet.json',
                   (json.dumps(packet,ensure_ascii=False,indent=2)+'\n').encode())
        if packet['review_rows']:
            body=html_review_sheet(original,packet,max_preview_rows=85)
            safe_write(str(private)+'.html',body.encode())
            item['review_sheet_created']=True
        print(name,'rows',packet['candidate_rows_seen'],
              'ready',item['operator_ready_rows'],'blocked',item['blocked_review_rows'],
              flush=True)
        out.append(item)
    total=sum(x['operator_ready_rows'] for x in out)
    return {'schema':SCHEMA,'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
      'frozen_first_pass_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
      'original_first_pages_attempted':len(out),
      'original_candidate_rows':sum(x['first_pass_candidate_rows'] for x in out),
      'original_source_witnessed_review_rows':total,
      'blocked_from_operator_review':sum(x['blocked_review_rows'] for x in out),
      'private_review_sheets_created':sum(x['review_sheet_created'] for x in out),
      'original_candidates_failing_engine':sum(x['state']=='ENGINE_ERROR_STILL_BLOCKED' for x in out),
      'operator_actions_submitted':0,'real_independent_reviewers':0,
      'trusted_pdfscope_promotions':0,'trusted_dataset_rows':0,
      'source_pdf_and_review_text_committed':False,
      'auto_publish':False,'auto_register_dataset':False,
      'release_state':'HOLD_OPERATOR_AND_SECOND_REVIEW_MISSING',
      'cases':out}

def main():
    p=argparse.ArgumentParser()
    for key in ('manifest','baseline','original-dir','private-out','research-drive-root','out'):
        p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite original operator cohort receipt')
    r=run(a.manifest,a.baseline,a.original_dir,a.private_out,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as stream:json.dump(r,stream,indent=2);stream.write('\n')
    print(json.dumps({k:r[k] for k in (
        'original_first_pages_attempted','original_candidate_rows',
        'original_source_witnessed_review_rows','blocked_from_operator_review',
        'private_review_sheets_created','original_candidates_failing_engine')}))

if __name__=='__main__':main()
