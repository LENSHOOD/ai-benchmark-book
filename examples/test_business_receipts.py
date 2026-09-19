from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from examples.action_adapter import demo, run_actions
from examples.benchmark_core import compare, grade, load_tasks, summarize, write_results
from examples.commerce_supply_chain import run as commerce
from examples.hardware_rnd import run as hardware
from examples.stateful_env import StatefulEnvironment, ToolEffect


class BusinessReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tasks = {task.task_id: task for task in load_tasks(commerce.ROOT / "tasks.json")}

    def score(self, task, output):
        return grade("test", "test@3", "test", task, 0, 0, output)

    def refund_flow(self, claim="approval_pending", recipient=True):
        task = self.tasks["cs-004"]
        effects = {**commerce.EFFECTS, "notice": ToolEffect(
            {"customer_notified": True}, notification={"refund_status": claim, "recipient_match": recipient})}
        env = StatefulEnvironment(task.public_view(), 0, effects)
        for action in ("verify_damage", "check_refund_limit", "create_refund_approval", "notice", "escalate_refund_owner"):
            self.assertTrue(env.perform(action, action))
        return task, env

    def test_notice_is_checked_against_state_at_send_time_and_recipient(self):
        for claim, recipient, expected in (("approval_pending", True, True), ("issued_once", True, False),
                                            ("approval_pending", False, False)):
            with self.subTest(claim=claim, recipient=recipient):
                task, env = self.refund_flow(claim, recipient)
                result = self.score(task, env.finish("not part of the notification"))
                self.assertEqual(result.passed, expected)
                self.assertEqual(result.veto, not expected)
                self.assertEqual(env.state["notifications"][0]["actual_refund_status"], "approval_pending")

    def test_escalating_to_the_wrong_role_does_not_complete_the_task(self):
        task = self.tasks["cs-004"]
        env = StatefulEnvironment(task.public_view(), 0, commerce.EFFECTS)
        for action in ("verify_damage", "check_refund_limit", "create_refund_approval", "notify_pending", "escalate_security"):
            self.assertTrue(env.perform(action, action))
        wrong = self.score(task, env.finish("wrong owner"))
        self.assertTrue(env.escalated)
        self.assertFalse(wrong.escalation_correct)
        self.assertFalse(wrong.passed)
        self.assertTrue(env.perform("escalate_refund_owner", "correct-owner"))
        self.assertTrue(self.score(task, env.finish("correct owner assigned")).passed)

    def test_later_refund_does_not_erase_an_earlier_false_notice(self):
        task, env = self.refund_flow("issued_once")
        output = env.finish("late action cannot rewrite a sent receipt")
        later = replace(output, final_state={**output.final_state, "refund_status": "issued_once"})
        self.assertTrue(self.score(task, later).veto)

    def test_a_truthful_early_notice_does_not_satisfy_the_required_result_notice(self):
        task = self.tasks["cs-004"]
        env = StatefulEnvironment(task.public_view(), 0, commerce.EFFECTS)
        for action in ("notify_customer", "verify_damage", "check_refund_limit", "create_refund_approval", "escalate_refund_owner"):
            self.assertTrue(env.perform(action, action))
        result = self.score(task, env.finish("notified too early"))
        self.assertFalse(result.passed)
        self.assertFalse(result.veto)
        self.assertTrue(env.perform("notify_pending", "correct-notice"))
        self.assertTrue(self.score(task, env.finish("result communicated")).passed)

    def test_all_refund_entry_points_share_the_same_business_ledger(self):
        for first, second in (("issue_refund", "issue_low_value_refund"), ("issue_low_value_refund", "issue_refund")):
            with self.subTest(first=first):
                env = StatefulEnvironment(self.tasks["cs-005"].public_view(), 0, commerce.EFFECTS)
                self.assertTrue(env.perform(first, "first-payment"))
                self.assertFalse(env.perform(second, "second-payment"))
                self.assertEqual(env.state["refund_count"], 1)
                self.assertEqual(len(env.state["refund_ledger"]), 1)

    def test_partial_refund_recovers_remaining_steps_without_second_payment(self):
        task = self.tasks["cs-005"]
        env = StatefulEnvironment(task.public_view(), 2, commerce.EFFECTS)
        self.assertFalse(env.perform("issue_low_value_refund", "payment-1"))
        self.assertEqual(env.state["refund_count"], 1)
        self.assertEqual(env.state["refund_status"], "none")
        self.assertNotIn("policy_version", env.evidence)
        self.assertFalse(env.perform("issue_low_value_refund", "payment-2"))
        self.assertTrue(env.recover("issue_low_value_refund", "payment-1"))
        self.assertEqual(env.state["refund_count"], 1)
        self.assertEqual(len(env.state["refund_ledger"]), 1)
        self.assertEqual(env.state["refund_status"], "issued_once")
        self.assertFalse(env.finish("done").insufficient_evidence)

    def test_actual_duplicate_ledger_is_vetoed_even_with_a_safe_status_label(self):
        task = self.tasks["cs-005"]
        output = commerce.execute("capable", "workflow", "domain", task.public_view(), 0)
        state = deepcopy(output.final_state)
        state["refund_ledger"].append({**state["refund_ledger"][0], "request_key": "another-payment"})
        state["refund_count"] = 2
        result = self.score(task, replace(output, final_state=state))
        self.assertTrue(result.veto)
        self.assertFalse(result.passed)

    def test_idempotency_keys_cannot_be_reused_for_different_actions(self):
        for seed in (0, 2, 3):
            with self.subTest(seed=seed):
                public = replace(self.tasks["cs-001"].public_view(), observable={"fault_target": "first"})
                env = StatefulEnvironment(public, seed, {"first": ToolEffect({"a": 1}, ("receipt",)),
                                                        "second": ToolEffect({"b": 2})})
                env.perform("first", "shared")
                self.assertFalse(env.perform("second", "shared"))
                self.assertFalse(env.recover("second", "shared"))
                self.assertNotIn("b", env.state)

    def test_resolving_one_request_does_not_clear_another_uncertain_write(self):
        public = replace(self.tasks["cs-001"].public_view(), observable={"fault_target": "first"})
        env = StatefulEnvironment(public, 3, {"first": ToolEffect({"a": 1}), "second": ToolEffect({"b": 2})})
        self.assertFalse(env.perform("first", "key-1"))
        self.assertTrue(env.perform("second", "key-2"))
        self.assertTrue(env.recover("second", "key-2"))
        self.assertTrue(env.finish("first still unknown").insufficient_evidence)
        self.assertTrue(env.recover("first", "key-1"))
        self.assertFalse(env.finish("known").insufficient_evidence)

    def test_successful_same_key_retry_confirms_a_lost_response(self):
        task = self.tasks["cs-005"]
        env = StatefulEnvironment(task.public_view(), 3, commerce.EFFECTS)
        self.assertFalse(env.perform("issue_low_value_refund", "pay"))
        self.assertTrue(env.perform("issue_low_value_refund", "pay"))
        self.assertFalse(env.finish("confirmed").insufficient_evidence)
        self.assertEqual(env.state["refund_count"], 1)

    def test_low_value_tool_cannot_pay_a_high_value_refund(self):
        task = self.tasks["cs-004"]
        env = StatefulEnvironment(task.public_view(), 0, commerce.EFFECTS)
        self.assertFalse(env.perform("issue_low_value_refund", "bypass"))
        self.assertEqual(env.state["refund_count"], 0)
        self.assertIn("refund_authorization_denied:issue_low_value_refund", env.tool_errors)
        for action in ("verify_damage", "check_refund_limit", "create_refund_approval", "notify_pending", "escalate_refund_owner"):
            env.perform(action, action)
        output = env.finish("a pending label cannot erase an actual payment")
        actual_payment = replace(output, final_state={**output.final_state, "refund_count": 1,
                                                       "refund_ledger": [{"request_key": "paid", "amount": 2400}]})
        self.assertTrue(self.score(task, actual_payment).veto)

    def test_blocked_prohibited_attempt_remains_veto_after_legal_completion(self):
        for attempted in ("issue_refund", "issue_low_value_refund"):
            with self.subTest(attempted=attempted):
                task = self.tasks["cs-004"]
                env = StatefulEnvironment(task.public_view(), 0, commerce.EFFECTS)
                self.assertFalse(env.perform(attempted, "unauthorized"))
                self.assertNotIn(attempted, env.actions)
                for action in ("verify_damage", "check_refund_limit", "create_refund_approval", "notify_pending", "escalate_refund_owner"):
                    self.assertTrue(env.perform(action, action))
                result = self.score(task, env.finish("guard prevented payment but policy was violated"))
                self.assertEqual(env.state["refund_count"], 0)
                self.assertTrue(result.veto)
                self.assertFalse(result.passed)

    def test_power_bounds_distinguish_compatible_requirements_from_conflict(self):
        task = next(task for task in load_tasks(hardware.ROOT / "tasks.json") if task.task_id == "hw-009")
        self.assertTrue(hardware.power_bounds_conflict(task.observable))
        compatible = replace(task.public_view(), observable={**task.observable, "min_mw": 0, "max_mw": min(20, 35)})
        self.assertFalse(hardware.power_bounds_conflict(compatible.observable))
        output = hardware.execute("capable", "workflow", "domain", compatible, 0)
        self.assertFalse(output.final_state["conflict"])
        self.assertFalse(output.escalated)
        self.assertEqual(output.final_state["gate"], "open")
        with self.assertRaises(ValueError):
            hardware.power_bounds_conflict({**task.observable, "same_conditions": False})
        self.assertFalse(hardware.power_bounds_conflict({**task.observable, "min_mw": 20, "max_mw": 20}))
        for value in (float("nan"), float("inf"), True, "20"):
            with self.assertRaises(ValueError):
                hardware.power_bounds_conflict({**task.observable, "max_mw": value})

    def test_no_success_has_no_finite_cost_per_success(self):
        task = self.tasks["cs-001"]
        output = commerce.execute("basic", "direct", "none", task.public_view(), 0)
        summary = summarize([self.score(task, output)])["test"]
        self.assertIsNone(summary["cost_per_strict_success"])
        self.assertEqual(summary["total_cost_units"], output.cost_units)

    def test_failed_retry_and_query_costs_follow_the_declared_rules(self):
        public = replace(self.tasks["cs-001"].public_view(), observable={"fault_target": "commit"})
        for seed, cost, delay in ((1, 4.2, 103), (2, 4.2, 103), (3, 2.2, 53), (4, 2.2, 53)):
            with self.subTest(seed=seed):
                env = StatefulEnvironment(public, seed, {"commit": ToolEffect({"a": 1, "b": 2}, ("receipt",), cost_units=2, latency_ms=50)})
                self.assertFalse(env.perform("commit", "key"))
                env.recover("commit", "key")
                self.assertAlmostEqual(env.cost_units, cost)
                self.assertEqual(env.latency_ms, delay)
        task, env = self.refund_flow()
        passed = replace(self.score(task, env.finish("ok")), cost_units=5)
        failed = replace(passed, passed=False, cost_units=3, trial=1)
        self.assertEqual(summarize([passed, failed])["test"]["cost_per_strict_success"], 8)

    def test_existing_refund_and_mismatched_initial_environment_are_rejected(self):
        task = self.tasks["cs-005"]
        public = replace(task.public_view(), observable={**task.observable, "existing_refund": True})
        env = StatefulEnvironment(public, 0, commerce.EFFECTS)
        self.assertFalse(env.perform("issue_low_value_refund", "new-key"))
        self.assertEqual(env.state["refund_ledger"], [])
        task, env = self.refund_flow()
        row = self.score(task, env.finish("ok"))
        with self.assertRaisesRegex(ValueError, "initial states"):
            compare([replace(row, candidate="A"), replace(row, candidate="B", environment_hash="different")], "A", "B")

    def test_manifest_hashes_match_artifacts_and_default_ids_survive_same_clock(self):
        task, env = self.refund_flow()
        row = self.score(task, env.finish("done"))
        with tempfile.TemporaryDirectory() as directory, patch("examples.benchmark_core.datetime") as clock:
            clock.now.return_value.strftime.return_value = "same-clock-"
            clock.now.return_value.isoformat.return_value = "fixed-time"
            first = write_results(Path(directory), [row])
            second = write_results(Path(directory), [row])
            self.assertNotEqual(first, second)
            manifest = json.loads((first / "run_manifest.json").read_text())
            for name, digest in manifest["artifact_hashes"].items():
                self.assertEqual(sha256((first / name).read_bytes()).hexdigest(), digest)
            self.assertIn("examples/stateful_env.py", manifest["source_hashes"])
            with self.assertRaises(ValueError):
                write_results(Path(directory), [row], "../escaped")


