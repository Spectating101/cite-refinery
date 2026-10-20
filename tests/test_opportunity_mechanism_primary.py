import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cite_refinery.opportunity_mechanism_primary import build, exact_excerpt, markdown

ROOT=Path(__file__).resolve().parents[1] / "research_materials/opportunity_atlas"

def fixture():
    texts=[
        "A measured study finds costs depend strongly on transportation distance and wage assumptions, controlling for several processes.",
        "An operational report records repeated observations, but no causal outcome proof follows from the recorded inputs.",
    ]
    sources=[]; readings=[]
    for i,t in enumerate(texts):
        id="SOURCE-"+str(i)
        digest=hashlib.sha256(t.encode()).hexdigest()
        sources.append(dict(id=id,url="https://example.org/"+id,title=id,origin_type="abstract",
                            source_scope="sample only",text=t,sha256=digest))
        readings.append(dict(source_id=id,source_url="https://example.org/"+id,
                             source_sha256=digest,role="unverified_academic_finding"))
    manifest={"schema":"cite_refinery.primary_mechanism_dossiers_input.v1","entries":[{
        "key":"operational_cost_case","family":"economics",
        "problem":"The observed cost constraints cannot establish the profitability of the full system.",
        "mechanism":"Transportation, labor and process conditions jointly determine whether the system performs acceptably.",
        "capability_contract":"Explicit inputs and reproducible scenario calculations with a clear set of required outputs.",
        "validation":"Compare predicted outcomes to an independent field trial and audit the complete expense statement.",
        "gap":"The software prototype is not independently validated and may omit delivery expense assumptions.",
        "basis":[["SOURCE-0","transportation distance"],["SOURCE-1","no causal outcome proof"]],
        "repo":"dummy/example","repo_role":"partial_component","repo_excerpt":"Small Python test tool","repo_sha":None}]}
    corpus={"schema":"cite_refinery.open_corpus.v1","material_type":"unclassified_source_records","sources":sources}
    read={"schema":"cite_refinery.open_corpus_provisional_map.v1","readings":readings}
    return manifest,corpus,read

def make_readme(manifest,folder):
    data=b"# Test repository\nSmall Python test tool.\n"
    (folder/"dummy__example.md").write_bytes(data)
    manifest["entries"][0]["repo_sha"]=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class PrimaryMechanismTest(unittest.TestCase):
    def test_real_bounded_artifacts(self):
        j=json.loads((ROOT/"primary_mechanism_network.json").read_text())
        self.assertEqual(j["coverage"]["operational_mechanisms_described"],8)
        self.assertEqual(j["coverage"]["primary_source_identities"],31)
        self.assertEqual(j["coverage"]["repo_readme_blobs_verified"],7)
        self.assertEqual(j["coverage"]["full_operational_stacks_validated"],0)
        self.assertEqual(j["coverage"]["commercial_contracts_verified"],0)
        self.assertFalse(j["coverage"]["research_holdout_touched"])
        for b in j["briefs"]:
            self.assertFalse(b["economics_confirmed"])
            self.assertFalse(b["technical_fitness_confirmed"])
            self.assertTrue(all(len(s["quote"].split())<=22 for s in b["primary_sources"]))
        self.assertIn("intentionally unfilled",markdown(j))

    def test_exact_quotes_and_immutable_digests(self):
        self.assertRaises(ValueError,exact_excerpt,"some source evidence exists","invented claim")
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);m,c,r=fixture();make_readme(m,p)
            valid=build(m,c,r,readme_dir=p,observed_at="2026-10-21")
            self.assertEqual(len(valid["edges"]),3)
            self.assertEqual(valid["coverage"]["repo_readme_blobs_verified"],1)
            tampered=copy.deepcopy(c);tampered["sources"][0]["text"]+=" falsified"
            with self.assertRaisesRegex(ValueError,"SHA/url"):
                build(m,tampered,r,readme_dir=p,observed_at="2026-10-21")
            badread=copy.deepcopy(r);badread["readings"][0]["source_url"]="https://bad.example/"
            with self.assertRaisesRegex(ValueError,"SHA/url"):
                build(m,c,badread,readme_dir=p,observed_at="2026-10-21")
            (p/"dummy__example.md").write_text("Completely different material")
            with self.assertRaisesRegex(ValueError,"README changed"):
                build(m,c,r,readme_dir=p,observed_at="2026-10-21")

    def test_missing_technology_kept_missing(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);m,c,r=fixture()
            m["entries"][0]["repo"]=None
            m["entries"][0]["repo_role"]="no_credible_repo_link_yet"
            out=build(m,c,r,readme_dir=p,observed_at="2026-10-21")
            self.assertIsNone(out["briefs"][0]["implementation_lead"])
            self.assertEqual(out["coverage"]["repo_readme_blobs_verified"],0)
