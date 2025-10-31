"""
Simple script to test the DriftGuards application.
Run this after setting up your environment.
"""

import asyncio

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_configuration() -> None:
    """Test configuration loading."""
    logger.info("Testing configuration...")

    logger.info(
        "Configuration loaded successfully",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        aws_region=settings.aws_region,
        bedrock_model=settings.bedrock_model_id,
    )


async def test_aws_clients() -> None:
    """Test AWS client initialization."""
    logger.info("Testing AWS clients...")

    try:
        from app.services.aws_client import get_aws_client_factory

        factory = get_aws_client_factory()

        # Test EC2 client
        ec2 = factory.get_client("ec2")
        logger.info("EC2 client initialized successfully")

        # Test S3 client
        s3 = factory.get_client("s3")
        logger.info("S3 client initialized successfully")

        # Test CloudWatch client
        cloudwatch = factory.get_client("cloudwatch")
        logger.info("CloudWatch client initialized successfully")

        logger.info("All AWS clients initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize AWS clients", error=str(e), exc_info=e)
        raise


async def test_models() -> None:
    """Test data models."""
    logger.info("Testing data models...")

    from datetime import datetime

    from app.models import DriftRecord, DriftType, Severity

    # Create a test drift record
    drift = DriftRecord(
        drift_id="test-drift-001",
        resource_id="i-test123",
        resource_type="aws_instance",
        drift_type=DriftType.MODIFIED,
        terraform_value={"instance_type": "t2.micro"},
        actual_value={"instance_type": "t3.medium"},
        diff={"instance_type": {"before": "t2.micro", "after": "t3.medium"}},
        severity=Severity.HIGH,
        account_id="123456789012",
        region="us-east-1",
        detected_at=datetime.utcnow(),
    )

    logger.info(
        "Drift record created successfully",
        drift_id=drift.drift_id,
        resource_id=drift.resource_id,
        severity=drift.severity,
    )


async def main() -> None:
    """Main test function."""
    logger.info("=" * 60)
    logger.info("DriftGuards - Application Test")
    logger.info("=" * 60)

    try:
        # Test configuration
        await test_configuration()
        logger.info("✅ Configuration test passed")

        # Test data models
        await test_models()
        logger.info("✅ Data models test passed")

        # Test AWS clients (only if credentials are configured)
        if settings.aws_access_key_id or settings.is_production:
            await test_aws_clients()
            logger.info("✅ AWS clients test passed")
        else:
            logger.warning("⚠️  AWS credentials not configured, skipping AWS clients test")

        logger.info("=" * 60)
        logger.info("✅ All tests passed successfully!")
        logger.info("=" * 60)
        logger.info("Next steps:")
        logger.info("1. Configure your .env file with AWS credentials")
        logger.info("2. Run: python -m uvicorn app.main:app --reload")
        logger.info("3. Visit: http://localhost:8000/docs")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("Test failed", error=str(e), exc_info=e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