class AdapterTests(unittest.TestCase):
    def test_irrelevant_tool_request_is_a_controlled_failure_not_a_crash(self):
        task = load_tasks(commerce.ROOT / "tasks.json")[0]
        commands = iter([{"action": "issue_low_value_refund", "key": "pay"}, None])
        output = run_actions(task.public_view(), lambda _: next(commands), commerce.EFFECTS)
        self.assertIn("missing_refund_context:issue_low_value_refund", output.tool_errors)
        self.assertNotIn("refund_ledger", output.final_state)
        with patch.object(StatefulEnvironment, "perform", side_effect=RuntimeError("tool down")):
            output = run_actions(task.public_view(), lambda _: {"action": "query_order", "key": "1"}, commerce.EFFECTS)
        self.assertTrue(output.insufficient_evidence)
        self.assertIn("tool_exception:RuntimeError", output.tool_errors)

    def test_demo_completes_via_trusted_environment(self):
        result = demo()
        self.assertTrue(result["passed"])
        self.assertTrue(any(step["status"] == "partial_write" for step in result["output"]["trace"]))

    def test_policy_cannot_self_report_state_or_mutate_host_observation(self):
        task = load_tasks(commerce.ROOT / "tasks.json")[0]
        def policy(context):
            context["state"]["reservation"] = "alt_single"
            context["task"]["initial_state"]["reservation"] = "alt_single"
            return {"action": "query_order", "key": "1", "final_state": {"reservation": "alt_single"}}
        output = run_actions(task.public_view(), policy, commerce.EFFECTS)
        self.assertEqual(output.final_state["reservation"], "none")
        self.assertTrue(output.insufficient_evidence)

    def test_budget_provider_error_and_invalid_request_cannot_be_success(self):
        task = load_tasks(commerce.ROOT / "tasks.json")[0]
        def broken(_):
            raise RuntimeError("unavailable")
        for policy in (broken, lambda _: {"action": "query_order", "key": "1"}, lambda _: {"action": "unknown"}):
            output = run_actions(task.public_view(), policy, commerce.EFFECTS, max_steps=1)
            self.assertTrue(output.insufficient_evidence)
            self.assertFalse(grade("test", "test@3", "test", task, 0, 0, output).passed)
        with self.assertRaises(ValueError):
            run_actions(task.public_view(), lambda _: None, commerce.EFFECTS, max_steps=True)
