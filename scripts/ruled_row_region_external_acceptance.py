#!/usr/bin/env python3
"""Sanitized original-PDF row-region transfer check on two public fixtures.

Calls Research Drive's original-source row-region proposer. Only manually
pinned sample literals are compared; no raw parsed text or PDF bytes in Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA='atlas.original_pdf_row_region_external_acceptance.v1'


def run(oracle_path:Path, fixture_dir:Path, prior_pdf_dir:Path,
        research_drive_root:Path) -> dict:
    sys.path.insert(0,str(research_drive_root.resolve(strict=True)/'drive'))
    from scripts.cluster_agent.optional_pdf_ruled_inventory import propose_original_ruled_row_regions
    oracle=json.loads(oracle_path.read_text(encoding='utf-8'))
    if oracle.get('schema')!='atlas.original_ruled_row_region_external_oracle.v1':
        raise ValueError('source oracle schema mismatch')
    summaries={}
    for fixture_id in ('health','foo','previous_ruled_reference'):
        spec=oracle[fixture_id]
        file= (prior_pdf_dir/'arxiv2506.pdf') if fixture_id=='previous_ruled_reference' else (
            fixture_dir/(fixture_id+'.pdf'))
        file=file.expanduser().resolve(strict=True)
        source=hashlib.sha256(file.read_bytes()).hexdigest()
        if source!=spec['source_sha256']:
            raise ValueError('original externally pinned PDF source hash differs')
        preview=propose_original_ruled_row_regions(
            file,source_sha256=source,page=spec['physical_page'],
            rule_bbox_pdf=spec['table_slice_bbox_pdf'],
            column_edges_pdf=spec['column_edges_pdf'],rule_strategy=spec['source_rule_strategy'])
        rows=preview['candidate_rows']
        single_line=sum(x['status']=='SINGLE_LINE_SOURCE_REGION_NEEDS_OPERATOR_REVIEW' for x in rows)
        flagged=len(rows)-single_line
        summary={'source_id':spec['source_id'],'source_sha256':source,
            'public_fixture_url':spec.get('source_url'),
            'original_physical_page':spec['physical_page'],
            'strategy':spec['source_rule_strategy'],
            'source_rule_boundaries':preview['boundaries_count'],
            'source_row_region_proposals':len(rows),
            'source_column_count':len(spec['column_edges_pdf'])-1,
            'source_words_in_operator_region':preview['original_word_count_in_region'],
            'source_words_assigned':preview['assigned_word_count'],
            'source_words_ambiguous_or_unassigned':preview['ambiguous_or_unassigned_original_words'],
            'single_line_rows_needing_review':single_line,
            'flagged_empty_or_multiline_rows':flagged,
            'geometry_status':preview['geometry_status'],
            'operator_review_completed':False,'trusted_dataset_rows':0}
        if fixture_id=='health':
            checks=[]
            for assertion in spec['sample_original_page_word_controls']:
                ri=assertion['row_index']
                actual=[c['source_text_unreviewed'] for c in rows[ri]['cells']]
                checks.append({'row_index':ri,
                    'literal_source_cell_match':actual==assertion['expected_original_cells'],
                    'cell_count':len(actual)})
            summary.update({'original_page_literal_control_rows':len(checks),
                'source_literal_controls_matched':sum(c['literal_source_cell_match'] for c in checks),
                'sample_control_results':checks,
                'complete_entire_table_across_pages':False,
                'authenticated_original_government_source':False})
        if fixture_id=='foo':
            summary['held_on_incomplete_original_word_coverage']=(
                preview['geometry_status']=='ABSTAIN_BOUNDARY_OR_WORD_COVERAGE')
        summaries[fixture_id]=summary
    return {'schema':SCHEMA,
        'authority':'SOURCE_ONLY_OPERATOR_ROW_REGION_PROPOSALS_NOT_DATASET_EVIDENCE',
        'public_external_fixture_count':2,
        'preexisting_reference_document_count':1,
        'external_fixture_selection_blind':False,
        'source_bytes_sha_verified_locally':True,
        'full_unreviewed_source_word_text_committed':False,
        'selected_operator_literal_controls_committed':True,
        'original_pdf_bytes_committed':False,
        'human_second_reviewer':False,
        'table_semantics_verified':False,
        'auto_publish':False,'auto_register_dataset':False,
        'trusted_pdfscope_promotions':0,
        'release_decision':'HOLD_UNVERIFIED_SOURCE_ROWS_AND_HELDOUT_LAYOUT_AMBIGUITIES',
        'cases':summaries}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--fixture-dir',type=Path,required=True)
    p.add_argument('--prior-pdf-dir',type=Path,required=True)
    p.add_argument('--research-drive-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('cannot overwrite source review result')
    result=run(a.oracle,a.fixture_dir,a.prior_pdf_dir,a.research_drive_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False);stream.write('\n')
    for k,s in result['cases'].items():
        print(json.dumps({'source':k,'rows':s['source_row_region_proposals'],
            'assigned':s['source_words_assigned'],
            'source_words':s['source_words_in_operator_region'],
            'geometry':s['geometry_status'],
            'manual_literal_checks':s.get('source_literal_controls_matched')}))


if __name__=='__main__':main()
