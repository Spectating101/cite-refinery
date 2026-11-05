#!/usr/bin/env python3
"""Preregister new external rotated/cropped/general PDF sources from metadata.

No original PDF byte downloads or content access before this manifest commits.
"""
import hashlib,json,urllib.request
from pathlib import Path

UPSTREAM='4c64b92d5caccd71c645e98e0fabb0c4dba7ff45'
SEED='independent-original-geometry-20261105-source-only-v1'
STRESS=(
  'annotations-rotated-90.pdf',
  'annotations-rotated-180.pdf',
  'annotations-rotated-270.pdf',
  'nics-background-checks-2015-11-rotated.pdf',
  'page-boxes-example.pdf',
  'table-curves-example.pdf',
  'senate-expenditures.pdf',
)
PREFIX='https://raw.githubusercontent.com/jsvine/pdfplumber/'+UPSTREAM+'/tests/pdfs/'

def main():
    url=f'https://api.github.com/repos/jsvine/pdfplumber/contents/tests/pdfs?ref={UPSTREAM}'
    req=urllib.request.Request(url,headers={
      'User-Agent':'Spectating101-locked-original-source-geometry-validation',
      'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=35) as r:items=json.load(r)
    metadata={x['name']:x for x in items if x.get('type')=='file' and x['name'].lower().endswith('.pdf')}
    if not set(STRESS)<=set(metadata):raise ValueError('selected source metadata not available')
    pool=[n for n,x in metadata.items() if n not in STRESS and 4000<x.get('size',0)<1_000_000]
    random_sample=sorted(pool,key=lambda n:(hashlib.sha256((SEED+'|'+n).encode()).hexdigest(),n))[:5]
    chosen=list(STRESS)+random_sample
    if len(chosen)!=12 or len(set(chosen))!=12:raise ValueError('external source selection invalid')
    manifest={'schema':'atlas.pdfplumber_new_geometry_holdout_preregistration.v1',
       'selection_date':'2026-11-05',
       'upstream_repository':'https://github.com/jsvine/pdfplumber',
       'upstream_commit':UPSTREAM,
       'selection_seed':SEED,
       'predeclared_geometry_and_table_stress_cases':list(STRESS),
       'deterministically_sampled_uninspected_filenames':random_sample,
       'intent_to_test_original_first_pages':12,
       'prior_tabula_and_camelot_fixture_corpora_not_reused':True,
       'pdf_bytes_not_opened_or_downloaded_before_commit':True,
       'cases':[{'filename':n,'original_source_url':PREFIX+n,
                 'repository_metadata_size_bytes':metadata[n].get('size'),
                 'physical_page':1,'selection_type':'stress' if n in STRESS else 'hash_sample'}
                for n in chosen],
       'frozen_test_contract':{
          'original_source_sha256':'pin every original file after downloading; no substitutions',
          'source_metric':'PDF physical-page original word retention and independent word-box affine mapping',
          'candidate_metric':'fixed Camelot 1.0.9 hybrid on independently normalized source derivative only when calibration succeeds',
          'strict_row_metric':'source-only nonempty nonoverlap original word review gate, no semantic row approval',
          'zero_truth_invention':'no original table gold available by default; precision and recall UNKNOWN without separate authored external row gold',
          'failure_policy':'all 12 cases count; timeouts, errors, abstentions, negative cases remain',
          'no_tuning':'no adaptive page-specific flavor/coordinate changes after source download',
          'bounded_execution':'per-document offline subprocess with finite timeout',
          'original_pages_only':'first original physical page; other pages explicitly out of scope',
          'future_changed_scanner_requires_new_cohort':True},
       'independent_human_reviewer':False,
       'trusted_pdfscope_promotions':0,
       'auto_publish':False,'auto_register_dataset':False}
    p=Path(__file__).resolve().parents[1]/'examples/discovery/pdfplumber_geometry_holdout_preregistration_20261105.json'
    if p.exists():raise FileExistsError('immutable selection already exists')
    p.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'count':len(chosen),'stress':len(STRESS),'hash_sample':random_sample}))
if __name__=='__main__':main()
