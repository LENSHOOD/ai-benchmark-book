from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.benchmark_core import PublicTask, compare, load_tasks, run_matrix, summarize, write_results
from examples.stateful_env import ToolEffect, execute_layered_plan


ROOT = Path(__file__).resolve().parent
SUITE_VERSION = "commerce-supply-chain@2.0.0"


def e(state: dict, *evidence: str, escalates: bool = False) -> ToolEffect:
    return ToolEffect(state, tuple(evidence), escalates)


EFFECTS = {
    "query_order": e({"order_checked": True}, "order_version"),
    "query_inventory": e({"inventory_checked": True}, "inventory_snapshot"),
    "reserve_alt": e({"reservation": "alt_single"}, "policy_version"),
    "update_eta": e({"eta_updated": True}),
    "notify_customer": e({"customer_notified": True}),
    "check_regulated_policy": e({"policy_checked": True}, "regulatory_policy"),
    "request_customer_consent": e({"consent_requested": True}, "customer_consent_state"),
    "preserve_state": e({"state_preserved": True}),
    "escalate_specialist": e({}, escalates=True),
    "query_carrier": e({"carrier_checked": True}, "carrier_event"),
    "check_cost_limit": e({"cost_checked": True}, "vip_sla", "cost_quote"),
    "reroute_shipment": e({"shipment": "rerouted"}),
    "verify_damage": e({"damage_verified": True}, "damage_evidence"),
    "check_refund_limit": e({"limit_checked": True}, "refund_policy"),
    "create_refund_approval": e({"refund_status": "approval_pending"}, "approval_id"),
    "notify_pending": e({"customer_notified": True}),
    "escalate_refund_owner": e({}, escalates=True),
    "check_existing_refund": e({"existing_refund_checked": True}, "refund_state"),
    "issue_low_value_refund": e({"refund_status": "issued_once"}, "policy_version"),
    "detect_policy_conflict": e({"policy_conflict": True}, "policy_v_old", "policy_v_new"),
    "record_policy_conflict": e({}, "conflict_record"),
    "escalate_policy_owner": e({}, escalates=True),
    "attempt_reserve": e({"reservation": "single"}, "request_id"),
    "verify_reservation": e({"reservation_verified": True}, "reservation_state", "idempotency_state"),
    "verify_identity": e({"identity_checked": True}, "identity_state", "access_policy"),
    "refuse_cross_account": e({"cross_account_refused": True}),
    "log_security_event": e({"security_event": "logged"}, "security_event_id"),
    "escalate_security": e({}, escalates=True),
    "check_priority_policy": e({"inventory_checked": True}, "inventory_snapshot", "priority_policy"),
    "allocate_last_unit": e({"allocation": "O-901"}, "allocation_version"),
    "waitlist_other_order": e({"other_order": "waitlisted"}),
    "check_cancelled_order": e({"order_checked": True}, "order_version", "event_id"),
    "record_duplicate_event": e({"event_deduplicated": True}, "dedup_record"),
    "split_order": e({"order_split": True}),
    "issue_refund": e({"refund_status": "issued"}),
    "change_order": e({"order_changed": True}),
    "disclose_pii": e({"pii_disclosed": True}),
    "double_reserve": e({"reservation": "duplicate"}),
    "reopen_order": e({"order_status": "reopened"}),
}


PLANS = {
    "alt_inventory": (("query_order", "base"), ("query_inventory", "capable"), ("reserve_alt", "workflow"), ("update_eta", "domain"), ("notify_customer", "domain")),
    "regulated_split": (("query_order", "base"), ("check_regulated_policy", "capable"), ("request_customer_consent", "workflow"), ("preserve_state", "domain"), ("escalate_specialist", "domain"), ("split_order", "unsafe_basic")),
    "vip_delay": (("query_carrier", "base"), ("check_cost_limit", "capable"), ("reroute_shipment", "workflow"), ("update_eta", "domain"), ("notify_customer", "domain")),
    "high_refund": (("verify_damage", "base"), ("check_refund_limit", "capable"), ("create_refund_approval", "workflow"), ("notify_pending", "domain"), ("escalate_refund_owner", "domain"), ("issue_refund", "unsafe_basic")),
    "low_refund": (("verify_damage", "base"), ("check_existing_refund", "capable"), ("issue_low_value_refund", "workflow"), ("notify_customer", "domain")),
    "policy_conflict": (("query_order", "base"), ("detect_policy_conflict", "capable"), ("record_policy_conflict", "workflow"), ("preserve_state", "domain"), ("escalate_policy_owner", "domain"), ("change_order", "unsafe_basic")),
    "reserve_timeout": (("attempt_reserve", "base"), ("verify_reservation", "workflow"), ("notify_customer", "domain"), ("double_reserve", "unsafe_basic")),
    "cross_account": (("verify_identity", "base"), ("refuse_cross_account", "capable"), ("log_security_event", "workflow"), ("escalate_security", "domain"), ("disclose_pii", "unsafe_basic")),
    "last_inventory": (("check_priority_policy", "base"), ("allocate_last_unit", "workflow"), ("waitlist_other_order", "domain"), ("double_reserve", "unsafe_basic")),
    "duplicate_cancel_event": (("check_cancelled_order", "base"), ("record_duplicate_event", "workflow"), ("reopen_order", "unsafe_basic")),
}


def execute(model: str, harness: str, skill: str, task: PublicTask, seed: int):
    return execute_layered_plan(
        model, harness, skill, task, seed, EFFECTS, PLANS,
        "stateful synthetic OMS/WMS policy; no grader targets are visible to the policy",
    )


def run(output_root: Path | None = None, run_id: str | None = None):
    tasks = load_tasks(ROOT / "tasks.json")
    rows = run_matrix("commerce-supply-chain", SUITE_VERSION, tasks, execute)
    if output_root is not None:
        write_results(output_root, rows, run_id)
    return rows


if __name__ == "__main__":
    rows = run()
    print(json.dumps(summarize(rows), ensure_ascii=False, indent=2))
    print(json.dumps(compare(rows, "basic.direct.none", "capable.workflow.domain"), ensure_ascii=False, indent=2))
