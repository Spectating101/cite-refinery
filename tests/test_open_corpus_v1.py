"""No-preassigned-map corpus collector, source integrity and fail-closed claims."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cite_refinery.open_corpus import collect,search_openalex,_abstract,SCHEMA
from cite_refinery.open_corpus_map import stable_shards,validate_map,map_prompt

def _academic(query,limit=3):
    return [{"id":"EPMC-"+str(i),"title":"Area-specific study "+str(i),
             "url":"https://doi.org/10.1000/study"+str(i),
             "text":"Community health exposure was measured using a survey and time-based observations, but these results did not establish effects of a government intervention.",
             "origin_type":"scholarly_abstract_lead","source_scope":"abstract only"} for i in range(limit)]
def _openalex(query,limit=3):
    return [{"id":"OA-"+str(i),"title":"Independent methodology "+str(i),
             "url":"https://doi.org/10.2000/method"+str(i),
             "text":"A randomized reference study evaluated observational bias and proposed a new methodology for public monitoring, subject to uncertainty about real operational effects.",
             "origin_type":"openalex_bibliographic_abstract_lead","source_scope":"abstract only"} for i in range(limit)]
def _official(query,limit=2):
    return [{"id":"OFF-"+str(i),"title":"Institutional public guidance "+str(i),
             "url":"https://www.who.int/test"+str(i),
             "text":"An institutional advisory recommends that public organizations monitor occupational health and environmental exposure. These recommendations are not a confirmed deployment.",
             "origin_type":"official_webpage_excerpt_unverified","source_scope":"published page"} for i in range(limit)]

def sample():
    with TemporaryDirectory() as folder:
        c,m=collect(folder,queries={"test":{"academic":"test academic research collection",
                                           "official":"test official material collection"}},
                    europe=2,openalex=3,official=2,efunc=_academic,afunc=_openalex,ofunc=_official)
        return c,m

def accepted_for(chunk):
    readings=[]
    for s in chunk:
        readings.append({"source_id":s["id"],"role":"academic_method","fit":"relevant",
                         "statement":"A study describes evidence and uncertainty about measurement.",
                         "quote":s["text"][:65],
                         "scope":"Published study methodological comparison",
                         "caveat":"No independent causal effect is verified by this excerpt."})
    return {"batch_id":"shard-00","readings":readings,
            "clusters":[{"name":"Measurement uncertainty in public problems",
                         "source_ids":[x["id"] for x in chunk],
                         "question":"Can these measurement approaches distinguish effect from intervention rhetoric?"}],
            "links":[],"unknowns":[
             {"question":"What field observations could independently verify changes?",
              "source_ids":[chunk[0]["id"]]},
             {"question":"Which sources describe deployment rather than guidelines?",
              "source_ids":[chunk[1]["id"]]}]}

class CorpusTests(unittest.TestCase):
    def test_openalex_inverted_abstract(self):
        self.assertEqual(_abstract({"One":[0],"two":[1],"result":[2]}),"One two result")
    def test_local_dump_manifest_never_copies_publisher_passages(self):
        c,m=sample()
        self.assertEqual(c["schema"],SCHEMA)
        self.assertEqual(c["source_count"],7)
        self.assertEqual(len(m["source_records"]),7)
        self.assertFalse(m["ontology_preassigned"])
        self.assertTrue(all("text" not in entry for entry in m["source_records"]))
        self.assertTrue(all(s["sha256"] for s in c["sources"]))
        self.assertEqual(len(stable_shards(c,max_per=4)),2)
    def test_all_sources_required_and_exact_quotes(self):
        c,_=sample();batch=stable_shards(c,max_per=9)[0]
        raw=accepted_for(batch)
        v=validate_map(raw,batch,"shard-00")
        self.assertEqual(v["source_count"],7)
        self.assertEqual(v["accepted_scientific_conclusions"],0)
        self.assertEqual(v["links"],[])
        self.assertNotIn("h01",map_prompt(batch,"shard-00"))
    def test_role_and_source_tamper_rejected(self):
        c,_=sample();batch=stable_shards(c,max_per=9)[0]
        r=accepted_for(batch)
        r["readings"][0]["quote"]="Invented program achieved zero worker deaths, as proven by WHO."
        with self.assertRaisesRegex(ValueError,"source quote"):validate_map(r,batch,"shard-00")
        r=accepted_for(batch);r["readings"][0]["role"]="certified_outcome_success"
        with self.assertRaisesRegex(ValueError,"source role"):validate_map(r,batch,"shard-00")
        r=accepted_for(batch);r["readings"].pop()
        with self.assertRaisesRegex(ValueError,"Every source"):validate_map(r,batch,"shard-00")
    def test_spurious_or_unrelated_links_not_required(self):
        c,_=sample();batch=stable_shards(c,max_per=9)[0]
        r=accepted_for(batch);r["links"]=[{"from_source":batch[0]["id"],
                                           "to_source":"NOT_ACTUAL_SOURCE",
                                           "relation":"corroborates",
                                           "reason":"These papers appear superficially similar but have no relation."}]
        with self.assertRaisesRegex(ValueError,"Unsupported edge"):validate_map(r,batch,"shard-00")

if __name__=="__main__":unittest.main()
