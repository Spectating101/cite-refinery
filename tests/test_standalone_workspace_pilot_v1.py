"""End-to-end read-only evidence-pilot controls using actual public frozen source indexes."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.academic_evidence_atlas import build_academic_atlas
from cite_refinery.implementation_evidence_atlas import build_implementation_atlas
from cite_refinery.layer_foundations import build
from cite_refinery.standalone_workspace import build_pilot, write_pilot, SCHEMA

ROOT=Path(__file__).resolve().parents[1]
MATERIALS=ROOT/"research_materials/runtime_trials/open_corpus_20261020"
ACADEMIC=ROOT/"research_materials/runtime_trials/richer_corpus_20261020"
ORIGINALS=ROOT/"research_materials/opportunity_atlas"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class OfflineStandalonePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foundation=build(
            load(MATERIALS/"source_manifest.json"),
            [load(p) for p in sorted((MATERIALS/"source_readings").glob("shard-*.json"))],
            load(MATERIALS/"global_atlas.json"),
            load(ORIGINALS/"github_repository_survey.json"),
            load(ORIGINALS/"github_frontier_repository_survey.json"),
            load(ORIGINALS/"atlas_network.json"),
            load(ORIGINALS/"ted_published_notice_context.json"))
        cls.academic=build_academic_atlas(
            load(ACADEMIC/"development_source_manifest.json"),
            load(ACADEMIC/"frozen_split_receipt.json"))
        cls.impl=build_implementation_atlas(cls.foundation,
             functional_trials=load(ORIGINALS/"functional_component_trials.json"))
        cls.pilot=build_pilot(cls.foundation,cls.academic,cls.impl)

    def test_three_complete_independent_source_collections_are_browsable(self):
        m=self.pilot
        self.assertEqual(m["schema"],SCHEMA)
        self.assertEqual(m["record_count"],1497)
        self.assertEqual(m["by_layer"],
                         {"practical":57,"academic":150,"implementation":1290})
        self.assertEqual(m["original_data"]["practical_legacy_reported_not_firsthand"],9)
        self.assertEqual(m["original_data"]["separate_procurement_notices"],48)
        self.assertEqual(m["original_data"]["academic_sealed_holdout_not_imported"],66)
        self.assertEqual(m["original_data"]["independently_validated_scientific_findings"],0)
        self.assertEqual(m["original_data"]["implementation_original_modules_tested"],0)
        self.assertEqual(m["original_data"]["implementation_live_field_outcomes"],0)
        self.assertGreaterEqual(sum(bool(x["subjects"]) for x in m["cards"]),1400)
        self.assertFalse(m["original_data"]["practical_public_nocturnal_attached"])
        self.assertFalse(m["original_data"]["world_coverage_complete"])

    def test_field_source_notices_are_context_not_verified_demand(self):
        p=[x for x in self.pilot["cards"] if x["layer"]=="practical"]
        self.assertEqual(len(p),57)
        reports=[x for x in p if x["group"]=="reported_case"]
        notices=[x for x in p if x["group"]=="published_notice"]
        self.assertEqual((len(reports),len(notices)),(9,48))
        self.assertTrue(all("reported_not_field_validated" in x["flags"] for x in reports))
        self.assertTrue(all("demand_unconfirmed" in x["flags"] for x in notices))

    def test_academic_legacy_not_conflated_with_103_development_sources(self):
        a=[x for x in self.pilot["cards"] if x["layer"]=="academic"]
        self.assertEqual(sum(x["group"]=="legacy_abstract" for x in a),47)
        self.assertEqual(sum(x["group"]=="development_source" for x in a),103)
        self.assertTrue(all("development_only" in x["flags"]
                            for x in a if x["group"]=="development_source"))
        self.assertTrue(all(not any(f["name"]=="Original extracted body"
                            for f in x["facts"]) for x in a))
        self.assertTrue(all(not x["details"][0]["text"].startswith("Methods:")
                            for x in a if x["group"]=="development_source"))

    def test_historical_external_probes_not_mislabeled_as_functional_survey(self):
        impl=[x for x in self.pilot["cards"] if x["layer"]=="implementation"]
        self.assertEqual(len(impl),1290)
        self.assertEqual(sum(x["group"]=="surveyed_repository" for x in impl),1287)
        prior=[x for x in impl if x["group"]=="external_historical_trial"]
        self.assertEqual(len(prior),3)
        self.assertTrue(all("outside_survey" in x["flags"] for x in prior))
        self.assertTrue(all(x["subjects"] for x in prior))
        self.assertTrue(all(x["subjects"] for x in impl if x["group"]=="surveyed_repository"))
        self.assertTrue(all("historical_receipt" in x["flags"] for x in prior))

    def test_refuses_fake_validation_unsealed_holdout_or_injected_source(self):
        a=deepcopy(self.academic)
        a["provenance"]["heldout_source_id_or_text_imported"]=True
        with self.assertRaisesRegex(ValueError,"frozen, sealed"):
            build_pilot(self.foundation,a,self.impl)
        fake=deepcopy(self.impl)
        fake["coverage"]["live_operational_implementations_verified"]=2
        with self.assertRaisesRegex(ValueError,"live Implementation"):
            build_pilot(self.foundation,self.academic,fake)
        f=deepcopy(self.foundation)
        f["practical"]["published_procurement_notices_as_separate_context"][0]["url"]="javascript:alert(1)"
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            build_pilot(f,self.academic,self.impl)
        unapproved={"schema":"cite_refinery.nocturnal_practical_atlas.v1",
                    "provenance":{"approved_public_release_only":False}}
        with self.assertRaisesRegex(ValueError,"publication-authorized"):
            build_pilot(self.foundation,self.academic,self.impl,unapproved)

    def test_writes_offline_page_with_export_controls_no_external_runtime(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"research-atlas"
            meta=write_pilot(self.pilot,root)
            self.assertEqual(meta["records"],1497)
            self.assertTrue((root/"index.html").is_file())
            self.assertTrue((root/"atlas.json").is_file())
            page=(root/"index.html").read_text(encoding="utf-8")
            self.assertIn("Independent Evidence Atlases",page)
            self.assertIn('id="atlas-data"',page)
            self.assertIn("Download dossier JSON",page)
            self.assertIn("Export filtered research packet",page)
            self.assertIn('id="subject"',page)
            self.assertIn('id="coverage"',page)
            self.assertIn("changeLayer",page)
            self.assertNotIn("<!-- ATLAS_JSON_SLOT -->",page)
            self.assertNotIn("fetch(",page)
            self.assertNotIn("<script src=",page)
            self.assertEqual(load(root/"atlas.json")["by_layer"]["academic"],150)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                write_pilot(self.pilot,root)

    def test_script_context_metadata_is_encoded_not_executable(self):
        tampered=deepcopy(self.pilot)
        tampered["cards"][0]["title"]='</script><script>alert(1)</script>'
        with TemporaryDirectory() as td:
            root=Path(td)/"safe"
            write_pilot(tampered,root)
            html=(root/"index.html").read_text(encoding="utf-8")
            self.assertNotIn('</script><script>alert(1)</script>',html)
            self.assertIn('\\u003c/script\\u003e',html)
            self.assertIn("atlas-data",html)

    def test_all_source_links_HTTPS_and_record_names_unique(self):
        cards=self.pilot["cards"]
        self.assertEqual(len(cards),len({x["id"] for x in cards}))
        self.assertTrue(all(link.startswith("https://")
                            for card in cards for link in card["urls"]))
        self.assertTrue(all(card["authority"] for card in cards))


if __name__=="__main__":
    unittest.main()
