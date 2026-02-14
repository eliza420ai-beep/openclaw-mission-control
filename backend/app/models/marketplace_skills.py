"""Organization-scoped skill catalog entries for the skills marketplace."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.tenancy import TenantScoped

RUNTIME_ANNOTATION_TYPES = (datetime,)


class MarketplaceSkill(TenantScoped, table=True):
    """A marketplace skill entry that can be installed onto one or more gateways."""

    __tablename__ = "marketplace_skills"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_url",
            name="uq_marketplace_skills_org_source_url",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    name: str
    description: str | None = Field(default=None)
    category: str | None = Field(default=None)
    risk: str | None = Field(default=None)
    source: str | None = Field(default=None)
    source_url: str
    metadata_: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
