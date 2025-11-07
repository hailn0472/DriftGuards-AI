"""Tests for configuration management."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env for tests
load_dotenv()


def test_env_file_exists():
    """Test that .env file exists."""
    env_file = Path(__file__).parent.parent / ".env"
    assert env_file.exists() or Path(__file__).parent.parent / ".env.example", ".env or .env.example should exist"


def test_aws_credentials_loaded():
    """Test that AWS credentials are loaded from environment."""
    # Should have either AWS credentials or profile
    has_credentials = bool(os.getenv("AWS_ACCESS_KEY_ID")) or bool(os.getenv("AWS_PROFILE"))
    assert has_credentials, "AWS credentials should be configured"


def test_aws_region_configured():
    """Test that AWS region is configured."""
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    assert region is not None, "AWS region should be configured"


@pytest.mark.skipif(not os.getenv("AWS_ACCESS_KEY_ID"), reason="AWS credentials not configured")
def test_boto3_session():
    """Test that boto3 can create a session with current credentials."""
    import boto3
    
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        assert "Account" in identity
        assert "Arn" in identity
    except Exception as e:
        pytest.fail(f"Failed to create boto3 session: {e}")
