"""Atlas multi-source discovery offline tests with provider fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cite_refinery.multi_source_discovery import (
    SCHEMA, SourceFailure, _doi, _save, collect, collect_provider,
    headless_packet, validate_sources, fetch_http,
)


def s(provider="openalex", sid="example", query="solar data", limit=3):
    return {"id":sid, "provider":provider, "query":query,"tags":["research"],
            "project_targets":["policy_lab"], "limit":limit}


class SourceTests(unittest.TestCase):
    def test_manifest_validation_and_no_arbitrary_provider(self):
        rows=validate_sources({"schema":SCHEMA,"sources":[s()]})
        self.assertEqual(rows[0]["provider"],"openalex")
        for provider in ("raw_scrape", "file", "ftp", "github.com/evil"):
            with self.assertRaises(ValueError):
                validate_sources({"schema":SCHEMA,"sources":[s(provider)]})
        with self.assertRaises(ValueError):
            validate_sources({"schema":SCHEMA,"sources":[s(query="\nnetwork")]})

    def test_doi_normalization(self):
        self.assertEqual(_doi("https://doi.org/10.1234/QWE"),"doi:10.1234/qwe")
        self.assertIsNone(_doi("https://evil.example/a"))

    def test_github_signals_csv_filter_and_direct_repo_identity(self):
        data=("published_at,repo_slug,repo_url,repo_keywords,caption\n"
              "2026-11-01,Org/ResearchRepo,https://github.com/Org/ResearchRepo,solar research,test\n"
              "2026-11-01,Evil/Repo,https://evil.test/Evil/Repo,solar research,test\n").encode()
        results=collect_provider(s("github_signals",query="research"),fetch=lambda url:data)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["entity_key"],"github:org/researchrepo")
        self.assertEqual(results[0]["evidence_status"],"unverified_external_metadata")

    def test_github_search_relevance_default_and_explicit_recent(self):
        from cite_refinery.multi_source_discovery import validate_sources
        calls=[]
        def github(path):
            calls.append(path)
            return {"items":[{"full_name":"Org/Repo","html_url":"https://github.com/Org/Repo"}]}
        base=s("github_search",query="web archiving")
        manifest={"schema":SCHEMA,"sources":[base]}
        relevance=validate_sources(manifest)[0]
        collect_provider(relevance,gh=github)
        self.assertNotIn("sort=updated",calls[-1])
        manifest["sources"][0]["ranking"]="recent"
        recent=validate_sources(manifest)[0]
        collect_provider(recent,gh=github)
        self.assertIn("sort=updated",calls[-1])
        manifest["sources"][0]["ranking"]="random"
        with self.assertRaises(ValueError):
            validate_sources(manifest)

    def test_github_search_and_signals_share_entity_key(self):
        csv=("repo_slug,repo_url,repo_keywords\n"
             "Org/Repo,https://github.com/Org/Repo,solar\n").encode()
        def gh(path):
            self.assertTrue(path.startswith("search/repositories?"))
            return {"items":[{"full_name":"Org/Repo",
                              "html_url":"https://github.com/Org/Repo",
                              "description":"solar"}]}
        output=collect({"schema":SCHEMA,"sources":[
            s("github_signals",sid="signal",query="solar"),
            s("github_search",sid="search",query="solar")
        ]},fetch=lambda url:csv,gh=gh)
        self.assertEqual(len(output["records"]),2)
        self.assertEqual(len(output["same_identity_candidates"]),1)

    def test_openalex_and_crossref_doi_cluster(self):
        def fetch(url):
            if "api.openalex.org" in url:
                return json.dumps({"results":[{"id":"https://openalex.org/W123",
                   "display_name":"PV quality", "doi":"https://doi.org/10.1234/abc"}]}).encode()
            if "api.crossref.org" in url:
                return json.dumps({"message":{"items":[{"DOI":"10.1234/ABC",
                    "title":["PV quality"]}]}}).encode()
            raise AssertionError("unknown URL")
        a=collect({"schema":SCHEMA,"sources":[s("openalex",sid="openalex"),
                            s("crossref",sid="crossref")]},fetch=fetch)
        self.assertEqual(len(a["records"]),2)
        self.assertEqual(a["same_identity_candidates"][0]["entity_key"],"doi:10.1234/abc")
        self.assertEqual(headless_packet(a)["schema"],"cite_refinery.headless_records.v1")

    def test_annotated_failures_no_false_empty_success(self):
        def fail(url):
            raise SourceFailure("test unavailable")
        res=collect({"schema":SCHEMA,"sources":[s()]},fetch=fail)
        self.assertEqual(res["source_results"][0]["state"],"unavailable")
        self.assertEqual(res["records"],[])

    def test_npm_results(self):
        p=json.dumps({"objects":[{"package":{"name":"data-verify",
            "description":"Provenance toolkit"}}]}).encode()
        out=collect_provider(s("npm"),fetch=lambda url:p)
        self.assertEqual(out[0]["entity_key"],"npm:data-verify")

    def test_huggingface_models_and_datasets(self):
        m=json.dumps([{"id":"org/model"}]).encode()
        d=json.dumps([{"id":"org/dataset"}]).encode()
        model=collect_provider(s("huggingface_models"),fetch=lambda url:m)
        dataset=collect_provider(s("huggingface_datasets"),fetch=lambda url:d)
        self.assertEqual(model[0]["entity_key"],"huggingface:models:org/model")
        self.assertEqual(dataset[0]["entity_key"],"huggingface:datasets:org/dataset")

    def test_rss_and_atom(self):
        rss=b'<rss><channel><item><title>package 1.0</title><link>https://pypi.org/project/package/1.0/</link></item></channel></rss>'
        p=collect_provider(s("pypi_updates",query=""),fetch=lambda url:rss)
        self.assertEqual(p[0]["entity_key"],"pypi:package")
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/2611.00001</id><title>New paper</title><link rel="alternate" href="https://arxiv.org/abs/2611.00001"/></entry></feed>'
        a=collect_provider(s("arxiv_ai",query=""),fetch=lambda url:atom)
        self.assertEqual(a[0]["entity_key"],"arxiv:2611.00001")

    def test_provider_links_are_strictly_host_scoped(self):
        forged=json.dumps({"results":[{"id":"https://openalex.org/W1",
            "display_name":"Poison link", "doi":"https://malicious.example/xx"}]}).encode()
        output=collect_provider(s("openalex"),fetch=lambda url:forged)
        # OpenAlex's trusted own identifier remains a valid fallback where
        # the DOI is not usable; arbitrary external URL must not be linked.
        self.assertEqual(output,[])

    def test_reject_other_domains_and_redirects(self):
        with self.assertRaises(SourceFailure):
            fetch_http("https://127.0.0.1/private")
        with self.assertRaises(SourceFailure):
            fetch_http("http://api.crossref.org/works")
        with self.assertRaises(SourceFailure):
            fetch_http("https://api.crossref.org:8443/works")

    def test_datacite_and_zenodo_independent_doi_cluster(self):
        def f(url):
            if "api.datacite.org" in url:
                return json.dumps({"data":[{"id":"10.5678/test","attributes":{
                    "doi":"10.5678/test","titles":[{"title":"A Research Dataset"}]}}]}).encode()
            if "zenodo.org" in url:
                return json.dumps({"hits":{"hits":[{"id":1234,"metadata":{
                    "title":"A Research Dataset","doi":"10.5678/test"}}]}}).encode()
            raise AssertionError(url)
        result=collect({"schema":SCHEMA,"sources":[
            s("datacite",sid="datacite"),s("zenodo",sid="zenodo")]},fetch=f)
        self.assertEqual(len(result["same_identity_candidates"]),1)
        self.assertEqual(result["same_identity_candidates"][0]["entity_key"],"doi:10.5678/test")

    def test_community_and_government_are_leads_not_fact(self):
        def f(url):
            if "hn.algolia.com" in url:
                return json.dumps({"hits":[{"objectID":"1234","title":"Community story",
                    "url":"https://bad.example/"}]}).encode()
            if "federalregister.gov" in url:
                return json.dumps({"results":[{"document_number":"2026-12345",
                    "title":"Energy Notice", "html_url":"https://www.federalregister.gov/documents/notice",
                    "publication_date":"2026-10-31"}]}).encode()
            raise AssertionError(url)
        result=collect({"schema":SCHEMA,"sources":[
            s("hackernews",sid="hackernews"),s("federal_register",sid="federal")]},fetch=f)
        self.assertEqual(len(result["records"]),2)
        self.assertTrue(result["records"][0]["source_url"].startswith("https://news.ycombinator.com/item?id="))
        self.assertEqual(result["records"][1]["evidence_status"],"unverified_external_metadata")

    def test_catalog_declares_candidates_not_live_integrations(self):
        path=Path(__file__).resolve().parent.parent/"examples/discovery/source_catalog.json"
        doc=json.loads(path.read_text())
        self.assertEqual(doc["schema"],"cite_refinery.discovery_source_catalog.v1")
        sources=doc["sources"]
        self.assertGreaterEqual(len(sources),80)
        self.assertEqual(len(set(v["id"] for v in sources)),len(sources))
        ready={v["id"] for v in sources if v["readiness"]=="implemented_live"}
        self.assertIn("datacite",ready)
        self.assertIn("zenodo",ready)
        self.assertNotIn("open_sanctions",ready)

    def test_immutable_private_outputs_and_git_guards(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"private"/"snapshot.json"
            _save(p,{"a":1})
            self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(ValueError):
                _save(p,{"a":2})
            (Path(td)/".git").mkdir()
            with self.assertRaises(ValueError):
                _save(Path(td)/"other"/"output.json",{"a":3})


if __name__ == "__main__":
    unittest.main()
