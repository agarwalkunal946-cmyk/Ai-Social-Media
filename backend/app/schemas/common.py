from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    message: str
    data: Any | None = None


class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    role: str = "user"
    mode: str = "creator"
    avatar_url: str | None = None
    provider: str | None = None
    created_at: datetime | None = None


class ProviderConnection(BaseModel):
    platform: str
    status: str
    access_mode: str
    connected: bool = False
    handle: str | None = None
    account_name: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class AlertItem(BaseModel):
    id: str
    source_type: str
    platform: str
    title: str
    severity: str
    timestamp: datetime
    explanation: str
    recommended_action: str
    status: str
    affected_content: str | None = None


class ReportSummary(BaseModel):
    id: str
    title: str
    period: str
    created_at: datetime
    public_token: str
    insights: list[str] = Field(default_factory=list)

