from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from examples.benchmark_core import (
    GraderConfig,
    PublicTask,
    _coverage,
    compare,
    grade,
    load_grader_config,
    load_tasks,
    write_results,
)
from examples.commerce_supply_chain.run import ROOT, execute
from examples.stateful_env import StatefulEnvironment, ToolEffect


class BenchmarkCoreContractTests(unittest.TestCase):
    """Each named grader failure mode must have a direct behavioral test.

    The suite intentionally avoids a universal mutation-score threshold. Its
    structural contract is stronger and easier to audit: every failure_class
    emitted by grade() is constructed below and must imply passed=False,
    except the explicit success class ``none``.
    """

    def setUp(self):
        self.task = load_tasks(ROOT / "tasks.json")[0]
        self.public = self.task.public_view()
        self.output = execute("capable", "workflow", "domain", self.public, 10)

    def test_answer_key_isolation_is_a_type_boundary(self):
        self.assertIsInstance(self.public, PublicTask)
        for private_name in ("target_state", "forbidden_final_states", "required_evidence", "forbidden_actions"):
            self.assertFalse(hasattr(self.public, private_name))

    def test_corrupting_target_does_not_change_policy_and_fails_grader(self):
        corrupted = replace(self.task, target_state={"reservation": "impossible_value"})
        result = grade("test", "test@1", "candidate", corrupted, 0, 10, self.output)
        self.assertFalse(result.passed)
        self.assertEqual(result.failure_class, "target_state")

    def test_alternative_action_trace_can_pass_when_terminal_state_is_correct(self):
        result = grade("test", "test@1", "candidate", self.task, 0, 10, self.output)
        self.assertTrue(result.passed)
        alternate = replace(self.output, actions=("different_valid_route",), trace=({"action": "different_valid_route", "status": "ok"},))
        alternate_result = grade("test", "test@1", "candidate", self.task, 0, 10, alternate)
        self.assertTrue(alternate_result.passed)

    def test_dangerous_shortcut_triggers_veto(self):
        unsafe = replace(self.output, actions=self.output.actions + ("double_reserve",), final_state={**self.output.final_state, "reservation": "duplicate"})
        result = grade("test", "test@1", "candidate", self.task, 0, 10, unsafe)
        self.assertTrue(result.veto)
        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)

    def test_forbidden_terminal_state_triggers_veto(self):
        task = replace(self.task, forbidden_final_states=(dict(self.output.final_state),))
        result = grade("test", "test@1", "candidate", task, 0, 10, self.output)
        self.assertTrue(result.veto)
        self.assertFalse(result.passed)
        self.assertEqual(result.failure_class, "veto")

    def test_every_named_failure_class_has_a_direct_contract(self):
        cases = {
            "environment_error": (self.task, replace(self.output, environment_error=True)),
            "veto": (self.task, replace(self.output, actions=self.output.actions + ("double_reserve",))),
            "insufficient_evidence": (self.task, replace(self.output, insufficient_evidence=True)),
            "target_state": (replace(self.task, target_state={"reservation": "impossible_value"}), self.output),
            "missing_evidence": (self.task, replace(self.output, evidence=())),
            "escalation": (replace(self.task, requires_escalation=not self.output.escalated), self.output),
        }
        for expected, (task, output) in cases.items():
            with self.subTest(failure_class=expected):
                result = grade("test", "test@1", "candidate", task, 0, 10, output)
                self.assertFalse(result.passed)
                self.assertEqual(result.failure_class, expected)

        success = grade("test", "test@1", "candidate", self.task, 0, 10, self.output)
        self.assertTrue(success.passed)
        self.assertEqual(success.failure_class, "none")

    def test_empty_evidence_is_rejected_at_the_grader_boundary(self):
        with self.assertRaisesRegex(ValueError, "required evidence must not be empty"):
            _coverage((), ())

    def test_diagnostic_score_uses_the_declared_weights(self):
        missing_evidence = replace(self.output, evidence=())
        target_only = grade(
            "test", "test@1", "candidate", self.task, 0, 10, missing_evidence,
            GraderConfig("target-only", target_weight=1.0, evidence_weight=0.0, escalation_weight=0.0),
        )
        evidence_only = grade(
            "test", "test@1", "candidate", self.task, 0, 10, missing_evidence,
            GraderConfig("evidence-only", target_weight=0.0, evidence_weight=1.0, escalation_weight=0.0),
        )
        self.assertEqual(target_only.score, 1.0)
        self.assertEqual(evidence_only.score, 0.0)

    def test_compare_derives_paired_tasks_from_the_intersection(self):
        template = grade("test", "test@1", "template", self.task, 0, 10, self.output)
        rows = [
            replace(template, candidate="baseline", task_id="shared-a", score=0.2),
            replace(template, candidate="baseline", task_id="shared-b", score=0.4),
            replace(template, candidate="baseline", task_id="baseline-only", score=0.9),
            replace(template, candidate="candidate", task_id="shared-a", score=0.8),
            replace(template, candidate="candidate", task_id="shared-b", score=0.6),
            replace(template, candidate="candidate", task_id="candidate-only", score=0.1),
        ]
        result = compare(rows, "baseline", "candidate", bootstrap_samples=100)
        self.assertEqual(result["paired_tasks"], 2)
        self.assertEqual(result["total_trials"], 6)
        self.assertEqual(result["candidate_wins"], 2)

    def test_compare_rejects_an_unpaired_experiment(self):
        with self.assertRaisesRegex(ValueError, "no paired tasks"):
            compare([], "baseline", "candidate")

    def test_grader_config_rejects_invalid_weights(self):
        invalid = (
            ({"target_state": -0.1, "evidence": 0.6, "escalation": 0.5}, "non-negative"),
            ({"target_state": 0.5, "evidence": 0.5, "escalation": 0.5}, "sum to 1"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grader.json"
            for weights, message in invalid:
                with self.subTest(weights=weights):
                    path.write_text(json.dumps({"version": "test", "diagnostic_weights": weights}))
                    with self.assertRaisesRegex(ValueError, message):
                        load_grader_config(path)

    def test_result_writer_is_auditable_and_non_overwriting(self):
        row = grade("test", "test@1", "candidate", self.task, 0, 10, self.output)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = write_results(root, [row], run_id="fixed-run")
            self.assertEqual(len((output / "trials.jsonl").read_text().splitlines()), 1)
            manifest = json.loads((output / "run_manifest.json").read_text())
            self.assertEqual(manifest["row_count"], 1)
            self.assertEqual(manifest["candidate_count"], 1)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["candidate"]["pass_rate"], 1.0)
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                write_results(root, [row], run_id="fixed-run")

    def test_stateful_environment_merges_nested_state_and_deduplicates(self):
        task = replace(self.public, initial_state={"order": {"status": "open", "amount": 1}})
        environment = StatefulEnvironment(
            task,
            seed=0,
            effects={"commit": ToolEffect({"order": {"status": "reserved"}}, evidence=("receipt",))},
        )
        self.assertTrue(environment.perform("commit", "key-1"))
        self.assertTrue(environment.perform("commit", "key-1"))
        self.assertFalse(environment.perform("missing", "key-2"))
        output = environment.finish("done")
        self.assertEqual(output.final_state["order"], {"status": "reserved", "amount": 1})
        self.assertEqual(output.actions, ("commit",))
        self.assertIn("idempotency_state", output.evidence)
        self.assertIn("unknown_action:missing", output.tool_errors)

    def test_task_schema_rejects_empty_target_and_evidence(self):
        payload = {
            "tasks": [{
                "task_id": "bad", "title": "bad", "prompt": "bad", "observable": {},
                "initial_state": {}, "target_state": {}, "required_evidence": []
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "target_state must not be empty"):
                load_tasks(path)


if __name__ == "__main__":
    unittest.main()
