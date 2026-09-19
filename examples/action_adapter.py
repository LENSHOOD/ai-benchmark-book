"""Provider-neutral teaching boundary: policies propose actions, the host records effects.

This is an in-process interface example, not an adversarial code sandbox.
An actual provider wrapper belongs in choose(); it must not see private Task data.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import json
from typing import Any, Callable, Mapping

from examples.benchmark_core import AgentOutput, PublicTask, grade, load_tasks
from examples.stateful_env import StatefulEnvironment, ToolEffect


def run_actions(
    task: PublicTask,
    choose: Callable[[dict[str, Any]], Mapping[str, Any] | None],
    effects: Mapping[str, ToolEffect],
    seed: int = 0,
    max_steps: int = 20,
) -> AgentOutput:
    if type(max_steps) is not int or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    env = StatefulEnvironment(task, seed, effects)
    for _ in range(max_steps):
        context = {"task": asdict(task), "allowed_actions": sorted(effects),
                   "state": env.state, "trace": env.trace}
        try:
            request = choose(deepcopy(context))
        except Exception as exc:
            env.tool_errors.append(f"provider_error:{type(exc).__name__}")
            return replace(env.finish("provider_error"), insufficient_evidence=True)
        if request is None:
            return env.finish("policy_stopped")
        if (not isinstance(request, Mapping) or set(request) - {"action", "key", "recover"}
                or not isinstance(request.get("action"), str) or request["action"] not in effects
                or not isinstance(request.get("key"), str) or not request["key"].strip()
                or type(request.get("recover", False)) is not bool):
            env.tool_errors.append("invalid_action_request")
            return replace(env.finish("invalid_action_request"), insufficient_evidence=True)
        try:
            if request.get("recover", False):
                env.recover(request["action"], request["key"])
            else:
                env.perform(request["action"], request["key"])
        except Exception as exc:
            env.tool_errors.append(f"tool_exception:{type(exc).__name__}")
            return replace(env.finish("tool_exception"), insufficient_evidence=True)
        if env.environment_error:
            return env.finish("environment_error")
    return replace(env.finish("step_budget_exhausted"), insufficient_evidence=True)


def demo() -> dict:
    from examples.commerce_supply_chain.run import EFFECTS, ROOT, SUITE_VERSION

    task = next(task for task in load_tasks(ROOT / "tasks.json") if task.task_id == "cs-004")
    actions = ("verify_damage", "check_refund_limit", "create_refund_approval", "notify_pending", "escalate_refund_owner")
    requests = iter({"action": action, "key": action, "recover": recover}
                    for action in actions for recover in (False, True))
    output = run_actions(task.public_view(), lambda _: next(requests, None), EFFECTS, seed=2)
    result = grade("commerce-supply-chain", SUITE_VERSION, "adapter.demo", task, 0, 2, output)
    return asdict(result)


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
