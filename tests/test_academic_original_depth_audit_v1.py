"""Original JATS inspection is source-structural, never scientific adjudication."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xml.sax.saxutils import escape

from cite_refinery.academic_evidence_atlas import build_academic_atlas
from cite_refinery.academic_original_depth_audit import (
    audit_original_jats, attach_original_jats_structure, main as audit_cli,
)

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"research_materials/runtime_trials/richer_corpus_20261020"


def atlas():
    return build_academic_atlas(
        json.loads((DATA/"development_source_manifest.json").read_text()),
        json.loads((DATA/"frozen_split_receipt.json").read_text()))


def fake_article(title):
    return (
        "<article><front><article-meta>"
        "<article-id pub-id-type='doi'>10.1111/fictional.42</article-id>"
        "<title-group><article-title>"+escape(title)+"</article-title></title-group>"
        "</article-meta></front><body>"
        "<sec><title>Materials and methods</title><p>Fictional measurements only.</p></sec>"
        "<sec><title>Results</title><p>Nothing represents real-world data.</p></sec>"
        "<table-wrap id='T1'><caption>Fictional table</caption>"
        "<table><tr><th>Group</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>"
        "</table-wrap></body></article>").encode()


class AcademicOriginalJatsAuditTests(unittest.TestCase):
    def test_real_index_original_article_identity_and_structural_receipt(self):
        a=atlas()
        source=min((v for v in a["sources"].values()
                    if v["origin_genre"]=="full_text_jats"),
                   key=lambda x:sha256(x["id"].encode()).hexdigest())
        number=source["id"][len("PMC-"):]
        xml=fake_article(source["title"])
        observed=[]
        def get(pmcid):
            observed.append(pmcid)
            return ("https://www.ebi.ac.uk/europepmc/webservices/rest/"
                    +pmcid+"/fullTextXML",xml)
        report=audit_original_jats(a,fetcher=get,limit=1)
        self.assertEqual(observed,[number])
        self.assertEqual(report["original_structure_inspected"],1)
        rec=report["records"][0]
        self.assertEqual(rec["section_count"],2)
        self.assertEqual(rec["table_count"],1)
        self.assertEqual(rec["method_heading_candidates"],1)
        self.assertEqual(rec["result_heading_candidates"],1)
        self.assertEqual(rec["original_xml_sha256"],sha256(xml).hexdigest())
        self.assertFalse(rec["original_retrieved_text_digest_revalidated"])
        enriched=attach_original_jats_structure(a,report)
        self.assertEqual(enriched["coverage"]["original_public_jats_structure_inspected"],1)
        self.assertEqual(enriched["coverage"]["independently_validated_scientific_findings"],0)
        self.assertIsNone(enriched["sources"][next(iter(enriched["groups"]["dataset_metadata"]))].get(
            "source_xml_structure_receipt"))
        self.assertNotIn("xml",str(enriched["sources"][source["id"]].keys()))

    def test_mismatched_publication_does_not_raise_scientific_qualification(self):
        a=atlas()
        def mismatched(pmcid):
            return ("https://www.ebi.ac.uk/europepmc/webservices/rest/"+pmcid+"/fullTextXML",
                    fake_article("Entirely unrelated fake article"))
        report=audit_original_jats(a,fetcher=mismatched,limit=1)
        self.assertEqual(report["original_structure_inspected"],0)
        self.assertEqual(report["bibliographic_or_original_title_mismatch"],1)
        enriched=attach_original_jats_structure(a,report)
        self.assertEqual(enriched["coverage"]["original_public_jats_structure_inspected"],0)

    def test_publisher_network_unavailable_never_silent_success(self):
        a=atlas()
        def broken(pmcid):
            raise TimeoutError("fictional timeout")
        report=audit_original_jats(a,fetcher=broken,limit=1)
        self.assertEqual(report["records"][0]["status"],
                         "publisher_source_unavailable_or_unparseable")
        self.assertEqual(report["original_structure_inspected"],0)

    def test_forged_original_publisher_adjudication_rejected(self):
        a=atlas()
        def get(pmcid):
            source=next(v for v in a["sources"].values() if
                        v["id"]=="PMC-"+pmcid)
            return ("https://www.ebi.ac.uk/europepmc/webservices/rest/"+pmcid+"/fullTextXML",
                    fake_article(source["title"]))
        report=audit_original_jats(a,fetcher=get,limit=1)
        bad=deepcopy(report)
        bad["records"][0]["scientific_findings_or_study_design_verified"]=True
        with self.assertRaisesRegex(ValueError,"authority"):
            attach_original_jats_structure(a,bad)
        bad=deepcopy(report)
        bad["records"][0]["original_xml_sha256"]="forged"
        with self.assertRaisesRegex(ValueError,"digest"):
            attach_original_jats_structure(a,bad)
        bad=deepcopy(report)
        bad["records"].append(deepcopy(bad["records"][0]))
        bad["sampled_count"]+=1
        bad["original_structure_inspected"]+=1
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            attach_original_jats_structure(a,bad)


if __name__=="__main__":
    unittest.main()
