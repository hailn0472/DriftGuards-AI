"""AWS SDK client wrappers."""

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AWSClientFactory:
    """Factory for creating AWS service clients."""

    def __init__(self) -> None:
        """Initialize AWS client factory."""
        self.session = self._create_session()
        self.config = self._create_config()

    def _create_session(self) -> boto3.Session:
        """Create boto3 session."""
        session_kwargs: dict[str, Any] = {"region_name": settings.aws_region}

        # Add credentials if provided (otherwise use IAM role)
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        if settings.aws_session_token:
            session_kwargs["aws_session_token"] = settings.aws_session_token

        return boto3.Session(**session_kwargs)

    def _create_config(self) -> Config:
        """Create boto3 client configuration."""
        return Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=60,
        )

    def get_client(self, service_name: str, region: str | None = None) -> Any:
        """
        Get AWS service client.

        Args:
            service_name: AWS service name (e.g., 'ec2', 's3')
            region: Optional region override

        Returns:
            boto3 client
        """
        client_region = region or settings.aws_region

        try:
            client = self.session.client(
                service_name, region_name=client_region, config=self.config
            )
            logger.debug(
                "Created AWS client",
                service=service_name,
                region=client_region,
            )
            return client
        except Exception as e:
            logger.error(
                "Failed to create AWS client",
                service=service_name,
                region=client_region,
                error=str(e),
            )
            raise

    def get_resource(self, service_name: str, region: str | None = None) -> Any:
        """
        Get AWS service resource.

        Args:
            service_name: AWS service name (e.g., 's3', 'dynamodb')
            region: Optional region override

        Returns:
            boto3 resource
        """
        resource_region = region or settings.aws_region

        try:
            resource = self.session.resource(
                service_name, region_name=resource_region, config=self.config
            )
            logger.debug(
                "Created AWS resource",
                service=service_name,
                region=resource_region,
            )
            return resource
        except Exception as e:
            logger.error(
                "Failed to create AWS resource",
                service=service_name,
                region=resource_region,
                error=str(e),
            )
            raise


@lru_cache()
def get_aws_client_factory() -> AWSClientFactory:
    """Get cached AWS client factory instance."""
    return AWSClientFactory()


