#!/usr/bin/env python3
"""Source-byte pinned geometry triage; NEVER silently unrotate or recrop."""
import argparse,hashlib,json
from pathlib import Path

SCHEMA='atlas.original_pdf_geometry_blockers.v1'

def run(baseline_path:Path,original_dir:Path):
    import pdfplumber
    base=json.loads(baseline_path.read_text())
    if base.get('schema')!='atlas.tabula_existing_engine_first_pass.v1' or len(base['cases'])!=12:
        raise ValueError('invalid original frozen engine cohort')
    out=[]
    for c in base['cases']:
        path=original_dir/c['filename']
        data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
        if sha!=c['original_sha256']:raise ValueError('original PDF SHA changed')
        with pdfplumber.open(path) as doc:
            p=doc.pages[0]
            rotation=p.rotation
            offset=any(abs(a-b)>0.01 for a,b in zip(p.cropbox,(0,0,p.width,p.height)))
            bbox_offset=any(abs(a-b)>0.01 for a,b in zip(p.bbox,(0,0,p.width,p.height)))
        error=c['engines']['hybrid']['status']!='SOURCE_REVIEW_ONLY'
        if error and rotation!=0:reason='ROTATED_ORIGINAL_PAGE_REQUIRES_CALIBRATION'
        elif error and (offset or bbox_offset):reason='OFFSET_OR_CROPPED_ORIGINAL_PAGE_REQUIRES_CALIBRATION'
        elif error:reason='CAMELOT_TABLE_ROW_OR_CELL_GEOMETRY_INCONSISTENT'
        else:reason='NO_ENGINE_ERROR_ON_FIRST_PAGE'
        out.append({'source_file':c['filename'],'original_sha256':sha,
            'original_rotation_degrees':rotation,
            'original_media_width_pdf_points':p.width,
            'original_media_height_pdf_points':p.height,
            'source_cropbox_is_offset':offset,
            'source_bbox_is_offset':bbox_offset,
            'engine_hybrid_error':error,
            'reason':reason,'original_coordinate_calibration_approved':False})
    result={'schema':SCHEMA,'original_cohort_sha256':hashlib.sha256(
        baseline_path.read_bytes()).hexdigest(),
        'checked_original_first_pages':len(out),
        'frozen_primary_engine_errors':sum(x['engine_hybrid_error'] for x in out),
        'rotation_blockers':sum(x['reason']=='ROTATED_ORIGINAL_PAGE_REQUIRES_CALIBRATION' for x in out),
        'cropbox_or_bbox_blockers':sum(x['reason']=='OFFSET_OR_CROPPED_ORIGINAL_PAGE_REQUIRES_CALIBRATION' for x in out),
        'other_candidate_geometry_errors':sum(x['reason']=='CAMELOT_TABLE_ROW_OR_CELL_GEOMETRY_INCONSISTENT' for x in out),
        'source_qualified_for_trusted_use':0,'unverified_source_transformations_applied':0,
        'auto_publish':False,'auto_register_dataset':False,
        'state':'HOLD_SEPARATE_CALIBRATION_REQUIRED','cases':out}
    return result

def main():
    a=argparse.ArgumentParser()
    for k in ('baseline','original-dir','out'):a.add_argument('--'+k,required=True,type=Path)
    p=a.parse_args()
    if p.out.exists():raise FileExistsError('refusing to replace pinned geometry triage')
    result=run(p.baseline,p.original_dir)
    with p.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('checked_original_first_pages',
      'frozen_primary_engine_errors','rotation_blockers',
      'cropbox_or_bbox_blockers','other_candidate_geometry_errors')}))
if __name__=='__main__':main()
