"""Check publisher text matching without granting scientific or operator authority."""
from __future__ import annotations
import base64
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
from hashlib import sha1, sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.investigation_controller import InvestigationController, validate_supplied_evidence
from cite_refinery.source_authentication import (
    SCHEMA, audit_sources, classify, match_source,
)
from cite_refinery.layered_cli import main as app_cli

SHA="a"*40
CODE="def calculate_total(volume, price):\n    return volume * price\n\ndef emit_audit_receipt():\n    return 'candidate only'\n"
ISSUE="Public problem report: A map incorrectly centers the area when an outlying location is included. No measured revenue loss was established."
ABSTRACT="A study compares regional heat warning thresholds but does not prove that warnings directly caused reductions in hospital admissions."

def fixture():
    return {
        "schema":"cite_refinery.supplied_evidence.v1",
        "sources":[
            {"id":"USR-P-01","family":"practical","title":"Example reported issue",
             "url":"https://github.com/someowner/somerepo/issues/42",
             "text":ISSUE[:105],
             "scope":"Illustrative public reporter account, not verified field outcome."},
            {"id":"USR-I-01","family":"implementation","title":"Example source function",
             "url":f"https://github.com/someowner/somerepo/blob/{SHA}/src/math.py",
             "text":CODE[:65],
             "scope":"Exact file text matching; no execution, test or license validation."},
            {"id":"USR-A-01","family":"academic","title":"Example abstract passage",
             "url":"https://europepmc.org/article/MED/41622278",
             "text":ABSTRACT[:90],
             "scope":"Publication identity and abstract excerpt only; no scientific outcome audit."},
        ],
    }

def github_fetch(path):
    if path=="someowner/somerepo/issues/42":
        return {"number":42,
                "html_url":"https://github.com/someowner/somerepo/issues/42",
                "body":ISSUE,"updated_at":"2026-10-21T12:00:00Z"}
    if path=="someowner/somerepo/contents/src/math.py?ref="+SHA:
        raw=CODE.encode()
        return {"type":"file","path":"src/math.py","encoding":"base64",
                "sha":sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),
                "content":base64.b64encode(raw).decode()}
    raise AssertionError("unrecognized constrained trusted endpoint")

def epmc_fetch(pmid):
    assert pmid=="41622278"
    return {"resultList":{"result":[{
        "pmid":pmid,"source":"MED","title":"Heat warnings and thresholds",
        "abstractText":"<p>"+ABSTRACT+"</p>",
    }]}}

