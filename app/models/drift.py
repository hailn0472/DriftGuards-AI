"""Data models for drift detection."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DriftType(str, Enum):
    """Types of drift."""

    MODIFIED = "modified"
    DELETED = "deleted"
    UNMANAGED = "unmanaged"
    CREATED = "created"


class Severity(str, Enum):
    """Severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DriftStatus(str, Enum):
    """Drift record status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


class DriftRecord(BaseModel):
    """Drift detection record."""

    drift_id: str = Field(..., description="Unique drift identifier")
    resource_id: str = Field(..., description="AWS resource ID")
    resource_type: str = Field(..., description="Resource type (e.g., aws_instance)")
    drift_type: DriftType = Field(..., description="Type of drift detected")
    terraform_value: Dict[str, Any] = Field(
        default_factory=dict, description="Expected Terraform state"
    )
    actual_value: Dict[str, Any] = Field(default_factory=dict, description="Actual AWS state")
    diff: Dict[str, Any] = Field(default_factory=dict, description="Differences between states")
    detected_at: datetime = Field(
        default_factory=datetime.utcnow, description="Detection timestamp"
    )
    severity: Severity = Field(default=Severity.MEDIUM, description="Drift severity")
    account_id: str = Field(..., description="AWS account ID")
    region: str = Field(..., description="AWS region")
    status: DriftStatus = Field(default=DriftStatus.OPEN, description="Current status")
    environment: Optional[str] = Field(default=None, description="Environment tag")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    has_downstream_dependencies: bool = Field(default=False, description="Has dependent resources")

    # Computed fields
    diff_hash: Optional[str] = Field(default=None, description="Hash of diff for deduplication")
    remediation_id: Optional[str] = Field(default=None, description="Associated remediation ID")
    assigned_to: Optional[str] = Field(default=None, description="User assigned to handle drift")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution timestamp")
    
    # Approval tracking
    approved: bool = Field(default=False, description="Whether drift is approved")
    approved_by: Optional[str] = Field(default=None, description="User who approved")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    approval_reason: Optional[str] = Field(default=None, description="Approval reason")

    class Config:
        json_schema_extra = {
            "example": {
                "drift_id": "drift-2025-10-31-001",
                "resource_id": "i-0abc123456def",
                "resource_type": "aws_instance",
                "drift_type": "modified",
                "terraform_value": {"instance_type": "t2.micro"},
                "actual_value": {"instance_type": "t3.medium"},
                "diff": {"instance_type": {"before": "t2.micro", "after": "t3.medium"}},
                "severity": "high",
                "account_id": "123456789012",
                "region": "us-east-1",
                "status": "open",
            }
        }


class DriftSuppression(BaseModel):
    """Drift suppression record."""

    suppression_id: str = Field(..., description="Unique suppression identifier")
    drift_id: str = Field(..., description="Associated drift ID")
    reason: str = Field(..., description="Reason for suppression")
    suppressed_by: str = Field(..., description="User who suppressed")
    suppressed_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Suppression expiration")
    active: bool = Field(default=True, description="Whether suppression is active")


class ScanRequest(BaseModel):
    """Drift scan request."""

    accounts: List[str] = Field(..., description="AWS account IDs to scan")
    regions: List[str] = Field(..., description="AWS regions to scan")
    resource_types: Optional[List[str]] = Field(default=None, description="Resource types to scan")
    tags_filter: Optional[Dict[str, str]] = Field(default=None, description="Filter by tags")
    force_refresh: bool = Field(default=False, description="Force Terraform state refresh")

    class Config:
        json_schema_extra = {
            "example": {
                "accounts": ["123456789012"],
                "regions": ["us-east-1", "us-west-2"],
                "resource_types": ["aws_instance", "aws_s3_bucket"],
                "force_refresh": False,
            }
        }


class DriftListResponse(BaseModel):
    """Response for drift list endpoint."""

    drifts: List[DriftRecord] = Field(..., description="List of drift records")
    total: int = Field(..., description="Total number of drifts")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=50, description="Items per page")
    has_more: bool = Field(default=False, description="More pages available")


class DriftStatistics(BaseModel):
    """Drift statistics."""

    total_drifts: int = Field(..., description="Total drift count")
    by_severity: Dict[str, int] = Field(default_factory=dict, description="Count by severity")
    by_resource_type: Dict[str, int] = Field(
        default_factory=dict, description="Count by resource type"
    )
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")
    by_region: Dict[str, int] = Field(default_factory=dict, description="Count by region")
    trend: List[Dict[str, Any]] = Field(default_factory=list, description="Time series trend")

    class Config:
        json_schema_extra = {
            "example": {
                "total_drifts": 42,
                "by_severity": {"critical": 3, "high": 8, "medium": 20, "low": 11},
                "by_resource_type": {
                    "aws_instance": 15,
                    "aws_s3_bucket": 12,
                    "aws_rds_instance": 10,
                },
                "by_status": {"open": 30, "in_progress": 8, "resolved": 4},
            }
        }
