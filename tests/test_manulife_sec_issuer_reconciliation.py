"""Pinned issuer-filed EDGAR cross-format evidence without trusted promotion."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ManulifeSECSourceReconciliation(unittest.TestCase):
    def test_original_edgar_issuer_html_corroborates_all_manual_figures(self):
        receipt=json.loads((ROOT/'examples/discovery/manulife_sec_issuer_reconciliation_20261103.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/manulife_sec_issuer_reconciliation_oracle_20261103.json').read_text())
        figure=json.loads((ROOT/'examples/discovery/heterogeneous_original_source_cell_oracle_20261103.json').read_text())
        self.assertEqual(receipt['schema'],'atlas.manulife_sec_issuer_reconciliation.v1')
        self.assertEqual(receipt['reproduced_figure_source_sha256'],figure['source_sha256'])
        self.assertTrue(receipt['local_original_html_sha256_verified'])
        self.assertFalse(receipt['issuer_original_pdf_sha256_verified'])
        self.assertFalse(receipt['independent_second_human_review'])
        self.assertTrue(receipt['manual_cross_format_metric_alignment'])
        self.assertEqual(receipt['original_figure_parser_strict_source_matches'],6)
        self.assertEqual(receipt['original_figure_parser_strict_source_abstentions'],2)
        self.assertEqual(receipt['trusted_pdfscope_promotions'],0)
        self.assertEqual(receipt['trusted_dataset_registrations'],0)
        self.assertFalse(receipt['auto_publish'])
        self.assertFalse(receipt['auto_register_dataset'])
        self.assertFalse(receipt['original_html_bytes_committed'])
        self.assertFalse(receipt['original_figure_pdf_bytes_committed'])
        self.assertEqual(receipt['source_document_type'],'ISSUER_AUTHORED_SEC_EDGAR_EXHIBITS_NOT_MANULIFE_COM_PDF')
        self.assertEqual(receipt['release_decision'],'HOLD_INDEPENDENT_HUMAN_REVIEW_AND_ORIGINAL_PDF_LINKAGE')
        self.assertEqual(set(receipt['source_roles']),{'shareholder_report','earnings_release'})
        for role,expected_count in [('shareholder_report',8),('earnings_release',7)]:
            evidence=receipt['source_roles'][role]
            manual=oracle['primary_issuer_edgar_exhibits'][role]
            self.assertEqual(evidence['source_url'],manual['url'])
            self.assertEqual(evidence['source_sha256'],manual['sha256'])
            self.assertTrue(evidence['source_url'].startswith('https://www.sec.gov/Archives/edgar/data/1086888/'))
            self.assertEqual(evidence['source_kind'],'SEC_EDGAR_ISSUER_FILED_EXHIBIT_HTML_NOT_DIRECT_ISSUER_PDF')
            self.assertEqual((evidence['checked'],evidence['matched'],evidence['abstained']),
                             (expected_count,expected_count,0))
            self.assertEqual(len(evidence['row_verdicts']),expected_count)
            for cell in evidence['row_verdicts']:
                self.assertEqual(cell['quarter_header'],'1Q24')
                self.assertEqual(cell['status'],'issuer_edgar_row_and_unit_witness_match')
                self.assertEqual(len(cell['checks']),6)
                self.assertTrue(all(cell['checks'].values()))
        self.assertEqual((receipt['expense_qualifier_context']['checked'],
                          receipt['expense_qualifier_context']['matched'],
                          receipt['expense_qualifier_context']['abstained']),(1,1,0))
        self.assertEqual(receipt['expense_qualifier_context']['row_verdicts'][0]['source_numeric'],'1,102')

    def test_ape_rounding_is_explicit_and_secondary_labels_not_fuzzily_approved(self):
        receipt=json.loads((ROOT/'examples/discovery/manulife_sec_issuer_reconciliation_20261103.json').read_text())
        first={r['case_id']:r for r in receipt['source_roles']['shareholder_report']['row_verdicts']}
        self.assertEqual(len(first),8)
        ape=first['manulife-04']
        self.assertEqual(ape['issuer_numeric'],'1,883')
        self.assertEqual(ape['reproduced_figure_numeric'],'$1.9')
        self.assertEqual(ape['issuer_unit'],'CAD_millions')
        self.assertEqual(ape['reconciliation'],'millions_to_billions_one_decimal')
        self.assertEqual(first['manulife-05']['issuer_label'],'NBV')
        self.assertEqual(first['manulife-06']['issuer_label'],'New business CSM')
        self.assertTrue(receipt['manual_cross_format_metric_alignment'])
        # This cross-format exercise does not reverse either arXiv parser-abstention.
        self.assertEqual(receipt['original_figure_parser_strict_source_abstentions'],2)
        for item in ('manulife-05','manulife-06'):
            self.assertEqual(first[item]['status'],'issuer_edgar_row_and_unit_witness_match')

if __name__=='__main__':unittest.main()
