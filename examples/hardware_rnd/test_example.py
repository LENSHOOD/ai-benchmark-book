import unittest

from examples.benchmark_core import compare, load_tasks, trial_variation
from examples.hardware_rnd.run import ROOT, run


class HardwareRAndDTests(unittest.TestCase):
    def test_suite_matches_the_ten_narrative_scenarios(self):
        tasks = load_tasks(ROOT / "tasks.json")
        self.assertEqual(len(tasks), 10)
        self.assertTrue(any("evt" in task.tags for task in tasks))
        self.assertTrue(any("safety" in task.tags for task in tasks))
        self.assertTrue(any("requirements" in task.tags for task in tasks))

    def test_matrix_has_faults_state_and_auditable_results(self):
        rows = run()
        self.assertEqual(len(rows), 2 * 2 * 2 * 10 * 4)
        self.assertGreater(trial_variation(rows), 0)
        strongest = [row for row in rows if row.candidate == "capable.workflow.domain"]
        self.assertTrue(any(row.passed for row in strongest))
        self.assertTrue(any(row.environment_error for row in strongest))
        self.assertTrue(all(row.environment_hash and row.grader_version for row in rows))

    def test_unsafe_baseline_is_vetoed_and_comparison_is_task_paired(self):
        rows = run()
        self.assertTrue(any(row.veto for row in rows if row.candidate == "basic.direct.none"))
        result = compare(rows, "basic.direct.none", "capable.workflow.domain")
        self.assertEqual(result["paired_tasks"], 10)
        self.assertGreater(result["mean_score_delta"], 0)


if __name__ == "__main__":
    unittest.main()
