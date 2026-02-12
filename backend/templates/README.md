# `backend/templates/` — Gateway workspace templates

This directory contains **Jinja2 templates** that Mission Control renders and syncs into each OpenClaw gateway agent’s on-disk workspace (the `workspace-*` folder).

These files are the agent’s “operating manual” (instructions, heartbeat rules, tools, identity, etc.).

## Where templates are rendered / synced

**Rendering engine**
- Renderer: Jinja2 `Environment(FileSystemLoader(templates_root))`.
- Config (important for safe changes):
  - `undefined=StrictUndefined` → **missing variables crash render** (good: prevents silent partial templates).
  - `autoescape=False` → markdown is rendered “verbatim” (no HTML escaping).
  - `keep_trailing_newline=True`.

Evidence:
- `backend/app/services/openclaw/provisioning.py::_template_env()`

**Sync workflows**
- API: `POST /api/v1/gateways/{gateway_id}/templates/sync`
  - Router: `backend/app/api/gateways.py` (`sync_gateway_templates`).
  - DB-backed service: `backend/app/services/openclaw/provisioning_db.py::OpenClawProvisioningService.sync_gateway_templates()`.
- CLI: `backend/scripts/sync_gateway_templates.py --gateway-id <uuid> [--board-id <uuid>] [--reset-sessions] [--rotate-tokens] [--force-bootstrap]`

## Which files are provisioned

Default set (rendered for each agent workspace):
- `AGENTS.md`, `SOUL.md`, `TASK_SOUL.md`, `SELF.md`, `AUTONOMY.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, `BOOT.md`, `BOOTSTRAP.md`, `MEMORY.md`

Evidence:
- `backend/app/services/openclaw/constants.py::DEFAULT_GATEWAY_FILES`

### “Main agent” template mapping

The gateway *main* agent uses a few different templates (prefixed `MAIN_...`) for some files:

| Workspace file | Main-agent template |
|---|---|
| `AGENTS.md` | `MAIN_AGENTS.md` |
| `HEARTBEAT.md` | `MAIN_HEARTBEAT.md` |
| `USER.md` | `MAIN_USER.md` |
| `BOOT.md` | `MAIN_BOOT.md` |
| `TOOLS.md` | `MAIN_TOOLS.md` |

Evidence:
- `backend/app/services/openclaw/constants.py::MAIN_TEMPLATE_MAP`

## Template variables (context)

Templates are rendered with a context built from:
- Agent + board + gateway fields
- Mission Control backend settings (`base_url`)
- Optional user profile fields
- Agent identity profile fields

Evidence:
- `backend/app/services/openclaw/provisioning.py::_build_context()` (board-scoped agents)
- `backend/app/services/openclaw/provisioning.py::_build_main_context()` (main agent)
- Identity/user mapping: `backend/app/services/openclaw/provisioning.py::_identity_context()`, `_user_context()`

### Common context keys

These keys are available to *all* templates (agent + main):

- `agent_name`
- `agent_id`
- `session_key`
- `base_url`
- `auth_token`
- `main_session_key`
- `workspace_root`

User fields (may be empty strings):
- `user_name`, `user_preferred_name`, `user_pronouns`, `user_timezone`
- `user_notes`, `user_context`

Identity fields (defaults apply if missing):
- `identity_role`
- `identity_communication_style`
- `identity_emoji`

Extra identity fields (optional; may be empty strings):
- `identity_autonomy_level`, `identity_verbosity`, `identity_output_format`, `identity_update_cadence`
- `identity_purpose`, `identity_personality`, `identity_custom_instructions`

Evidence:
- Defaults + mapping: `backend/app/services/openclaw/constants.py::{DEFAULT_IDENTITY_PROFILE, IDENTITY_PROFILE_FIELDS, EXTRA_IDENTITY_PROFILE_FIELDS}`

### Board-scoped-only keys

Only board-scoped agents receive:
- `board_id`, `board_name`, `board_type`
- `board_objective`, `board_success_metrics`, `board_target_date`
- `board_goal_confirmed`
- `is_board_lead`
- `workspace_path`
- `board_*` fields above

Evidence:
- `backend/app/services/openclaw/provisioning.py::_build_context()`

## HEARTBEAT template selection

`HEARTBEAT.md` is special: it renders one of two templates depending on whether the agent is a board lead:
- lead: `HEARTBEAT_LEAD.md`
- agent: `HEARTBEAT_AGENT.md`

Evidence:
- Template names: `backend/app/services/openclaw/constants.py::{HEARTBEAT_LEAD_TEMPLATE, HEARTBEAT_AGENT_TEMPLATE}`
- Selection logic: `backend/app/services/openclaw/provisioning.py::_heartbeat_template_name()`

## Safe change guidelines

1) **Assume templates are user-facing instructions**
   - Keep edits backwards compatible when possible.
   - Prefer additive changes (new sections) over rewriting major flows.

2) **Do not break rendering**
   - Because `StrictUndefined` is enabled, adding `{{ new_var }}` requires also adding that key to the context builder(s).

3) **Preserved (agent-editable) files**
   Some files are intentionally not overwritten on template sync if they already exist in the agent workspace (the agent/human may edit them):
   - `SELF.md`, `USER.md`, `MEMORY.md`, `TASK_SOUL.md`

   Evidence:
   - `backend/app/services/openclaw/constants.py::PRESERVE_AGENT_EDITABLE_FILES`

4) **Main-agent vs board-agent differences**
   - If changing `TOOLS.md`, `HEARTBEAT.md`, etc., check whether the change should also apply to the main-agent templates (`MAIN_*`).

5) **Prefer small PRs + keep template scope task-scoped**

## Previewing / testing template changes locally

### Option A (recommended): run template sync against a dev gateway
Use either:
- API: `POST /api/v1/gateways/{gateway_id}/templates/sync`
- CLI: `backend/scripts/sync_gateway_templates.py --gateway-id <uuid> ...`

Then inspect the provisioned files in the gateway’s workspace directory (the exact path is computed in `backend/app/services/openclaw/provisioning.py::_workspace_path()`).

### Option B: quick offline render (Jinja2 only)
This is useful for confirming Markdown formatting and variable names.

```bash
python3 - <<'PY'
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

