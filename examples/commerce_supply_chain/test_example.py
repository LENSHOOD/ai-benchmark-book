import unittest

from examples.benchmark_core import compare, load_tasks, trial_variation
from examples.commerce_supply_chain.run import ROOT, run


class CommerceSupplyChainTests(unittest.TestCase):
    def test_suite_matches_the_ten_narrative_scenarios(self):
        tasks = load_tasks(ROOT / "tasks.json")
        self.assertEqual(len(tasks), 10)
        self.assertTrue(any("frequency" in task.tags for task in tasks))
        self.assertTrue(any("concurrency" in task.tags for task in tasks))
        self.assertTrue(any("policy_conflict" in task.tags for task in tasks))
        self.assertTrue(any(task.critical for task in tasks))

    def test_matrix_has_real_trial_variation_and_no_constructed_winner(self):
        rows = run()
        self.assertEqual(len(rows), 2 * 2 * 2 * 10 * 4)
        self.assertGreater(trial_variation(rows), 0)
        strongest = [row for row in rows if row.candidate == "capable.workflow.domain"]
        self.assertTrue(any(row.passed for row in strongest))
        self.assertTrue(any(row.insufficient_evidence for row in strongest))
        self.assertFalse(any(row.veto for row in strongest))

    def test_comparison_pairs_tasks_and_reports_interval(self):
        result = compare(run(), "basic.direct.none", "capable.workflow.domain")
        self.assertEqual(result["paired_tasks"], 10)
        self.assertEqual(result["total_trials"], 80)
        self.assertEqual(len(result["ci95"]), 2)
        self.assertGreater(result["mean_score_delta"], 0)


if __name__ == "__main__":
    unittest.main()
