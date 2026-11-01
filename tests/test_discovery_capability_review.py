"""Contract tests for Atlas conservative capability review and history diff."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from cite_refinery.discovery_capability_review import (
    SCHEMA, REQUIREMENTS_SCHEMA, load_requirements, match_one, review, changes,
)


def requirements():
    return {"schema": REQUIREMENTS_SCHEMA, "requirements": [
        {"id":"pv_qa","project":"policy_lab","question":"Find PV quality diagnostics",
         "must_match":[["photovolta","solar","pv"],["anomal","quality","fault"]],
         "bonus":["dataset"],"allow_source_types":["research","datasets","software"]},
        {"id":"nocturnal_custody","project":"nocturnal","question":"Archive web evidence",
         "must_match":[["web","website","online"],["archiv","preserv"]],
         "bonus":["evidence"],"allow_source_types":["software"]},
    ]}


def record(id="src:123",title="Photovoltaic Anomaly Detection Dataset",
           source="openalex",typ="research",desc="Data for failure analysis"):
    return {"id":id, "title":title,"description":desc,
            "source_url":"https://doi.org/10.1234/pv",
            "entity_key":"doi:10.1234/pv",
            "discovery_provider":source,"observation_type":typ}


def collection(records=None,source_state="ok"):
    return {"schema":"cite_refinery.multisource_discovery.v1",
            "records":records if records is not None else [record()],
            "source_results":[{"source":"src","state":source_state}]}


class ReviewTests(unittest.TestCase):
    def test_prespecified_requirement_match(self):
        req=load_requirements(requirements())[0]
        actual=match_one(req,record())
        self.assertIsNotNone(actual)
        self.assertEqual(actual["decision"],"SOURCE_REVIEW_NEEDED")
        self.assertEqual(len(actual["matched_mandatory_concepts"]),2)

    def test_no_false_pv_match_from_unrelated_topic_tags(self):
        req=load_requirements(requirements())[0]
        neg=record(title="Automotive anomaly detection",desc="Photovoltaic market guide",
                   typ="community")
        self.assertIsNone(match_one(req,neg))
        neg["observation_type"]="research"
        neg["title"]="Automotive inventory automation"
        neg["description"]="Published market report"
        self.assertIsNone(match_one(req,neg))

    def test_stem_does_not_match_inside_other_words(self):
        req=load_requirements(requirements())[0]
        neg=record(title="review of pavements anomaly detection",
                   desc="data set of roofing materials")
        self.assertIsNone(match_one(req,neg))

    def test_abstention_count_and_no_auto_adoption(self):
        data=collection([record(),record(id="src:4",title="Unrelated tool",desc="random item")])
        out=review(data,requirements())
        self.assertEqual(out["records_abstained"],1)
        self.assertEqual(out["requirements"][0]["matched"],1)
        self.assertEqual(out["requirements"][1]["matched"],0)
        self.assertTrue(all(x.get("decision")=="SOURCE_REVIEW_NEEDED"
                            for g in out["requirements"] for x in g["unreviewed"]))

    def test_exact_identity_history_is_a_diff_not_deletion(self):
        old=collection([record(id="src:1"),record(id="src:2")])
        new=collection([record(id="src:1",title="Revised PV anomaly paper"),
                        record(id="src:3")])
        result=changes(old,new)
        c={r["record_id"]:r["status"] for r in result["changes"]}
        self.assertEqual(c["src:1"],"revised_observation")
        self.assertEqual(c["src:2"],"not_observed_in_latest_sample")
        self.assertEqual(c["src:3"],"new_observation")
        self.assertFalse(any(v=="deleted" for v in c.values()))
        new["source_results"][0]["state"]="unavailable"
        c2={r["record_id"]:r["status"] for r in changes(old,new)["changes"]}
        self.assertEqual(c2["src:2"],"source_not_compared")

    def test_reject_unbounded_and_untrusted_requirements(self):
        payload=requirements()
        payload["requirements"][0]["must_match"]=[["arbitrary"]]
        with self.assertRaises(ValueError):
            load_requirements(payload)
        payload=requirements()
        payload["requirements"][0]["must_match"][0]=["http://127.0.0.1"]
        with self.assertRaises(ValueError):
            load_requirements(payload)

    def test_real_manifest_loads(self):
        root=Path(__file__).resolve().parent.parent
        x=json.loads((root/"examples/discovery/capability_requirements_v1.json").read_text())
        self.assertEqual(len(load_requirements(x)),4)


if __name__=="__main__":
    unittest.main()