root = Path('backend/templates')
env = Environment(
    loader=FileSystemLoader(root),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)

# Minimal dummy context (must include any variables referenced by the template).
ctx = {
    'agent_name': 'ExampleAgent',
    'agent_id': '00000000-0000-0000-0000-000000000000',
    'board_id': '00000000-0000-0000-0000-000000000000',
    'board_name': 'Example Board',
    'board_type': 'general',
    'board_objective': '',
    'board_success_metrics': '{}',
    'board_target_date': '',
    'board_goal_confirmed': 'false',
    'is_board_lead': 'false',
    'session_key': 'agent:example',
    'workspace_path': '/tmp/workspace-example',
    'base_url': 'http://localhost:8000',
    'auth_token': 'REDACTED',
    'main_session_key': 'agent:gateway-main',
    'workspace_root': '/tmp',
    'user_name': '',
    'user_preferred_name': '',
    'user_pronouns': '',
    'user_timezone': '',
    'user_notes': '',
    'user_context': '',
    'identity_role': 'Generalist',
    'identity_communication_style': 'direct',
    'identity_emoji': ':gear:',
    'identity_autonomy_level': '',
    'identity_verbosity': '',
    'identity_output_format': '',
    'identity_update_cadence': '',
    'identity_purpose': '',
    'identity_personality': '',
    'identity_custom_instructions': '',
}

print(env.get_template('AGENTS.md').render(**ctx))
PY
```

If the template references a variable not present in `ctx`, Jinja2 will raise immediately (by design).
