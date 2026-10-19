"""Non-production integration contracts for optional open-source research engines."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from cite_refinery.external_engines import (
    EngineUnavailable, _local_endpoint, docling_extract, executable_claims_analyze,
    grobid_extract, lightrag_propose, openalex_discover, paperqa_ask, prov_export_packet,
)
from cite_refinery.external_explorer import export_cytoscape_explorer
from cite_refinery.external_cli import catalog


class _FakeWorks:
    def search(self, query):
        self.query = query
        return self

    def get(self, per_page):
        assert per_page == 2
        return [{
            "id": "https://openalex.org/W123",
            "title": "Free roaming dog populations",
            "doi": "https://doi.org/10.1000/sample",
            "publication_year": 2025,
            "primary_location": {"source": {"display_name": "Field Ecology"}},
            "abstract_inverted_index": {"Survey": [0], "dogs": [1]},
            "cited_by_count": 7,
        }]


class _FakeConverter:
    def convert(self, value):
        self.input = value
        return SimpleNamespace(document=SimpleNamespace(
            export_to_markdown=lambda: "# Heading\n\nSample observation.\n"))


class _HttpResponse:
    def __init__(self, payload=None, text=""):
        self.payload = payload
        self.text = text
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class _ClaimsClient:
    def __init__(self):
        self.calls = []
    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return _HttpResponse({"analysis_id": "run-15"})
    def get(self, url):
        self.calls.append(("get", url))
        return _HttpResponse({"claims": [{"status": "unsupported"}]})


class _GrobidClient:
    def post(self, url, **kwargs):
        assert url.endswith("/api/processFulltextDocument")
        assert kwargs["files"]["input"][2] == "application/pdf"
        return _HttpResponse(text='<?xml version="1.0"?><TEI xmlns="http://www.tei-c.org/ns/1.0"><text/></TEI>')


class _FakeRAG:
    def __init__(self):
        self.queries = []
        self.inserted = []
    async def ainsert(self, text):
        self.inserted.append(text)
    async def aquery(self, text, param):
        self.queries.append((text, param))
        return json.dumps({"proposals": [
            {"source": "AW-01", "target": "PH-02", "relation": "CONTEXT_FOR",
             "evidence_refs": ["https://example.org/study"], "reason": "candidate only"},
            {"source": "AW-01", "target": "PH-02", "relation": "CAUSES",
             "evidence_refs": ["https://example.org/study"], "reason": "too strong"},
            {"source": "AW-01", "target": "PH-02", "relation": "CONTEXT_FOR",
             "evidence_refs": ["https://invalid.example/unknown"], "reason": "invented"},
            {"source": "AW-01", "target": "NEW-99", "relation": "RELATED_TO",
             "evidence_refs": ["https://example.org/study"], "reason": "invented module"},
        ]})


class OpenSourceEngineTests(unittest.TestCase):
    def test_pyalex_adapter_returns_source_leads_not_accepted_claims(self):
        leads = openalex_discover("free roaming dogs", limit=2, works_factory=_FakeWorks)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["abstract_excerpt"], "Survey dogs")
        self.assertEqual(leads[0]["kind"], "source_lead")
        self.assertIn("not_verified", leads[0]["review_status"])
        with self.assertRaises(ValueError):
            openalex_discover("x", works_factory=_FakeWorks)

    def test_docling_real_converter_protocol_and_local_boundary(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "field.md"
            p.write_text("# Heading\n\nSample observation.\n")
            fake = _FakeConverter()
            result = docling_extract(p, converter=fake)
            self.assertEqual(fake.input, str(p))
            self.assertEqual(result["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertTrue(result["source_id"].startswith("sha256:"))
            self.assertIn("requires_source_review", result["review_status"])
            with self.assertRaises(ValueError):
                docling_extract(Path(tmp) / "not-local.pdf", converter=fake)

    def test_paperqa_cli_uses_argv_not_shell_and_returns_candidate(self):
        with TemporaryDirectory() as tmp:
            binary = Path(tmp) / "fake-pqa"
            binary.write_text("#!/bin/sh\nprintf 'Reply: %s\\n' \"$2\"\n")
            binary.chmod(0o755)
            ans = paperqa_ask(tmp, "Some source?; echo PWN", executable=str(binary))
            self.assertIn("Some source?; echo PWN", ans["answer_candidate"])
            self.assertIn("citation_and_evidence_review", ans["review_status"])
            with self.assertRaises(EngineUnavailable):
                paperqa_ask(tmp, "some source", executable="nonexistent-paperqa-command")

    def test_lightrag_rejects_fake_source_or_causal_promotions(self):
        rag = _FakeRAG()
        got = asyncio.run(lightrag_propose(
            rag, source_text="One cited observation, another cited observation.",
            module_ids={"AW-01", "PH-02"},
            source_refs={"https://example.org/study"}, query_param=object()))
        self.assertEqual(len(rag.inserted), 1)
        self.assertEqual(len(got["proposals"]), 1)
        self.assertEqual(got["rejected_proposals"], 3)
        self.assertEqual(got["proposals"][0]["status"], "candidate")
        self.assertEqual(got["proposals"][0]["relation"], "CONTEXT_FOR")

    def test_executableclaims_calls_real_routes_no_generated_code(self):
        client = _ClaimsClient()
        report = executable_claims_analyze(
            "This is a scientific claim about measured rates.", client=client)
        self.assertEqual(report["analysis_id"], "run-15")
        self.assertEqual(report["detail"]["claims"][0]["status"], "unsupported")
        self.assertFalse(client.calls[0][2]["json"]["generate_capsules"])
        self.assertIn("/api/v1/analysis/run-15", client.calls[1][1])
        for unsafe in ["https://evil.example", "http://evil.example", "http://user:pass@localhost:8000"]:
            with self.assertRaises(ValueError):
                _local_endpoint(unsafe)

    def test_grobid_tei_local_pdf_no_fetching_website(self):
        with TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "sample.pdf"
            pdf.write_bytes(b"%PDF-1.4\nmock testing pdf")
            result = grobid_extract(pdf, client=_GrobidClient())
            self.assertIn("<TEI", result["tei_xml"])
            self.assertIn("machine_extraction", result["review_status"])

    def test_cytoscape_static_export_includes_license_and_sanitization(self):
        packet = {"nodes": [
            {"key": "question", "statement": "</script><script>alert('x')</script>",
             "layer": "neutral", "kind": "research_question"},
            {"key": "research", "statement": "Study exists", "layer": "academic",
             "source_refs": ["https://example.org/paper"]},
        ], "edges": [
            {"source": "research", "target": "question",
             "relation": "CONTEXT_FOR", "status": "candidate",
             "evidence_refs": ["https://example.org/paper"]},
        ]}
        with TemporaryDirectory() as tmp:
            out = export_cytoscape_explorer(packet, tmp)
            content = Path(out["path"]).read_text()
            self.assertEqual(out["node_count"], 2)
            self.assertTrue((Path(tmp) / "CYTO_LICENSE.txt").exists())
            self.assertGreater((Path(tmp) / "cytoscape.min.js").stat().st_size, 100000)
            self.assertNotIn("</script><script>alert('x')</script>", content)
            self.assertIn("cytoscape(", content)
            with self.assertRaises(ValueError):
                export_cytoscape_explorer({"nodes": packet["nodes"], "edges": [
                    {"source": "invented", "target": "research"}]}, tmp)

    def test_prov_export_real_dependency_or_fails_explicitly(self):
        try:
            import prov
        except ImportError:
            with self.assertRaises(EngineUnavailable):
                prov_export_packet({"nodes": []})
        else:
            result = prov_export_packet({"nodes": [
                {"key": "source-claim", "statement": "Limited observation",
                 "layer": "practical", "source_refs": ["https://example.org/report"]},
            ]})
            self.assertEqual(result["source_count"], 1)
            self.assertIn("entity", result["document"])
            self.assertIn("wasDerivedFrom", result["document"])

    def test_catalog_reports_optional_and_offline_viewer(self):
        cat = catalog()
        self.assertIn("lightrag", cat)
        self.assertTrue(cat["cytoscape"]["available"])


if __name__ == "__main__":
    unittest.main()
