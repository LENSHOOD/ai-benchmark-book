"""Dependency-free stateful benchmark runner shared by both teaching projects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import platform
import random
from statistics import mean
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class PublicTask:
    """The only task view available to the system under test.

    Target states, forbidden states and required evidence intentionally do not
    exist on this type. This makes answer-key leakage a type-level error.
    """

    task_id: str
    title: str
    tags: tuple[str, ...]
    prompt: str
    observable: Mapping[str, Any]
    initial_state: Mapping[str, Any]


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    tags: tuple[str, ...]
    prompt: str
    observable: Mapping[str, Any]
    initial_state: Mapping[str, Any]
    target_state: Mapping[str, Any]
    forbidden_final_states: tuple[Mapping[str, Any], ...]
    forbidden_actions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    requires_escalation: bool
    critical: bool

    def public_view(self) -> PublicTask:
        return PublicTask(
            task_id=self.task_id,
            title=self.title,
            tags=self.tags,
            prompt=self.prompt,
            observable=self.observable,
            initial_state=self.initial_state,
        )


@dataclass(frozen=True)
class AgentOutput:
    actions: tuple[str, ...]
    evidence: tuple[str, ...]
    escalated: bool
    note: str
    final_state: Mapping[str, Any]
    trace: tuple[Mapping[str, Any], ...]
    tool_errors: tuple[str, ...] = ()
    cost_units: float = 0.0
    latency_ms: int = 0
    environment_error: bool = False
    insufficient_evidence: bool = False


@dataclass(frozen=True)
class TrialResult:
    suite: str
    suite_version: str
    grader_version: str
    candidate: str
    task_id: str
    trial: int
    seed: int
    environment_hash: str
    score: float
    passed: bool
    veto: bool
    target_coverage: float
    evidence_coverage: float
    escalation_correct: bool
    failure_class: str
    environment_error: bool
    insufficient_evidence: bool
    cost_units: float
    latency_ms: int
    output: AgentOutput


@dataclass(frozen=True)
class GraderConfig:
    version: str
    target_weight: float
    evidence_weight: float
    escalation_weight: float


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_tasks(path: Path) -> list[Task]:
    payload = json.loads(path.read_text())
    _require(isinstance(payload, dict) and isinstance(payload.get("tasks"), list), "tasks.json must contain a tasks list")
    _require(bool(payload["tasks"]), "suite must contain at least one task")
    tasks: list[Task] = []
    seen: set[str] = set()
    for index, row in enumerate(payload["tasks"]):
        prefix = f"task[{index}]"
        _require(isinstance(row, dict), f"{prefix} must be an object")
        task_id = row.get("task_id")
        _require(isinstance(task_id, str) and bool(task_id.strip()), f"{prefix}.task_id is required")
        _require(task_id not in seen, f"duplicate task id: {task_id}")
        seen.add(task_id)
        for key in ("title", "prompt"):
            _require(isinstance(row.get(key), str) and bool(row[key].strip()), f"{task_id}.{key} is required")
        for key in ("observable", "initial_state", "target_state"):
            _require(isinstance(row.get(key), dict), f"{task_id}.{key} must be an object")
        _require(bool(row["target_state"]), f"{task_id}.target_state must not be empty")
        required_evidence = row.get("required_evidence")
        _require(isinstance(required_evidence, list) and bool(required_evidence), f"{task_id}.required_evidence must not be empty")
        forbidden_states = row.get("forbidden_final_states", [])
        _require(isinstance(forbidden_states, list) and all(isinstance(x, dict) and x for x in forbidden_states), f"{task_id}.forbidden_final_states must contain non-empty objects")
        tasks.append(
            Task(
                task_id=task_id,
                title=row["title"],
                tags=tuple(row.get("tags", [])),
                prompt=row["prompt"],
                observable=row["observable"],
                initial_state=row["initial_state"],
                target_state=row["target_state"],
                forbidden_final_states=tuple(forbidden_states),
                forbidden_actions=tuple(row.get("forbidden_actions", [])),
                required_evidence=tuple(required_evidence),
                requires_escalation=bool(row.get("requires_escalation", False)),
                critical=bool(row.get("critical", False)),
            )
        )
    return tasks


def load_grader_config(path: Path | None = None) -> GraderConfig:
    path = path or Path(__file__).with_name("grader_config.json")
    row = json.loads(path.read_text())
    weights = row["diagnostic_weights"]
    values = [float(weights[name]) for name in ("target_state", "evidence", "escalation")]
    _require(all(value >= 0 for value in values), "grader weights must be non-negative")
    _require(abs(sum(values) - 1.0) < 1e-9, "grader weights must sum to 1")
    return GraderConfig(str(row["version"]), *values)


def _leaf_items(value: Mapping[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    leaves: list[tuple[tuple[str, ...], Any]] = []
    for key, item in value.items():
        path = prefix + (key,)
        if isinstance(item, dict):
            leaves.extend(_leaf_items(item, path))
        else:
            leaves.append((path, item))
    return leaves


_MISSING = object()


def _lookup(state: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = state
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _state_matches(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    return all(_lookup(observed, path) == value for path, value in _leaf_items(expected))


def _state_coverage(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> float:
    leaves = _leaf_items(expected)
    if not leaves:
        raise ValueError("target state must not be empty")
    return sum(_lookup(observed, path) == value for path, value in leaves) / len(leaves)


def _coverage(required: Iterable[str], observed: Iterable[str]) -> float:
    required_set = set(required)
    if not required_set:
        raise ValueError("required evidence must not be empty")
    return len(required_set & set(observed)) / len(required_set)


def _environment_hash(task: Task) -> str:
    payload = json.dumps(task.initial_state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()[:16]


def grade(
    suite: str,
    suite_version: str,
    candidate: str,
    task: Task,
    trial: int,
    seed: int,
    output: AgentOutput,
    config: GraderConfig | None = None,
) -> TrialResult:
    config = config or load_grader_config()
    target_coverage = _state_coverage(task.target_state, output.final_state)
    evidence_coverage = _coverage(task.required_evidence, output.evidence)
    forbidden_action_hit = bool(set(task.forbidden_actions) & set(output.actions))
    forbidden_state_hit = any(_state_matches(state, output.final_state) for state in task.forbidden_final_states)
    escalation_correct = output.escalated == task.requires_escalation
    target_satisfied = _state_matches(task.target_state, output.final_state)
    insufficient = output.insufficient_evidence or output.environment_error
    veto = forbidden_action_hit or forbidden_state_hit
    passed = target_satisfied and set(task.required_evidence).issubset(output.evidence) and escalation_correct and not veto and not insufficient
    score = (
        config.target_weight * target_coverage
        + config.evidence_weight * evidence_coverage
        + config.escalation_weight * float(escalation_correct)
    )
    if veto:
        score = 0.0

    if output.environment_error:
        failure_class = "environment_error"
    elif veto:
        failure_class = "veto"
    elif insufficient:
        failure_class = "insufficient_evidence"
    elif not target_satisfied:
        failure_class = "target_state"
    elif not set(task.required_evidence).issubset(output.evidence):
        failure_class = "missing_evidence"
    elif not escalation_correct:
        failure_class = "escalation"
    else:
        failure_class = "none"

    return TrialResult(
        suite=suite,
        suite_version=suite_version,
        grader_version=config.version,
        candidate=candidate,
        task_id=task.task_id,
        trial=trial,
        seed=seed,
        environment_hash=_environment_hash(task),
        score=round(score, 4),
        passed=passed,
        veto=veto,
        target_coverage=round(target_coverage, 4),
        evidence_coverage=round(evidence_coverage, 4),
        escalation_correct=escalation_correct,
        failure_class=failure_class,
        environment_error=output.environment_error,
        insufficient_evidence=insufficient,
        cost_units=round(output.cost_units, 4),
        latency_ms=output.latency_ms,
        output=output,
    )


Executor = Callable[[str, str, str, PublicTask, int], AgentOutput]


def stable_seed(base_seed: int, *parts: str | int) -> int:
    payload = "|".join(map(str, (base_seed, *parts)))
    return int.from_bytes(sha256(payload.encode()).digest()[:8], "big")


def run_matrix(
    suite: str,
    suite_version: str,
    tasks: list[Task],
    executor: Executor,
    models: tuple[str, ...] = ("basic", "capable"),
    harnesses: tuple[str, ...] = ("direct", "workflow"),
    skills: tuple[str, ...] = ("none", "domain"),
    trials: int = 4,
    base_seed: int = 20260827,
) -> list[TrialResult]:
    _require(trials > 0, "trials must be positive")
    config = load_grader_config()
    rows: list[TrialResult] = []
    for model, harness, skill, task, trial in product(models, harnesses, skills, tasks, range(trials)):
        candidate = f"{model}.{harness}.{skill}"
        seed = stable_seed(base_seed, suite_version, candidate, task.task_id, trial)
        output = executor(model, harness, skill, task.public_view(), seed)
        rows.append(grade(suite, suite_version, candidate, task, trial, seed, output, config))
    return rows


def summarize(rows: list[TrialResult]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[TrialResult]] = {}
    for row in rows:
        grouped.setdefault(row.candidate, []).append(row)
    return {
        candidate: {
            "trials": len(items),
            "tasks": len({x.task_id for x in items}),
            "mean_score": round(mean(x.score for x in items), 4),
            "pass_rate": round(mean(x.passed for x in items), 4),
            "veto_rate": round(mean(x.veto for x in items), 4),
            "insufficient_evidence_rate": round(mean(x.insufficient_evidence for x in items), 4),
            "mean_cost_units": round(mean(x.cost_units for x in items), 4),
            "mean_latency_ms": round(mean(x.latency_ms for x in items), 1),
        }
        for candidate, items in sorted(grouped.items())
    }


def compare(
    rows: list[TrialResult],
    baseline: str,
    candidate: str,
    bootstrap_samples: int = 2000,
    bootstrap_seed: int = 20260827,
) -> dict[str, float | int | str | list[float]]:
    def task_means(name: str) -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for row in rows:
            if row.candidate == name:
                grouped.setdefault(row.task_id, []).append(row.score)
        return {task_id: mean(values) for task_id, values in grouped.items()}

    left = task_means(baseline)
    right = task_means(candidate)
    keys = sorted(left.keys() & right.keys())
    if not keys:
        raise ValueError("comparison has no paired tasks")
    deltas = [right[key] - left[key] for key in keys]
    rng = random.Random(bootstrap_seed)
    boot = [mean(rng.choice(deltas) for _ in deltas) for _ in range(bootstrap_samples)]
    boot.sort()
    low = boot[int(0.025 * (bootstrap_samples - 1))]
    high = boot[int(0.975 * (bootstrap_samples - 1))]
    return {
        "baseline": baseline,
        "candidate": candidate,
        "paired_tasks": len(keys),
        "total_trials": sum(row.candidate in {baseline, candidate} for row in rows),
        "mean_score_delta": round(mean(deltas), 4),
        "ci95": [round(low, 4), round(high, 4)],
        "candidate_wins": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
        "candidate_losses": sum(delta < 0 for delta in deltas),
    }


def trial_variation(rows: list[TrialResult]) -> int:
    grouped: dict[tuple[str, str], set[float]] = {}
    for row in rows:
        grouped.setdefault((row.candidate, row.task_id), set()).add(row.score)
    return sum(len(values) > 1 for values in grouped.values())


def write_results(output_root: Path, rows: list[TrialResult], run_id: str | None = None) -> Path:
    run_id = run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    output_dir = output_root / run_id
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite result directory: {output_dir}")
    output_dir.mkdir(parents=True)
    with (output_dir / "trials.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "suite": rows[0].suite if rows else None,
        "suite_version": rows[0].suite_version if rows else None,
        "grader_version": rows[0].grader_version if rows else None,
        "row_count": len(rows),
        "task_count": len({row.task_id for row in rows}),
        "candidate_count": len({row.candidate for row in rows}),
        "seed_count": len({row.seed for row in rows}),
        "trial_variation_cells": trial_variation(rows),
    }
    (output_dir / "summary.json").write_text(json.dumps(summarize(rows), ensure_ascii=False, indent=2) + "\n")
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return output_dir
