import unittest
from cite_refinery.portfolio_atomic_tasks import tasks_from_receipt, validate_atomic_answer, DossierError

def sample():
    repos=["hardware-splicer","yzu-cluster","gauntlet-blowback","animal-charity",
           "live-presenter","cite-refinery","Invisible-ledger","citation-engine"]
    return {"private_repositories_included":0,
            "atlas_actual_semantic_graph_ingested":True,
            "source_snapshots":[{"repo":r} for r in repos],
            "packet":{"nodes":[{"key":"repo_"+r.lower().replace("-","_"),
                      "layer":"program",
                      "statement":"Maintainer describes research provenance and data processing for "+r,
                      "source_refs":["https://github.com/Spectating101/"+r+"/blob/123/README.md"]}
                      for r in repos],"edges":[]}}

class AtomicTaskTests(unittest.TestCase):
    def test_real_graph_task_pack(self):
        pack=tasks_from_receipt(sample())
        self.assertEqual(pack["project_count"],8)
        self.assertEqual(pack["task_count"],32)
        self.assertFalse(pack["task_generation_independently_reasoned"])

    def test_unknown_physical_claim_cannot_be_approved(self):
        task=tasks_from_receipt(sample())["tasks"][1]
        with self.assertRaisesRegex(DossierError,"cannot prove independent"):
            validate_atomic_answer(task,{"id":task["id"],"verdict":"self_reported","evidence_id":task["allowed_evidence_ids"][0],"quote":"independently measured"})

    def test_no_hallucinated_source_quote(self):
        task=tasks_from_receipt(sample())["tasks"][0]
        with self.assertRaisesRegex(DossierError,"quote not verified"):
            validate_atomic_answer(task,{"id":task["id"],"verdict":"self_reported",
              "evidence_id":task["allowed_evidence_ids"][0],"quote":"guaranteed commercial adoption"})

    def test_correct_self_attribution_contract(self):
        task=tasks_from_receipt(sample())["tasks"][0]
        out=validate_atomic_answer(task,{"id":task["id"],"verdict":"self_reported",
              "evidence_id":task["allowed_evidence_ids"][0],
              "quote":"Maintainer describes research provenance"})
        self.assertFalse(out["semantic_entailment_verified"])

    def test_private_pack_rejected(self):
        x=sample()
        x["private_repositories_included"]=1
        with self.assertRaisesRegex(DossierError,"public-only"):
            tasks_from_receipt(x)

if __name__=="__main__":
    unittest.main()
