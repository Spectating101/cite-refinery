#!/usr/bin/env python3
"""Run pinned existing engines on preregistered Tabula files, untrusted only."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,json,os,subprocess
from pathlib import Path

SCHEMA='atlas.tabula_existing_engine_first_pass.v1'
SOURCE_SHA='9b502d8'
FLAVORS=('hybrid','network','lattice')
PYTHON='/home/phyrexian/chatgpt-work/review-20261103/camelot-interop-venv/bin/python'


def execute_one(case,root,private,repo):
    import pdfplumber
    p=(private/case['filename']).resolve(strict=True)
    data=p.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    entry={'filename':case['filename'],'stratum':case['stratum'],'original_sha256':digest,
           'original_size_bytes':len(data),'original_pdf_pages':None,
           'engines':{},'trusted_rows':0}
    try:
        with pdfplumber.open(p) as d:
            entry['original_pdf_pages']=len(d.pages)
    except Exception as ex:
        entry['original_pdf_metadata_error']=type(ex).__name__
    for flavor in FLAVORS:
        target=private/(case['filename']+'.'+flavor+'.private-candidates.json')
        args=[PYTHON,'-m','scripts.cluster_agent.optional_pdf_camelot_review',
              '--pdf',str(p),'--sha256',digest,'--page','1','--flavor',flavor,
              '--out',str(target)]
        try:
            process=subprocess.run(args,cwd=str(root),env={**os.environ,
                'PYTHONPATH':'.:drive'},capture_output=True,text=True,timeout=35)
            if process.returncode or not target.exists():
                entry['engines'][flavor]={'status':'ENGINE_ERROR',
                   'error_type':'SubprocessNonzeroExit','candidate_rows':0,
                   'candidate_tables':0,'candidate_cells':0,'source_word_witness_cells':0}
                continue
            report=json.loads(target.read_text())
            if (report['original_source_sha256']!=digest or
                report['parser_flavor']!=flavor or report['auto_publish'] is not False):
                raise ValueError('source candidate trust contract differs')
            entry['engines'][flavor]={'status':'SOURCE_REVIEW_ONLY',
                'candidate_rows':report['candidate_row_count'],
                'candidate_tables':report['candidate_table_count'],
                'candidate_cells':report['candidate_cell_count'],
                'source_word_witness_cells':report['literal_original_pdf_witness_cell_matches'],
                'fully_original_word_matched_rows':sum(
                    r['all_cells_literal_source_matched'] for t in report['tables']
                    for r in t['rows'])}
        except subprocess.TimeoutExpired:
            entry['engines'][flavor]={'status':'ENGINE_TIMEOUT','candidate_rows':0,
                    'candidate_tables':0,'candidate_cells':0,'source_word_witness_cells':0}
        except Exception as ex:
            entry['engines'][flavor]={'status':'ENGINE_ERROR','error_type':type(ex).__name__,
                    'candidate_rows':0,'candidate_tables':0,'candidate_cells':0,
                    'source_word_witness_cells':0}
    print(case['filename'],*(f"{e}:{entry['engines'][e]['status']}/{entry['engines'][e]['candidate_rows']}" for e in FLAVORS),flush=True)
    return entry


def run(manifest,root,private):
    original=manifest.read_bytes()
    selection=json.loads(original)
    if selection['schema']!='atlas.preregistered_tabula_external_engine_holdout.v1' or len(selection['files'])!=12:
        raise ValueError('frozen cohort differs')
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if not sha.startswith(SOURCE_SHA):
        raise ValueError('original engine not at frozen commit')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda x:execute_one(x,root,private,root),selection['files']))
    return {'schema':SCHEMA,
        'original_manifest_sha256':hashlib.sha256(original).hexdigest(),
        'original_upstream_commit':selection['source_commit'],
        'frozen_research_drive_commit':sha,
        'primary_engine':'hybrid','diagnostic_engines':['network','lattice'],
        'original_first_pages_attempted':len(results),
        'primary_pages_with_candidates':sum(
            x['engines']['hybrid']['candidate_rows']>0 for x in results),
        'primary_candidate_rows':sum(x['engines']['hybrid']['candidate_rows'] for x in results),
        'primary_candidate_source_word_matched_rows':sum(
            x['engines']['hybrid'].get('fully_original_word_matched_rows',0) for x in results),
        'primary_engine_errors_or_timeouts':sum(
            x['engines']['hybrid']['status']!='SOURCE_REVIEW_ONLY' for x in results),
        'primary_source_only_not_truth':True,
        'source_reference_row_accuracy_not_yet_scored':True,
        'trusted_publication_rows':0,
        'all_pdf_and_candidate_text_private':True,
        'auto_publish':False,'auto_register_dataset':False,
        'release':'HOLD_EXTERNAL_ORACLE_AND_INDEPENDENT_HUMAN_REQUIRED',
        'cases':results}


def main():
    ap=argparse.ArgumentParser()
    for key in ('manifest','research-drive-root','private-dir','out'):
        ap.add_argument('--'+key,required=True,type=Path)
    a=ap.parse_args()
    if a.out.exists():raise FileExistsError('first-pass evidence immutable')
    r=run(a.manifest,a.research_drive_root,a.private_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:r[k] for k in ('original_first_pages_attempted',
        'primary_pages_with_candidates','primary_candidate_rows',
        'primary_candidate_source_word_matched_rows','primary_engine_errors_or_timeouts')}))


if __name__=='__main__':main()
