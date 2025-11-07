"""Data models for drift approval."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApprovalRecord(BaseModel):
    """Record of drift approval."""
    
    approval_id: str = Field(..., description="Unique approval identifier")
    drift_id: str = Field(..., description="Associated drift ID")
    resource_id: str = Field(..., description="Resource ID")
    resource_type: str = Field(..., description="Resource type")
    
    # Approval metadata
    approved_by: str = Field(..., description="User who approved")
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    approval_reason: Optional[str] = Field(None, description="Reason for approval")
    
    # State snapshots
    previous_baseline: dict = Field(default_factory=dict, description="Previous baseline state")
    new_baseline: dict = Field(default_factory=dict, description="New approved state")
    
    # Tracking
    environment: Optional[str] = Field(None, description="Environment")
    tags: dict[str, str] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "approval_id": "approval-abc123",
                "drift_id": "drift-2025-11-07-001",
                "resource_id": "i-0abc123456def",
                "resource_type": "aws_instance",
                "approved_by": "admin@example.com",
                "approved_at": "2025-11-07T13:00:00Z",
                "approval_reason": "Manual scaling due to increased load",
                "environment": "production",
            }
        }


class ApprovalRequest(BaseModel):
    """Request to approve a drift."""
    
    drift_id: str = Field(..., description="Drift ID to approve")
    approved_by: str = Field(..., description="User approving the drift")
    reason: Optional[str] = Field(None, description="Reason for approval")
    update_baseline: bool = Field(
        default=True, 
        description="Update baseline state with new configuration"
    )
    notify: bool = Field(
        default=True, 
        description="Send notifications about approval"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "drift_id": "drift-2025-11-07-001",
                "approved_by": "admin@example.com",
                "reason": "Approved capacity increase for peak traffic",
                "update_baseline": True,
                "notify": True,
            }
        }
