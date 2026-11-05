#!/usr/bin/env python3
"""Post-holdout original-source affine recovery; frozen results not rewritten."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path

SCHEMA='atlas.tabula_original_source_affine_recovery.v1'
CASES={
    'rotated_page.pdf':'rotated-second',
    'schools.pdf':'schools-calibrated',
    'Publication_of_award_of_Bids_for_Transport_Sector__August_2016.pdf':'transport-calibrated',
    'should_detect_rulings.pdf':'cropped-first',
}
STILL_BLOCKED='argentina_diputados_voting_record.pdf'

def run(first_pass:Path,source_dir:Path,private_dir:Path,drive_root:Path):
    sys.path.insert(0,str(drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_calibrated_geometry import calibrate
    from scripts.cluster_agent.optional_camelot_row_review import produce_packet
    baseline=json.loads(first_pass.read_text())
    if baseline.get('schema')!='atlas.tabula_existing_engine_first_pass.v1' or len(baseline['cases'])!=12:
        raise ValueError('frozen original Tabula first pass is missing')
    cases={x['filename']:x for x in baseline['cases']}
    out=[]
    for filename,stem in CASES.items():
        case=cases[filename]
        if case['engines']['hybrid']['status']=='SOURCE_REVIEW_ONLY':
            raise ValueError('original engine outcome was not geometry-blocked')
        source=source_dir/filename
        raw=source.read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        if sha!=case['original_sha256']:
            raise ValueError('original source PDF bytes differ from frozen first pass')
        normalized=private_dir/(stem+'.NORMALIZED-EXTRACTION-AID.pdf')
        mapped=json.loads((private_dir/(stem+'.ORIGINAL-MAPPED-CANDIDATES.json')).read_text())
        saved_packet=json.loads((private_dir/(stem+'.OPERATOR-PACKET.json')).read_text())
        count=json.loads((private_dir/(stem+'.SANITIZED-COUNTS.json')).read_text())
        proof=calibrate(source,normalized,page=1)
        if (proof!=mapped['source_geometry_calibration'] or
            mapped['original_source_sha256']!=sha or
            count['original_source_sha256']!=sha or
            count['normalization_sha256']!=proof['derivative_sha256']):
            raise ValueError('replay original-calibrated source and derivative digest mismatch')
        rerun=produce_packet(source,mapped,normalized_pdf=normalized)
        if rerun!=saved_packet:
            raise ValueError('original source row packet changed from private replay')
        if (count['candidate_rows']!=rerun['candidate_rows_seen'] or
            count['strict_operator_review_rows']!=rerun['source_witnessed_operator_review_rows'] or
            count['blocked_candidate_rows']!=rerun['blocked_rows_count'] or
            count['trusted_rows']!=0 or count['source_original_pdf_unchanged'] is not True):
            raise ValueError('sanitized original-source review denominator or authority changed')
        html_path=private_dir/(stem+'.SOURCE-REVIEW.html')
        if html_path.exists()!=count['private_review_sheet_created']:
            raise ValueError('private original PDF review sheet missing or unexpectedly present')
        out.append({'source_file':filename,'original_sha256':sha,
            'source_first_pass_status':case['engines']['hybrid']['status'],
            'original_rotation':proof['original_rotation'],
            'original_cropbox_is_offset':proof['original_cropbox']!=[0,0,*proof['original_page_size_pdf']],
            'derivative_sha256':proof['derivative_sha256'],
            'independent_unique_word_anchors':proof['unique_source_anchors'],
            'source_word_boxes_with_exact_mapping':proof['independently_matched_word_boxes'],
            'max_source_word_box_residual_pdf':proof['max_original_word_box_error_pdf'],
            'total_original_source_words_preserved':proof['preserved_original_words'],
            'candidate_rows_on_calibrated_page':count['candidate_rows'],
            'rows_with_all_literal_original_word_cells':count['rows_source_literally_matched'],
            'strict_review_ready_rows':count['strict_operator_review_rows'],
            'blocked_candidate_rows':count['blocked_candidate_rows'],
            'blocked_reason_counts':count['blocked_reason_counts'],
            'private_source_review_sheet_created':count['private_review_sheet_created'],
            'operator_actions_submitted':0,'human_second_review_approvals':0,
            'trusted_rows':0})
        print(filename,'original rows',count['candidate_rows'],
            'review-ready',count['strict_operator_review_rows'],flush=True)
    fifth=cases[STILL_BLOCKED]
    if fifth['engines']['hybrid']['status']=='SOURCE_REVIEW_ONLY':
        raise ValueError('pre-existing inconsistent-geometry source status changed')
    return {'schema':SCHEMA,
        'original_first_pass_sha256':hashlib.sha256(first_pass.read_bytes()).hexdigest(),
        'previously_geometry_blocked_sources':5,'sources_with_verified_affine_calibration':len(out),
        'still_inconsistent_parser_geometry_source':STILL_BLOCKED,
        'original_pdf_pages_recovered_as_source_candidate_regions':len(out),
        'new_original_source_candidate_rows':sum(x['candidate_rows_on_calibrated_page'] for x in out),
        'new_strict_source_review_rows':sum(x['strict_review_ready_rows'] for x in out),
        'new_blocked_candidate_rows':sum(x['blocked_candidate_rows'] for x in out),
        'new_real_private_review_sheets':sum(x['private_source_review_sheet_created'] for x in out),
        'original_source_geometry_proof_replayed':True,'source_docs_normalized_for_extraction_only':True,
        'old_first_pass_metrics_unchanged':True,
        'not_prospective_on_frozen_cohort':True,
        'operator_actions_submitted':0,'real_independent_reviewers':0,'trusted_pdfscope_promotions':0,
        'trusted_dataset_rows':0,'original_PDF_or_full_review_rows_committed':False,
        'auto_publish':False,'auto_register_dataset':False,
        'release_state':'HOLD_GEOMETRY_RECOVERED_NOT_HUMAN_SEMANTICS_APPROVED',
        'cases':out}

def main():
    p=argparse.ArgumentParser()
    for k in ('first-pass','source-dir','private-dir','research-drive-root','out'):
        p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('original source calibrated acceptance immutable')
    r=run(a.first_pass,a.source_dir,a.private_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:r[k] for k in (
        'previously_geometry_blocked_sources','sources_with_verified_affine_calibration',
        'new_original_source_candidate_rows','new_strict_source_review_rows',
        'new_blocked_candidate_rows','new_real_private_review_sheets')}))
if __name__=='__main__':main()
