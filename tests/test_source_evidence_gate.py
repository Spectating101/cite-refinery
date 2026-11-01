"""Offline evidence gate tests; provider calls are all fixtures."""
import base64
import hashlib
import json
import unittest
from pathlib import Path
from cite_refinery.source_evidence_gate import (
    CONFIG_SCHEMA, SourceUnverified, assess, compare_labels, load_config,
    original_receipt, run, _resolve,
)


def rec(url="https://github.com/Example/Repo", key="github:example/repo"):
    return {"id":"github_archive:example/repo", "title":"Evidence web archives",
            "description":"Capture websites with hashes","source_url":url,
            "entity_key":key,"observation_type":"software","discovery_provider":"github_search"}


def config():
    return {"schema":CONFIG_SCHEMA,"requirements":{"schema":"cite_refinery.discovery_requirements.v1",
        "requirements":[{"id":"nocturnal_archiving","project":"nocturnal","question":"Archive websites",
         "must_match":[["web","website"],["archiv","capture"]],"bonus":["evidence"],
         "allow_source_types":["software"]}]},
        "gates":[{"requirement_id":"nocturnal_archiving",
          "evidence_must_contain":[["website","web page"],["archive","capture"],["hash","timestamp"]]}],
        "originals":{}}


def gh_doc(text):
    raw=text.encode()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    return {"encoding":"base64","content":base64.b64encode(raw).decode(),"sha":sha,
            "html_url":"https://github.com/Example/Repo/blob/main/README.md"}


