"""Frozen original-source multi-engine cohort, all errors and denominators pinned."""
import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]/'examples/discovery'

def load(name):
    return json.loads((R/name).read_text())

class TabulaExistingPDFEngineAcceptance(unittest.TestCase):
    def test_original_cohort_not_posthoc_selected(self):
        m=load('tabula_engine_holdout_preregistration_20261104.json')
        r=load('tabula_engine_holdout_first_pass_20261104.json')
        assert m['source_commit']=='2cdf3b4fd3f7e921dca8cc6814cdd9316be40f0f'
        assert m['metadata_only_before_pdf_download']
        assert m['frozen_engine_policy']['primary'].startswith('camelot-py==1.0.9 flavor=hybrid')
        assert r['original_manifest_sha256']==hashlib.sha256(
            (R/'tabula_engine_holdout_preregistration_20261104.json').read_bytes()).hexdigest()
        assert r['frozen_research_drive_commit'].startswith('9b502d8')
        assert r['original_first_pages_attempted']==12
        assert r['primary_pages_with_candidates']==6
        assert r['primary_candidate_rows']==325
        assert r['primary_candidate_source_word_matched_rows']==171
        assert r['primary_engine_errors_or_timeouts']==5
        assert len(r['cases'])==12
        assert {x['filename'] for x in r['cases']}=={x['filename'] for x in m['files']}
        for case in r['cases']:
            assert len(case['original_sha256'])==64
            assert case['trusted_rows']==0
            assert set(case['engines'])=={'hybrid','network','lattice'}
            for info in case['engines'].values():
                assert info['status'] in {'SOURCE_REVIEW_ONLY','ENGINE_ERROR','ENGINE_TIMEOUT'}
                assert info['source_word_witness_cells']<=info['candidate_cells']
        assert not r['auto_publish'] and not r['auto_register_dataset']
        assert r['trusted_publication_rows']==0

    def test_external_csv_row_scores_and_source_gate_are_separate(self):
        r=load('tabula_engine_holdout_csv_scoring_20261104.json')
        baseline=load('tabula_engine_holdout_first_pass_20261104.json')
        assert r['first_pass_sha256']==hashlib.sha256(
            (R/'tabula_engine_holdout_first_pass_20261104.json').read_bytes()).hexdigest()
        assert r['frozen_primary']=='hybrid'
        assert r['pages_with_comparable_published_csv']==6
        assert r['pages_without_comparable_published_csv']==6
        s=r['primary_summary']
        assert (s['exact_full_row_tp'],s['unmatched_proposed_fp'],s['missed_expected_fn'])==(185,67,53)
        assert (s['source_and_csv_exact_row_matches'],s['source_witnessed_candidate_rows'])==(135,150)
        assert s['proposed_rows_on_scored_pages']==252
        assert abs(s['conditional_precision']-185/252)<1e-12
        assert abs(s['conditional_recall']-185/238)<1e-12
        assert (r['diagnostic_summaries']['network']['exact_full_row_tp'],
                r['diagnostic_summaries']['lattice']['exact_full_row_tp'])==(185,146)
        assert r['original_PDF_source_word_match_is_not_row_truth']
        assert r['trusted_rows']==0 and not r['auto_publish']
        assert all(c['reference_status'] in {
            'NO_COMPARABLE_REFERENCE','UNSCORED_REFERENCE_COVERS_MULTIPAGE_DOCUMENT',
            'REFERENCE_SCORABLE_SINGLE_ORIGINAL_PAGE','EMPTY_OR_UNSUPPORTED_REFERENCE'} for c in r['cases'])

    def test_same_cohort_old_scanner_is_posthoc_diagnostic_not_blind(self):
        old=load('tabula_ruled_baseline_same_cohort_20261104.json')
        new=load('tabula_engine_holdout_csv_scoring_20261104.json')
        assert old['old_engine_commit']=='2f5bd7f'
        assert old['not_originally_preregistered_as_primary']
        assert old['same_original_pdf_sha_verified']
        assert old['attempted_pages']==12
        assert (old['pages_with_ruled_row_proposals'],old['row_proposals_total'])==(4,163)
        assert (old['scored_pages'],old['true_positive_rows'],
                old['false_positive_rows'],old['false_negative_rows'])==(6,115,48,123)
        assert abs(old['conditional_precision']-115/163)<1e-12
        assert abs(old['conditional_recall']-115/238)<1e-12
        assert new['primary_summary']['exact_full_row_tp']>old['true_positive_rows']
        assert new['trusted_rows']==0 and old['trusted_rows']==0
        assert not old['auto_publish']

if __name__=='__main__': unittest.main()
