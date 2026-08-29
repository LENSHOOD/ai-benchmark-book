"""Small stateful sandbox with deterministic fault injection and idempotency."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from examples.benchmark_core import AgentOutput, PublicTask


@dataclass(frozen=True)
class ToolEffect:
    state: Mapping[str, Any]
    evidence: tuple[str, ...] = ()
    escalates: bool = False
    cost_units: float = 1.0
    latency_ms: int = 10


def _merge(target: dict[str, Any], patch: Mapping[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


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
        self.actions: list[str] = []
        self.evidence: set[str] = set()
        self.trace: list[dict[str, Any]] = []
        self.tool_errors: list[str] = []
        self.escalated = False
        self.cost_units = 0.0
        self.latency_ms = 0
        self.environment_error = False
        self.uncertain_write = False

    def _apply(self, action: str, key: str) -> None:
        effect = self.effects[action]
        _merge(self.state, effect.state)
        self.evidence.update(effect.evidence)
        self.escalated = self.escalated or effect.escalates
        self.cost_units += effect.cost_units
        self.latency_ms += effect.latency_ms
        self.actions.append(action)
        self._applied_keys.add(key)

    def perform(self, action: str, key: str) -> bool:
        if action not in self.effects:
            self.tool_errors.append(f"unknown_action:{action}")
            self.trace.append({"action": action, "status": "unknown_action", "idempotency_key": key})
            return False
        if key in self._applied_keys:
            self.evidence.add("idempotency_state")
            self.trace.append({"action": action, "status": "deduplicated", "idempotency_key": key})
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
        if profile in {"partial_write", "response_lost"}:
            self._fault_consumed = True
            self._apply(action, key)
            self.uncertain_write = True
            self.tool_errors.append(f"{profile}:{action}")
            self.trace.append({"action": action, "status": profile, "idempotency_key": key})
            return False

        self._apply(action, key)
        self.trace.append({"action": action, "status": "ok", "idempotency_key": key})
        return True

    def recover(self, action: str, key: str) -> bool:
        self.cost_units += 0.2
        self.latency_ms += 3
        applied = key in self._applied_keys
        self.evidence.add("idempotency_state")
        self.trace.append({"action": "query_idempotency", "status": "applied" if applied else "not_applied", "idempotency_key": key})
        if applied:
            self.uncertain_write = False
            return True
        if self.environment_error:
            return False
        ok = self.perform(action, key)
        if ok:
            self.uncertain_write = False
        return ok

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
