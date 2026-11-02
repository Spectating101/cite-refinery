"""Bounded typed capability registry and mapping tests (offline fixtures)."""
import base64
import hashlib
import json
import unittest
from pathlib import Path

from cite_refinery.typed_capability_map import (
    read_rules, read_needs, windows, classify_original, compile_map,
)


def _orig(text):
    return {"source_text":text,"source_url":"https://github.com/example/repo/blob/main/README.md",
            "sha256":"a"*64,"pinned_source_blob":"b"*40,"source_kind":"github_readme"}


def _gh(text, repo):
    data=text.encode()
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    return {"encoding":"base64","content":base64.b64encode(data).decode(),"sha":sha,
            "html_url":"https://github.com/"+repo+"/blob/main/README.md"}


ROOT=Path(__file__).resolve().parent.parent/"examples/discovery"
RULES=json.loads((ROOT/"typed_capability_rules.json").read_text())
NEEDS=json.loads((ROOT/"typed_project_needs.json").read_text())
CAPS={c["id"]:c for c in read_rules(RULES)}


def rec(name="example/repo"):
    return {"id":"case:"+name, "title":name,
            "source_url":"https://github.com/"+name,"entity_key":"github:"+name.lower(),
            "observation_type":"software","discovery_provider":"github_search"}


class TypedMapTests(unittest.TestCase):
    def test_rulebook_and_requirements_references_valid(self):
        self.assertGreaterEqual(len(CAPS),8)
        self.assertEqual(len(read_needs(NEEDS,set(CAPS))),7)
        self.assertEqual(CAPS["archive_replay"]["input"],"Existing web archive")

    def test_web_capture_not_automatically_replay(self):
        text="This tool captures websites as WARC and HTML snapshots."
        self.assertIsNotNone(classify_original(_orig(text),CAPS["web_capture"],source_category="software"))
        self.assertIsNone(classify_original(_orig(text),CAPS["archive_replay"],source_category="software"))

    def test_archive_replay_not_automatically_capture(self):
        text="Tool for replaying archived web pages from web archives using Wayback."
        self.assertIsNotNone(classify_original(_orig(text),CAPS["archive_replay"],source_category="software"))
        self.assertIsNone(classify_original(_orig(text),CAPS["web_capture"],source_category="software"))

    def test_pv_cell_image_does_not_satisfy_plant_timeseries(self):
        img="Photovoltaic cell anomaly detection dataset with labeled electroluminescence images of module defects."
        plant="Photovoltaic plant field measurements from inverters; 30 seconds time series for detected fault events."
        self.assertIsNotNone(classify_original(_orig(img),CAPS["pv_cell_image_dataset"],source_category="datasets"))
        self.assertIsNone(classify_original(_orig(img),CAPS["pv_plant_timeseries_dataset"],source_category="datasets"))
        self.assertIsNotNone(classify_original(_orig(plant),CAPS["pv_plant_timeseries_dataset"],source_category="datasets"))

    def test_pdf_extraction_not_same_as_cell_verification(self):
        extract="Extract tables from PDF files with a parser for structured rows."
        validate="Validate the PDF table against source values, checking keyed cell assertions and exact row labels."
        self.assertIsNotNone(classify_original(_orig(extract),CAPS["pdf_table_extraction"],source_category="software"))
        self.assertIsNone(classify_original(_orig(extract),CAPS["pdf_cell_validation"],source_category="software"))
        self.assertIsNotNone(classify_original(_orig(validate),CAPS["pdf_cell_validation"],source_category="software"))

    def test_far_apart_sections_are_not_a_single_documentary_claim(self):
        text="Capturing websites into HTML snapshots. " + "unrelated filler " * 250 + "For offline replay of recorded pages."
        self.assertIsNone(classify_original(_orig(text),CAPS["archive_replay"],source_category="software"))
        self.assertIsNotNone(classify_original(_orig(text),CAPS["web_capture"],source_category="software"))

    def test_cell_extractor_mention_of_checks_is_not_validation(self):
        excerpt = "PDF table extraction library. Extract tables and row cell values. Check extraction confidence and options."
        self.assertIsNone(classify_original(_orig(excerpt),CAPS["pdf_cell_validation"],source_category="software"))

    def test_review_excerpt_centers_actual_evidence_not_readme_badges(self):
        excerpt = ("status badges and unrelated headers. "*22)+("This program captures websites into HTML and WARC snapshots.")
        hit = classify_original(_orig(excerpt),CAPS["web_capture"],source_category="software")
        self.assertIsNotNone(hit)
        self.assertIn("captures websites",hit["evidence"]["excerpt"])

    def test_candidate_edge_only_from_source_supported_capability(self):
        item=rec("example/repo")
        collection={"schema":"cite_refinery.multisource_discovery.v1","records":[item]}
        cases={"schema":"cite_refinery.typed_trial_cases.v1","cases":[{"record_id":item["id"]}],"originals":{}}
        src="We capture websites as HTML snapshot and WARC archives."
        result=compile_map(collection,RULES,NEEDS,cases,github=lambda _: _gh(src,"example/repo"))
        ids={edge["candidate_capability_id"] for edge in result["candidate_edges"]}
        self.assertIn("web_capture",ids)
        self.assertNotIn("archive_replay",ids)
        self.assertTrue(all(edge["authority"]=="NO_CODE_EXECUTION_NO_ADOPTION" for edge in result["candidate_edges"]))

    def test_list_is_not_a_software_adoption_candidate(self):
        item=rec("example/awesome-web-archiving")
        collection={"schema":"cite_refinery.multisource_discovery.v1","records":[item]}
        cases={"schema":"cite_refinery.typed_trial_cases.v1","cases":[{"record_id":item["id"]}],"originals":{}}
        text="Websites capture HTML archive and replaying web archives with Wayback."
        result=compile_map(collection,RULES,NEEDS,cases,github=lambda _: _gh(text,"example/awesome-web-archiving"))
        self.assertEqual(result["sources"][0]["status"],"DISCOVERY_INDEX_ONLY")
        self.assertEqual(result["candidate_edges"],[])

    def test_missing_source_abstains_without_negative_assertion(self):
        item=rec()
        collection={"schema":"cite_refinery.multisource_discovery.v1","records":[item]}
        cases={"schema":"cite_refinery.typed_trial_cases.v1","cases":[{"record_id":item["id"]}],"originals":{}}
        result=compile_map(collection,RULES,NEEDS,cases,github=lambda _: (_ for _ in ()).throw(ValueError("unavailable")))
        self.assertEqual(result["sources"][0]["status"],"SOURCE_UNAVAILABLE")
        self.assertFalse(result["candidate_edges"])

    def test_disallowed_original_override_and_duplicate_cases(self):
        item=rec()
        collection={"schema":"cite_refinery.multisource_discovery.v1","records":[item]}
        cases={"schema":"cite_refinery.typed_trial_cases.v1","cases":[{"record_id":item["id"]}],"originals":{item["id"]:"https://localhost/private"}}
        with self.assertRaises(ValueError):
            compile_map(collection,RULES,NEEDS,cases)
        cases["originals"]={}
        cases["cases"].append({"record_id":item["id"]})
        with self.assertRaises(ValueError):
            compile_map(collection,RULES,NEEDS,cases)


if __name__ == "__main__":
    unittest.main()
