#!/usr/bin/env python3
"""Replay existing Research Drive source-word AND period-context witnesses.

All sources/hash pins and header anchor boxes were manually scoped from the
original PDF. No parser is implemented here; no data is published or approved.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys


def run(oracle_path:Path,pdf_dir:Path,drive_root:Path, *, isolated=False) -> dict:
    root=drive_root.resolve(strict=True)
    sys.path.insert(0,str(root/'drive'))
    from scripts.cluster_agent.optional_pdf_candidates import extract_candidates
    from scripts.cluster_agent.optional_pdf_source_check import _canonical_label
    from scripts.cluster_agent.optional_pdf_period_check import verify_candidate_period_context
    if isolated:
        from scripts.cluster_agent.optional_pdf_offline_check import check_period_context_offline
    oracle=json.loads(oracle_path.read_text())
    if oracle.get('schema')!='atlas.operator_reviewed_financial_cells.v1' or len(oracle.get('sources',[]))!=5:
        raise ValueError('invalid or insufficient pinned operator corpus')
    cases=[]
    for src in oracle['sources']:
        pdf=(pdf_dir/(src['id']+'.pdf')).resolve(strict=True)
        if hashlib.sha256(pdf.read_bytes()).hexdigest()!=src['sha256']:
            raise ValueError('original source bytes differ from operator oracle')
        candidate=extract_candidates(pdf,[src['physical_page']])
        declarations=[]
        for target in src['targets']:
            table_index=target['table_index']
            table=candidate['tables'][table_index]
            matching=[i for i,row in enumerate(table['rows']) if row and
                      _canonical_label(row[0])==_canonical_label(target['row_label'])]
            if len(matching)!=1:
                raise ValueError('target row ambiguous or missing: '+target['id'])
            keys=src['word_witness_header_contract']
            period_key=target['period_key']
            period=src['period_anchor_contracts'][str(table_index)][period_key]
            cell={'page':src['physical_page'],'table_index':table_index,
                  'row_index':matching[0],'label_column':0,
                  'value_column':src['column_map'][period_key]['optional'],
                  'expected_label':target['row_label'],
                  'expected_numeric':target['expected_printed_numeric'],
                  'header_row':keys['row_index'],
                  'expected_header':keys['period_key_to_printed_text'][period_key]}
            # The second Alphabet table has its own header, same year.
            declarations.append({'cell':cell,**period})
        r=verify_candidate_period_context(pdf,candidate,declarations)
        independent=None
        if isolated:
            independent=check_period_context_offline(pdf,candidate,declarations)
            if (independent['matched']!=r['matched'] or independent['abstained']!=r['abstained']
                    or independent['original_pdf_sha256']!=src['sha256'] or independent['network']!='disabled'):
                raise ValueError('isolated source-period check disagreed with local replay')
        cases.append({'source_id':src['id'],'original_sha256':src['sha256'],
            'checked_cells':r['checked_cells'],'matched':r['matched'],
            'abstained':r['abstained'],
            'isolated':({'runtime':independent['checker_runtime'],
                         'matched':independent['matched'],'abstained':independent['abstained'],
                         'passed':independent['passed'], 'network':independent['network'],
                         'authority':independent['authority']} if independent else None),
            'cell_verdicts':[{'cell_id':target['id'],'status':result['status'],
              'kind':result['kind'],'checks':result['checks']}
             for target,result in zip(src['targets'],r['results'])]})
    return {'schema':'atlas.period_context_original_source_acceptance.v1',
      'authority':'REVIEW_ONLY_NOT_TRUSTED_CSV',
      'original_pdfs_committed':False,
      'manual_geometry_scope':True,'isolated_replay':bool(isolated),
      'operator_double_reviewed':False,
      'auto_publish':False,'auto_register_dataset':False,
      'semantic_claim':'explicit group/date/year anchors, NOT full accounting interpretation',
      'document_count':len(cases),'checked_cells':sum(c['checked_cells'] for c in cases),
      'matched':sum(c['matched'] for c in cases),
      'abstained':sum(c['abstained'] for c in cases),
      'isolated_matched':sum((c['isolated'] or {}).get('matched',0) for c in cases),
      'cases':cases}

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--oracle',type=Path,required=True)
    cli.add_argument('--pdf-dir',type=Path,required=True)
    cli.add_argument('--drive-root',type=Path,required=True)
    cli.add_argument('--out',type=Path,required=True)
    cli.add_argument('--isolated',action='store_true',help='also run the native Research Drive bwrap/libseccomp witness')
    args=cli.parse_args()
    if args.out.exists():raise FileExistsError('immutable source receipt already exists')
    result=run(args.oracle,args.pdf_dir,args.drive_root,isolated=args.isolated)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'checked_cells':result['checked_cells'],'matched':result['matched'],
                      'abstained':result['abstained']}))
if __name__=='__main__':main()
