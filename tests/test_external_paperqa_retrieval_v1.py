"""Real PaperQA2 sparse retrieval adapter's stable contract and safe boundaries."""
from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from cite_refinery.external_engines import paperqa_retrieve_local


class FakePaperQADocs:
    def __init__(self):
        self.metadata_request = None
        self.query = None

    async def aadd(self, path, *, citation, title, doi, settings):
        self.metadata_request = (path, citation, title, doi)
        return "DocBelo"

    async def retrieve_texts(self, question, k, settings):
        self.query=(question,k)
        return [SimpleNamespace(name="Belo2015 chunk 2",
                                text="This paragraph discusses population estimation sampling bias.",
                                doc=SimpleNamespace(dockey="Belo2015"))]


class PaperQARetrievalContractTests(unittest.TestCase):
    def test_retrieval_returns_neutral_evidence_without_model_judgments(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"public-paper.txt"
            p.write_text("An academic publication discusses dog population estimates.")
            fake=FakePaperQADocs()
            result=asyncio.run(paperqa_retrieve_local(
                p,"population estimate sampling bias",
                citation="Belo et al. 2015 systematic review",
                title="Free roaming dog estimation",
                doi="10.1371/journal.pone.0144830",
                k=2,
                docs_factory=lambda:fake,
                settings=object()))
            self.assertEqual(len(result["matches"]),1)
            self.assertTrue(result["source_document_sha256"])
            self.assertEqual(result["llm_answer_generation"],"disabled")
            self.assertEqual(result["metadata_network_lookup"],"disabled")
            self.assertIn("requires_passage_and_entailment_review",result["matches"][0]["review_status"])
            self.assertEqual(fake.query[1],2)
            self.assertEqual(fake.metadata_request[3],"10.1371/journal.pone.0144830")

    def test_rejects_missing_and_unsafe_inputs(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"paper.txt"
            p.write_text("some content")
            bad=[
                (p,"a", "Some citation", 2),
                (p,"sampling bias","a",2),
                (p,"sampling bias","valid citation",99),
                (Path(tmp)/"missing.pdf","sampling bias","valid citation",2),
            ]
            for path,question,citation,k in bad:
                with self.subTest(path=path,question=question,k=k):
                    with self.assertRaises(ValueError):
                        asyncio.run(paperqa_retrieve_local(
                            path,question,citation=citation,k=k,
                            docs_factory=FakePaperQADocs,
                            settings=object()))


if __name__=="__main__":
    unittest.main()
