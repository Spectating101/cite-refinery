"""Offline numeric-identity and non-promotion tests; no PDF or CV dependency."""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('financial_source_cell_acceptance', ROOT/'scripts/financial_source_cell_acceptance.py')
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)

class SourceCellAcceptanceTests(unittest.TestCase):
    def test_receipt_pinned_40_manual_cells_no_false_claims(self):
        corpus=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        receipt=json.loads((ROOT/'examples/discovery/financial_source_cell_acceptance_20261103.json').read_text())
        self.assertEqual(corpus['schema'],M.ORACLE_SCHEMA)
        self.assertFalse(corpus['double_reviewed'])
        self.assertEqual(receipt['schema'],M.SCHEMA)
        self.assertEqual(receipt['source_count'],5)
        self.assertEqual(receipt['target_cell_count'],40)
        self.assertEqual(len({s['sha256'] for s in corpus['sources']}),5)
        self.assertEqual(receipt['oracle_review'],'SINGLE_VISUAL_OPERATOR_NOT_DOUBLE_ADJUDICATED')
        self.assertEqual(receipt['operator_review_seconds'],'NOT_TIMED')
        self.assertEqual(receipt['adoption'],'HOLD_PENDING_BROADER_INDEPENDENT_ADJUDICATION')
        self.assertEqual(receipt['totals']['native']['exact_row_period_cells'],16)
        self.assertEqual(receipt['totals']['native']['abstained_cells'],24)
        self.assertEqual(receipt['totals']['optional']['exact_row_period_cells'],40)
        self.assertEqual(receipt['totals']['optional']['abstained_cells'],0)
        self.assertEqual(receipt['totals']['optional']['wrong_cell_associations'],0)
        self.assertEqual({r['source_sha256'] for r in receipt['cases']},{r['sha256'] for r in corpus['sources']})
        for engine in ('native','optional'):
            totals=receipt['totals'][engine]
            self.assertEqual(totals['exact_row_period_cells']+totals['wrong_cell_associations']+totals['abstained_cells'],40)
            self.assertTrue(all(c['engines'][engine]['execution']=='ok' for c in receipt['cases']))

    def test_decoy_same_number_wrong_row_and_missing_column_abstains(self):
        claim={'id':'t','row_label':'Net income','expected_printed_numeric':'1,250','period_key':'current','table_index':0}
        tables=[{'page':1,'table_index':0,'rows':[['Revenue','1,250'],['Net income','900']]}]
        result=M.evaluate_cell(tables,claim,column=1,physical_page=1)
        self.assertEqual(result['status'],'wrong_cell_value')
        self.assertEqual(result['observed'],'900')
        self.assertEqual(M.evaluate_cell(tables,claim,column=2,physical_page=1)['status'],'abstain_missing_column')

    def test_swapped_reporting_period_does_not_wrongly_pass(self):
        target={'id':'t','row_label':'Operating income','expected_printed_numeric':'25','period_key':'2025','table_index':0}
        tables=[{'page':1,'table_index':0,'rows':[['Operating income','23','25']]}]
        self.assertEqual(M.evaluate_cell(tables,target,column=1,physical_page=1)['status'],'wrong_cell_value')
        self.assertEqual(M.evaluate_cell(tables,target,column=2,physical_page=1)['status'],'pass')
        self.assertEqual(M.evaluate_cell(tables,target,column=None,physical_page=1)['status'],'abstain_no_period_column')

    def test_flattened_row_does_not_pass_as_verified_source_cell(self):
        target={'id':'t','row_label':'Net income','expected_printed_numeric':'28,196','period_key':'2025','table_index':0}
        tables=[{'page':1,'table_index':0,'rows':[['Net income $ 23,619 $ 28,196']]}]
        self.assertEqual(M.evaluate_cell(tables,target,column=1,physical_page=1)['status'],'abstain_no_separate_row_label')

    def test_ambiguous_repeated_label_abstains(self):
        target={'id':'t','row_label':'Services','expected_printed_numeric':'28,750','period_key':'2025','table_index':0}
        tables=[{'page':1,'table_index':0,'rows':[['Services','28,750'],['Services','28,750']]}]
        self.assertEqual(M.evaluate_cell(tables,target,column=1,physical_page=1)['status'],'abstain_ambiguous_duplicate_row')

    def test_negative_sign_precision_and_untyped_extra_values(self):
        self.assertEqual(M.canonical_numeric(' $\n (1,691)  '),'(1,691)')
        self.assertEqual(M.canonical_numeric('$ 64.00 $'),'64.00')
        self.assertNotEqual(M.canonical_numeric('64.00'),M.canonical_numeric('64'))
        self.assertIsNone(M.canonical_numeric('64.00 31.00'))
        self.assertIsNone(M.canonical_numeric('1,691 (2025)'))
        self.assertIsNone(M.canonical_numeric('N/A'))

if __name__=='__main__':unittest.main()
