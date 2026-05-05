from typing import Any

from pydantic import BaseModel, Field


class OverviewMetric(BaseModel):
    label: str
    value: str
    delta: str
    tone: str = "neutral"


class DashboardPayload(BaseModel):
    overview: list[OverviewMetric]
    sentiment_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    emotion_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    platform_comparison: list[dict[str, Any]] = Field(default_factory=list)
    engagement_trend: list[dict[str, Any]] = Field(default_factory=list)
    top_content: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    alerts_preview: list[dict[str, Any]] = Field(default_factory=list)
    report_preview: list[dict[str, Any]] = Field(default_factory=list)
    platform_rollups: list[dict[str, Any]] = Field(default_factory=list)
    toxicity_summary: dict[str, Any] = Field(default_factory=dict)
    audience_insights: dict[str, Any] = Field(default_factory=dict)
    predictive_analysis: dict[str, Any] = Field(default_factory=dict)
    explainable_ai: dict[str, Any] = Field(default_factory=dict)
    trending_hashtags: list[dict[str, Any]] = Field(default_factory=list)
    chatbot: dict[str, Any] = Field(default_factory=dict)
    moderation_queue: list[dict[str, Any]] = Field(default_factory=list)
    crisis_alerts: list[dict[str, Any]] = Field(default_factory=list)
    connected_accounts: list[dict[str, Any]] = Field(default_factory=list)
    model_stack: dict[str, Any] = Field(default_factory=dict)
