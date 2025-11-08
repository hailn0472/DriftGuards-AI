"""Data models for AI analysis."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ActionOption(BaseModel):
    """Alternative action option."""

    action: str = Field(..., description="Action type")
    description: str = Field(..., description="Action description")
    risk: Literal["low", "medium", "high"] = Field(..., description="Risk level")
    reason: str = Field(..., description="Reason for risk level")
    estimated_duration: Optional[str] = Field(default=None, description="Estimated time")


class DriftAnalysis(BaseModel):
    """AI analysis of drift."""

    analysis_id: str = Field(..., description="Analysis identifier")
    resource_id: str = Field(..., description="AWS resource ID")
    drift_id: str = Field(..., description="Associated drift ID")

    # AI-generated insights
    explanation: str = Field(..., description="Human-readable explanation of drift")
    root_cause: str = Field(..., description="Root cause analysis")
    business_impact: str = Field(..., description="Business and operational impact")

    # Recommendations
    recommended_action: Literal["update_baseline", "revert_aws", "ignore", "manual_review"] = Field(
        ..., description="Recommended action"
    )
    alternative_actions: List[ActionOption] = Field(
        default_factory=list, description="Alternative actions"
    )

    # Scoring
    confidence_score: int = Field(..., ge=0, le=100, description="AI confidence score")
    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Severity assessment"
    )

    # Risk assessment
    estimated_fix_time: str = Field(..., description="Estimated fix time")
    rollback_complexity: Literal["simple", "moderate", "complex"] = Field(
        ..., description="Rollback complexity"
    )
    blast_radius: str = Field(..., description="Potential impact scope")

    # Remediation plan
    remediation_steps: List[str] = Field(default_factory=list, description="Step-by-step plan")
    prerequisites: List[str] = Field(
        default_factory=list, description="Prerequisites for remediation"
    )
    rollback_steps: List[str] = Field(default_factory=list, description="Rollback procedure")

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    model_id: str = Field(..., description="AI model used")
    model_version: Optional[str] = Field(default=None, description="Model version")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "analysis-001",
                "resource_id": "i-0abc123456def",
                "drift_id": "drift-2025-10-31-001",
                "explanation": "Instance type was manually upgraded from t2.micro to t3.medium",
                "root_cause": "High CPU utilization triggered manual intervention",
                "business_impact": "Performance improved but costs increased by 120%",
                "recommended_action": "update_terraform",
                "confidence_score": 92,
                "severity": "high",
                "estimated_fix_time": "5 minutes",
                "rollback_complexity": "simple",
                "blast_radius": "Single instance, no downstream dependencies",
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            }
        }


class AnalysisRequest(BaseModel):
    """Request for AI analysis."""

    drift_id: str = Field(..., description="Drift ID to analyze")
    include_metrics: bool = Field(default=True, description="Include metrics context")
    force_reanalysis: bool = Field(default=False, description="Force new analysis")


class AnalysisResponse(BaseModel):
    """Response from AI analysis."""

    analysis: DriftAnalysis = Field(..., description="Analysis result")
    cached: bool = Field(default=False, description="Whether result was cached")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