class PublisherTextMatchingTests(unittest.TestCase):
    def test_allowlisted_routes_and_unsupported_no_external_fetch(self):
        self.assertEqual(classify("https://github.com/someowner/somerepo/issues/42"),
                         ("github_issue","someowner","somerepo","42"))
        self.assertEqual(classify(f"https://github.com/someowner/somerepo/blob/{SHA}/src/math.py"),
                         ("github_blob","someowner","somerepo",SHA,"src/math.py"))
        self.assertEqual(classify("https://europepmc.org/article/MED/41622278"),
                         ("europepmc_abstract","41622278"))
        for url in ("https://github.com/someowner/somerepo/pull/42",
                    "https://github.com/someowner/somerepo/issues/42?payload=hi",
                    "https://github.com.evil.com/someowner/somerepo/issues/42",
                    "https://github.com/someowner/somerepo/blob/"+SHA+"/../secrets",
                    "https://github.com:444/someowner/somerepo/issues/42",
                    "https://127.0.0.1/secret",
                    "https://user:pass@github.com/someowner/somerepo/issues/42",
                    "http://github.com/someowner/somerepo/issues/42",
                    "https://raw.githubusercontent.com/test",
                    "https://europepmc.org/article/MED/notanumber"):
            self.assertIsNone(classify(url),url)
        bad=validate_supplied_evidence({
            "schema":fixture()["schema"],
            "sources":[{**fixture()["sources"][0],"url":"https://127.0.0.1/private"}],
        })[0]
        seen=[]
        def forbidden(*args):
            seen.append(args);raise AssertionError("must not fetch untrusted network address")
        result=match_source(bad,github_fetch=forbidden,epmc_fetch=forbidden)
        self.assertEqual(result["status"],"unsupported_publisher_route")
        self.assertEqual(seen,[])

    def test_three_families_are_matched_exactly_but_never_accepted(self):
        normalized=validate_supplied_evidence(fixture())
        report=audit_sources(normalized,github_fetch=github_fetch,epmc_fetch=epmc_fetch)
        self.assertEqual(len(report),3)
        self.assertEqual([r["status"] for r in report],
                         ["publisher_passage_matched_claim_unreviewed"]*3)
        self.assertEqual([r["publisher_record_type"] for r in report],[
            "github_issue_report","github_exact_commit_source_file",
            "europepmc_bibliographic_abstract"])
        self.assertEqual(report[1]["publisher_git_blob_sha"],
                         github_fetch("someowner/somerepo/contents/src/math.py?ref="+SHA)["sha"])
        for r in report:
            self.assertEqual(r["schema"],SCHEMA)
            self.assertTrue(r["exact_normalized_source_excerpt_match"])
            self.assertEqual(r["authority"],"NONE_ACCEPTED")
            self.assertFalse(r["source_claim_verified"])
            self.assertFalse(r["semantic_entailment_verified"])
            self.assertFalse(r["source_independent_field_outcome_verified"])
            self.assertFalse(r["implementation_function_executed"])

    def test_forged_and_changed_source_gets_a_mismatch_not_approval(self):
        changed=fixture()
        changed["sources"][0]["text"]=(
            "Public problem report: This map system cut hospitalization by thirty percent without evidence."
        )
        matches=audit_sources(validate_supplied_evidence(changed),
                              github_fetch=github_fetch,epmc_fetch=epmc_fetch)
        self.assertEqual(matches[0]["status"],"submitted_text_does_not_match_publisher")
        self.assertFalse(matches[0]["exact_normalized_source_excerpt_match"])
        self.assertEqual(matches[0]["authority"],"NONE_ACCEPTED")
        self.assertEqual(matches[1]["status"],"publisher_passage_matched_claim_unreviewed")

    def test_github_issue_cannot_impersonate_pr_and_blob_digest_protected(self):
        records=validate_supplied_evidence(fixture())
        with self.assertRaisesRegex(ValueError,"pull request impersonation"):
            match_source(records[0],github_fetch=lambda path:{
                **github_fetch(path),"pull_request":{"url":"https://github.com/other/pr"}})
        with self.assertRaisesRegex(ValueError,"blob identity"):
            match_source(records[1],github_fetch=lambda path:{
                **github_fetch(path),"sha":"0"*40})
        with self.assertRaisesRegex(ValueError,"PMID identity"):
            match_source(records[2],epmc_fetch=lambda pmid:
                {"resultList":{"result":[{"pmid":"0000000","source":"MED"}]}})

    def test_publisher_verification_rejects_modified_local_state_digest(self):
        material=validate_supplied_evidence(fixture())[0]
        changed={**material,"text":material["text"]+" unauthorized claim"}
        with self.assertRaisesRegex(ValueError,"digest mismatch"):
            match_source(changed,github_fetch=github_fetch,epmc_fetch=epmc_fetch)

    def test_source_family_spoofing_fails_before_network(self):
        issue=deepcopy(fixture()["sources"][0])
        issue["family"]="academic"
        issue["id"]="USR-A-02"
        x=validate_supplied_evidence({"schema":fixture()["schema"],"sources":[issue]})[0]
        used=[]
        def forbidden(_):
            used.append(True)
            raise AssertionError("wrong family must not trigger network fetch")
        result=match_source(x,github_fetch=forbidden,epmc_fetch=forbidden)
        self.assertEqual(result["status"],"publisher_route_source_family_mismatch")
        self.assertEqual(result["expected_family"],"practical")
        self.assertEqual(used,[])

    def test_unavailable_source_abstains_without_claiming_forgery(self):
        normalized=validate_supplied_evidence(fixture())
        result=audit_sources(normalized,
                 github_fetch=lambda path:(_ for _ in ()).throw(ConnectionError("offline")),
                 epmc_fetch=lambda path:(_ for _ in ()).throw(TimeoutError("offline")))
        self.assertEqual([r["status"] for r in result],
                         ["publisher_verification_unavailable"]*3)
        self.assertTrue(all(not r["source_claim_verified"] for r in result))

    def test_controller_receipts_are_durable_and_never_promoted(self):
        with TemporaryDirectory() as td:
            cli_source=Path(td)/"source.json"
            cli_source.write_text(json.dumps(fixture()))
            state=StringIO()
            with redirect_stdout(state):
                app_cli(["investigate","--workspace",td,"init",
                         "--question","How can a source evidence system distinguish citations from impact?",
                         "--evidence",str(cli_source)])
            initial=json.loads(state.getvalue())
            c=InvestigationController(td,reasoner=None)
            verified=c.authenticate_supplied_evidence(initial["id"],
                          github_fetch=github_fetch,epmc_fetch=epmc_fetch)
            self.assertEqual(len(verified["source_authentication"]),3)
            self.assertEqual(verified["authority"],"candidate_neutral_only")
            self.assertEqual(verified["stage"],"plan")
            loaded=c.load(initial["id"])
            self.assertEqual(loaded["source_authentication"],verified["source_authentication"])
            self.assertEqual(len(loaded["rounds"]),0)
            self.assertTrue(all(not r["source_claim_verified"] for r in
                                loaded["source_authentication"]))
            c.authenticate_supplied_evidence(initial["id"],
                         github_fetch=github_fetch,epmc_fetch=epmc_fetch)
            self.assertEqual(len(c.load(initial["id"])["source_authentication"]),3)

if __name__=="__main__":
    unittest.main()
