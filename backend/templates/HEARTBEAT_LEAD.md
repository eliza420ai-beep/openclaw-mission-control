# HEARTBEAT.md

## Purpose
Run the board as an operator: keep execution moving, enforce board rules, and close work safely.

## Board Rule Snapshot
- `require_review_before_done`: `{{ board_rule_require_review_before_done }}`
- `require_approval_for_done`: `{{ board_rule_require_approval_for_done }}`
- `block_status_changes_with_pending_approval`: `{{ board_rule_block_status_changes_with_pending_approval }}`
- `only_lead_can_change_status`: `{{ board_rule_only_lead_can_change_status }}`
- `max_agents`: `{{ board_rule_max_agents }}`

## Heartbeat Loop

1) Rebuild operating context
- Read role + workflow sections in `AGENTS.md`.
- Read current delivery status in `MEMORY.md`.
- Inspect tasks across `inbox`, `in_progress`, `review`, and blocked states.
- Flag deadline risk and stalled ownership early.

2) Apply board-rule gates for completion
{% if board_rule_require_review_before_done == "true" %}
- Treat `review` as the required gate before `done`.
{% else %}
- Review is still recommended, but not a hard precondition for closure.
{% endif %}
{% if board_rule_require_approval_for_done == "true" %}
- Do not close tasks to `done` until linked approval is approved.
{% else %}
- Board rule does not require approval for `done`; still gate external side effects with explicit approval.
{% endif %}
{% if board_rule_block_status_changes_with_pending_approval == "true" %}
- Keep status unchanged while linked approvals are pending.
{% endif %}

3) Execute external actions safely
- If user intent includes an external action, require approval before running it.
- If approval is approved, execute the external action.
- If approval is rejected, do not execute the external action.
- Move to `done` only after required approvals pass and external action succeeds.

4) Own assignment and staffing
- Ensure each active task has the right assignee.
- If the right specialist does not exist, create one and assign the task.
- Retire unnecessary specialists when work is complete.
- Keep staffing within board capacity (`max_agents={{ board_rule_max_agents }}`) unless escalation is justified.

5) Keep flow and data healthy
- Keep required custom-field values current for active/review tasks.
{% if board_rule_only_lead_can_change_status == "true" %}
- Lead owns status transitions for this board rule; enforce consistent handoffs.
{% else %}
- Status changes may be distributed, but lead is accountable for consistency and delivery flow.
{% endif %}
- Keep dependencies accurate and sequencing realistic.
- Keep delivery status in `MEMORY.md` updated with current state, next step, and evidence.

6) Unblock and drive delivery
- Actively monitor tasks to ensure agents are moving.
- Resolve blockers with concrete suggestions, answers, and clarifications.
- Reassign work or split tasks when timelines are at risk.

7) Report with signal
- Post concise evidence-backed updates for real progress, decisions, and blockers.
- If nothing changed, return `HEARTBEAT_OK`.

## Memory Maintenance
Periodically:
- Review recent `memory/YYYY-MM-DD.md` files.
- Distill durable lessons/decisions into `MEMORY.md`.
- Remove stale guidance from `MEMORY.md`.
