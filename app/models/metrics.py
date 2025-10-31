"""Data models for metrics collection."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CloudWatchMetric(BaseModel):
    """CloudWatch metric data."""

    metric_name: str = Field(..., description="Metric name")
    namespace: str = Field(..., description="CloudWatch namespace")
    statistics: Dict[str, float] = Field(default_factory=dict, description="Metric statistics")
    unit: str = Field(default="None", description="Metric unit")
    datapoints: List[Dict[str, Any]] = Field(default_factory=list, description="Metric datapoints")


class ConfigChange(BaseModel):
    """AWS Config configuration change."""

    change_id: str = Field(..., description="Change identifier")
    timestamp: datetime = Field(..., description="Change timestamp")
    user: Optional[str] = Field(default=None, description="User who made the change")
    action: str = Field(..., description="Action performed")
    changes: Dict[str, Any] = Field(default_factory=dict, description="Configuration changes")
    compliance_type: Optional[str] = Field(default=None, description="Compliance status")


class CostData(BaseModel):
    """Cost Explorer data."""

    daily_cost: float = Field(..., description="Current daily cost")
    monthly_projection: float = Field(..., description="Projected monthly cost")
    previous_month_cost: float = Field(default=0.0, description="Previous month cost")
    cost_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Cost trend data")
    increase_percent: Optional[float] = Field(default=None, description="Cost increase percentage")
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="Cost anomalies")


class CostAnalysis(BaseModel):
    """Detailed cost analysis."""

    current_cost: float = Field(..., description="Current cost")
    projected_cost: float = Field(..., description="Projected cost")
    cost_change: float = Field(..., description="Cost change amount")
    cost_change_percent: float = Field(..., description="Cost change percentage")
    budget_impact: Optional[str] = Field(default=None, description="Budget impact assessment")
    recommendations: List[str] = Field(
        default_factory=list, description="Cost optimization recommendations"
    )


class PerformanceBaseline(BaseModel):
    """Performance baseline metrics."""

    cpu_baseline: Optional[float] = Field(default=None, description="CPU utilization baseline")
    memory_baseline: Optional[float] = Field(
        default=None, description="Memory utilization baseline"
    )
    network_baseline: Optional[float] = Field(
        default=None, description="Network throughput baseline"
    )
    disk_baseline: Optional[float] = Field(default=None, description="Disk I/O baseline")
    established_at: Optional[datetime] = Field(
        default=None, description="When baseline was established"
    )


class ComplianceViolation(BaseModel):
    """Compliance violation record."""

    violation_id: str = Field(..., description="Violation identifier")
    rule_name: str = Field(..., description="Config rule name")
    compliance_type: str = Field(..., description="NON_COMPLIANT, COMPLIANT, etc.")
    severity: str = Field(..., description="Violation severity")
    message: str = Field(..., description="Violation message")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    annotation: Optional[str] = Field(default=None, description="Additional annotation")


class RelatedChange(BaseModel):
    """Related infrastructure change."""

    change_id: str = Field(..., description="Change identifier")
    resource_id: str = Field(..., description="Related resource ID")
    resource_type: str = Field(..., description="Related resource type")
    change_type: str = Field(..., description="Type of change")
    timestamp: datetime = Field(..., description="Change timestamp")
    correlation_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Correlation score")


class MetricsContext(BaseModel):
    """Complete metrics context for a resource."""

    resource_id: str = Field(..., description="AWS resource ID")
    resource_type: str = Field(..., description="Resource type")
    cloudwatch_metrics: Dict[str, CloudWatchMetric] = Field(
        default_factory=dict, description="CloudWatch metrics"
    )
    config_history: List[ConfigChange] = Field(default_factory=list, description="Config history")
    cost_data: Optional[CostAnalysis] = Field(default=None, description="Cost data")
    performance_baseline: Optional[PerformanceBaseline] = Field(
        default=None, description="Performance baseline"
    )
    compliance_violations: List[ComplianceViolation] = Field(
        default_factory=list, description="Compliance violations"
    )
    related_changes: List[RelatedChange] = Field(
        default_factory=list, description="Related infrastructure changes"
    )
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "resource_id": "i-0abc123456def",
                "resource_type": "aws_instance",
                "cloudwatch_metrics": {
                    "CPUUtilization": {
                        "metric_name": "CPUUtilization",
                        "namespace": "AWS/EC2",
                        "statistics": {"Average": 85.2, "Maximum": 98.5},
                    }
                },
                "config_history": [],
                "compliance_violations": [],
            }
        }
