#!/usr/bin/env python3
"""Immutable new-corpus original-PDF geometry and complex-row source evaluation.

Original external PDF bytes must not be opened until preregistration + engine
and this source runner are committed. Fixed Camelot hybrid; no per-file tuning.
New benchmark evaluates source preservation, not semantic table precision.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import urllib.request

SCHEMA='atlas.pdfplumber_original_geometry_external_first_pass.v1'
ENGINE_PREFIX='4e3dabe'
UPSTREAM='4c64b92d5caccd71c645e98e0fabb0c4dba7ff45'
WORKER_MAX_SECONDS=55

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _private_file(file:Path,data:bytes):
    file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(file,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data)

def _worker(original:Path,receipt:Path,drive_root:Path):
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_calibrated_geometry import (
         prepare_normalized,convert_candidate)
    from scripts.cluster_agent.optional_pdf_camelot_review import extract_review_candidates
    from scripts.cluster_agent.optional_camelot_row_review import produce_packet
    from scripts.cluster_agent.optional_pdf_complex_structure_review import build_complex_packet
    from scripts.cluster_agent.optional_native_pdf_crop_review import _source
    import pdfplumber
    original,raw,sha=_source(original)
    result={'source_sha256':sha,'source_size_bytes':len(raw),
            'source_pdf_physical_page':1,
            'stage':'SOURCE_ORIGINAL_METADATA','status':'ERROR',
            'original_rotation':None,'original_offset_cropbox':None,
            'original_pdf_word_count':0,
            'normalized_word_retention':0,'unique_original_word_box_anchors':0,
            'verified_original_word_box_anchors':0,
            'max_source_word_box_residual_pdf':None,
            'candidate_tables':0,'candidate_rows':0,'candidate_cells':0,
            'strict_review_ready_rows':0,'blocked_source_rows':0,
            'blocked_structural_evidence_rows':0,
            'literal_source_matched_cells':0,'empty_or_merged_source_slots':0,
            'multiline_source_cell_groups':0,
            'trusted_rows':0,'auto_publish':False}
    try:
        with pdfplumber.open(original) as d:
            page=d.pages[0]
            result['original_rotation']=page.rotation
            result['original_offset_cropbox']=any(
                abs(a-b)>.01 for a,b in zip(page.cropbox,
                                   (0,0,page.width,page.height)))
            result['original_pdf_word_count']=len(page.extract_words())
        directory=receipt.parent
        derivative=directory/(original.name+'.private-normalized-extraction-aid.pdf')
        result['stage']='SOURCE_PDF_NORMALIZATION'
        proof=prepare_normalized(original,derivative,page=1)
        result['stage']='ORIGINAL_WORD_GEOMETRY_CALIBRATION'
        result['normalized_word_retention']=proof['preserved_original_words']
        result['unique_original_word_box_anchors']=proof['unique_source_anchors']
        result['verified_original_word_box_anchors']=proof['independently_matched_word_boxes']
        result['max_source_word_box_residual_pdf']=proof['max_original_word_box_error_pdf']
        result['stage']='FIXED_CAMELOT_HYBRID'
        candidate=extract_review_candidates(derivative,
            source_sha256=proof['derivative_sha256'],page=1,flavor='hybrid')
        result['stage']='ORIGINAL_SOURCE_CELL_REVERSE_MAPPING'
        mapped=convert_candidate(original,derivative,candidate,proof)
        result['stage']='STRICT_ORIGINAL_SOURCE_OPERATOR_GATE'
        packet=produce_packet(original,mapped,normalized_pdf=derivative)
        result['stage']='BLOCKED_MULTILINE_MERGED_STRUCTURAL_AUDIT'
        complex_packet=build_complex_packet(original,mapped,normalized_pdf=derivative)
        if (complex_packet['strict_clean_rows_not_modified']!=
                packet['source_witnessed_operator_review_rows'] or
            complex_packet['blocked_rows_with_structural_evidence']!=
                packet['blocked_rows_count'] or
            packet['candidate_rows_seen']!=mapped['candidate_row_count']):
            raise ValueError('source row denominator changed during original audit')
        result['candidate_tables']=mapped['candidate_table_count']
        result['candidate_rows']=mapped['candidate_row_count']
        result['candidate_cells']=mapped['candidate_cell_count']
        result['literal_source_matched_cells']=mapped['literal_original_pdf_witness_cell_matches']
        result['strict_review_ready_rows']=packet['source_witnessed_operator_review_rows']
        result['blocked_source_rows']=packet['blocked_rows_count']
        result['blocked_structural_evidence_rows']=complex_packet['blocked_rows_with_structural_evidence']
        result['empty_or_merged_source_slots']=sum(
            c['empty_slot_kind'] is not None
            for r in complex_packet['structural_rows'] for c in r['source_cells'])
        result['multiline_source_cell_groups']=sum(
            c['multiline_source']
            for r in complex_packet['structural_rows'] for c in r['source_cells'])
        result['status']='REVIEW_ONLY_CANDIDATES' if mapped['candidate_row_count'] else 'ABSTAIN_NO_TABLE_CANDIDATES'
        result['stage']='COMPLETE'
        if hashlib.sha256(original.read_bytes()).hexdigest()!=sha:
            raise ValueError('original source mutated during evaluation')
        # NEVER persist full source words or candidate rows on this public
        # benchmark route: the verified private derivative itself is retained.
    except Exception as ex:
        result['status']='ERROR_HELD_NO_TRUSTED_ROWS'
        result['error_stage']=result['stage']
        result['error_type']=type(ex).__name__
        # Do not hide failure behind partial candidate statistics.
        for n in ('candidate_tables','candidate_rows','candidate_cells',
                  'literal_source_matched_cells','strict_review_ready_rows',
                  'blocked_source_rows','blocked_structural_evidence_rows',
                  'empty_or_merged_source_slots','multiline_source_cell_groups'):
            result[n]=0
    _private_file(receipt,(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({'stage':result['stage'],'status':result['status'],
        'source_sha256':sha,'candidate_rows':result['candidate_rows'],
        'strict_review_ready_rows':result['strict_review_ready_rows']}))

def _download(url:str,target:Path,expected_size:int):
    if target.exists():
        raise ValueError('locked fixture already exists before first evaluation')
    if type(expected_size)!=int or not 100<=expected_size<4_000_000:
        raise ValueError('source file outside predeclared PDF byte budget')
    req=urllib.request.Request(url,headers={'User-Agent':'Spectating101-source-only-PDF-geometry-holdout'})
    with urllib.request.urlopen(req,timeout=35) as fp:
        raw=fp.read(4_000_001)
    if len(raw)>4_000_000 or not raw.startswith(b'%PDF-'):
        raise ValueError('upstream content not a bounded PDF')
    _private_file(target,raw)
    return len(raw)

def _run_one(row:dict,source_dir:Path,root:Path,interpreter:str):
    name=row['filename']
    if '/' in name or '\\' in name or not name.endswith('.pdf'):
        raise ValueError('manifest source name is not safe')
    pdf=source_dir/name
    receipt=source_dir/(name+'.private-worker-result.json')
    expected_url='https://raw.githubusercontent.com/jsvine/pdfplumber/'+UPSTREAM+'/tests/pdfs/'+name
    if row['original_source_url']!=expected_url:
        raise ValueError('non-pinned upstream PDF original source URL')
    outer={'filename':name,'original_source_url':row['original_source_url'],
           'selection_type':row['selection_type'],'physical_page':1,
           'original_source_sha256':None,'download_status':'UNKNOWN',
           'worker_status':'NOT_RUN','candidate_rows':0,'strict_review_ready_rows':0,
           'blocked_source_rows':0,'trusted_rows':0}
    try:
        _download(row['original_source_url'],pdf,row['repository_metadata_size_bytes'])
        outer['download_status']='EXACT_UPSTREAM_BYTES_ACQUIRED'
        outer['original_source_sha256']=_sha(pdf.read_bytes())
        process=subprocess.run([interpreter,__file__,'--worker-original',str(pdf),
            '--worker-receipt',str(receipt),'--research-drive-root',str(root)],
            timeout=WORKER_MAX_SECONDS,capture_output=True,text=True)
        if process.returncode!=0 or not receipt.exists():
            outer['worker_status']='WORKER_EXIT_ERROR'
        else:
            result=json.loads(receipt.read_text())
            if result['source_sha256']!=outer['original_source_sha256'] or result['trusted_rows']!=0:
                raise ValueError('worker receipt not pinned to original source SHA')
            for k in ('stage','status','error_stage','error_type','original_rotation',
                      'original_offset_cropbox','original_pdf_word_count','normalized_word_retention',
                      'unique_original_word_box_anchors','verified_original_word_box_anchors',
                      'max_source_word_box_residual_pdf','candidate_tables','candidate_rows',
                      'candidate_cells','literal_source_matched_cells',
                      'strict_review_ready_rows','blocked_source_rows',
                      'blocked_structural_evidence_rows','empty_or_merged_source_slots',
                      'multiline_source_cell_groups'):
                if k in result:outer[k]=result[k]
            outer['worker_status']='WORKER_COMPLETED_WITH_HOLD_RECEIPT'
    except subprocess.TimeoutExpired:
        outer['worker_status']='WORKER_TIMEOUT'
    except Exception as ex:
        outer['worker_status']='ERROR_HELD'
        outer['outer_error_type']=type(ex).__name__
    print(name,outer['worker_status'],outer.get('status'),
        'candidate',outer['candidate_rows'],'strict',outer['strict_review_ready_rows'],flush=True)
    return outer

def run(manifest_path:Path,original_dir:Path,drive_root:Path,interpreter:str):
    m=json.loads(manifest_path.read_text())
    if (m.get('schema')!='atlas.pdfplumber_new_geometry_holdout_preregistration.v1' or
        m.get('upstream_commit')!=UPSTREAM or len(m['cases'])!=12 or
        m.get('pdf_bytes_not_opened_or_downloaded_before_commit') is not True):
        raise ValueError('prospective new PDF cohort contract differs')
    sha=subprocess.check_output(['git','-C',str(drive_root),'rev-parse','HEAD'],text=True).strip()
    if not sha.startswith(ENGINE_PREFIX):
        raise ValueError('original source engine changed after freeze')
    if any((a/'.git').exists() for a in (original_dir.resolve(),*original_dir.resolve().parents)):
        raise ValueError('never write original PDF bytes inside Git')
    original_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows=list(executor.map(lambda row:_run_one(row,original_dir,drive_root,interpreter),m['cases']))
    return {'schema':SCHEMA,'original_source_repository_commit':UPSTREAM,
        'locked_manifest_sha256':_sha(manifest_path.read_bytes()),
        'frozen_research_drive_source_commit':sha,
        'engine_mode':'camelot-py-1.0.9-hybrid-fixed',
        'source_extraction_normalization_only':True,
        'original_first_page_cases_locked':12,'original_first_page_cases_attempted':len(rows),
        'original_pdfs_sha_pinned':sum(x['original_source_sha256'] is not None for x in rows),
        'worker_source_errors_or_timeouts':sum(
            x['worker_status']!='WORKER_COMPLETED_WITH_HOLD_RECEIPT' or
            x.get('status')=='ERROR_HELD_NO_TRUSTED_ROWS' for x in rows),
        'source_pages_with_calibrated_word_proof':sum(
            x.get('verified_original_word_box_anchors',0)>=20 and
            x.get('verified_original_word_box_anchors')==x.get('unique_original_word_box_anchors')
            for x in rows),
        'source_pages_with_candidate_rows':sum(x['candidate_rows']>0 for x in rows),
        'candidate_rows_total':sum(x['candidate_rows'] for x in rows),
        'strict_review_ready_rows_total':sum(x['strict_review_ready_rows'] for x in rows),
        'blocked_source_rows_total':sum(x['blocked_source_rows'] for x in rows),
        'structural_rows_untrusted_total':sum(x.get('blocked_structural_evidence_rows',0) for x in rows),
        'external_published_row_gold_available':False,
        'row_precision':None,'row_recall':None,
        'original_pdf_bytes_or_source_rows_committed':False,
        'not_independent_human_blind_review':True,
        'first_pass_never_tuned_to_selected_sources':True,
        'first_pass_release':'HOLD_NO_ORIGINAL_TABLE_GOLD_OR_HUMAN_APPROVAL',
        'trusted_rows':0,'auto_publish':False,'auto_register_dataset':False,
        'cases':rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker-original',type=Path)
    p.add_argument('--worker-receipt',type=Path)
    p.add_argument('--manifest',type=Path)
    p.add_argument('--original-dir',type=Path)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--interpreter')
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.worker_original is not None:
        if a.worker_receipt is None:raise ValueError('worker needs private original source receipt')
        _worker(a.worker_original,a.worker_receipt,a.research_drive_root)
        return
    if a.manifest is None or a.original_dir is None or a.out is None or a.interpreter is None:
        p.error('new locked original-source evaluation requires all explicit CLI paths')
    if a.out.exists():raise FileExistsError('immutable first-pass acceptance receipt exists')
    result=run(a.manifest,a.original_dir,a.research_drive_root,a.interpreter)
    _private_file(a.out,(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:result[k] for k in (
        'original_first_page_cases_attempted','original_pdfs_sha_pinned',
        'worker_source_errors_or_timeouts','source_pages_with_calibrated_word_proof',
        'source_pages_with_candidate_rows','candidate_rows_total',
        'strict_review_ready_rows_total','blocked_source_rows_total')}))

if __name__=='__main__':main()
