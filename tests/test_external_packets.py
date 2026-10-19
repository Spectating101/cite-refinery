"""Safe external engine outputs may be staged, but never accepted automatically."""
from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest
from cite_refinery import CiteRefinery, SemanticGraph
from cite_refinery.external_packets import (
    source_lead_packet, relation_proposal_packet,
)


class ExternalPacketsTests(unittest.TestCase):
    def test_pyalex_metadata_remains_neutral_and_idempotently_ingests(self):
        leads = [{
            "id": "https://openalex.org/W100",
            "title": "Free-roaming dog survey methods",
            "source_ref": "https://doi.org/10.1000/dog",
            "source_provider": "OpenAlex",
        }]
        packet = source_lead_packet("AW-01", "Animal population observability", leads + leads)
        self.assertEqual(len(packet["nodes"]), 2)
        self.assertEqual(len(packet["edges"]), 1)
        self.assertTrue(all(n["layer"] == "neutral" for n in packet["nodes"]))
        self.assertEqual(packet["nodes"][1]["kind"], "source")
        self.assertEqual(packet["edges"][0]["relation"], "DISCOVERED_FOR")
        self.assertEqual(packet["edges"][0]["status"], "candidate")
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("External sources", "Isolated lead registry")
            graph = SemanticGraph(app.store)
            a = graph.ingest_packet(project.id, packet)
            b = graph.ingest_packet(project.id, packet)
            self.assertEqual(a["id"], b["id"])
            m = graph.cluster_map(project.id)
            self.assertEqual(m["clusters"][0]["layer_presence"],
                             {"practical": False, "academic": False, "program": False})

    def test_lightrag_proposals_remain_candidate_and_pinned(self):
        mods = {"AW-01": "Dog population observability", "PH-02": "Healthcare access"}
        proposals = [{"source": "AW-01", "target": "PH-02",
                      "relation": "CONTEXT_FOR", "status": "candidate",
                      "evidence_refs": ["https://example.org/study"],
                      "reason": "Some shared context"}]
        packet = relation_proposal_packet(mods, proposals)
        self.assertEqual(len(packet["nodes"]), 2)
        self.assertEqual(len(packet["edges"]), 1)
        self.assertEqual(packet["conversion_metadata"]["status"],
                         "GENERATED_RELATIONS_REVIEW_REQUIRED")
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("External proposals", "Unreviewed graph")
            receipt = SemanticGraph(app.store).ingest_packet(project.id, packet)
            self.assertEqual(len(receipt["edge_ids"]), 1)
        for forbidden in ("CAUSES", "SUPPORTS", "ADDRESSES"):
            bad = [dict(proposals[0], relation=forbidden)]
            with self.assertRaises(ValueError):
                relation_proposal_packet(mods, bad)
        with self.assertRaises(ValueError):
            relation_proposal_packet(mods, [dict(proposals[0], target="X")])
        with self.assertRaises(ValueError):
            source_lead_packet("AW-01", "animal welfare", [{"title": "No actual reference"}])


if __name__ == "__main__":
    unittest.main()
