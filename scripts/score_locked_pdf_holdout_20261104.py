#!/usr/bin/env python3
"""Score frozen no-hint PDF source-band predictions vs upstream authored gold.

No PDF parsing, threshold tuning, or output relabeling. Upstream test variables
are sourced via AST literal-only reads; no execution of third-party Python.
Only six cases with explicitly identified upstream expected rows are scored.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

SCHEMA='atlas.locked_external_pdf_row_reference_scoring.v1'
# Upstream fixture tests independently specify these expected DataFrame rows.
# We compare the single first PDF page's emitted row text against these
# original (separately authored) test assertions, not self-generated labels.
GOLD={
 'multiple_tables.pdf':('data_network_two_tables_b_1','data_network_two_tables_b_2'),
 'vertical_header.pdf':('data_network_vertical_headers',),
 'background_lines_1.pdf':('data_lattice_process_background',),
 'column_span_2.pdf':('data_lattice_shift_text_left_top',),
 'edge_tol.pdf':('data_network_edge_tol',),
 'detect_vertical_false.pdf':('data_network_strip_text',),
}
UPSTREAM_SHA='92777b852e00933a5c4b9ba642601784604356cd'


def safe_gold_assignments(path:Path):
    parsed=ast.parse(path.read_text(encoding='utf-8'))
    values={}
    for node in parsed.body:
        if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):
            continue
        var=node.targets[0].id
        try:
            value=ast.literal_eval(node.value)
        except (ValueError,TypeError,AttributeError):
            if isinstance(node.value,ast.Name):
                value=values.get(node.value.id)
            elif isinstance(node.value,ast.Subscript) and isinstance(node.value.value,ast.Name):
                source=values.get(node.value.value.id)
                v=node.value.slice
                if (isinstance(source,list) and isinstance(v,ast.Slice)
                    and v.step is None):
                    try:
                        lo=ast.literal_eval(v.lower) if v.lower else None
                        hi=ast.literal_eval(v.upper) if v.upper else None
                        value=source[slice(lo,hi)]
                    except (ValueError,TypeError):
                        continue
                else:continue
            else:continue
        if isinstance(value,list):
            values[var]=value
    return values


def normalize(text):
    text=unicodedata.normalize('NFKC',str(text)).casefold()
    return ' '.join(text.split())


def gold_row_text(row):
    if not isinstance(row,list) or any(not isinstance(x,str) for x in row):
        raise ValueError('external upstream expected row not literal text list')
    return normalize(' '.join(x for x in row if x))


def score(baseline_path:Path,private_dir:Path,upstream_gold_dir:Path):
    baseline=json.loads(baseline_path.read_text())
    if (baseline.get('schema')!='atlas.locked_external_pdf_first_page_scan.v1' or
        baseline.get('intent_to_test_pages')!=16 or len(baseline['cases'])!=16 or
        baseline.get('locked_engine_commit','')[:7]!='2f5bd7f'):
        raise ValueError('first-pass frozen scan evidence differs')
    gold_file=upstream_gold_dir/'data.py'
    data=safe_gold_assignments(gold_file)
    outputs=[]
    unknown=[]
    totals={'tp':0,'fp':0,'fn':0}
    for case in baseline['cases']:
        fname=case['filename']
        if fname not in GOLD:
            unknown.append(fname);continue
        golden=[]
        for variable in GOLD[fname]:
            table=data.get(variable)
            if not isinstance(table,list) or not table:
                raise ValueError('missing upstream fixture expected row '+variable)
            golden.extend(gold_row_text(r) for r in table)
        predictions=[]
        source=private_dir/(fname+'.private-row-proposals.json')
        if source.exists():
            packet=json.loads(source.read_text())
            if packet['source_sha256']!=case['original_sha256']:
                raise ValueError('private original PDF source row digest mismatch')
            for tab in packet['tables']:
                predictions.extend(normalize(r['unverified_source_row_text']) for r in tab['rows'])
        else:
            if case['scan_status']!='ERROR_NO_SOURCE_AUTHORITY' and case['source_row_regions_proposed']!=0:
                raise ValueError('missing required private row proposal original for '+fname)
        if len(predictions)!=case['source_row_regions_proposed']:
            raise ValueError('unpublished source row denominator differs from baseline')
        pred=Counter(predictions)
        want=Counter(golden)
        tp=sum(min(n,want[k]) for k,n in pred.items())
        fp=len(predictions)-tp;fn=len(golden)-tp
        totals['tp']+=tp;totals['fp']+=fp;totals['fn']+=fn
        outputs.append({'filename':fname,'gold_variables':list(GOLD[fname]),
            'expected_upstream_test_rows':len(golden),
            'predicted_source_band_rows':len(predictions),
            'exact_normalized_row_tp':tp,'exact_normalized_row_fp':fp,
            'exact_normalized_row_fn':fn,
            'precision':(tp/(tp+fp)) if tp+fp else None,
            'recall':(tp/(tp+fn)) if tp+fn else None,
            'matching_contract':'strict_NFKC_casefold_whitespace_row_text_equality'})
    if len(outputs)!=len(GOLD) or len(unknown)!=10:
        raise ValueError('externally reference-supported cases do not match frozen evaluation partition')
    precision=(totals['tp']/(totals['tp']+totals['fp'])) if (totals['tp']+totals['fp']) else None
    recall=(totals['tp']/(totals['tp']+totals['fn'])) if totals['tp']+totals['fn'] else None
    return {'schema':SCHEMA,'source_manifest_sha256':baseline['manifest_sha256'],
        'source_upstream_git_commit':UPSTREAM_SHA,
        'golden_reference_data_url':
            f'https://raw.githubusercontent.com/camelot-dev/camelot/{UPSTREAM_SHA}/tests/data.py',
        'golden_reference_sha256':hashlib.sha256(gold_file.read_bytes()).hexdigest(),
        'intent_to_test_pages':16,
        'pages_with_upstream_expected_row_assertions':len(outputs),
        'pages_without_comparable_upstream_expected_row_assertions':len(unknown),
        'unscored_filenames':unknown,
        'exact_normalized_row_tp':totals['tp'],
        'exact_normalized_row_fp':totals['fp'],
        'exact_normalized_row_fn':totals['fn'],
        'scored_row_precision_conditional':precision,
        'scored_row_recall_conditional':recall,
        'unscored_candidate_rows_not_assumed_true':True,
        'metric_not_full_corpus_or_global_accuracy':True,
        'third_party_parser_tests_not_independent_human_adjudication':True,
        'source_pdf_bytes_committed':False,
        'complete_original_row_text_committed':False,
        'auto_publish':False,'trusted_dataset_promotions':0,
        'release_decision':'HOLD_LOW_RECALL_AND_UNKNOWN_GOLD',
        'scored_cases':outputs}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',required=True,type=Path)
    p.add_argument('--private-dir',required=True,type=Path)
    p.add_argument('--gold-dir',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite prospective first-pass score')
    result=score(a.baseline,a.private_dir,a.gold_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in (
        'pages_with_upstream_expected_row_assertions',
        'exact_normalized_row_tp','exact_normalized_row_fp','exact_normalized_row_fn',
        'scored_row_precision_conditional','scored_row_recall_conditional')}))


if __name__=='__main__':main()
