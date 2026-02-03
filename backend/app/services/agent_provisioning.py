from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.integrations.openclaw_gateway import send_message
from app.models.agents import Agent

TEMPLATE_FILES = [
    "AGENTS.md",
    "BOOT.md",
    "BOOTSTRAP.md",
    "HEARTBEAT.md",
    "IDENTITY.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _templates_root() -> Path:
    return _repo_root() / "templates"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid4().hex


def _read_templates() -> dict[str, str]:
    root = _templates_root()
    templates: dict[str, str] = {}
    for name in TEMPLATE_FILES:
        path = root / name
        if path.exists():
            templates[name] = path.read_text(encoding="utf-8").strip()
        else:
            templates[name] = ""
    return templates


def _render_file_block(name: str, content: str) -> str:
    body = content if content else f"# {name}\n\nTODO: add content\n"
    return f"\n{name}\n```md\n{body}\n```\n"


def _workspace_path(agent_name: str) -> str:
    root = settings.openclaw_workspace_root or "~/.openclaw/workspaces"
    root = root.rstrip("/")
    return f"{root}/{_slugify(agent_name)}"


def build_provisioning_message(agent: Agent) -> str:
    templates = _read_templates()
    agent_id = _slugify(agent.name)
    workspace_path = _workspace_path(agent.name)
    session_key = agent.openclaw_session_id or ""
    base_url = settings.base_url or ""

    file_blocks = "".join(
        _render_file_block(name, templates.get(name, "")) for name in TEMPLATE_FILES
    )

    return (
        "Provision a new OpenClaw agent workspace.\n\n"
        f"Agent name: {agent.name}\n"
        f"Agent id: {agent_id}\n"
        f"Session key: {session_key}\n"
        f"Workspace path: {workspace_path}\n\n"
        f"Base URL: {base_url or 'UNSET'}\n\n"
        "Steps:\n"
        "1) Create the workspace directory.\n"
        "2) Write the files below with the exact contents.\n"
        f"3) Set BASE_URL to {base_url or '{{BASE_URL}}'} for the agent runtime.\n"
        "4) Replace placeholders like {{AGENT_NAME}}, {{AGENT_ID}}, {{BASE_URL}}, {{AUTH_TOKEN}}.\n"
        "5) Leave BOOTSTRAP.md in place; the agent should run it on first start and delete it.\n"
        "6) Register agent id in OpenClaw so it uses this workspace path.\n\n"
        "Files:" + file_blocks
    )


async def send_provisioning_message(agent: Agent) -> None:
    main_session = settings.openclaw_main_session_key
    if not main_session:
        return
    message = build_provisioning_message(agent)
    await send_message(message, session_key=main_session, deliver=False)
