import unittest

from portable.agency_ragas_eval import evaluate_codebase_answer, retrieval_metrics


class RagasEvalTests(unittest.TestCase):
    def test_retrieval_precision_recall_and_path_hit(self) -> None:
        metrics = retrieval_metrics(
            ["Planner builds the execution plan"],
            relevant_contexts=["Planner builds the execution plan"],
            retrieved_paths=["portable/agency_execution_plan.py"],
            expected_paths=["portable/agency_execution_plan.py"],
        )
        self.assertEqual(metrics.context_recall, 1.0)
        self.assertEqual(metrics.path_hit_rate, 1.0)
        self.assertGreater(metrics.context_precision, 0.0)

    def test_unsupported_claim_reduces_faithfulness(self) -> None:
        result = evaluate_codebase_answer(
            "Where is Planner defined?",
            "Planner is defined in planner.py. It also calls a hidden database.",
            ["Planner is defined in planner.py."],
            retrieved_paths=["planner.py"],
            expected_paths=["planner.py"],
        )
        self.assertLess(result.answer.faithfulness, 1.0)
        self.assertIn("answer contains claims", " ".join(result.findings))


if __name__ == "__main__":
    unittest.main()
