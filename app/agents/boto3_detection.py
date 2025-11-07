"""boto3-based drift detection - replaces Terraform functionality."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from app.config import get_settings
from app.models.drift import DriftRecord, DriftType, Severity
from app.services.aws_client import AWSClientFactory
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Boto3DriftDetector:
    """Detects infrastructure drift using boto3 instead of Terraform."""

    def __init__(self):
        """Initialize boto3 drift detector."""
        self.factory = AWSClientFactory()
        self.baseline_file = Path("data/baseline/baseline_state.json")

    async def load_baseline_state(self) -> dict[str, Any] | None:
        """Load baseline (expected) infrastructure state."""
        if not self.baseline_file.exists():
            logger.warning(f"Baseline file not found: {self.baseline_file}")
            return None

        try:
            with open(self.baseline_file) as f:
                baseline = json.load(f)
            logger.info(f"Loaded baseline state from {self.baseline_file}")
            return baseline
        except Exception as e:
            logger.error(f"Error loading baseline: {e}")
            return None

    async def create_baseline(self, account_id: str, region: str) -> dict[str, Any]:
        """Create baseline from current AWS state."""
        logger.info(f"Creating baseline for {account_id}/{region}")

        current_state = await self.discover_current_state(account_id, region)

        # Save as baseline
        with open(self.baseline_file, "w") as f:
            json.dump(current_state, f, indent=2, default=str)

        logger.info(f"Baseline saved to {self.baseline_file}")
        return current_state

    async def discover_current_state(self, account_id: str, region: str) -> dict[str, Any]:
        """
        Discover current AWS infrastructure state using boto3.

        This is similar to scripts/discover_aws_resources.py but async.
        """
        logger.info(f"Discovering current state in {account_id}/{region}")

        state = {
            "account_id": account_id,
            "region": region,
            "timestamp": datetime.now().isoformat(),
            "resources": {},
        }

        # Discover all resource types
        state["resources"]["vpcs"] = await self._discover_vpcs()
        state["resources"]["ec2_instances"] = await self._discover_ec2_instances()
        state["resources"]["eks_clusters"] = await self._discover_eks_clusters()
        state["resources"]["ecs_clusters"] = await self._discover_ecs_clusters()
        state["resources"]["rds_instances"] = await self._discover_rds_instances()
        state["resources"]["rds_clusters"] = await self._discover_rds_clusters()
        state["resources"]["s3_buckets"] = await self._discover_s3_buckets()
        state["resources"]["dynamodb_tables"] = await self._discover_dynamodb_tables()
        state["resources"]["sqs_queues"] = await self._discover_sqs_queues()
        state["resources"]["lambda_functions"] = await self._discover_lambda_functions()
        state["resources"]["security_groups"] = await self._discover_security_groups()

        return state

    async def _discover_vpcs(self) -> list[dict[str, Any]]:
        """Discover VPCs."""
        ec2_client = self.factory.get_client("ec2")
        response = ec2_client.describe_vpcs()
        return [
            {
                "id": vpc["VpcId"],
                "cidr": vpc.get("CidrBlock"),
                "is_default": vpc.get("IsDefault", False),
                "state": vpc.get("State"),
                "tags": vpc.get("Tags", []),
            }
            for vpc in response.get("Vpcs", [])
        ]

    async def _discover_ec2_instances(self) -> list[dict[str, Any]]:
        """Discover EC2 instances."""
        ec2_client = self.factory.get_client("ec2")
        response = ec2_client.describe_instances()

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append(
                    {
                        "id": instance["InstanceId"],
                        "type": instance.get("InstanceType"),
                        "state": instance.get("State", {}).get("Name"),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "tags": instance.get("Tags", []),
                    }
                )
        return instances

    async def _discover_eks_clusters(self) -> list[dict[str, Any]]:
        """Discover EKS clusters."""
        eks_client = self.factory.get_client("eks")
        response = eks_client.list_clusters()
        cluster_names = response.get("clusters", [])

        clusters = []
        for name in cluster_names:
            cluster_info = eks_client.describe_cluster(name=name)
            cluster = cluster_info["cluster"]
            clusters.append(
                {
                    "name": name,
                    "arn": cluster.get("arn"),
                    "version": cluster.get("version"),
                    "status": cluster.get("status"),
                    "endpoint": cluster.get("endpoint"),
                }
            )
        return clusters

    async def _discover_ecs_clusters(self) -> list[dict[str, Any]]:
        """Discover ECS clusters."""
        ecs_client = self.factory.get_client("ecs")
        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        if not cluster_arns:
            return []

        clusters_response = ecs_client.describe_clusters(clusters=cluster_arns)
        return [
            {
                "name": c.get("clusterName"),
                "arn": c.get("clusterArn"),
                "status": c.get("status"),
                "running_tasks": c.get("runningTasksCount", 0),
                "active_services": c.get("activeServicesCount", 0),
            }
            for c in clusters_response.get("clusters", [])
        ]

    async def _discover_rds_instances(self) -> list[dict[str, Any]]:
        """Discover RDS instances."""
        rds_client = self.factory.get_client("rds")
        response = rds_client.describe_db_instances()
        return [
            {
                "id": i.get("DBInstanceIdentifier"),
                "arn": i.get("DBInstanceArn"),
                "engine": i.get("Engine"),
                "instance_class": i.get("DBInstanceClass"),
                "status": i.get("DBInstanceStatus"),
                "endpoint": i.get("Endpoint", {}).get("Address"),
            }
            for i in response.get("DBInstances", [])
        ]

    async def _discover_rds_clusters(self) -> list[dict[str, Any]]:
        """Discover RDS clusters."""
        rds_client = self.factory.get_client("rds")
        response = rds_client.describe_db_clusters()
        return [
            {
                "id": c.get("DBClusterIdentifier"),
                "arn": c.get("DBClusterArn"),
                "engine": c.get("Engine"),
                "status": c.get("Status"),
                "endpoint": c.get("Endpoint"),
                "members": [m.get("DBInstanceIdentifier") for m in c.get("DBClusterMembers", [])],
            }
            for c in response.get("DBClusters", [])
        ]

    async def _discover_s3_buckets(self) -> list[dict[str, Any]]:
        """Discover S3 buckets."""
        s3_client = self.factory.get_client("s3")
        response = s3_client.list_buckets()
        
        buckets = []
        for b in response.get("Buckets", []):
            bucket_name = b["Name"]
            bucket_info = {
                "name": bucket_name,
                "creation_date": str(b.get("CreationDate")),
            }
            
            # Get additional bucket properties
            try:
                # Versioning
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                bucket_info["versioning"] = versioning.get("Status", "Disabled")
                
                # Encryption
                try:
                    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                    bucket_info["encryption"] = "Enabled"
                    bucket_info["encryption_type"] = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [{}])[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", "Unknown")
                except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                    bucket_info["encryption"] = "Disabled"
                
                # Public access block
                try:
                    public_access = s3_client.get_public_access_block(Bucket=bucket_name)
                    config = public_access.get("PublicAccessBlockConfiguration", {})
                    bucket_info["public_access_blocked"] = all([
                        config.get("BlockPublicAcls", False),
                        config.get("IgnorePublicAcls", False),
                        config.get("BlockPublicPolicy", False),
                        config.get("RestrictPublicBuckets", False)
                    ])
                except s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
                    bucket_info["public_access_blocked"] = False
                
                # Tags
                try:
                    tags = s3_client.get_bucket_tagging(Bucket=bucket_name)
                    bucket_info["tags"] = tags.get("TagSet", [])
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchTagSet':
                        bucket_info["tags"] = []
                    else:
                        raise
                    
            except Exception as e:
                logger.warning(f"Could not get details for bucket {bucket_name}: {e}")
            
            buckets.append(bucket_info)
        
        return buckets

    async def _discover_dynamodb_tables(self) -> list[dict[str, Any]]:
        """Discover DynamoDB tables."""
        dynamodb_client = self.factory.get_client("dynamodb")
        response = dynamodb_client.list_tables()
        table_names = response.get("TableNames", [])

        tables = []
        for name in table_names:
            try:
                table_info = dynamodb_client.describe_table(TableName=name)
                table = table_info["Table"]
                tables.append(
                    {
                        "name": name,
                        "arn": table.get("TableArn"),
                        "status": table.get("TableStatus"),
                        "billing_mode": table.get("BillingModeSummary", {}).get("BillingMode"),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not describe table {name}: {e}")
        return tables

    async def _discover_sqs_queues(self) -> list[dict[str, Any]]:
        """Discover SQS queues."""
        sqs_client = self.factory.get_client("sqs")
        response = sqs_client.list_queues()
        queue_urls = response.get("QueueUrls", [])

        queues = []
        for url in queue_urls:
            try:
                attrs = sqs_client.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])
                queues.append(
                    {
                        "url": url,
                        "name": url.split("/")[-1],
                        "arn": attrs.get("Attributes", {}).get("QueueArn"),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not get queue attributes for {url}: {e}")
        return queues

    async def _discover_lambda_functions(self) -> list[dict[str, Any]]:
        """Discover Lambda functions."""
        lambda_client = self.factory.get_client("lambda")
        response = lambda_client.list_functions()
        return [
            {
                "name": f.get("FunctionName"),
                "arn": f.get("FunctionArn"),
                "runtime": f.get("Runtime"),
                "memory": f.get("MemorySize"),
                "timeout": f.get("Timeout"),
            }
            for f in response.get("Functions", [])
        ]

    async def _discover_security_groups(self) -> list[dict[str, Any]]:
        """Discover security groups."""
        ec2_client = self.factory.get_client("ec2")

        # Get all VPCs first
        vpcs_response = ec2_client.describe_vpcs()
        vpc_ids = [vpc["VpcId"] for vpc in vpcs_response.get("Vpcs", [])]

        all_sgs = []
        for vpc_id in vpc_ids:
            response = ec2_client.describe_security_groups(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            all_sgs.extend(response.get("SecurityGroups", []))

        return [
            {
                "id": sg.get("GroupId"),
                "name": sg.get("GroupName"),
                "vpc_id": sg.get("VpcId"),
                "ingress_rules": len(sg.get("IpPermissions", [])),
                "egress_rules": len(sg.get("IpPermissionsEgress", [])),
            }
            for sg in all_sgs
        ]

    async def compare_states(
        self,
        baseline: dict[str, Any],
        current: dict[str, Any],
        account_id: str,
        region: str,
    ) -> list[DriftRecord]:
        """
        Compare baseline and current states to detect drift.

        Args:
            baseline: Expected infrastructure state
            current: Current AWS state
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of detected drift records
        """
        logger.info("Comparing baseline vs current state")
        drift_records = []

        # Compare each resource type
        for resource_type, baseline_resources in baseline.get("resources", {}).items():
            current_resources = current.get("resources", {}).get(resource_type, [])

            # Detect drift for this resource type
            drifts = await self._compare_resource_type(
                resource_type, baseline_resources, current_resources, account_id, region
            )
            drift_records.extend(drifts)

        logger.info(f"Found {len(drift_records)} drifts")
        return drift_records

    async def _compare_resource_type(
        self,
        resource_type: str,
        baseline_resources: list[dict[str, Any]],
        current_resources: list[dict[str, Any]],
        account_id: str,
        region: str,
    ) -> list[DriftRecord]:
        """Compare a specific resource type for drift."""
        drifts = []

        # Create lookup dictionaries
        baseline_dict = {self._get_resource_id(r): r for r in baseline_resources}
        current_dict = {self._get_resource_id(r): r for r in current_resources}

        # Detect deleted resources
        for resource_id, baseline_resource in baseline_dict.items():
            if resource_id not in current_dict:
                drift = self._create_drift_record(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    drift_type=DriftType.DELETED,
                    baseline_value=baseline_resource,
                    current_value={},
                    account_id=account_id,
                    region=region,
                )
                drifts.append(drift)

        # Detect new/unmanaged resources
        for resource_id, current_resource in current_dict.items():
            if resource_id not in baseline_dict:
                drift = self._create_drift_record(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    drift_type=DriftType.UNMANAGED,
                    baseline_value={},
                    current_value=current_resource,
                    account_id=account_id,
                    region=region,
                )
                drifts.append(drift)

        # Detect modified resources
        for resource_id in set(baseline_dict.keys()) & set(current_dict.keys()):
            baseline_resource = baseline_dict[resource_id]
            current_resource = current_dict[resource_id]

            if baseline_resource != current_resource:
                diff = self._calculate_diff(baseline_resource, current_resource)
                drift = self._create_drift_record(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    drift_type=DriftType.MODIFIED,
                    baseline_value=baseline_resource,
                    current_value=current_resource,
                    account_id=account_id,
                    region=region,
                    diff=diff,
                )
                drifts.append(drift)

        return drifts

    def _get_resource_id(self, resource: dict[str, Any]) -> str:
        """Extract resource ID from resource dict."""
        # Try common ID fields
        for field in ["id", "name", "arn", "url"]:
            if field in resource:
                return str(resource[field])
        return str(hash(json.dumps(resource, sort_keys=True)))

    def _calculate_diff(self, baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        """Calculate differences between baseline and current."""
        diff = {}
        all_keys = set(baseline.keys()) | set(current.keys())

        for key in all_keys:
            baseline_val = baseline.get(key)
            current_val = current.get(key)

            if baseline_val != current_val:
                diff[key] = {"baseline": baseline_val, "current": current_val}

        return diff

    def _create_drift_record(
        self,
        resource_id: str,
        resource_type: str,
        drift_type: DriftType,
        baseline_value: dict[str, Any],
        current_value: dict[str, Any],
        account_id: str,
        region: str,
        diff: dict[str, Any] | None = None,
    ) -> DriftRecord:
        """Create a DriftRecord from detected drift."""
        if diff is None:
            diff = self._calculate_diff(baseline_value, current_value)

        # Calculate severity
        severity = self._calculate_severity(resource_type, diff, drift_type)

        # Generate drift ID
        import hashlib

        now = datetime.now()
        unique_string = f"{resource_id}-{account_id}-{region}-{now.isoformat()}"
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        drift_id = f"drift-boto3-{now.strftime('%Y%m%d')}-{hash_suffix}"

        # Hash diff for deduplication
        diff_str = json.dumps(diff, sort_keys=True)
        diff_hash = hashlib.sha256(diff_str.encode()).hexdigest()

        return DriftRecord(
            drift_id=drift_id,
            resource_id=resource_id,
            resource_type=resource_type,
            drift_type=drift_type,
            terraform_value=baseline_value,  # baseline instead of terraform
            actual_value=current_value,
            diff=diff,
            detected_at=now,
            severity=severity,
            account_id=account_id,
            region=region,
            diff_hash=diff_hash,
        )

    def _calculate_severity(
        self, resource_type: str, diff: dict[str, Any], drift_type: DriftType
    ) -> Severity:
        """Calculate drift severity."""
        # Critical for deletions
        if drift_type == DriftType.DELETED:
            return Severity.CRITICAL

        # Critical for security-sensitive changes
        security_fields = {
            "acl",
            "public",
            "encryption",
            "iam",
            "security_group",
            "policy",
        }
        for field in diff.keys():
            if any(sec in field.lower() for sec in security_fields):
                return Severity.CRITICAL

        # High for unmanaged resources
        if drift_type == DriftType.UNMANAGED:
            return Severity.HIGH

        # High for instance type/size changes
        if "instance_type" in diff or "instance_class" in diff or "size" in diff:
            return Severity.HIGH

        # Medium for tag changes
        if set(diff.keys()) == {"tags"}:
            return Severity.MEDIUM

        # Default to medium
        return Severity.MEDIUM
