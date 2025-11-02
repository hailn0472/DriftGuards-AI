"""Metrics Collector Agent for enriching drift data with AWS metrics."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.models.drift import DriftRecord
from app.models.metrics import (
    CloudWatchMetric,
    ComplianceViolation,
    ConfigChange,
    CostAnalysis,
    MetricsContext,
    PerformanceBaseline,
    RelatedChange,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MetricsCollectorAgent:
    """Agent responsible for collecting comprehensive AWS metrics for drift context."""

    def __init__(self):
        """Initialize metrics collector agent."""
        self.cloudwatch_client = None
        self.config_client = None
        self.ce_client = None  # Cost Explorer

    def _get_cloudwatch_client(self, region: str):
        """Get CloudWatch client for region."""
        if not self.cloudwatch_client:
            self.cloudwatch_client = boto3.client(
                "cloudwatch",
                region_name=region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.cloudwatch_client

    def _get_config_client(self, region: str):
        """Get AWS Config client for region."""
        if not self.config_client:
            self.config_client = boto3.client(
                "config",
                region_name=region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.config_client

    def _get_ce_client(self):
        """Get Cost Explorer client."""
        if not self.ce_client:
            # Cost Explorer is only available in us-east-1
            ce_region = "us-east-1"  # noqa: S105
            self.ce_client = boto3.client(
                "ce",
                region_name=ce_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.ce_client

    async def collect_metrics(self, drift_records: List[DriftRecord]) -> List[MetricsContext]:
        """
        Collect metrics for multiple drift records in parallel.

        Args:
            drift_records: List of drift records to enrich

        Returns:
            List of metrics contexts
        """
        logger.info(f"Collecting metrics for {len(drift_records)} drift records")

        try:
            # Collect metrics in parallel
            tasks = [
                self._collect_metrics_for_resource(drift) for drift in drift_records
            ]

            metrics_contexts = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_contexts = []
            for i, context in enumerate(metrics_contexts):
                if isinstance(context, Exception):
                    logger.error(
                        f"Failed to collect metrics for {drift_records[i].resource_id}: {context}"
                    )
                else:
                    valid_contexts.append(context)

            logger.info(f"Successfully collected metrics for {len(valid_contexts)} resources")
            return valid_contexts

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}", exc_info=True)
            raise

    async def _collect_metrics_for_resource(self, drift: DriftRecord) -> MetricsContext:
        """
        Collect comprehensive metrics for a single resource.

        Args:
            drift: Drift record

        Returns:
            Complete metrics context
        """
        logger.debug(f"Collecting metrics for resource {drift.resource_id}")

        try:
            # Run all metric collection tasks in parallel
            results = await asyncio.gather(
                self._collect_cloudwatch_metrics(drift),
                self._collect_config_history(drift),
                self._collect_cost_data(drift),
                asyncio.to_thread(self._establish_performance_baseline, drift),
                self._collect_compliance_violations(drift),
                asyncio.to_thread(self._find_related_changes, drift),
                return_exceptions=True,
            )

            # Unpack results
            cloudwatch_metrics = results[0] if not isinstance(results[0], Exception) else {}
            config_history = results[1] if not isinstance(results[1], Exception) else []
            cost_data = results[2] if not isinstance(results[2], Exception) else None
            performance_baseline = results[3] if not isinstance(results[3], Exception) else None
            compliance_violations = results[4] if not isinstance(results[4], Exception) else []
            related_changes = results[5] if not isinstance(results[5], Exception) else []

            return MetricsContext(
                resource_id=drift.resource_id,
                resource_type=drift.resource_type,
                cloudwatch_metrics=cloudwatch_metrics,
                config_history=config_history,
                cost_data=cost_data,
                performance_baseline=performance_baseline,
                compliance_violations=compliance_violations,
                related_changes=related_changes,
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error collecting metrics for {drift.resource_id}: {e}", exc_info=True)
            raise

    async def _collect_cloudwatch_metrics(
        self, drift: DriftRecord
    ) -> Dict[str, CloudWatchMetric]:
        """
        Collect CloudWatch metrics based on resource type.

        Args:
            drift: Drift record

        Returns:
            Dictionary of CloudWatch metrics
        """
        try:
            cloudwatch = self._get_cloudwatch_client(drift.region)

            # Determine which metrics to collect based on resource type
            metrics_config = self._get_metrics_config(drift.resource_type)

            if not metrics_config:
                logger.debug(f"No CloudWatch metrics configured for {drift.resource_type}")
                return {}

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=settings.cloudwatch_lookback_hours)

            collected_metrics = {}

            for metric_name in metrics_config["metrics"]:
                try:
                    response = await asyncio.to_thread(
                        cloudwatch.get_metric_statistics,
                        Namespace=metrics_config["namespace"],
                        MetricName=metric_name,
                        Dimensions=self._build_dimensions(drift),
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour
                        Statistics=["Average", "Maximum", "Minimum"],
                    )

                    datapoints = response.get("Datapoints", [])

                    if datapoints:
                        # Calculate statistics
                        stats = {
                            "Average": sum(dp.get("Average", 0) for dp in datapoints)
                            / len(datapoints),
                            "Maximum": max(dp.get("Maximum", 0) for dp in datapoints),
                            "Minimum": min(dp.get("Minimum", 0) for dp in datapoints),
                        }

                        collected_metrics[metric_name] = CloudWatchMetric(
                            metric_name=metric_name,
                            namespace=metrics_config["namespace"],
                            statistics=stats,
                            unit=response.get("Label", "None"),
                            datapoints=datapoints,
                        )

                except (BotoCoreError, ClientError) as e:
                    logger.warning(f"Failed to collect metric {metric_name}: {e}")
                    continue

            return collected_metrics

        except Exception as e:
            logger.error(f"CloudWatch metrics collection error: {e}", exc_info=True)
            return {}

    async def _collect_config_history(self, drift: DriftRecord) -> List[ConfigChange]:
        """
        Collect AWS Config history for resource.

        Args:
            drift: Drift record

        Returns:
            List of configuration changes
        """
        try:
            config = self._get_config_client(drift.region)

            # Map resource type to Config resource type
            config_resource_type = self._map_to_config_resource_type(drift.resource_type)

            if not config_resource_type:
                logger.debug(f"No Config resource type mapping for {drift.resource_type}")
                return []

            later_time = datetime.utcnow()
            earlier_time = later_time - timedelta(days=settings.config_lookback_days)

            response = await asyncio.to_thread(
                config.get_resource_config_history,
                resourceType=config_resource_type,
                resourceId=drift.resource_id,
                laterTime=later_time,
                earlierTime=earlier_time,
                limit=50,
            )

            config_items = response.get("configurationItems", [])
            config_changes = []

            for item in config_items:
                config_change = ConfigChange(
                    change_id=item.get("configurationItemCaptureTime", ""),
                    timestamp=datetime.fromisoformat(
                        item.get("configurationItemCaptureTime", "").replace("Z", "+00:00")
                    ) if item.get("configurationItemCaptureTime") else datetime.now(datetime.UTC),
                    user=item.get("arn", "").split("/")[-1] if item.get("arn") else None,
                    action=item.get("configurationItemStatus", ""),
                    changes=item.get("configuration", {}),
                    compliance_type=item.get("complianceType"),
                )
                config_changes.append(config_change)

            logger.debug(f"Found {len(config_changes)} config changes for {drift.resource_id}")
            return config_changes

        except (BotoCoreError, ClientError) as e:
            logger.warning(f"Config history collection failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Config history error: {e}", exc_info=True)
            return []

    async def _collect_cost_data(self, drift: DriftRecord) -> Optional[CostAnalysis]:
        """
        Collect cost data from Cost Explorer.

        Args:
            drift: Drift record

        Returns:
            Cost analysis or None
        """
        try:
            ce = self._get_ce_client()

            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=settings.cost_explorer_lookback_days)

            # Get cost for this specific resource
            response = await asyncio.to_thread(
                ce.get_cost_and_usage,
                TimePeriod={
                    "Start": start_date.isoformat(),
                    "End": end_date.isoformat(),
                },
                Granularity="DAILY",
                Metrics=["UnblendedCost", "UsageQuantity"],
                Filter={
                    "Dimensions": {
                        "Key": "RESOURCE_ID",
                        "Values": [drift.resource_id],
                    }
                },
            )

            results_by_time = response.get("ResultsByTime", [])

            if not results_by_time:
                logger.debug(f"No cost data found for {drift.resource_id}")
                return None

            # Calculate costs
            daily_costs = []
            total_cost = 0.0

            for result in results_by_time:
                cost = float(result.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
                daily_costs.append(cost)
                total_cost += cost

            avg_daily_cost = total_cost / len(daily_costs) if daily_costs else 0.0
            monthly_projection = avg_daily_cost * 30

            # Calculate cost change (compare last week to previous week)
            mid_point = len(daily_costs) // 2
            recent_avg = sum(daily_costs[mid_point:]) / len(daily_costs[mid_point:])
            previous_avg = sum(daily_costs[:mid_point]) / len(daily_costs[:mid_point])

            cost_change = recent_avg - previous_avg
            cost_change_percent = (
                (cost_change / previous_avg * 100) if previous_avg > 0 else 0.0
            )

            cost_analysis = CostAnalysis(
                current_cost=avg_daily_cost,
                projected_cost=monthly_projection,
                cost_change=cost_change,
                cost_change_percent=cost_change_percent,
                budget_impact=self._assess_budget_impact(monthly_projection, cost_change_percent),
                recommendations=[],
            )
            return cost_analysis

        except (BotoCoreError, ClientError) as e:
            logger.warning(f"Cost data collection failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Cost data error: {e}", exc_info=True)
            return None

    def _establish_performance_baseline(
        self, _drift: DriftRecord
    ) -> Optional[PerformanceBaseline]:
        """
        Establish performance baseline from historical metrics.

        Args:
            _drift: Drift record (unused currently)

        Returns:
            Performance baseline or None
        """
        try:
            # Use collected CloudWatch metrics to establish baseline
            # This is a simplified version - in production, you'd want more sophisticated
            # baseline calculation (e.g., using statistical methods)

            baseline = PerformanceBaseline(
                cpu_baseline=None,
                memory_baseline=None,
                network_baseline=None,
                disk_baseline=None,
                established_at=datetime.now(datetime.UTC),
            )
            return baseline

        except Exception as e:
            logger.error("Baseline establishment error: %s", e, exc_info=True)
            return None

    async def _collect_compliance_violations(
        self, drift: DriftRecord
    ) -> List[ComplianceViolation]:
        """
        Collect compliance violations from AWS Config.

        Args:
            drift: Drift record

        Returns:
            List of compliance violations
        """
        try:
            config = self._get_config_client(drift.region)

            # Get compliance details for resource
            config_resource_type = self._map_to_config_resource_type(drift.resource_type)

            if not config_resource_type:
                return []

            response = await asyncio.to_thread(
                config.describe_compliance_by_resource,
                ResourceType=config_resource_type,
                ResourceId=drift.resource_id,
            )

            compliance_results = response.get("ComplianceByResources", [])
            violations = []

            for result in compliance_results:
                compliance = result.get("Compliance", {})
                compliance_type = compliance.get("ComplianceType", "")

                if compliance_type == "NON_COMPLIANT":
                    for contributor in compliance.get("ComplianceContributorCount", {}).get(
                        "CappedCount", []
                    ):
                        violation_msg = "Resource is non-compliant"
                        violation = ComplianceViolation(
                            violation_id=f"violation-{drift.resource_id}-{len(violations)}",
                            rule_name=contributor.get("RuleName", "unknown"),
                            compliance_type=compliance_type,
                            severity="high",
                            message=violation_msg,
                            detected_at=datetime.now(datetime.UTC),
                        )
                        violations.append(violation)

            return violations

        except (BotoCoreError, ClientError) as e:
            logger.warning(f"Compliance check failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Compliance error: {e}", exc_info=True)
            return []

    def _find_related_changes(self, _drift: DriftRecord) -> List[RelatedChange]:
        """
        Find related infrastructure changes that might have caused the drift.

        Args:
            _drift: Drift record (unused currently)

        Returns:
            List of related changes
        """
        try:
            # This would typically query Config history for related resources
            # For now, return empty list
            return []

        except Exception as e:
            logger.error("Related changes search error: %s", e, exc_info=True)
            return []

    def _get_metrics_config(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """Get CloudWatch metrics configuration for resource type."""
        metrics_map = {
            "aws_instance": {
                "namespace": "AWS/EC2",
                "metrics": [
                    "CPUUtilization",
                    "NetworkIn",
                    "NetworkOut",
                    "DiskReadOps",
                    "DiskWriteOps",
                    "StatusCheckFailed",
                ],
            },
            "aws_rds_instance": {
                "namespace": "AWS/RDS",
                "metrics": [
                    "DatabaseConnections",
                    "ReadLatency",
                    "WriteLatency",
                    "CPUUtilization",
                    "FreeableMemory",
                ],
            },
            "aws_lambda_function": {
                "namespace": "AWS/Lambda",
                "metrics": [
                    "Invocations",
                    "Errors",
                    "Duration",
                    "Throttles",
                    "ConcurrentExecutions",
                ],
            },
            "aws_s3_bucket": {
                "namespace": "AWS/S3",
                "metrics": ["BucketSizeBytes", "NumberOfObjects"],
            },
        }

        return metrics_map.get(resource_type)

    def _build_dimensions(self, drift: DriftRecord) -> List[Dict[str, str]]:
        """Build CloudWatch dimensions for resource."""
        if drift.resource_type == "aws_instance":
            return [{"Name": "InstanceId", "Value": drift.resource_id}]
        elif drift.resource_type == "aws_rds_instance":
            return [{"Name": "DBInstanceIdentifier", "Value": drift.resource_id}]
        elif drift.resource_type == "aws_lambda_function":
            return [{"Name": "FunctionName", "Value": drift.resource_id}]
        elif drift.resource_type == "aws_s3_bucket":
            return [
                {"Name": "BucketName", "Value": drift.resource_id},
                {"Name": "StorageType", "Value": "StandardStorage"},
            ]
        else:
            return []

    def _map_to_config_resource_type(self, terraform_type: str) -> Optional[str]:
        """Map Terraform resource type to AWS Config resource type."""
        mapping = {
            "aws_instance": "AWS::EC2::Instance",
            "aws_s3_bucket": "AWS::S3::Bucket",
            "aws_rds_instance": "AWS::RDS::DBInstance",
            "aws_lambda_function": "AWS::Lambda::Function",
            "aws_security_group": "AWS::EC2::SecurityGroup",
            "aws_iam_role": "AWS::IAM::Role",
        }

        return mapping.get(terraform_type)

    def _assess_budget_impact(self, projected_cost: float, change_percent: float) -> str:
        """Assess budget impact based on cost."""
        if projected_cost > 1000 and change_percent > 50:
            return "Critical - Significant cost increase detected"
        elif projected_cost > 500 and change_percent > 25:
            return "High - Notable cost increase"
        elif change_percent > 10:
            return "Medium - Moderate cost increase"
        else:
            return "Low - Minimal budget impact"

