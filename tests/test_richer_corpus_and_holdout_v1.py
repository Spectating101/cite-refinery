"""Real-material parser and leakage-free frozen split tests."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy
import json
import unittest

from cite_refinery.richer_public_sources import _jats_excerpt, acquire,SCHEMA
from cite_refinery.frozen_corpus_split import freeze,DOMAIN_HOLDOUT

def fake_doc(id,quota,type="full_text_jats",title=None):
    uri=f"https://example.org/doc/{id}"
    body=("This detailed report contains community measurements, respondent"
          " observations, statistical uncertainty, program implementation context."
          " No measured causal effect is independently confirmed. ")*20
    import hashlib
    return {
        "id":id,"canonical_url":uri,
        "title":title or "Long-term area case "+id,
        "text":body,"text_sha256":hashlib.sha256(body.encode()).hexdigest(),
        "type":type,"field":"fulltext",
        "collection_quota":quota,"word_count":len(body.split()),
    }

class RichCollectionTests(unittest.TestCase):
    def test_full_jats_section_parsing(self):
        xml=b'''<?xml version="1.0" encoding="utf-8"?>
        <article><front><article-meta><title-group><article-title>Community intervention outcomes</article-title>
        </title-group><abstract><p>This abstract describes the study context and its measurement period.</p></abstract>
        </article-meta></front><body><sec><title>Methods</title><p>Carefully documented descriptive research and repeated surveillance visits involve a real measurement design and potential detection errors.</p></sec>
        <sec><title>Results</title><p>Researchers reported an observed change in services, with uncertainty and no separate verified control population in this study.</p></sec>
        </body></article>'''
        title,text,n=_jats_excerpt(xml)
        self.assertEqual(title,"Community intervention outcomes")
        self.assertIn("SECTION: Methods",text)
        self.assertIn("SECTION: Results",text)
        self.assertEqual(n,2)

    def test_acquisition_keeps_distinct_real_source_kinds_not_fabricated_data(self):
        def mk(lane):
            def fn(q,n):
                return [fake_doc(f"{lane}-{i}","s01",
                          {"pmc":"full_text_jats","wb":"report_extracted_text",
                           "zenodo":"dataset_metadata"}[lane]) for i in range(n)],[]
            return fn
        with TemporaryDirectory() as td:
            doc=acquire(td,strata={"s01":{"pmc":"article","wb":"report",
                                        "zenodo":"dataset"}},
                       limits={"pmc":2,"wb":2,"zenodo":2},
                       provider_overrides={k:mk(k) for k in ("pmc","wb","zenodo")})
            self.assertEqual(doc["source_count"],6)
            self.assertEqual({x["type"] for x in doc["sources"]},
                             {"full_text_jats","report_extracted_text","dataset_metadata"})
            self.assertEqual(doc["retrieval_failures"],[])
            self.assertTrue((Path(td)/"new_private_materials.json").exists())

    def test_frozen_holdout_excludes_baseline_and_never_leaks_whole_domains(self):
        topics=["s01","s02","s09","s10","s11","s12"]
        records=[]
        for s in topics:
            for i in range(7):
                row=fake_doc(f"NEW-{s}-{i}",s,
                     ["full_text_jats","report_extracted_text","dataset_metadata"][i%3])
                records.append(row)
        # An exact-title/source alias appears in the earlier map; excluded.
        records[0]["title"]="Previously seen research article"
        baseline={"schema":"cite_refinery.open_corpus.v1","source_count":1,
                  "sources":[{"id":"OLD-1","url":"https://doi.org/10.1111/other",
                              "title":"Previously seen research article"}]}
        corpus={"schema":SCHEMA,"sources":records}
        with TemporaryDirectory() as td:
            receipt=freeze(corpus,baseline,td)
            self.assertEqual(receipt["excluded_previous_overlap"],1)
            self.assertEqual(receipt["eligible_new_materials"],41)
            self.assertTrue(receipt["holdout_count"]>receipt["whole_domain_holdout_count"])
            self.assertGreater(receipt["whole_domain_holdout_count"],0)
            self.assertFalse(receipt["accuracy_scores_available"])
            dev=json.loads((Path(td)/"development_only.json").read_text())
            hold=json.loads((Path(td)/"private_partition.json").read_text())["held_out"]
            self.assertTrue(all(x["collection_quota"] not in DOMAIN_HOLDOUT for x in dev["sources"]))
            self.assertTrue(any(x["collection_quota"] in DOMAIN_HOLDOUT for x in hold))
            self.assertFalse(set(x["id"] for x in dev["sources"])&set(x["id"] for x in hold))
            with self.assertRaises(FileExistsError):freeze(corpus,baseline,td)

    def test_doi_alias_blocks_title_wash_of_previous_article(self):
        baseline={"schema":"cite_refinery.open_corpus.v1","source_count":1,
                  "sources":[{"url":"https://doi.org/10.2222/my-article","title":"A Prior Study"}]}
        records=[]
        for i in range(9):
            doc=fake_doc(f"PMC-{i}","s02")
            if i==0:doc["doi"]="https://doi.org/10.2222/my-article"
            records.append(doc)
        with TemporaryDirectory() as td:
            r=freeze({"schema":SCHEMA,"sources":records},baseline,td)
            self.assertEqual(r["excluded_previous_overlap"],1)
            self.assertEqual(r["eligible_new_materials"],8)

if __name__=="__main__":
    unittest.main()
