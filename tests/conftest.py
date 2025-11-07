"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env for tests
load_dotenv()


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials for tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def sample_drift_data():
    """Provide sample drift data for testing."""
    from datetime import datetime
    from app.models.drift import DriftRecord, DriftType, Severity, DriftStatus
    
    return DriftRecord(
        drift_id="test-drift-1",
        resource_type="ec2_instances",
        resource_id="i-12345",
        drift_type=DriftType.CONFIGURATION_CHANGE,
        severity=Severity.HIGH,
        description="Instance type changed from t2.micro to t2.small",
        detected_at=datetime.now(),
        status=DriftStatus.OPEN,
        current_config={"type": "t2.small", "state": "running"},
        baseline_config={"type": "t2.micro", "state": "running"},
    )


@pytest.fixture
def sample_baseline_config():
    """Provide sample baseline configuration."""
    return {
        "account_id": "123456789012",
        "region": "us-east-1",
        "resources": {
            "ec2_instances": [
                {
                    "id": "i-12345",
                    "type": "t2.micro",
                    "state": "running",
                    "tags": [{"Key": "Name", "Value": "test-instance"}],
                }
            ],
            "vpcs": [
                {
                    "id": "vpc-12345",
                    "cidr": "10.0.0.0/16",
                    "state": "available",
                }
            ],
        },
    }
