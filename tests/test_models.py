"""Tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.drift import DriftRecord, DriftType, Severity, DriftStatus
from app.models.analysis import DriftAnalysis, ActionOption
from app.models.metrics import MetricsContext


class TestDriftRecord:
    """Tests for DriftRecord model."""
    
    def test_create_drift_record(self):
        """Test creating a drift record."""
        drift = DriftRecord(
            drift_id="test-drift-1",
            account_id="123456789012",
            region="us-east-1",
            resource_type="ec2_instances",
            resource_id="i-12345",
            drift_type=DriftType.MODIFIED,
            severity=Severity.HIGH,
            description="Instance type changed",
            detected_at=datetime.now(),
            status=DriftStatus.OPEN,
        )
        
        assert drift.drift_id == "test-drift-1"
        assert drift.resource_type == "ec2_instances"
        assert drift.severity == Severity.HIGH
        assert drift.status == DriftStatus.OPEN
    
    def test_drift_record_validation(self):
        """Test drift record validation - missing required field."""
        with pytest.raises(ValidationError):
            DriftRecord(
                drift_id="test-drift-1",
                # Missing account_id - should raise ValidationError
                region="us-east-1",
                resource_type="ec2_instances",
                resource_id="i-12345",
                drift_type=DriftType.MODIFIED,
                severity=Severity.HIGH,
            )


class TestDriftAnalysis:
    """Tests for DriftAnalysis model."""
    
    def test_create_drift_analysis(self):
        """Test creating a drift analysis."""
        analysis = DriftAnalysis(
            analysis_id="analysis-001",
            resource_id="i-12345",
            drift_id="test-drift-1",
            explanation="Configuration drift detected",
            root_cause="Manual change via AWS console",
            business_impact="Performance improved but costs increased",
            recommended_action="update_terraform",
            confidence_score=85,
            severity="medium",
            estimated_fix_time="5 minutes",
            rollback_complexity="simple",
            blast_radius="Single instance",
            model_id="claude-3-sonnet",
        )
        
        assert analysis.drift_id == "test-drift-1"
        assert analysis.severity == "medium"
        assert analysis.confidence_score == 85
        assert analysis.recommended_action == "update_terraform"


class TestMetricsContext:
    """Tests for MetricsContext model."""
    
    def test_create_metrics_context(self):
        """Test creating metrics context."""
        from app.models.metrics import CloudWatchMetric
        
        metrics = MetricsContext(
            resource_id="i-12345",
            resource_type="ec2_instances",
            cloudwatch_metrics={
                "CPUUtilization": CloudWatchMetric(
                    metric_name="CPUUtilization",
                    namespace="AWS/EC2",
                    statistics={"Average": 45.5},
                    unit="Percent",
                )
            },
        )
        
        assert metrics.resource_id == "i-12345"
        assert metrics.resource_type == "ec2_instances"
        assert "CPUUtilization" in metrics.cloudwatch_metrics
