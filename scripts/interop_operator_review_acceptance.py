#!/usr/bin/env python3
"""Replay Research Drive's source-backed operator review, never authorize a link.

The same original PDF can witness both possible interpretations of a reused
printed note marker; this acceptance gate is deliberately non-semantic.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA='atlas.operator_assisted_source_review_acceptance.v1'
TITLE='CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)'
UNITS='(In millions, except number of shares, which are reflected in thousands, and per-share amounts)'


def run(oracle_path:Path,pdf_dir:Path,research_drive_root:Path) -> dict:
    sys.path.insert(0,str(research_drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates
    from scripts.cluster_agent.optional_pdf_operator_review import review_operator_annotations
    from scripts.cluster_agent.optional_pdf_source_check import _canonical_label
    oracle=json.loads(oracle_path.read_text(encoding='utf-8'))
    if oracle.get('schema')!='atlas.operator_reviewed_financial_cells.v1':
        raise ValueError('unexpected operator oracle')
    cases=[]
    for source in oracle['sources']:
        name=source['id']
        if name not in {'apple_fy25q1','apple_fy25q4'}:
            continue
        pdf=(pdf_dir/(name+'.pdf')).resolve(strict=True)
        if hashlib.sha256(pdf.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('original publisher PDF bytes differ from pinned oracle')
        candidate=extract_candidates(pdf,[source['physical_page']])
        contexts=[{'role':'statement_title','expected':TITLE,'bbox_pdf':[140,60,473,75]},
                  {'role':'unit_disclosure','expected':UNITS,'bbox_pdf':[110,70,502,84]}]
        def annotation(target,footnote):
            index=target['table_index']
            tab=candidate['tables'][index]
            matches=[i for i,row in enumerate(tab['rows']) if row and
                 _canonical_label(row[0])==_canonical_label(target['row_label'])]
            if len(matches)!=1:
                raise ValueError('manual row label absent or ambiguous: '+target['id'])
            key=target['period_key']
            header=source['word_witness_header_contract']
            period={'cell':{'page':source['physical_page'],'table_index':index,
                 'row_index':matches[0],'label_column':0,
                 'value_column':source['column_map'][key]['optional'],
                 'expected_label':target['row_label'],
                 'expected_numeric':target['expected_printed_numeric'],
                 'header_row':header['row_index'],
                 'expected_header':header['period_key_to_printed_text'][key]},
                 **source['period_anchor_contracts'][str(index)][key]}
            return {'period':period,'context':contexts,'footnote':footnote}
        target=next(t for t in source['targets'] if t['row_label']=='Total net sales (1)'
                    and t['period_key']=='current_quarter')
        control=next(t for t in source['targets'] if t['row_label']=='Net income'
                    and t['period_key']=='current_quarter')
        cases_to_run=[('unresolved',target,{'mode':'unresolved','marker':'(1)',
              'reference_bottom':180,'definition_bbox_pdf':None,'expected_definition':None})]
        for alias,bbox,text in [
             ('segment_definition', [48,533,206,550], '(1) Net sales by reportable segment:'),
             ('category_definition',[48,647,175,664], '(1) Net sales by category:')]:
            cases_to_run.append((alias,target,{'mode':'selected_definition',
              'marker':'(1)','reference_bottom':180,
              'definition_bbox_pdf':bbox,'expected_definition':text}))
        cases_to_run.append(('unfootnoted_control',control,{'mode':'none','marker':None,
             'reference_bottom':None,'definition_bbox_pdf':None,'expected_definition':None}))
        for alias,entry,note in cases_to_run:
            original=review_operator_annotations(pdf,candidate,[annotation(entry,note)])
            outcome=original['results'][0]
            cases.append({'source_id':name,'original_sha256':source['sha256'],
                'case':alias,'target_id':entry['id'],
                'operator_decision':note['mode'],
                'candidate_note_definitions':outcome['footnote']['candidate_definition_count'],
                'original_statement_header_witnesses':sum(c['status']=='source_heading_witness_match'
                    for c in outcome['statement_context']),
                'source_period_status':outcome['period']['status'],
                'original_definition_witnessed':outcome['footnote']['source_definition_witnessed'],
                'review_state':outcome['review_state'],
                'independent_second_review_completed':False,
                'trusted_semantic_link':outcome['trusted_semantic_link']})
    if len(cases)!=8:raise ValueError('expected four reviews for each of two pinned Apple documents')
    return {'schema':SCHEMA,'authority':'REVIEW_ONLY_ORIGINAL_SOURCE_OPERATOR_ASSERTIONS',
        'documents':2,'annotations':len(cases),
        'unresolved_source_note_choices':sum(c['review_state']=='unresolved_note_selection' for c in cases),
        'source_witnesses_recorded':sum(c['review_state']=='operator_source_witnesses_recorded_second_review_pending' for c in cases),
        'conflicting_alternative_source_witnesses':4,
        'independent_second_reviewer':False,
        'semantic_note_links_independently_approved':0,
        'trusted_pdfscope_promotions':0,
        'automatic_publishing':False,'automatic_dataset_registration':False,
        'publisher_pdf_bytes_committed':False,
        'decision':'HOLD_SECOND_REVIEW_REQUIRED',
        'cases':cases}


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite source-review acceptance receipt')
    result=run(a.oracle,a.pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,ensure_ascii=False);handle.write('\n')
    print(json.dumps({'documents':result['documents'],'annotations':result['annotations'],
        'source_witnesses':result['source_witnesses_recorded'],
        'unresolved':result['unresolved_source_note_choices'],
        'independently_approved_links':result['semantic_note_links_independently_approved']}))

if __name__=='__main__':main()
