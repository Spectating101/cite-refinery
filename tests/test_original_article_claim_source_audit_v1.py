"""Independent original JATS source identity and numeric-anchor contract tests."""
from __future__ import annotations

from copy import deepcopy
import unittest

from cite_refinery.original_article_claim_source_audit import (
    audit_original, DOI, PMCID, NUMERIC_ANCHORS, SCHEMA,
)


def fixture(*, doi=DOI, pmcid=PMCID):
    data=(
        '<article><front><article-meta>'
        f'<article-id pub-id-type="doi">{doi}</article-id>'
        f'<article-id pub-id-type="pmcid">{pmcid}</article-id>'
        '<title-group><article-title>'
        'Long-term evaluation of a zoned catch-neuter-vaccinate-release program '
        'integrating owner engagement and buffer zone strategies for humane dog population management'
        '</article-title></title-group></article-meta></front>'
        '<body><p>'+" ".join(NUMERIC_ANCHORS)+'</p><p>'+('Authenticated structured source only. '*400)+'</p></body>'
        '</article>'
    )
    return data.encode()


class OriginalArticleSourceCheckTests(unittest.TestCase):
    def test_source_identity_and_visible_numeric_text_are_not_claim_adjudications(self):
        j=audit_original(fixture())
        self.assertEqual(j["schema"],SCHEMA)
        self.assertEqual(j["verified_doi"],DOI)
        self.assertEqual(j["verified_pmcid"],PMCID)
        self.assertTrue(all(j["numeric_table_anchor_presence"].values()))
        self.assertFalse(j["nli_model_question_entailment_approved"])
        self.assertFalse(j["archived_curated_excerpt_offsets_verified_against_this_xml"])
        self.assertFalse(j["causal_conclusion_independently_established"])
        self.assertTrue(j["no_article_fulltext_rehosted"])

    def test_canonical_bare_pmc_digits_accepted_not_other_articles(self):
        self.assertTrue(audit_original(fixture(pmcid="13500148"))["original_article_available"])
        with self.assertRaisesRegex(ValueError,"identity disagreement"):
            audit_original(fixture(pmcid="13500149"))
        with self.assertRaisesRegex(ValueError,"identity disagreement"):
            audit_original(fixture(doi="10.0000/unknown"))

    def test_missing_original_numerical_anchor_rejected(self):
        data=fixture().replace(b"0.55488235",b"0.12345678")
        with self.assertRaisesRegex(ValueError,"anchors missing"):
            audit_original(data)

    def test_html_or_xml_bomb_or_wrong_root_rejected(self):
        for val in (b"<html></html>",b"<!DOCTYPE article [ <!ENTITY x 'bad'> ]>"+fixture()):
            with self.assertRaises(ValueError):
                audit_original(val)

    def test_empty_corrupt_xml_does_not_become_zero_findings(self):
        with self.assertRaisesRegex(ValueError,"unavailable"):
            audit_original(b"no article")
        with self.assertRaisesRegex(ValueError,"valid XML"):
            audit_original((b"<article><title>broken"*700))


if __name__=="__main__":
    unittest.main()