class EvidenceGateTests(unittest.TestCase):
    def gate(self, text):
        cfg=load_config(config())
        return assess(rec(),cfg["requirements"][0],cfg["gates"]["nocturnal_archiving"],
                      originals={},github=lambda _:gh_doc(text))

    def test_readme_positive_and_receipt(self):
        o=self.gate("We archive websites. Each capture includes a timestamp and SHA hash.")
        self.assertEqual(o["status"],"DOC_CLAIMS_MATCH")
        self.assertEqual(len(o["original_sha256"]),64)
        self.assertEqual(len(o["pinned_source_blob"]),40)

    def test_offscope_but_keyword_matching_title(self):
        r=self.gate("This is a Next.js business website for selling services.")
        self.assertEqual(r["status"],"DOC_MODALITY_NOT_ESTABLISHED")

    def test_large_readme_bounded_prefix_full_integrity(self):
        doc="We archive websites with a timestamp and hash. " + ("Relevant documentation. "*5000)
        out=self.gate(doc)
        self.assertEqual(out["status"],"DOC_CLAIMS_MATCH")
        self.assertTrue(out["source_text_truncated"])
        self.assertEqual(len(out["original_sha256"]),64)

    def test_awesome_list_is_reference_not_implementation(self):
        from cite_refinery.source_evidence_gate import assess
        cfg=load_config(config())
        row=rec(url="https://github.com/Example/awesome-web-archiving",
                key="github:example/awesome-web-archiving")
        out=assess(row,cfg["requirements"][0],cfg["gates"]["nocturnal_archiving"],
                   originals={},github=lambda name:{
                       **gh_doc("We archive websites and preserve a timestamp hash."),
                       "html_url":"https://github.com/Example/awesome-web-archiving/blob/main/README.md"})
        self.assertEqual(out["status"],"SOURCE_REFERENCE_LIST_ONLY")

    def test_invalid_blob_identity_abstains(self):
        cfg=load_config(config())
        def bad(_):
            o=gh_doc("archive website hash");o["sha"]="0"*40;return o
        out=assess(rec(),cfg["requirements"][0],cfg["gates"]["nocturnal_archiving"],originals={},github=bad)
        self.assertEqual(out["status"],"ABSTAIN_ORIGINAL_UNAVAILABLE")
        self.assertIn("SHA1",out["unavailable_reason"])

    def test_cross_repo_identity_and_unapproved_source_url_blocked(self):
        with self.assertRaises(SourceUnverified):
            _resolve(rec(key="github:wrong/repo"),{})
        with self.assertRaises(ValueError):
            load_config({**config(),"originals":{"id":"http://127.0.0.1/secret"}})

    def test_zenodo_metadata_id_check(self):
        r=rec(url="https://doi.org/10.5281/zenodo.1111")
        valid=json.dumps({"id":1111,"metadata":{"title":"PV data",
            "description":"<p>Two photovoltaic plants with inverter faults</p>"}}).encode()
        result=original_receipt(r,originals={},http=lambda _:valid)
        self.assertIn("photovoltaic plants",result["source_text"])
        invalid=valid.replace(b"1111",b"2222")
        with self.assertRaises(SourceUnverified):
            original_receipt(r,originals={},http=lambda _:invalid)

    def test_arxiv_metadata_identity(self):
        r=rec(url="https://doi.org/10.7777/test")
        original={r["id"]:"https://arxiv.org/abs/2609.07652"}
        data=(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
              b'<id>http://arxiv.org/abs/2609.07652v1</id>'
              b'<title>Science claim</title><summary>Citation evidence review</summary>'
              b'</entry></feed>')
        out=original_receipt(r,originals=original,http=lambda _:data)
        self.assertIn("Citation evidence",out["source_text"])
        with self.assertRaises(SourceUnverified):
            original_receipt(r,originals=original,http=lambda _:data.replace(b"2609.07652v1",b"2609.07653v1"))

    def test_unavailable_remains_abstention(self):
        cfg=load_config(config())
        def unavailable(_):raise SourceUnverified("rate_limited")
        out=assess(rec(),cfg["requirements"][0],cfg["gates"]["nocturnal_archiving"],
                   originals={},github=unavailable)
        self.assertEqual(out["status"],"ABSTAIN_ORIGINAL_UNAVAILABLE")

    def test_run_rejects_unknown_collection_and_duplicate_cases(self):
        collection={"schema":"cite_refinery.multisource_discovery.v1","records":[rec()]}
        cases=[{"record_id":rec()["id"],"requirement_id":"nocturnal_archiving"}]
        data=run(collection,config(),cases,github=lambda _:gh_doc("archive website hash"))
        self.assertEqual(data["counts"]["DOC_CLAIMS_MATCH"],1)
        with self.assertRaises(ValueError):
            run(collection,config(),cases+cases)
        with self.assertRaises(ValueError):
            run({**collection,"schema":"wrong"},config(),cases)

    def test_diagnostic_labels_do_not_promote(self):
        result={"cases":[{"record_id":"x","requirement_id":"r","status":"DOC_CLAIMS_MATCH"},
                         {"record_id":"y","requirement_id":"r","status":"DOC_MODALITY_NOT_ESTABLISHED"},
                         {"record_id":"z","requirement_id":"r","status":"ABSTAIN_ORIGINAL_UNAVAILABLE"}]}
        labels={"cases":[{"record_id":"x","requirement_id":"r","decision":"ON_SCOPE_BENCHMARK_LEAD"},
                         {"record_id":"y","requirement_id":"r","decision":"OFF_SCOPE"},
                         {"record_id":"z","requirement_id":"r","decision":"ON_SCOPE_BENCHMARK_LEAD"}]}
        stats=compare_labels(result,labels)
        self.assertEqual(stats["true_positive"],1)
        self.assertEqual(stats["false_positive"],0)
        self.assertEqual(stats["missed_positive_or_abstained"],1)
        self.assertTrue(stats["no_auto_adoption"])

    def test_checked_in_gate_config(self):
        root=Path(__file__).resolve().parent.parent
        cfg=json.loads((root/"examples/discovery/original_source_gate_config.json").read_text())
        self.assertEqual(len(load_config(cfg)["gates"]),4)


if __name__=="__main__":
    unittest.main()
