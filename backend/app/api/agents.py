from __future__ import annotations

import re
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.auth import get_auth_context
from app.db.session import get_session
from app.integrations.openclaw_gateway import OpenClawGatewayError, openclaw_call
from app.models.activity_events import ActivityEvent
from app.models.agents import Agent
from app.schemas.agents import (
    AgentCreate,
    AgentHeartbeat,
    AgentHeartbeatCreate,
    AgentRead,
    AgentUpdate,
)
from app.services.admin_access import require_admin
from app.services.agent_provisioning import send_provisioning_message

router = APIRouter(prefix="/agents", tags=["agents"])

OFFLINE_AFTER = timedelta(minutes=10)
AGENT_SESSION_PREFIX = "agent"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid4().hex


def _build_session_key(agent_name: str) -> str:
    return f"{AGENT_SESSION_PREFIX}:{_slugify(agent_name)}:main"


async def _ensure_gateway_session(agent_name: str) -> tuple[str, str | None]:
    session_key = _build_session_key(agent_name)
    try:
        await openclaw_call("sessions.patch", {"key": session_key, "label": agent_name})
        return session_key, None
    except OpenClawGatewayError as exc:
        return session_key, str(exc)


def _with_computed_status(agent: Agent) -> Agent:
    now = datetime.utcnow()
    if agent.last_seen_at and now - agent.last_seen_at > OFFLINE_AFTER:
        agent.status = "offline"
    return agent


def _record_heartbeat(session: Session, agent: Agent) -> None:
    event = ActivityEvent(
        event_type="agent.heartbeat",
        message=f"Heartbeat received from {agent.name}.",
        agent_id=agent.id,
    )
    session.add(event)


@router.get("", response_model=list[AgentRead])
def list_agents(
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> list[Agent]:
    require_admin(auth)
    agents = list(session.exec(select(Agent)))
    return [_with_computed_status(agent) for agent in agents]


@router.post("", response_model=AgentRead)
async def create_agent(
    payload: AgentCreate,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> Agent:
    require_admin(auth)
    agent = Agent.model_validate(payload)
    session_key, session_error = await _ensure_gateway_session(agent.name)
    agent.openclaw_session_id = session_key
    session.add(agent)
    session.commit()
    session.refresh(agent)
    if session_error:
        session.add(
            ActivityEvent(
                event_type="agent.session.failed",
                message=f"Session sync failed for {agent.name}: {session_error}",
                agent_id=agent.id,
            )
        )
    else:
        session.add(
            ActivityEvent(
                event_type="agent.session.created",
                message=f"Session created for {agent.name}.",
                agent_id=agent.id,
            )
        )
    session.commit()
    try:
        await send_provisioning_message(agent)
    except OpenClawGatewayError as exc:
        session.add(
            ActivityEvent(
                event_type="agent.provision.failed",
                message=f"Provisioning message failed: {exc}",
                agent_id=agent.id,
            )
        )
        session.commit()
    except Exception as exc:  # pragma: no cover - unexpected provisioning errors
        session.add(
            ActivityEvent(
                event_type="agent.provision.failed",
                message=f"Provisioning message failed: {exc}",
                agent_id=agent.id,
            )
        )
        session.commit()
    return agent


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(
    agent_id: str,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> Agent:
    require_admin(auth)
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _with_computed_status(agent)


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> Agent:
    require_admin(auth)
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(agent, key, value)
    agent.updated_at = datetime.utcnow()
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return _with_computed_status(agent)


@router.post("/{agent_id}/heartbeat", response_model=AgentRead)
def heartbeat_agent(
    agent_id: str,
    payload: AgentHeartbeat,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> Agent:
    require_admin(auth)
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.status:
        agent.status = payload.status
    agent.last_seen_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    _record_heartbeat(session, agent)
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return _with_computed_status(agent)


@router.post("/heartbeat", response_model=AgentRead)
async def heartbeat_or_create_agent(
    payload: AgentHeartbeatCreate,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> Agent:
    require_admin(auth)
    agent = session.exec(select(Agent).where(Agent.name == payload.name)).first()
    if agent is None:
        agent = Agent(name=payload.name, status=payload.status or "online")
        session_key, session_error = await _ensure_gateway_session(agent.name)
        agent.openclaw_session_id = session_key
        session.add(agent)
        session.commit()
        session.refresh(agent)
        if session_error:
            session.add(
                ActivityEvent(
                    event_type="agent.session.failed",
                    message=f"Session sync failed for {agent.name}: {session_error}",
                    agent_id=agent.id,
                )
            )
        else:
            session.add(
                ActivityEvent(
                    event_type="agent.session.created",
                    message=f"Session created for {agent.name}.",
                    agent_id=agent.id,
                )
            )
        session.commit()
        try:
            await send_provisioning_message(agent)
        except OpenClawGatewayError as exc:
            session.add(
                ActivityEvent(
                    event_type="agent.provision.failed",
                    message=f"Provisioning message failed: {exc}",
                    agent_id=agent.id,
                )
            )
            session.commit()
        except Exception as exc:  # pragma: no cover - unexpected provisioning errors
            session.add(
                ActivityEvent(
                    event_type="agent.provision.failed",
                    message=f"Provisioning message failed: {exc}",
                    agent_id=agent.id,
                )
            )
            session.commit()
    elif not agent.openclaw_session_id:
        session_key, session_error = await _ensure_gateway_session(agent.name)
        agent.openclaw_session_id = session_key
        if session_error:
            session.add(
                ActivityEvent(
                    event_type="agent.session.failed",
                    message=f"Session sync failed for {agent.name}: {session_error}",
                    agent_id=agent.id,
                )
            )
        else:
            session.add(
                ActivityEvent(
                    event_type="agent.session.created",
                    message=f"Session created for {agent.name}.",
                    agent_id=agent.id,
                )
            )
        session.commit()
        try:
            await send_provisioning_message(agent)
        except OpenClawGatewayError as exc:
            session.add(
                ActivityEvent(
                    event_type="agent.provision.failed",
                    message=f"Provisioning message failed: {exc}",
                    agent_id=agent.id,
                )
            )
            session.commit()
        except Exception as exc:  # pragma: no cover - unexpected provisioning errors
            session.add(
                ActivityEvent(
                    event_type="agent.provision.failed",
                    message=f"Provisioning message failed: {exc}",
                    agent_id=agent.id,
                )
            )
            session.commit()
    if payload.status:
        agent.status = payload.status
    agent.last_seen_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    _record_heartbeat(session, agent)
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return _with_computed_status(agent)


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: str,
    session: Session = Depends(get_session),
    auth=Depends(get_auth_context),
) -> dict[str, bool]:
    require_admin(auth)
    agent = session.get(Agent, agent_id)
    if agent:
        session.delete(agent)
        session.commit()
    return {"ok": True}
