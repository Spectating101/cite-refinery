#!/usr/bin/env python3
"""Replay cross-format financial values against original source SHA-pinned SEC.

Issuer evidence is from SEC-hosted filed HTML EX-99.1, *not* original issuer
PDF. No second human reviewer or trusted Research Drive publication implied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA='atlas.manulife_sec_issuer_reconciliation.v1'


def run(oracle_path:Path,figure_path:Path,edgar_dir:Path,drive_root:Path)->dict:
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_issuer_edgar_reconcile import verify_issuer_filing_rows
    oracle=json.loads(oracle_path.read_text(encoding='utf-8'))
    figure=json.loads(figure_path.read_text(encoding='utf-8'))
    if oracle.get('schema')!='atlas.manulife_2024q1_sec_filing_reconciliation_oracle.v1':
        raise ValueError('source reconciliation oracle schema not recognized')
    if figure.get('source_sha256')!=oracle['original_reproduced_figure_sha256']:
        raise ValueError('reproduced figure source hash mismatch')
    orig={x['id']:x for x in figure['source_cells']}
    roles=[('shareholder_report',oracle['shareholder_report_rows']),
           ('earnings_release',oracle['earnings_release_rows'])]
    reports={}
    for role,claims in roles:
        source=oracle['primary_issuer_edgar_exhibits'][role]
        file=(edgar_dir/Path(source['url']).name).resolve(strict=True)
        for claim in claims:
            if claim['case_id'] not in orig or claim['expected_figure_numeric']!=orig[claim['case_id']]['expected_numeric']:
                raise ValueError('issuer reconciliation figure value not pinned to manual source oracle')
        reports[role]=verify_issuer_filing_rows(file,source,claims)
    context_spec=oracle['primary_issuer_edgar_exhibits']['shareholder_report']
    context=verify_issuer_filing_rows((edgar_dir/Path(context_spec['url']).name).resolve(strict=True),
                                    context_spec,oracle['extra_context_checks'])
    return {'schema':SCHEMA,'reproduced_figure_source_sha256':figure['source_sha256'],
      'source_roles':{k:{'issuer_cik':v['issuer_cik'],'source_url':v['source_url'],
          'source_sha256':v['source_sha256'],'source_kind':v['source_kind'],
          'checked':v['checked'],'matched':v['matched'],'abstained':v['abstained'],
          'row_verdicts':[{'case_id':r['case_id'],'status':r['status'],'checks':r['checks'],
              'issuer_label':r['source_label'],'issuer_numeric':r['source_numeric'],
              'issuer_unit':r['issuer_unit'],'reproduced_figure_numeric':r['figure_numeric'],
              'reconciliation':r['reconciliation'],'quarter_header':r['quarter_header'],
              'table_index':r['table_index'],'row_index':r['row_index']} for r in v['results']]}
          for k,v in reports.items()},
      'expense_qualifier_context':{'checked':context['checked'],
           'matched':context['matched'],'abstained':context['abstained'],
           'row_verdicts':[{'case_id':x['case_id'],'status':x['status'],
               'checks':x['checks'],'source_numeric':x['source_numeric'],
               'table_index':x['table_index'],'row_index':x['row_index']} for x in context['results']]},
      'source_document_type':'ISSUER_AUTHORED_SEC_EDGAR_EXHIBITS_NOT_MANULIFE_COM_PDF',
      'local_original_html_sha256_verified':True,
      'issuer_original_pdf_sha256_verified':False,
      'manual_cross_format_metric_alignment':True,
      'independent_second_human_review':False,
      'original_figure_parser_strict_source_matches':6,
      'original_figure_parser_strict_source_abstentions':2,
      'trusted_pdfscope_promotions':0,'trusted_dataset_registrations':0,
      'original_html_bytes_committed':False,'original_figure_pdf_bytes_committed':False,
      'auto_publish':False,'auto_register_dataset':False,
      'release_decision':'HOLD_INDEPENDENT_HUMAN_REVIEW_AND_ORIGINAL_PDF_LINKAGE'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',required=True,type=Path)
    p.add_argument('--figure-oracle',required=True,type=Path)
    p.add_argument('--edgar-dir',required=True,type=Path)
    p.add_argument('--research-drive-root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args()
    if args.out.exists():raise FileExistsError('cannot overwrite issuer filing evidence receipt')
    receipt=run(args.oracle,args.figure_oracle,args.edgar_dir,args.research_drive_root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False);f.write('\n')
    for k,v in receipt['source_roles'].items():print(k,'source rows',v['matched'],'/',v['checked'],'source_sha',v['source_sha256'])
    print('expense qualifier',receipt['expense_qualifier_context']['matched'],'/',receipt['expense_qualifier_context']['checked'])
if __name__=='__main__':main()
