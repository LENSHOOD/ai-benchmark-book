"""Behavioral regressions from the independent 2026-09-19 execution review.

These tests observe state, receipts and grading outcomes. A renamed failure
status or a successful command alone does not establish business correctness.
"""

from copy import deepcopy
from dataclasses import replace
import unittest

from examples.benchmark_core import compare, grade, load_tasks
from examples.commerce_supply_chain.run import EFFECTS, ROOT, execute
from examples.stateful_env import StatefulEnvironment, ToolEffect


class StatefulReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks(ROOT / "tasks.json")
        self.transaction = replace(
            self.tasks[0].public_view(),
            observable={"fault_target": "commit"},
            initial_state={"transaction": {"ledger_written": False, "stock_written": False}},
        )
        self.effects = {
            "commit": ToolEffect(
                {"transaction": {"ledger_written": True, "stock_written": True}},
                evidence=("full_receipt",),
                cost_units=2.0,
                latency_ms=50,
            )
        }

    def test_partial_write_commits_a_strict_subset_without_a_full_receipt(self):
        environment = StatefulEnvironment(self.transaction, seed=2, effects=self.effects)
        self.assertFalse(environment.perform("commit", "tx-1"))
        interrupted = environment.finish("interrupted transaction")
        committed = sum(interrupted.final_state["transaction"].values())
        self.assertGreater(committed, 0, "the injected failure must follow an actual write")
        self.assertLess(committed, 2, "partial_write must leave at least one write unfinished")
        self.assertNotIn("full_receipt", interrupted.evidence)
        self.assertNotIn("idempotency_state", interrupted.evidence)
        self.assertTrue(interrupted.insufficient_evidence)
        self.assertFalse(any(item["status"] == "deduplicated" for item in interrupted.trace))

    def test_partial_write_recovery_finishes_once_and_then_deduplicates(self):
        environment = StatefulEnvironment(self.transaction, seed=2, effects=self.effects)
        self.assertFalse(environment.perform("commit", "tx-1"))
        self.assertTrue(environment.recover("commit", "tx-1"))
        recovered = environment.finish("recovered transaction")
        self.assertEqual(recovered.final_state["transaction"], {"ledger_written": True, "stock_written": True})
        self.assertIn("full_receipt", recovered.evidence)
        self.assertFalse(recovered.insufficient_evidence)
        self.assertEqual(recovered.actions.count("commit"), 1)
        queries = [item for item in recovered.trace if item["action"] == "query_idempotency"]
        self.assertTrue(queries, "recovery must check the interrupted transaction")
        self.assertNotEqual(queries[0]["status"], "applied", "a partial write is not a completed key")

        self.assertTrue(environment.recover("commit", "tx-1"))
        self.assertTrue(environment.perform("commit", "tx-1"))
        repeated = environment.finish("repeated recovery and retry")
        self.assertEqual(repeated.final_state, recovered.final_state)
        self.assertEqual(repeated.actions, recovered.actions)

    def test_lost_response_is_a_complete_write_and_recovery_does_not_repeat_it(self):
        environment = StatefulEnvironment(self.transaction, seed=3, effects=self.effects)
        self.assertFalse(environment.perform("commit", "tx-1"))
        lost = environment.finish("response lost")
        self.assertEqual(lost.final_state["transaction"], {"ledger_written": True, "stock_written": True})
        self.assertIn("full_receipt", lost.evidence)
        self.assertTrue(lost.insufficient_evidence)
        self.assertTrue(environment.recover("commit", "tx-1"))
        recovered = environment.finish("confirmed existing transaction")
        self.assertEqual(recovered.final_state, lost.final_state)
        self.assertEqual(recovered.actions, lost.actions)
        self.assertFalse(recovered.insufficient_evidence)

    def test_refund_retry_with_the_same_key_records_one_payment(self):
        task = next(task for task in self.tasks if task.task_id == "cs-005")
        environment = StatefulEnvironment(task.public_view(), seed=0, effects=EFFECTS)
        self.assertTrue(environment.perform("issue_low_value_refund", "refund-1"))
        self.assertTrue(environment.perform("issue_low_value_refund", "refund-1"))
        output = environment.finish("same request retried")
        self.assertEqual(output.final_state["refund_count"], 1)
        self.assertEqual(len(output.final_state["refund_ledger"]), 1)
        self.assertEqual(output.actions.count("issue_low_value_refund"), 1)

    def test_refund_with_a_different_key_is_blocked_or_vetoed(self):
        task = next(task for task in self.tasks if task.task_id == "cs-005")
        environment = StatefulEnvironment(task.public_view(), seed=0, effects=EFFECTS)
        for action in ("verify_damage", "check_existing_refund"):
            self.assertTrue(environment.perform(action, action))
        self.assertTrue(environment.perform("issue_low_value_refund", "refund-1"))
        accepted = environment.perform("issue_low_value_refund", "refund-2")
        environment.perform("notify_customer", "notification-1")
        output = environment.finish("distinct duplicate refund request")
        result = grade("review", "review@1", "probe", task, 0, 0, output)
        self.assertTrue(
            not accepted or result.veto,
            "a distinct second payment must be blocked or trigger a business-state veto",
        )
        if accepted:
            self.assertFalse(result.passed)
        else:
            self.assertEqual(output.final_state["refund_count"], 1)
            self.assertEqual(len(output.final_state["refund_ledger"]), 1)

    def test_failed_attempts_include_cost_and_elapsed_time(self):
        for seed, profile in ((1, "pre_call"), (4, "unavailable")):
            with self.subTest(profile=profile):
                environment = StatefulEnvironment(self.transaction, seed, self.effects)
                self.assertFalse(environment.perform("commit", "tx-1"))
                output = environment.finish("failed attempt")
                self.assertGreater(output.cost_units, 0)
                self.assertGreater(output.latency_ms, 0)
                self.assertEqual(output.final_state, self.transaction.initial_state)
                self.assertNotIn("full_receipt", output.evidence)

    def test_public_view_mutations_cannot_pollute_later_trials(self):
        task = replace(
            self.tasks[0],
            observable={"inventory": {"units": [1, 2]}},
            initial_state={"order": {"status": "open", "events": []}},
        )
        original_observable = deepcopy(task.observable)
        original_state = deepcopy(task.initial_state)
        public = task.public_view()
        public.observable["inventory"]["units"].append(999)
        public.initial_state["order"]["status"] = "polluted"
        public.initial_state["order"]["events"].append({"unauthorized": True})
        self.assertEqual(task.observable, original_observable)
        self.assertEqual(task.initial_state, original_state)
        next_trial = task.public_view()
        self.assertEqual(next_trial.observable, original_observable)
        self.assertEqual(next_trial.initial_state, original_state)


class ComparisonReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        task = load_tasks(ROOT / "tasks.json")[0]
        output = execute("capable", "workflow", "domain", task.public_view(), 0)
        template = grade("review", "review@1", "template", task, 0, 0, output)
        self.rows = [
            replace(template, candidate=name, task_id="shared", trial=trial, score=float(trial))
            for name in ("baseline", "candidate")
            for trial in range(2)
        ]

    def test_duplicate_trial_identity_cannot_change_the_conclusion(self):
        clean = compare(self.rows, "baseline", "candidate", bootstrap_samples=100)
        self.assertEqual(clean["mean_score_delta"], 0)
        for duplicate in (self.rows[1], replace(self.rows[1], seed=999)):
            with self.subTest(duplicate_seed=duplicate.seed):
                with self.assertRaises(ValueError):
                    compare(self.rows + [duplicate], "baseline", "candidate", bootstrap_samples=100)

    def test_mixed_suite_and_scoring_versions_are_rejected(self):
        for field in ("suite", "suite_version", "grader_version"):
            with self.subTest(field=field):
                mixed = self.rows[:-1] + [replace(self.rows[-1], **{field: "incompatible"})]
                with self.assertRaises(ValueError):
                    compare(mixed, "baseline", "candidate", bootstrap_samples=100)

    def test_missing_tasks_are_explicitly_excluded_from_the_paired_result(self):
        rows = self.rows + [
            replace(self.rows[0], task_id="baseline-only", score=1.0),
            replace(self.rows[2], task_id="candidate-only", score=0.0),
        ]
        result = compare(rows, "baseline", "candidate", bootstrap_samples=100)
        self.assertEqual(result["paired_tasks"], 1)
        self.assertEqual(result["paired_trials"], 4)
        self.assertEqual(result["total_trials"], 6)
        self.assertEqual(result["mean_score_delta"], 0)
        self.assertEqual(
            result["unpaired_task_ids"],
            {"baseline": ["baseline-only"], "candidate": ["candidate-only"]},
        )

    def test_invalid_bootstrap_sample_counts_raise_a_clear_value_error(self):
        for samples in (0, -1, 1.5, True, False, "10", None):
            with self.subTest(bootstrap_samples=samples):
                with self.assertRaises(ValueError):
                    compare(self.rows, "baseline", "candidate", bootstrap_samples=samples)


if __name__ == "__main__":
    unittest.main()
