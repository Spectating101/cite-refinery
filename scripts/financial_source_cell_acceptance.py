#!/usr/bin/env python3
"""Bounded cross-repo replay against independently read public PDF source cells.

Never treats numeric existence in a PDF, or a concatenated text blob, as
verified column association. Does NOT create a parser, PDFScope, or dataset.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = 'atlas.financial_source_cell_acceptance.v1'
ORACLE_SCHEMA = 'atlas.operator_reviewed_financial_cells.v1'


def canonical_label(text: Any) -> str:
    if not isinstance(text, str):return ''
    return ' '.join(text.replace('$', '').split()).strip().casefold()


def canonical_numeric(text: Any) -> str | None:
    if not isinstance(text, str):return None
    value=''.join(text.replace('$','').split())
    if not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?|\((?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?\)',value):
        return None
    return value


def evaluate_cell(tables: list[dict], target: dict, *, column: int | None, physical_page: int) -> dict:
    """A row label and the numeric value must occupy DIFFERENT source cells."""
    base={'id':target['id'],'expected':target['expected_printed_numeric'], 'period_key':target['period_key']}
    if column is None or type(column) is not int or column <= 0:
        return {**base,'status':'abstain_no_period_column','observed':None}
    matches=[]
    for table in tables:
        if table.get('page')!=physical_page or table.get('table_index')!=target['table_index']:
            continue
        for ridx,row in enumerate(table.get('rows',[])):
            if not isinstance(row,list) or not row:continue
            if canonical_label(row[0])==canonical_label(target['row_label']):
                matches.append((row,ridx))
    if not matches:return {**base,'status':'abstain_no_separate_row_label','observed':None}
    if len(matches)!=1:return {**base,'status':'abstain_ambiguous_duplicate_row','observed':None}
    row,ridx=matches[0]
    if column>=len(row):return {**base,'status':'abstain_missing_column','observed':None}
    observed=canonical_numeric(row[column])
    if observed is None:return {**base,'status':'abstain_non_atomic_numeric_cell','observed':None}
    expected=canonical_numeric(target['expected_printed_numeric'])
    if expected is None:raise ValueError('operator oracle has an invalid numeric string')
    return {**base,'status':'pass' if observed==expected else 'wrong_cell_value',
            'observed':observed,'row_index':ridx,'table_index':target['table_index']}


def load_module(filepath: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,filepath)
    if spec is None or spec.loader is None:raise ValueError('missing project module')
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def run(oracle_path: Path, pdf_dir: Path, research_drive_root: Path) -> dict:
    corpus=json.loads(oracle_path.read_text(encoding='utf-8'))
    if corpus.get('schema')!=ORACLE_SCHEMA:raise ValueError('unsupported manual oracle schema')
    if len(corpus.get('sources',[]))!=5:raise ValueError('expect five pinned independent PDF sources')
    record=load_module(research_drive_root/'drive/scripts/cluster_agent/recorded_fetch.py','research_drive_recorded_fetch_for_acceptance')
    namespace={};exec(record.HELPER,namespace)
    native=namespace['pdf_tables']
    optional=load_module(research_drive_root/'drive/scripts/cluster_agent/optional_pdf_candidates.py','research_drive_optional_pdf_for_acceptance').extract_candidates
    cases=[]
    for source in corpus['sources']:
        path=(pdf_dir/(source['id']+'.pdf')).resolve(strict=True)
        if not path.is_file() or path.suffix.lower()!='.pdf':raise ValueError('source file not a local PDF')
        raw=path.read_bytes()
        if len(raw)>30*1024*1024 or not raw.startswith(b'%PDF-') or hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise ValueError('source original bytes do not match manually reviewed oracle')
        n=source['physical_page']
        case={'id':source['id'],'publisher':source['publisher'],'source_url':source['url'],
              'source_sha256':source['sha256'],'selected_physical_pages':[n],
              'oracle_cells':len(source['targets']),'engines':{}}
        for engine,fn in [('native',lambda:native(path,[n])),('optional',lambda:optional(path,[n]))]:
            began=time.perf_counter()
            try:
                parsed=fn();elapsed=round(time.perf_counter()-began,3)
                verdicts=[evaluate_cell(parsed['tables'],q,column=source['column_map'][q['period_key']][engine],physical_page=n) for q in source['targets']]
                case['engines'][engine]={'execution':'ok','elapsed_seconds':elapsed,
                    'detected_tables':len(parsed['tables']),'candidate_cells':parsed['cell_count'],
                    'pass':sum(q['status']=='pass' for q in verdicts),
                    'wrong':sum(q['status']=='wrong_cell_value' for q in verdicts),
                    'abstain':sum(q['status'].startswith('abstain') for q in verdicts),
                    'verdicts':verdicts}
            except Exception as exc:
                case['engines'][engine]={'execution':'error','elapsed_seconds':round(time.perf_counter()-began,3),
                    'exception_type':type(exc).__name__, 'exception_excerpt':str(exc)[:180],
                    'pass':0,'wrong':0,'abstain':len(source['targets']),
                    'verdicts':[{'id':q['id'],'status':'abstain_parser_exception'} for q in source['targets']]}
        cases.append(case)
    totals={}
    for engine in ('native','optional'):
        vals=[r['engines'][engine] for r in cases]
        totals[engine]={'executed_documents':sum(v['execution']=='ok' for v in vals),
            'errored_documents':sum(v['execution']=='error' for v in vals),
            'exact_row_period_cells':sum(v['pass'] for v in vals),
            'wrong_cell_associations':sum(v['wrong'] for v in vals),
            'abstained_cells':sum(v['abstain'] for v in vals),
            'mean_execution_seconds':round(sum(v['elapsed_seconds'] for v in vals)/len(vals),3)}
    return {'schema':SCHEMA,'date':'2026-11-03','authority':'REVIEW_ONLY_DO_NOT_AUTO_PROMOTE',
        'oracle_review':'SINGLE_VISUAL_OPERATOR_NOT_DOUBLE_ADJUDICATED',
        'operator_review_seconds':'NOT_TIMED','interpretation':'operator-predeclared per-PDF table and column mapping; not automatic header inference',
        'source_count':len(cases),'target_cell_count':sum(x['oracle_cells'] for x in cases),
        'no_ocr':True,'source_pdf_redistributed':False,
        'adoption':'HOLD_PENDING_BROADER_INDEPENDENT_ADJUDICATION',
        'totals':totals,'cases':cases}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('receipt is immutable; choose unused output path')
    report=run(a.oracle,a.pdf_dir,a.research_drive_root)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2,ensure_ascii=False);handle.write('\n')
    print(json.dumps({'targets':report['target_cell_count'],'totals':report['totals']}))
if __name__=='__main__':main()
