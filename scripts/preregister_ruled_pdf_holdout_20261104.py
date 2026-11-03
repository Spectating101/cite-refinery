#!/usr/bin/env python3
"""Immutable prospective fixture manifest; no PDF content access or tuning.

A deterministic selection from a pinned, public upstream repository tree.
This script only contacts upstream metadata; no table predictions or gold.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import urllib.request

UPSTREAM_SHA='92777b852e00933a5c4b9ba642601784604356cd'
SEED='2026-11-04-ruled-external-locked-v1'
CHALLENGE=('row_span_2.pdf','column_span_1.pdf','missing_values.pdf',
    'vertical_header.pdf','background_lines_1.pdf','image.pdf',
    'empty.pdf','multiple_tables.pdf')
PREVIOUS={'health.pdf','foo.pdf'}
SCHEMA='atlas.preregistered_untouched_pdf_holdout.v1'

def main():
    url=f'https://api.github.com/repos/camelot-dev/camelot/contents/tests/files?ref={UPSTREAM_SHA}'
    req=urllib.request.Request(url,headers={'User-Agent':'spectating101-research-evaluation',
                                              'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=30) as response:
        names={x['name'] for x in json.load(response)
               if x['type']=='file' and x['name'].endswith('.pdf')}
    if not set(CHALLENGE)<=names:
        raise ValueError('predeclared challenges missing upstream')
    pool=sorted(names-PREVIOUS-set(CHALLENGE),
        key=lambda name:(hashlib.sha256((SEED+'|'+name).encode()).hexdigest(),name))
    random_pick=pool[:8]
    selected=list(CHALLENGE)+random_pick
    if len(selected)!=16 or len(set(selected))!=16 or set(selected)&PREVIOUS:
        raise ValueError('invalid locked source selection')
    data={
        'schema':SCHEMA,'creation_date':'2026-11-04',
        'upstream_repo':'https://github.com/camelot-dev/camelot',
        'upstream_commit':UPSTREAM_SHA,
        'selection_seed':SEED,
        'predeclared_stress_fixture_names':list(CHALLENGE),
        'deterministic_hash_sample_count':8,
        'deterministic_hash_sample_names':random_pick,
        'selected_source_files':[{
            'filename':name,
            'original_source_url':f'https://raw.githubusercontent.com/camelot-dev/camelot/{UPSTREAM_SHA}/tests/files/{name}',
            'first_physical_page':1,
            'predeclared_stratum':'challenge' if name in CHALLENGE else 'hash_sample'
        } for name in selected],
        'previously_inspected_fixtures_excluded':sorted(PREVIOUS),
        'metric_contract':{
            'unit':'first-original-physical-PDF-page',
            'intent_to_test_pages':len(selected),
            'zero_cherry_picking':True,
            'recovery_attempt':'one noninteractive source-rule scan per page, no manual table crop or tuning after downloading selected PDFs',
            'row_precision':'TP/(TP+FP) against independently available upstream-oracle row transcription; UNKNOWN if no independent row oracle, never guessed',
            'row_recall':'TP/(TP+FN) against independently available upstream-oracle rows; UNKNOWN if no independent row oracle',
            'no_annotation_rule':'keep every page in intent-to-test denominator; do not manufacture source truth from parser predictions',
            'execution_failures':'count as failures or abstentions, do not omit from intent-to-test',
            'false_positive_policy':'chart, empty/image-only and unsupported merged headers must abstain when no source backed table',
            'source_custody':'original upstream commit, each downloaded original SHA-256, original page and no committed publisher PDFs',
            'trusted_data_promotions':0
        },
        'independent_external_human_review_requested':False,
        'source_pdf_bytes_downloaded_before_manifest_freeze':False,
        'data_release_authority':'NONE_HOLD'
    }
    target=Path(__file__).resolve().parents[1]/'examples/discovery/ruled_pdf_holdout_preregistration_20261104.json'
    if target.exists():raise FileExistsError('pre-registration is immutable; do not overwrite')
    target.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'selection_count':len(selected),'challenge_count':len(CHALLENGE),
        'sample':random_pick,'manifest':str(target)}))

if __name__=='__main__':main()