class EC2Client:
    """Wrapper for EC2 operations."""

    def __init__(self, factory: AWSClientFactory | None = None) -> None:
        """Initialize EC2 client."""
        self.factory = factory or get_aws_client_factory()

    async def describe_instances(
        self, region: str, instance_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Describe EC2 instances.

        Args:
            region: AWS region
            instance_ids: Optional list of instance IDs

        Returns:
            List of instance descriptions
        """
        client = self.factory.get_client("ec2", region=region)

        try:
            kwargs: dict[str, Any] = {}
            if instance_ids:
                kwargs["InstanceIds"] = instance_ids

            response = await asyncio.to_thread(client.describe_instances, **kwargs)

            instances = []
            for reservation in response.get("Reservations", []):
                instances.extend(reservation.get("Instances", []))

            logger.info(
                "Described EC2 instances",
                region=region,
                count=len(instances),
            )
            return instances

        except ClientError as e:
            logger.error(
                "Failed to describe EC2 instances",
                region=region,
                error=str(e),
            )
            raise


class S3Client:
    """Wrapper for S3 operations."""

    def __init__(self, factory: AWSClientFactory | None = None) -> None:
        """Initialize S3 client."""
        self.factory = factory or get_aws_client_factory()

    async def list_buckets(self) -> list[dict[str, Any]]:
        """List all S3 buckets."""
        client = self.factory.get_client("s3")

        try:
            response = await asyncio.to_thread(client.list_buckets)
            buckets = response.get("Buckets", [])

            logger.info("Listed S3 buckets", count=len(buckets))
            return buckets

        except ClientError as e:
            logger.error("Failed to list S3 buckets", error=str(e))
            raise

    async def get_bucket_location(self, bucket_name: str) -> str:
        """Get bucket location."""
        client = self.factory.get_client("s3")

        try:
            response = await asyncio.to_thread(client.get_bucket_location, Bucket=bucket_name)
            location = response.get("LocationConstraint") or "us-east-1"

            logger.debug("Got bucket location", bucket=bucket_name, location=location)
            return location

        except ClientError as e:
            logger.error(
                "Failed to get bucket location",
                bucket=bucket_name,
                error=str(e),
            )
            raise


class CloudWatchClient:
    """Wrapper for CloudWatch operations."""

    def __init__(self, factory: AWSClientFactory | None = None) -> None:
        """Initialize CloudWatch client."""
        self.factory = factory or get_aws_client_factory()

    async def get_metric_statistics(
        self,
        region: str,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        start_time: Any,
        end_time: Any,
        period: int = 300,
        statistics: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get metric statistics.

        Args:
            region: AWS region
            namespace: CloudWatch namespace
            metric_name: Metric name
            dimensions: Metric dimensions
            start_time: Start time
            end_time: End time
            period: Period in seconds
            statistics: List of statistics to retrieve

        Returns:
            Metric statistics
        """
        client = self.factory.get_client("cloudwatch", region=region)

        if statistics is None:
            statistics = ["Average", "Maximum", "Minimum"]

        try:
            response = await asyncio.to_thread(
                client.get_metric_statistics,
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=statistics,
            )

            logger.debug(
                "Got metric statistics",
                namespace=namespace,
                metric=metric_name,
                datapoints=len(response.get("Datapoints", [])),
            )
            return response

        except ClientError as e:
            logger.error(
                "Failed to get metric statistics",
                namespace=namespace,
                metric=metric_name,
                error=str(e),
            )
            raise


class ConfigClient:
    """Wrapper for AWS Config operations."""

    def __init__(self, factory: AWSClientFactory | None = None) -> None:
        """Initialize Config client."""
        self.factory = factory or get_aws_client_factory()

    async def get_resource_config_history(
        self,
        region: str,
        resource_type: str,
        resource_id: str,
        later_time: Any | None = None,
        earlier_time: Any | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get resource configuration history.

        Args:
            region: AWS region
            resource_type: AWS resource type
            resource_id: Resource ID
            later_time: Optional later time filter
            earlier_time: Optional earlier time filter

        Returns:
            Configuration history items
        """
        client = self.factory.get_client("config", region=region)

        try:
            kwargs: dict[str, Any] = {
                "resourceType": resource_type,
                "resourceId": resource_id,
            }

            if later_time:
                kwargs["laterTime"] = later_time
            if earlier_time:
                kwargs["earlierTime"] = earlier_time

            response = await asyncio.to_thread(client.get_resource_config_history, **kwargs)

            config_items = response.get("configurationItems", [])

            logger.debug(
                "Got resource config history",
                resource_type=resource_type,
                resource_id=resource_id,
                items=len(config_items),
            )
            return config_items

        except ClientError as e:
            logger.error(
                "Failed to get resource config history",
                resource_type=resource_type,
                resource_id=resource_id,
                error=str(e),
            )
            raise


class CostExplorerClient:
    """Wrapper for Cost Explorer operations."""

    def __init__(self, factory: AWSClientFactory | None = None) -> None:
        """Initialize Cost Explorer client."""
        self.factory = factory or get_aws_client_factory()

    async def get_cost_and_usage(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "DAILY",
        metrics: list[str] | None = None,
        filter_dict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get cost and usage data.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            granularity: Granularity (DAILY, MONTHLY)
            metrics: List of metrics
            filter_dict: Optional filter

        Returns:
            Cost and usage data
        """
        client = self.factory.get_client("ce")

        if metrics is None:
            metrics = ["UnblendedCost", "UsageQuantity"]

        try:
            kwargs: dict[str, Any] = {
                "TimePeriod": {"Start": start_date, "End": end_date},
                "Granularity": granularity,
                "Metrics": metrics,
            }

            if filter_dict:
                kwargs["Filter"] = filter_dict

            response = await asyncio.to_thread(client.get_cost_and_usage, **kwargs)

            logger.debug(
                "Got cost and usage data",
                start=start_date,
                end=end_date,
                results=len(response.get("ResultsByTime", [])),
            )
            return response

        except ClientError as e:
            logger.error(
                "Failed to get cost and usage data",
                start=start_date,
                end=end_date,
                error=str(e),
            )
            raise
