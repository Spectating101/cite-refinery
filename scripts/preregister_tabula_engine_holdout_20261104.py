#!/usr/bin/env python3
"""Reproducible preregistration from pre-inspected upstream filename METADATA ONLY."""
import hashlib,json
from pathlib import Path
SHA='2cdf3b4fd3f7e921dca8cc6814cdd9316be40f0f'
SEED='atlas-2026-11-04-separate-tabula-holdout-v1'
STRESS=['rotated_page.pdf','jpeg2000.pdf','spanning_cells.pdf','should_detect_rulings.pdf']
# Fixed filename listing collected from public repository metadata, not PDFs.
CSV_BACKED=['AnimalSounds.pdf','MultiColumn.pdf',
'Publication_of_award_of_Bids_for_Transport_Sector__August_2016.pdf',
'argentina_diputados_voting_record.pdf','frx_2012_disclosure.pdf',
'indictb1h_14.pdf','schools.pdf','spanning_cells.pdf',
'spreadsheet_no_bounding_frame.pdf','twotables.pdf','us-020.pdf']
BASE='https://raw.githubusercontent.com/tabulapdf/tabula-java/'+SHA+'/src/test/resources/technology/tabula/'
def main():
    pool=sorted(set(CSV_BACKED)-set(STRESS),key=lambda n:(hashlib.sha256((SEED+'|'+n).encode()).hexdigest(),n))
    chosen=STRESS+pool[:8]
    assert len(chosen)==12 and len(set(chosen))==12
    obj={'schema':'atlas.preregistered_tabula_external_engine_holdout.v1',
    'date':'2026-11-04','source_repo':'https://github.com/tabulapdf/tabula-java',
    'source_commit':SHA,'selection_seed':SEED,'metadata_only_before_pdf_download':True,
    'stress_cases_predeclared':STRESS,'hash_selected_csv_backed':pool[:8],
    'total_first_pages':len(chosen),'prior_camelot_test_holdout_reused':False,
    'files':[{'filename':n,'pdf_url':BASE+n,
      'independent_published_csv_url':BASE+'csv/'+n[:-4]+'.csv' if n in CSV_BACKED else None,
      'page':1,'stratum':'stress' if n in STRESS else 'hash_sample'} for n in chosen],
    'frozen_engine_policy':{'primary':'camelot-py==1.0.9 flavor=hybrid pages=1',
      'diagnostics':['camelot-py==1.0.9 flavor=network pages=1',
                     'camelot-py==1.0.9 flavor=lattice pages=1'],
      'selection':'never choose best engine based on gold',
      'source_guard':'original SHA-256 pinned + original pdfplumber source-word cell witness',
      'reference_policy':'score only independently published CSV rows with matching page scope; unscorable pages explicit',
      'denominators':'12 first pages all errors and abstentions retained',
      'replay_rule':'no tuning on cohort; revisions require new untouched cohort'},
    'human_review_completed':False,'trusted_source_registration':False,'auto_publish':False}
    p=Path(__file__).resolve().parents[1]/'examples/discovery/tabula_engine_holdout_preregistration_20261104.json'
    if p.exists():raise FileExistsError('already locked')
    p.write_text(json.dumps(obj,indent=2)+'\n')
    print('LOCKED',chosen)
if __name__=='__main__':main()
