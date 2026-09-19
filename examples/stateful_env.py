"""Small stateful sandbox with deterministic fault injection and idempotency."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from examples.benchmark_core import AgentOutput, PublicTask


@dataclass(frozen=True)
class ToolEffect:
    state: Mapping[str, Any]
    evidence: tuple[str, ...] = ()
    escalates: bool = False
    cost_units: float = 1.0
    latency_ms: int = 10
    refund: bool = False
    notification: Mapping[str, Any] | None = None
    escalation_target: str | None = None


def _merge(target: dict[str, Any], patch: Mapping[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def _patches(state: Mapping[str, Any]):
    """Split nested writes into individually observable commit steps."""
    for key, value in state.items():
        if isinstance(value, Mapping) and value:
            for child in _patches(value):
                yield {key: child}
        else:
            yield {key: deepcopy(value)}


@dataclass
class PendingWrite:
    operations: list[tuple[str, Any]]
    completed: int = 0


class StatefulEnvironment:
    FAILURE_PROFILES = ("none", "pre_call", "partial_write", "response_lost", "unavailable")

    def __init__(self, task: PublicTask, seed: int, effects: Mapping[str, ToolEffect]):
        self.task = task
        self.state = deepcopy(dict(task.initial_state))
        self.effects = effects
        self.failure_profile = self.FAILURE_PROFILES[seed % len(self.FAILURE_PROFILES)]
        self.fault_target = str(task.observable.get("fault_target", ""))
        self._fault_consumed = False
        self._applied_keys: set[str] = set()
        self._key_actions: dict[str, str] = {}
        self._pending: dict[str, PendingWrite] = {}
        self._unconfirmed: set[str] = set()
        self.actions: list[str] = []
        self.evidence: set[str] = set()
        self.trace: list[dict[str, Any]] = []
        self.tool_errors: list[str] = []
        self.escalated = False
        self.cost_units = 0.0
        self.latency_ms = 0
        self.environment_error = False

    @property
    def uncertain_write(self) -> bool:
        return bool(self._pending or self._unconfirmed)

    def _operations(self, action: str) -> list[tuple[str, Any]]:
        effect = self.effects[action]
        operations: list[tuple[str, Any]] = []
        if effect.refund:
            operations.append(("refund", None))
        operations.extend(("state", patch) for patch in _patches(effect.state))
        if effect.notification is not None:
            operations.append(("notification", dict(effect.notification)))
        operations.extend(("evidence", item) for item in effect.evidence)
        if effect.escalates:
            operations.append(("escalation", effect.escalation_target))
        return operations

    def _apply_one(self, operation: tuple[str, Any], key: str) -> None:
        kind, value = operation
        if kind == "state":
            _merge(self.state, value)
        elif kind == "refund":
            ledger = self.state.setdefault("refund_ledger", [])
            ledger.append({"request_key": key, "order_id": self.task.observable.get("order_id", self.task.task_id),
                           "amount": self.task.observable["amount"]})
            self.state["refund_count"] = len(ledger)
        elif kind == "notification":
            actual = self.state.get("refund_status")
            claimed = value.get("refund_status", "current")
            claimed = actual if claimed == "current" else claimed
            self.state.setdefault("notifications", []).append({
                "request_key": key,
                "claimed_refund_status": claimed,
                "actual_refund_status": actual,
                "recipient_match": value.get("recipient_match", True),
            })
            self.state["notified_refund_status"] = claimed
            self.evidence.add("customer_notice")
        elif kind == "evidence":
            self.evidence.add(value)
        elif kind == "escalation":
            self.escalated = True
            self.state["escalation_target"] = value

    def _apply(self, action: str, key: str) -> None:
        pending = self._pending.setdefault(key, PendingWrite(self._operations(action)))
        while pending.completed < len(pending.operations):
            self._apply_one(pending.operations[pending.completed], key)
            pending.completed += 1
        self.actions.append(action)
        self._applied_keys.add(key)
        del self._pending[key]

    def _reject(self, action: str, key: str, reason: str) -> bool:
        self.tool_errors.append(f"{reason}:{action}")
        self.trace.append({"action": action, "status": reason, "idempotency_key": key})
        return False

    def perform(self, action: str, key: str) -> bool:
        # Teaching units: every attempt pays the declared call cost and time.
        effect = self.effects.get(action)
        self.cost_units += effect.cost_units if effect else 0.2
        self.latency_ms += effect.latency_ms if effect else 3
        if action not in self.effects:
            return self._reject(action, key, "unknown_action")
        if key in self._key_actions and self._key_actions[key] != action:
            return self._reject(action, key, "key_conflict")
        self._key_actions[key] = action
        if key in self._applied_keys:
            self.evidence.add("idempotency_state")
            self.trace.append({"action": action, "status": "deduplicated", "idempotency_key": key})
            self._unconfirmed.discard(key)
            return True
        if effect.refund:
            amount, limit = self.task.observable.get("amount"), self.task.observable.get("direct_limit")
            if (any(type(value) not in (int, float) or not isfinite(value) for value in (amount, limit))
                    or amount <= 0 or limit < 0):
                return self._reject(action, key, "missing_refund_context")
            if amount > limit:
                return self._reject(action, key, "refund_authorization_denied")
            ledger = self.state.get("refund_ledger", [])
            if self.task.observable.get("existing_refund") or any(row["request_key"] != key for row in ledger):
                return self._reject(action, key, "duplicate_refund_blocked")

        if key in self._pending:
            self._apply(action, key)
            self.trace.append({"action": action, "status": "resumed", "idempotency_key": key})
            return True

        profile = self.failure_profile if action == self.fault_target and not self._fault_consumed else "none"
        if profile == "unavailable":
            self.environment_error = True
            self.tool_errors.append(f"unavailable:{action}")
            self.trace.append({"action": action, "status": "unavailable", "idempotency_key": key})
            return False
        if profile == "pre_call":
            self._fault_consumed = True
            self.tool_errors.append(f"pre_call:{action}")
            self.trace.append({"action": action, "status": "pre_call_failure", "idempotency_key": key})
            return False
        if profile == "partial_write":
            self._fault_consumed = True
            pending = PendingWrite(self._operations(action))
            self._pending[key] = pending
            # Never mark this request complete or emit its completion action.
            stop = max(0, min(len(pending.operations) - 1, len(pending.operations) // 2))
            while pending.completed < stop:
                self._apply_one(pending.operations[pending.completed], key)
                pending.completed += 1
            self.tool_errors.append(f"partial_write:{action}")
            self.trace.append({"action": action, "status": "partial_write", "idempotency_key": key,
                               "completed_steps": pending.completed, "total_steps": len(pending.operations)})
            return False
        if profile == "response_lost":
            self._fault_consumed = True
            self._apply(action, key)
            self._unconfirmed.add(key)
            self.tool_errors.append(f"{profile}:{action}")
            self.trace.append({"action": action, "status": profile, "idempotency_key": key})
            return False

        self._apply(action, key)
        self.trace.append({"action": action, "status": "ok", "idempotency_key": key})
        return True

    def recover(self, action: str, key: str) -> bool:
        self.cost_units += 0.2
        self.latency_ms += 3
        if key in self._key_actions and self._key_actions[key] != action:
            return self._reject(action, key, "key_conflict")
        applied = key in self._applied_keys
        self.evidence.add("idempotency_state")
        status = "applied" if applied else "partial" if key in self._pending else "not_applied"
        self.trace.append({"action": "query_idempotency", "status": status, "idempotency_key": key})
        if applied:
            self._unconfirmed.discard(key)
            return True
        if self.environment_error:
            return False
        return self.perform(action, key)

    def finish(self, note: str) -> AgentOutput:
        return AgentOutput(
            actions=tuple(self.actions),
            evidence=tuple(sorted(self.evidence)),
            escalated=self.escalated,
            note=note,
            final_state=deepcopy(self.state),
            trace=tuple(deepcopy(self.trace)),
            tool_errors=tuple(self.tool_errors),
            cost_units=self.cost_units,
            latency_ms=self.latency_ms,
            environment_error=self.environment_error,
            insufficient_evidence=self.uncertain_write,
        )


def execute_layered_plan(
    model: str,
    harness: str,
    skill: str,
    task: PublicTask,
    seed: int,
    effects: Mapping[str, ToolEffect],
    plans: Mapping[str, tuple[tuple[str, str], ...]],
    note: str,
) -> AgentOutput:
    """Run code-authored behavior plans without consulting private task targets."""

    scenario = str(task.observable["scenario"])
    env = StatefulEnvironment(task, seed, effects)
    enabled = {"base"}
    if model == "capable":
        enabled.add("capable")
    if harness == "workflow":
        enabled.add("workflow")
    if skill == "domain":
        enabled.add("domain")
    if model == "basic" and harness == "direct" and skill == "none":
        enabled.add("unsafe_basic")

    for index, (action, layer) in enumerate(plans[scenario]):
        if layer not in enabled:
            continue
        key = f"{task.task_id}:{action}:{index}"
        ok = env.perform(action, key)
        if not ok and harness == "workflow":
            ok = env.recover(action, key)
        if not ok and env.environment_error:
            break
    return env.finish(note)
