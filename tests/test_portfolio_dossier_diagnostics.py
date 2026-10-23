import unittest
from cite_refinery.portfolio_dossier_diagnostics import diagnose, aggregate

class DiagnosticsTests(unittest.TestCase):
    def test_missing_fields(self):
        x=diagnose('{"capabilities":[],"limitations":[]}')
        self.assertFalse(x["complete"])
        self.assertIn("missing_fields",x["errors"])

    def test_invalid_claim_list(self):
        x=diagnose('{"capabilities":[],"limitations":["unsupported"],"integration_candidates":[],"competitor_substitutions":[],"decision":"investigate","decision_rationale":"unknown","unanswered_questions":[]}')
        self.assertIn("malformed_limitations",x["errors"])

    def test_bad_json(self):
        self.assertFalse(diagnose("invalid")["parseable"])

    def test_aggregate(self):
        self.assertEqual(aggregate([{"raw":"{}"},{"raw":"invalid"}])["structurally_complete"],0)

if __name__=="__main__":
    unittest.main()
