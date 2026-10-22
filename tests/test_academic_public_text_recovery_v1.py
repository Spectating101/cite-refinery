"""Frozen 103-source original JATS recovery: original XML, text hash, isolation."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import unittest

from cite_refinery.academic_evidence_atlas import build_academic_atlas
from cite_refinery.academic_public_text_recovery import recover, SCHEMA,_jats_excerpt,BASE

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"research_materials/runtime_trials/richer_corpus_20261020"


def original_map():
    return build_academic_atlas(
        json.loads((FROZEN/"development_source_manifest.json").read_text("utf-8")),
        json.loads((FROZEN/"frozen_split_receipt.json").read_text("utf-8")))


def published_fixture():
    # Controlled realistic JATS fixture, NOT a real publisher response.
    paragraph="This sample paragraph tests precise recovery of the development extractor. "*4
    xml=("<article><front><article-meta>"
         "<title-group><article-title>Demonstration of source extraction fidelity</article-title></title-group>"
         "<abstract><p>The short source describes a registered observational design.</p></abstract>"
         "</article-meta></front><body>"
         "<sec><title>Methods</title><p>"+paragraph+"</p></sec>"
         "<sec><title>Results</title><p>"+paragraph.replace("tests","confirms")+"</p></sec>"
         "</body></article>")
    return xml.encode("utf-8")


class OriginalPublisherJatsRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas=original_map()
        cls.pmcid=sorted(sid for sid,entry in cls.atlas["sources"].items()
                         if entry["origin_genre"]=="full_text_jats")[0]
        cls.pmcurl=BASE+"/"+cls.pmcid.removeprefix("PMC-")+"/fullTextXML"
        cls.xml=published_fixture()
        cls.title,cls.text,cls.sections=_jats_excerpt(cls.xml)
        cls.fixture_atlas=deepcopy(cls.atlas)
        cls.fixture_atlas["sources"][cls.pmcid]["text_sha256"]=sha256(
            cls.text.encode("utf-8")).hexdigest()

    def test_same_original_extractor_and_matching_digest_recovery(self):
        self.assertGreaterEqual(self.sections,2)
        self.assertGreaterEqual(len(self.text),100)
        def fetch(url):
            self.assertEqual(url,self.pmcurl)
            return self.xml,url
        receipt,texts=recover(self.fixture_atlas,source_ids=[self.pmcid],
                              fetch=fetch)
        self.assertEqual(receipt["schema"],SCHEMA)
        self.assertEqual(receipt["requested"],1)
        self.assertEqual(receipt["recovered"],1)
        self.assertEqual(texts,{self.pmcid:self.text})
        self.assertEqual(receipt["records"][0]["status"],
                         "original_development_extraction_sha256_recovered")
        self.assertFalse(receipt["heldout_document_text_accessed"])
        self.assertFalse(receipt["model_called"])

    def test_changed_publisher_text_is_not_accepted_as_the_frozen_original(self):
        def changed(url):
            return self.xml.replace(b"design",b"survey"),url
        receipt,texts=recover(self.fixture_atlas,source_ids=[self.pmcid],
                              fetch=changed)
        self.assertFalse(texts)
        self.assertEqual(receipt["recovered"],0)
        self.assertEqual(receipt["digest_mismatches"],1)
        self.assertEqual(receipt["records"][0]["status"],
                         "publisher_source_version_or_extraction_digest_mismatch")
        self.assertNotEqual(receipt["records"][0]["retrieved_extracted_text_sha256"],
                            receipt["records"][0]["frozen_extracted_text_sha256"])

    def test_real_public_103_source_digest_not_replaced_by_synthetic_fixture(self):
        receipt,texts=recover(self.atlas,source_ids=[self.pmcid],
                              fetch=lambda url:(self.xml,url))
        self.assertEqual(receipt["recovered"],0)
        self.assertEqual(receipt["digest_mismatches"],1)
        self.assertFalse(texts)

    def test_original_source_identity_and_heldout_boundary(self):
        with self.assertRaisesRegex(ValueError,"not in 103"):
            recover(self.atlas,source_ids=["PMC-PMC999999999"],
                    fetch=lambda _:self.xml)
        zen=next(sid for sid,r in self.atlas["sources"].items()
                 if r["origin_genre"]=="dataset_metadata")
        with self.assertRaisesRegex(ValueError,"only the original Europe PMC"):
            recover(self.atlas,source_ids=[zen],fetch=lambda _:self.xml)
        with self.assertRaisesRegex(ValueError,"Repeated"):
            recover(self.atlas,source_ids=[self.pmcid,self.pmcid],fetch=lambda _:self.xml)
        with self.assertRaisesRegex(ValueError,"1-12"):
            recover(self.atlas,source_ids=[],fetch=lambda _:self.xml)

    def test_malformed_xml_and_redirect_are_unavailable_not_matching(self):
        receipt,texts=recover(self.fixture_atlas,source_ids=[self.pmcid],
                         fetch=lambda url:(b"<article>broken",url))
        self.assertEqual(receipt["unavailable_or_unparseable"],1)
        self.assertEqual(texts,{})
        receipt,texts=recover(self.fixture_atlas,source_ids=[self.pmcid],
                         fetch=lambda url:(self.xml,"https://attacker.invalid/"))
        self.assertEqual(receipt["unavailable_or_unparseable"],1)
        self.assertEqual(texts,{})


if __name__=="__main__":
    unittest.main()
