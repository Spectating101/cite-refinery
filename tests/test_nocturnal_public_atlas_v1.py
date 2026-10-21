"""Contract regression tests for Nocturnal's fictional public-snapshot schema.

These examples use fabricated organizations and .invalid domains only.
No private Nocturnal stores or allegations are opened.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.nocturnal_public_atlas import (
    build_practical_atlas, browse_practical, load_public_snapshot,
)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fixture(root: Path, *, second=True):
    root.mkdir(parents=True, exist_ok=True)
    source1 = "https://harbor-record.invalid/fictional-matter"
    source2 = "https://harbor-record.invalid/fictional-update"
    base = {
        "module_id": "fictional-module-1", "content_hash": "hash-original",
        "matter_id": "fictional-matter", "event_id": "event-original",
        "observed_at": "2026-01-01", "article_title": "Fictional procurement award",
        "text": "A completely fictional town announced a contract.",
        "status": "reported", "status_stage": "announced",
        "source_urls": [source1], "canonical_url": source1,
        "entities": [{"entity_id": "fictional-town", "name": "Fictional Town"}],
        "archive_refs": [], "evidence_grade": "sourced",
        "editorial_review_state": "approved", "dispute_state": "none",
        "correction_of": None, "supersedes": [],
    }
    correct = {
        **deepcopy(base), "module_id": "fictional-module-2",
        "content_hash": "hash-correction", "event_id": "event-correction",
        "observed_at": "2026-02-01", "article_title": "Fictional record correction",
        "text": "Fictional town corrected the earlier published status.",
        "status": "corrected", "status_stage": "corrected",
        "source_urls": [source2], "canonical_url": source2,
        "correction_of": "fictional-module-1", "supersedes": ["fictional-module-1"],
    }
    modules = [base, correct] if second else [base]
    mids = [x["module_id"] for x in modules]
    matters = [{
        "matter_id": "fictional-matter", "module_count": len(modules),
        "first_seen": base["observed_at"],
        "last_seen": modules[-1]["observed_at"],
        "current_stage": modules[-1]["status_stage"],
        "latest_module_id": modules[-1]["module_id"],
        "module_ids": mids,
        "status_history": [{
            "module_id": item["module_id"], "event_id": item["event_id"],
            "observed_at": item["observed_at"], "stage": item["status_stage"]
        } for item in modules],
        "correction_count": 1 if second else 0
    }]
    entities = [{
        "entity_id": "fictional-town", "name": "Fictional Town",
        "schema": "Organization", "identity_state": "reviewed",
        "review_state": "approved", "module_count": len(modules),
        "matter_count": 1, "module_ids": mids,
        "matter_ids": ["fictional-matter"], "observed_years": ["2026"],
    }]
    sources = [{
        "url": url, "domain": "harbor-record.invalid",
        "module_count": 1, "module_ids": [mid],
        "matter_ids": ["fictional-matter"],
        "evidence_grades": ["sourced"], "archive_refs": [],
    } for url, mid in [(source1, base["module_id"])] +
        ([(source2, correct["module_id"])] if second else [])]
    corrections = [{
        "module_id": correct["module_id"], "matter_id": correct["matter_id"],
        "event_id": correct["event_id"], "observed_at": correct["observed_at"],
        "correction_of": correct["correction_of"], "status_stage": "corrected",
        "source_urls": correct["source_urls"],
    }] if second else []
    batches = {"modules": modules, "matters": matters, "entities": entities,
               "sources": sources, "corrections": corrections}
    files = {}
    for name, records in batches.items():
        data = "".join(canonical(item) + "\n" for item in records).encode()
        (root / (name + ".jsonl")).write_bytes(data)
        files[name + ".jsonl"] = {"bytes": len(data), "sha256": sha256(data).hexdigest()}
    stewardship = b'{"fictional":true}\n'
    (root / "stewardship.json").write_bytes(stewardship)
    files["stewardship.json"] = {"bytes": len(stewardship),
                                "sha256": sha256(stewardship).hexdigest()}
    counts = {name: len(records) for name, records in batches.items()}
    hashes = {name: descriptor["sha256"] for name, descriptor in files.items()}
    pilot = {"schema": "nocturnal.pilot_manifest.v1",
             "pilot_id": "fictional-harbor-county-pilot", "fictional": True,
             "scope": {"jurisdiction": "fictional-harbor-county",
                       "domain": "fictional procurement"},
             "publication_allowed": True, "blockers": []}
    digest = sha256(canonical({"schema": "nocturnal.public_snapshot.v1",
                              "files": hashes, "counts": counts,
                              "pilot_id": pilot["pilot_id"]}).encode()).hexdigest()
    manifest = {
        "schema": "nocturnal.public_snapshot.v1",
        "snapshot_id": "nocturnal-" + digest[:20],
        "generated_at": "2026-10-21T00:00:00Z", "commit_sha": "fixture-only",
        "dataset_license": "CC-BY-4.0", "source_rights_reviewed": True,
        "pilot_gate": pilot, "publishable": True,
        "publication_blockers": [], "integrity": {"ok": True,
                                                  "chains": [{"chain_id": "demo",
                                                              "ok": True}]},
        "counts": {**counts, "chains": 1}, "files": files,
        "limitations": ["Fictional fixture only"],
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


class NocturnalPublicAtlasTests(unittest.TestCase):
    def test_fictional_snapshot_map_is_independently_navigable(self):
        with TemporaryDirectory() as td:
            fixture(Path(td))
            m = build_practical_atlas(td)
            self.assertTrue(m["provenance"]["fictional"])
            self.assertEqual(m["coverage"]["matter_count"], 1)
            self.assertEqual(m["coverage"]["module_count"], 2)
            self.assertEqual(m["coverage"]["correction_count"], 1)
            self.assertEqual(m["coverage"]["source_url_count"], 2)
            self.assertEqual(m["coverage"]["source_domain_count"], 1)
            self.assertEqual(m["coverage"]["untagged_cross_domain_subjects"], 1)
            self.assertFalse(m["coverage"]["world_or_field_completeness_measured"])
            matter = m["matters"]["fictional-matter"]
            self.assertEqual([x["stage"] for x in matter["timeline"]],
                             ["announced", "corrected"])
            self.assertFalse(matter["substantive_outcome_independently_verified"])
            self.assertTrue(m["interpretation"]["source_url_count_is_not_independent_corroboration"])
            self.assertEqual(browse_practical(m, terms="correction")["matching_count"], 1)
            self.assertEqual(browse_practical(m, terms="invented")["matching_count"], 0)
            self.assertEqual(m["modules"]["fictional-module-2"]["correction_of"],
                             "fictional-module-1")
            self.assertNotIn("text", str(m["modules"]))
            self.assertIn("#L2", m["modules"]["fictional-module-2"]["original_snapshot_locator"])

    def test_changed_or_truncated_bytes_fail_even_if_manifest_claims_publication(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            with (root / "modules.jsonl").open("a") as f:
                f.write('{"module_id":"unreviewed-leak"}\n')
            with self.assertRaisesRegex(ValueError, "hash/size"):
                build_practical_atlas(root)

    def test_nonpublishing_release_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            m = fixture(root)
            m["publishable"] = False
            (root / "manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "publication gate"):
                build_practical_atlas(root)
            m["publishable"] = True
            m["pilot_gate"]["publication_allowed"] = False
            (root / "manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "publication gate"):
                build_practical_atlas(root)

    def test_file_manifest_fingerprint_and_symlink_guard(self):
        with TemporaryDirectory() as td:
            root = Path(td) / "actual"
            manifest = fixture(root)
            manifest["snapshot_id"] = "nocturnal-wrong"
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "ID does not bind"):
                load_public_snapshot(root)
            alias = Path(td) / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real local directory"):
                load_public_snapshot(alias)

    def test_index_forgery_detected_even_with_recomputed_manifest_hashes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            m = fixture(root)
            sources = [json.loads(x) for x in (root/"sources.jsonl").read_text().splitlines()]
            sources[0]["module_ids"] = ["fictional-module-2"]
            data = "".join(canonical(x) + "\n" for x in sources).encode()
            (root/"sources.jsonl").write_bytes(data)
            m["files"]["sources.jsonl"] = {
                "sha256": sha256(data).hexdigest(), "bytes": len(data)}
            hashes = {name: x["sha256"] for name, x in m["files"].items()}
            digest = sha256(canonical({"schema": "nocturnal.public_snapshot.v1",
                                     "files": hashes, "counts": {
                                         x: m["counts"][x] for x in
                                         ("modules","matters","entities","sources","corrections")},
                                     "pilot_id": m["pilot_gate"]["pilot_id"]}).encode()).hexdigest()
            m["snapshot_id"] = "nocturnal-" + digest[:20]
            (root/"manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "source/module"):
                build_practical_atlas(root)

    def test_incremental_sync_preserves_corrections_and_marks_withheld_ids(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            earlier = root/"earlier"
            fixture(earlier, second=False)
            previous = build_practical_atlas(earlier)
            later = root/"later"
            fixture(later, second=True)
            updated = build_practical_atlas(later, previous=previous)
            self.assertEqual(updated["sync"]["added_module_ids"], ["fictional-module-2"])
            self.assertEqual(updated["sync"]["unchanged_module_count"], 1)
            self.assertEqual(updated["sync"]["no_longer_public_module_ids"], [])
            self.assertEqual(updated["coverage"]["correction_count"], 1)
            replay = build_practical_atlas(later, previous=updated)
            self.assertEqual(replay["sync"]["added_module_ids"], [])
            withheld = build_practical_atlas(earlier, previous=updated)
            self.assertEqual(withheld["sync"]["no_longer_public_module_ids"],
                             ["fictional-module-2"])
            self.assertNotIn("fictional-module-2", withheld["modules"])
            self.assertFalse(withheld["sync"]["no_longer_public_records_retained"])

    def test_changed_original_module_requires_new_correction_record(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            first = root/"first"
            fixture(first)
            previous = build_practical_atlas(first)
            altered = deepcopy(previous)
            altered["modules"]["fictional-module-1"]["text_sha256"] = "0"*64
            with self.assertRaisesRegex(ValueError, "mutated"):
                build_practical_atlas(first, previous=altered)

    def test_browse_rejects_unknown_matter_and_unbounded_results(self):
        with TemporaryDirectory() as td:
            fixture(Path(td))
            m=build_practical_atlas(td)
            with self.assertRaises(ValueError):
                browse_practical(m,matter_id="unpublished-person")
            with self.assertRaises(ValueError):
                browse_practical(m,limit=10000)


if __name__ == "__main__":
    unittest.main()
