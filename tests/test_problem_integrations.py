import unittest

from cite_refinery.problem_commons import ProblemCommons, Visibility
from cite_refinery.problem_integrations import ContextKind, ContextUpdate, apply_update


class IntegrationContractTests(unittest.TestCase):
    def setUp(self):
        self.commons = ProblemCommons()
        self.problem = self.commons.create_problem(
            title="Example problem",
            observed_condition="A recurring condition is observed.",
            unresolved_core="Determine the binding mechanism.",
            steward="curator",
        )

    def test_nocturnal_observation_requires_explicit_apply(self):
        update = ContextUpdate(
            id="ctx:1",
            source_system="nocturnal",
            source_ref="matter:1",
            kind=ContextKind.OBSERVATION,
            confidence="reviewed",
            visibility=Visibility.RESTRICTED,
            payload={"summary": "Condition recurred.", "locator": "restricted:matter:1"},
        )
        self.assertEqual(self.problem.evidence, [])
        apply_update(self.problem, update, accepted_by="reviewer")
        self.assertEqual(len(self.problem.evidence), 1)
        self.assertEqual(self.problem.external_refs[0].system, "nocturnal")

    def test_cite_and_refinery_updates_merge_frontiers(self):
        apply_update(self.problem, ContextUpdate(
            id="ctx:k", source_system="cite", source_ref="dossier:1",
            kind=ContextKind.KNOWLEDGE,
            payload={"frontier": ["Mechanism A is supported only in context X."]},
        ), accepted_by="reviewer")
        apply_update(self.problem, ContextUpdate(
            id="ctx:c", source_system="refinery", source_ref="search:1",
            kind=ContextKind.CAPABILITY,
            payload={"frontier": ["routing available"], "needs": [{"name": "live capacity verification", "state": "needed"}]},
        ), accepted_by="reviewer")
        self.assertIn("Mechanism A is supported only in context X.", self.problem.knowledge_frontier)
        self.assertIn("routing available", self.problem.capability_frontier)
        self.assertEqual(self.problem.capability_needs[0].name, "live capacity verification")

    def test_public_good_diagnosis_does_not_authorize_action(self):
        apply_update(self.problem, ContextUpdate(
            id="ctx:d", source_system="public-good", source_ref="case:1",
            kind=ContextKind.DIAGNOSIS,
            payload={"diagnosis": ["Access may be the bottleneck."], "authority_boundary": "Operator approval required.", "implementation_pathway": ["shadow test"]},
        ), accepted_by="reviewer")
        self.assertEqual(self.problem.authority_decisions, [])
        self.assertEqual(self.problem.authority_boundary, "Operator approval required.")


if __name__ == "__main__":
    unittest.main()
