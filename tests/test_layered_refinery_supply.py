import tempfile
import unittest

from cite_refinery import CiteRefinery
from cite_refinery.solution import LayeredRefinerySearchAdapter, RefinerySearchResult


class FakeCanonical:
    def __init__(self, *, candidate=True):
        self.candidate = candidate
        self.queries = []

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        self.queries.append((query, limit))
        commons = []
        if self.candidate:
            commons = [{
                "kind": "capability",
                "subject_id": "capability:version-history",
                "capability": "version-history",
                "authority": "commons",
            }]
        return RefinerySearchResult(
            engine="fake:canonical",
            status="completed",
            raw="canonical",
            structured={"query": query, "commons": commons, "operational": []},
        )


class FakeMarket:
    def __init__(self, *, status="completed", candidate=True):
        self.status = status
        self.candidate = candidate
        self.queries = []

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        self.queries.append((query, limit))
        if self.status != "completed":
            return RefinerySearchResult(
                engine="fake:market",
                status=self.status,
                raw="market unavailable",
                structured=None,
            )
        results = []
        if self.candidate:
            results = [{
                "kind": "reviewed_market_entity",
                "authority": "reviewed_market_graph",
                "entity_id": "repo:example/version-vault",
                "name": "VersionVault",
                "repository": "example/version-vault",
                "reviewed_relations": [{
                    "predicate": "solves_job",
                    "object_value": "document revision provenance",
                }],
            }]
        return RefinerySearchResult(
            engine="fake:market",
            status="completed",
            raw="market",
            structured={"query": query, "results": results},
        )


class LayeredRefinerySupplyTests(unittest.TestCase):
    def test_layered_adapter_preserves_two_authorities(self):
        canonical = FakeCanonical()
        market = FakeMarket()
        adapter = LayeredRefinerySearchAdapter(canonical=canonical, market=market)
        result = adapter.search("version provenance", limit=8)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.structured["commons"][0]["authority"], "commons")
        self.assertEqual(result.structured["reviewed_market"][0]["authority"], "reviewed_market_graph")
        self.assertEqual(result.structured["results"], result.structured["reviewed_market"])
        self.assertIn("do not inherit Commons admission", result.structured["boundary"])
        self.assertEqual(canonical.queries, [("version provenance", 8)])
        self.assertEqual(market.queries, [("version provenance", 8)])

    def test_solution_map_can_surface_commons_and_market_without_auto_adoption(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = LayeredRefinerySearchAdapter(canonical=FakeCanonical(), market=FakeMarket())
            app = CiteRefinery(tmp, solution_refinery=adapter)
            project = app.init_project("Revision provenance", "Find existing ways to preserve changing public records")
            requirement = app.add_requirement(
                project.id,
                "Preserve document revision provenance",
                tags=["provenance", "versioning"],
            )
            solution_map = app.map_requirements(project.id, [requirement.id], limit=10)
            mapped = solution_map.results[requirement.id]

            self.assertEqual(mapped["canonical_candidate_count"], 2)
            self.assertEqual(mapped["supply_candidate_count"], 2)
            self.assertEqual(
                mapped["supply_authority_counts"],
                {"commons": 1, "reviewed_market_graph": 1},
            )
            authorities = {row.get("authority") for row in mapped["supply_candidates"]}
            self.assertEqual(authorities, {"commons", "reviewed_market_graph"})
            self.assertIn("Authority is per candidate", mapped["supply_boundary"])
            state = app.store.load()
            self.assertEqual(state["capabilities"], {})
            self.assertEqual(state["implementations"], {})

            market_candidate = next(
                row for row in mapped["supply_candidates"]
                if row.get("authority") == "reviewed_market_graph"
            )
            self.assertEqual(market_candidate["repository"], "example/version-vault")

    def test_explicit_adoption_retains_market_candidate_reference_but_not_authority_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = LayeredRefinerySearchAdapter(canonical=FakeCanonical(candidate=False), market=FakeMarket())
            app = CiteRefinery(tmp, solution_refinery=adapter)
            project = app.init_project("Revision provenance", "Evaluate reviewed market supply")
            requirement = app.add_requirement(project.id, "Preserve document revision provenance")
            solution_map = app.map_requirements(project.id, [requirement.id])

            cap = app.adopt_capability(
                project.id,
                requirement.id,
                name="VersionVault evaluation",
                description="Project-local candidate evaluation of a reviewed market repository",
                solution_map_id=solution_map.id,
                candidate_ref="reviewed-market:repo:example/version-vault",
            )
            self.assertEqual(cap.scope, "project")
            self.assertEqual(cap.provenance["candidate_ref"], "reviewed-market:repo:example/version-vault")
            self.assertFalse(any(
                impl["capability_id"] == cap.id
                for impl in app.store.load()["implementations"].values()
            ))

    def test_market_not_run_keeps_canonical_path_usable(self):
        adapter = LayeredRefinerySearchAdapter(
            canonical=FakeCanonical(),
            market=FakeMarket(status="not_run", candidate=False),
        )
        result = adapter.search("version provenance")
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.structured["commons"]), 1)
        self.assertEqual(result.structured["reviewed_market"], [])
        self.assertEqual(result.structured["layers"]["reviewed_market"]["status"], "not_run")

    def test_market_error_is_visible_as_partial_not_silently_ignored(self):
        adapter = LayeredRefinerySearchAdapter(
            canonical=FakeCanonical(),
            market=FakeMarket(status="error", candidate=False),
        )
        result = adapter.search("version provenance")
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.structured["layers"]["canonical"]["status"], "completed")
        self.assertEqual(result.structured["layers"]["reviewed_market"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
