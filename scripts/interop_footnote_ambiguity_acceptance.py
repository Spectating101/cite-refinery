#!/usr/bin/env python3
"""Replay original Research Drive note-marker heuristic; never auto-link notes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SAMPLES={'apple_fy25q1':(1,180),'apple_fy25q4':(1,180),
         'alphabet_2025q2':(2,450),'alphabet_2025q3':(2,460)}
EXPECTED={'apple_fy25q1':'abstain_ambiguous_reused_marker',
          'apple_fy25q4':'abstain_ambiguous_reused_marker',
          'alphabet_2025q2':'single_printed_definition_requires_manual_link_review',
          'alphabet_2025q3':'single_printed_definition_requires_manual_link_review'}


def run(oracle_path:Path,pdf_dir:Path,research_drive_root:Path) -> dict:
    sys.path.insert(0,str(research_drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_note_audit import audit_note_markers
    oracle=json.loads(oracle_path.read_text())
    cases=[]
    source_by_id={s['id']:s for s in oracle['sources']}
    for source_id,(page,bottom) in SAMPLES.items():
        source=source_by_id[source_id]
        pdf=(pdf_dir/(source_id+'.pdf')).resolve(strict=True)
        raw=pdf.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise ValueError('original financial source PDF SHA mismatch')
        result=audit_note_markers(pdf,source_sha256=source['sha256'],
                    page=page,marker='(1)',reference_bottom=bottom)
        if result['status']!=EXPECTED[source_id]:
            raise ValueError('manual note-marker holdout changed: '+source_id)
        cases.append({'source_id':source_id,'original_source_sha256':source['sha256'],
              'page':page,'marker':'(1)','reference_bottom':bottom,
              'candidate_definition_count':result['candidate_definition_count'],
              'status':result['status'],'semantic_note_link':'NOT_VERIFIED',
              'authority':result['authority']})
    return {'schema':'atlas.real_pdf_footnote_marker_holdout.v1',
      'authority':'REVIEW_ONLY_NO_AUTO_FOOTNOTE_LINK',
      'source_count':len(cases),
      'ambiguous_reused_markers':sum(c['status'].startswith('abstain_ambiguous') for c in cases),
      'single_printed_definition_manual_review':sum(c['status'].startswith('single_printed') for c in cases),
      'semantic_links_verified':0,'automatic_acceptances':0,
      'original_source_pdf_bytes_committed':False,
      'status':'HOLD_FOOTNOTE_SEMANTIC_LINK_UNVERIFIED',
      'interpretation':'leftmost original-page marker heuristic, not interpretation of note scope or footnote text',
      'cases':cases}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite original-source acceptance receipt')
    result=run(a.oracle,a.pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('source_count','ambiguous_reused_markers','single_printed_definition_manual_review','automatic_acceptances')}))

if __name__=='__main__':main()
