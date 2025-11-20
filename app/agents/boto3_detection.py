"""boto3-based drift detection - replaces Terraform functionality."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from app.config import get_settings
from app.models.drift import DriftRecord, DriftType, Severity
from app.services.aws_client import AWSClientFactory
from app.utils.logger import get_logger
from app.agents.change_history import ChangeHistoryCollector

logger = get_logger(__name__)
settings = get_settings()


class Boto3DriftDetector:
    """Detects infrastructure drift using boto3 instead of Terraform."""

    def __init__(self):
        """Initialize boto3 drift detector."""
        self.factory = AWSClientFactory()

        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.baseline_file = project_root / "data" / "baseline" / "baseline_state.json"

        # Ensure directory exists
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)

        self.cloudwatch = None
        self.history_collector = ChangeHistoryCollector()

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

    async def discover_current_state(
        self, account_id: str, region: str, include_metrics: bool = True
    ) -> dict[str, Any]:
        """
        Discover current AWS infrastructure state using boto3.

        Args:
            account_id: AWS account ID
            region: AWS region
            include_metrics: Whether to collect CloudWatch metrics (default True)

        Returns:
            Current infrastructure state with optional metrics
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

        # Add CloudWatch metrics if requested
        if include_metrics:
            logger.info("Collecting CloudWatch metrics for baseline...")

            # Collect metrics in parallel using asyncio.gather
            if state["resources"]["ec2_instances"]:
                state["resources"]["ec2_instances"] = await asyncio.gather(
                    *[self._add_ec2_metrics(inst) for inst in state["resources"]["ec2_instances"]]
                )

            if state["resources"]["lambda_functions"]:
                state["resources"]["lambda_functions"] = await asyncio.gather(
                    *[
                        self._add_lambda_metrics(func)
                        for func in state["resources"]["lambda_functions"]
                    ]
                )

            if state["resources"]["rds_instances"]:
                state["resources"]["rds_instances"] = await asyncio.gather(
                    *[self._add_rds_metrics(inst) for inst in state["resources"]["rds_instances"]]
                )

            logger.info("Metrics collection completed")

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
        """Discover EC2 instances with comprehensive configuration details."""
        ec2_client = self.factory.get_client("ec2")
        response = ec2_client.describe_instances()

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Get instance type details for CPU/Memory info
                instance_type = instance.get("InstanceType")

                # Build comprehensive instance configuration
                instance_config = {
                    # Basic Info
                    "id": instance["InstanceId"],
                    "type": instance_type,
                    "state": instance.get("State", {}).get("Name"),
                    "state_transition_reason": instance.get("StateTransitionReason"),
                    "launch_time": str(instance.get("LaunchTime"))
                    if instance.get("LaunchTime")
                    else None,
                    # Placement & Availability
                    "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                    "tenancy": instance.get("Placement", {}).get("Tenancy"),
                    "host_id": instance.get("Placement", {}).get("HostId"),
                    # Network Configuration
                    "vpc_id": instance.get("VpcId"),
                    "subnet_id": instance.get("SubnetId"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "private_dns": instance.get("PrivateDnsName"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "public_dns": instance.get("PublicDnsName"),
                    # Network Interfaces
                    "network_interfaces": [
                        {
                            "id": ni.get("NetworkInterfaceId"),
                            "subnet_id": ni.get("SubnetId"),
                            "private_ip": ni.get("PrivateIpAddress"),
                            "public_ip": ni.get("Association", {}).get("PublicIp"),
                            "security_groups": [
                                {"id": sg.get("GroupId"), "name": sg.get("GroupName")}
                                for sg in ni.get("Groups", [])
                            ],
                            "source_dest_check": ni.get("SourceDestCheck"),
                            "device_index": ni.get("Attachment", {}).get("DeviceIndex"),
                        }
                        for ni in instance.get("NetworkInterfaces", [])
                    ],
                    # Security
                    "security_groups": [
                        {"id": sg.get("GroupId"), "name": sg.get("GroupName")}
                        for sg in instance.get("SecurityGroups", [])
                    ],
                    "key_name": instance.get("KeyName"),
                    "iam_instance_profile": instance.get("IamInstanceProfile", {}).get("Arn"),
                    # Storage
                    "root_device_type": instance.get("RootDeviceType"),
                    "root_device_name": instance.get("RootDeviceName"),
                    "block_device_mappings": [
                        {
                            "device_name": bdm.get("DeviceName"),
                            "volume_id": bdm.get("Ebs", {}).get("VolumeId"),
                            "status": bdm.get("Ebs", {}).get("Status"),
                            "delete_on_termination": bdm.get("Ebs", {}).get("DeleteOnTermination"),
                        }
                        for bdm in instance.get("BlockDeviceMappings", [])
                    ],
                    # Platform & AMI
                    "platform": instance.get("Platform"),  # 'windows' or None for Linux
                    "platform_details": instance.get("PlatformDetails"),
                    "image_id": instance.get("ImageId"),
                    "architecture": instance.get("Architecture"),
                    "virtualization_type": instance.get("VirtualizationType"),
                    "hypervisor": instance.get("Hypervisor"),
                    # Capacity & Performance
                    "cpu_options": {
                        "core_count": instance.get("CpuOptions", {}).get("CoreCount"),
                        "threads_per_core": instance.get("CpuOptions", {}).get("ThreadsPerCore"),
                    },
                    "ena_support": instance.get("EnaSupport"),  # Enhanced networking
                    "ebs_optimized": instance.get("EbsOptimized"),
                    # Monitoring & Logging
                    "monitoring_state": instance.get("Monitoring", {}).get("State"),
                    "instance_lifecycle": instance.get("InstanceLifecycle"),  # 'spot' or None
                    # Auto-scaling & Capacity Reservations
                    "capacity_reservation_id": instance.get("CapacityReservationId"),
                    "capacity_reservation_specification": instance.get(
                        "CapacityReservationSpecification"
                    ),
                    # Elastic IPs
                    "elastic_ip_associations": [
                        {
                            "public_ip": ni.get("Association", {}).get("PublicIp"),
                            "allocation_id": ni.get("Association", {}).get("AllocationId"),
                            "ip_owner_id": ni.get("Association", {}).get("IpOwnerId"),
                        }
                        for ni in instance.get("NetworkInterfaces", [])
                        if ni.get("Association")
                    ],
                    # Metadata & Options
                    "metadata_options": {
                        "http_tokens": instance.get("MetadataOptions", {}).get("HttpTokens"),
                        "http_put_response_hop_limit": instance.get("MetadataOptions", {}).get(
                            "HttpPutResponseHopLimit"
                        ),
                        "http_endpoint": instance.get("MetadataOptions", {}).get("HttpEndpoint"),
                    },
                    # Hibernation
                    "hibernation_configured": instance.get("HibernationOptions", {}).get(
                        "Configured"
                    ),
                    # License & Usage
                    "usage_operation": instance.get("UsageOperation"),
                    "usage_operation_update_time": str(instance.get("UsageOperationUpdateTime"))
                    if instance.get("UsageOperationUpdateTime")
                    else None,
                    # Tags
                    "tags": instance.get("Tags", []),
                }

                instances.append(instance_config)

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
            
            # Get node groups
            node_groups = []
            try:
                ng_response = eks_client.list_nodegroups(clusterName=name)
                for ng_name in ng_response.get("nodegroups", []):
                    ng_info = eks_client.describe_nodegroup(clusterName=name, nodegroupName=ng_name)
                    ng = ng_info["nodegroup"]
                    node_groups.append({
                        "name": ng_name,
                        "status": ng.get("status"),
                        "instance_types": ng.get("instanceTypes", []),
                        "desired_size": ng.get("scalingConfig", {}).get("desiredSize"),
                        "min_size": ng.get("scalingConfig", {}).get("minSize"),
                        "max_size": ng.get("scalingConfig", {}).get("maxSize"),
                        "ami_type": ng.get("amiType"),
                        "capacity_type": ng.get("capacityType"),
                    })
            except Exception as e:
                logger.warning(f"Failed to get node groups for {name}: {e}")
            
            # Get Fargate profiles
            fargate_profiles = []
            try:
                fp_response = eks_client.list_fargate_profiles(clusterName=name)
                fargate_profiles = fp_response.get("fargateProfileNames", [])
            except Exception as e:
                logger.warning(f"Failed to get Fargate profiles for {name}: {e}")
            
            # Get addons
            addons = []
            try:
                addon_response = eks_client.list_addons(clusterName=name)
                for addon_name in addon_response.get("addons", []):
                    addon_info = eks_client.describe_addon(clusterName=name, addonName=addon_name)
                    addon = addon_info["addon"]
                    addons.append({
                        "name": addon_name,
                        "version": addon.get("addonVersion"),
                        "status": addon.get("status"),
                    })
            except Exception as e:
                logger.warning(f"Failed to get addons for {name}: {e}")
            
            clusters.append(
                {
                    "name": name,
                    "arn": cluster.get("arn"),
                    "version": cluster.get("version"),
                    "status": cluster.get("status"),
                    "endpoint": cluster.get("endpoint"),
                    "platform_version": cluster.get("platformVersion"),
                    "role_arn": cluster.get("roleArn"),
                    "vpc_config": {
                        "subnet_ids": cluster.get("resourcesVpcConfig", {}).get("subnetIds", []),
                        "security_group_ids": cluster.get("resourcesVpcConfig", {}).get("securityGroupIds", []),
                        "cluster_security_group_id": cluster.get("resourcesVpcConfig", {}).get("clusterSecurityGroupId"),
                        "vpc_id": cluster.get("resourcesVpcConfig", {}).get("vpcId"),
                        "endpoint_public_access": cluster.get("resourcesVpcConfig", {}).get("endpointPublicAccess"),
                        "endpoint_private_access": cluster.get("resourcesVpcConfig", {}).get("endpointPrivateAccess"),
                        "public_access_cidrs": cluster.get("resourcesVpcConfig", {}).get("publicAccessCidrs", []),
                    },
                    "logging": cluster.get("logging", {}),
                    "identity": cluster.get("identity", {}),
                    "encryption_config": cluster.get("encryptionConfig", []),
                    "node_groups": node_groups,
                    "fargate_profiles": fargate_profiles,
                    "addons": addons,
                    "tags": cluster.get("tags", {}),
                    "created_at": str(cluster.get("createdAt", "")),
                }
            )
        return clusters

    async def _discover_ecs_clusters(self) -> list[dict[str, Any]]:
        """Discover ECS clusters with services and tasks."""
        ecs_client = self.factory.get_client("ecs")
        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        if not cluster_arns:
            return []

        clusters_response = ecs_client.describe_clusters(clusters=cluster_arns)
        clusters = []
        
        for c in clusters_response.get("clusters", []):
            cluster_name = c.get("clusterName")
            cluster_arn = c.get("clusterArn")
            
            # Get services
            services = []
            try:
                svc_response = ecs_client.list_services(cluster=cluster_arn)
                service_arns = svc_response.get("serviceArns", [])
                if service_arns:
                    svc_desc = ecs_client.describe_services(cluster=cluster_arn, services=service_arns)
                    for svc in svc_desc.get("services", []):
                        services.append({
                            "name": svc.get("serviceName"),
                            "status": svc.get("status"),
                            "desired_count": svc.get("desiredCount"),
                            "running_count": svc.get("runningCount"),
                            "launch_type": svc.get("launchType"),
                            "task_definition": svc.get("taskDefinition"),
                        })
            except Exception as e:
                logger.warning(f"Failed to get services for {cluster_name}: {e}")
            
            # Get tasks count
            tasks_count = 0
            try:
                tasks_response = ecs_client.list_tasks(cluster=cluster_arn)
                tasks_count = len(tasks_response.get("taskArns", []))
            except Exception as e:
                logger.warning(f"Failed to get tasks for {cluster_name}: {e}")
            
            clusters.append({
                "name": cluster_name,
                "arn": cluster_arn,
                "status": c.get("status"),
                "running_tasks_count": c.get("runningTasksCount", 0),
                "pending_tasks_count": c.get("pendingTasksCount", 0),
                "active_services_count": c.get("activeServicesCount", 0),
                "registered_container_instances_count": c.get("registeredContainerInstancesCount", 0),
                "settings": c.get("settings", []),
                "services": services,
                "tasks_count": tasks_count,
                "tags": c.get("tags", []),
            })
        
        return clusters

    async def _discover_rds_instances(self) -> list[dict[str, Any]]:
        """Discover RDS instances with comprehensive configuration."""
        rds_client = self.factory.get_client("rds")
        response = rds_client.describe_db_instances()

        instances = []
        for i in response.get("DBInstances", []):
            instance_config = {
                # Basic Info
                "id": i.get("DBInstanceIdentifier"),
                "arn": i.get("DBInstanceArn"),
                "db_name": i.get("DBName"),
                # Engine Configuration
                "engine": i.get("Engine"),
                "engine_version": i.get("EngineVersion"),
                "license_model": i.get("LicenseModel"),
                # Instance Configuration
                "instance_class": i.get("DBInstanceClass"),
                "status": i.get("DBInstanceStatus"),
                # Storage Configuration
                "allocated_storage": i.get("AllocatedStorage"),  # GB
                "max_allocated_storage": i.get("MaxAllocatedStorage"),
                "storage_type": i.get("StorageType"),  # gp2, gp3, io1, etc.
                "iops": i.get("Iops"),
                "storage_encrypted": i.get("StorageEncrypted"),
                "kms_key_id": i.get("KmsKeyId"),
                # Network Configuration
                "endpoint": i.get("Endpoint", {}).get("Address"),
                "port": i.get("Endpoint", {}).get("Port"),
                "availability_zone": i.get("AvailabilityZone"),
                "multi_az": i.get("MultiAZ"),
                "publicly_accessible": i.get("PubliclyAccessible"),
                "vpc_security_groups": [
                    {"id": sg.get("VpcSecurityGroupId"), "status": sg.get("Status")}
                    for sg in i.get("VpcSecurityGroups", [])
                ],
                "db_subnet_group": {
                    "name": i.get("DBSubnetGroup", {}).get("DBSubnetGroupName"),
                    "vpc_id": i.get("DBSubnetGroup", {}).get("VpcId"),
                    "subnets": [
                        {
                            "id": s.get("SubnetIdentifier"),
                            "az": s.get("SubnetAvailabilityZone", {}).get("Name"),
                        }
                        for s in i.get("DBSubnetGroup", {}).get("Subnets", [])
                    ],
                }
                if i.get("DBSubnetGroup")
                else None,
                # Backup Configuration
                "backup_retention_period": i.get("BackupRetentionPeriod"),  # days
                "preferred_backup_window": i.get("PreferredBackupWindow"),
                "latest_restorable_time": str(i.get("LatestRestorableTime"))
                if i.get("LatestRestorableTime")
                else None,
                # Maintenance
                "preferred_maintenance_window": i.get("PreferredMaintenanceWindow"),
                "auto_minor_version_upgrade": i.get("AutoMinorVersionUpgrade"),
                # Monitoring
                "monitoring_interval": i.get("MonitoringInterval"),  # seconds
                "monitoring_role_arn": i.get("MonitoringRoleArn"),
                "enhanced_monitoring_resource_arn": i.get("EnhancedMonitoringResourceArn"),
                "performance_insights_enabled": i.get("PerformanceInsightsEnabled"),
                "performance_insights_retention_period": i.get(
                    "PerformanceInsightsRetentionPeriod"
                ),
                # Logging
                "enabled_cloudwatch_logs_exports": i.get("EnabledCloudwatchLogsExports", []),
                # Read Replicas & Replication
                "read_replica_source": i.get("ReadReplicaSourceDBInstanceIdentifier"),
                "read_replica_identifiers": i.get("ReadReplicaDBInstanceIdentifiers", []),
                # Parameter & Option Groups
                "db_parameter_groups": [
                    {
                        "name": pg.get("DBParameterGroupName"),
                        "status": pg.get("ParameterApplyStatus"),
                    }
                    for pg in i.get("DBParameterGroups", [])
                ],
                "option_group_memberships": [
                    {"name": og.get("OptionGroupName"), "status": og.get("Status")}
                    for og in i.get("OptionGroupMemberships", [])
                ],
                # IAM Authentication
                "iam_database_authentication_enabled": i.get("IAMDatabaseAuthenticationEnabled"),
                # Deletion Protection
                "deletion_protection": i.get("DeletionProtection"),
                # Tags
                "tags": i.get("TagList", []),
                # Timestamps
                "instance_create_time": str(i.get("InstanceCreateTime"))
                if i.get("InstanceCreateTime")
                else None,
            }

            instances.append(instance_config)

        return instances

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
                    bucket_info["encryption_type"] = (
                        encryption.get("ServerSideEncryptionConfiguration", {})
                        .get("Rules", [{}])[0]
                        .get("ApplyServerSideEncryptionByDefault", {})
                        .get("SSEAlgorithm", "Unknown")
                    )
                except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                    bucket_info["encryption"] = "Disabled"

                # Public access block
                try:
                    public_access = s3_client.get_public_access_block(Bucket=bucket_name)
                    config = public_access.get("PublicAccessBlockConfiguration", {})
                    bucket_info["public_access_blocked"] = all(
                        [
                            config.get("BlockPublicAcls", False),
                            config.get("IgnorePublicAcls", False),
                            config.get("BlockPublicPolicy", False),
                            config.get("RestrictPublicBuckets", False),
                        ]
                    )
                except s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
                    bucket_info["public_access_blocked"] = False

                # Tags
                try:
                    tags = s3_client.get_bucket_tagging(Bucket=bucket_name)
                    bucket_info["tags"] = tags.get("TagSet", [])
                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchTagSet":
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
        """Discover Lambda functions with comprehensive configuration."""
        lambda_client = self.factory.get_client("lambda")
        response = lambda_client.list_functions()

        functions = []
        for f in response.get("Functions", []):
            function_name = f.get("FunctionName")

            # Get concurrency settings
            concurrency_config = None
            try:
                concurrency_response = lambda_client.get_function_concurrency(
                    FunctionName=function_name
                )
                concurrency_config = {
                    "reserved_concurrent_executions": concurrency_response.get(
                        "ReservedConcurrentExecutions"
                    )
                }
            except lambda_client.exceptions.ResourceNotFoundException:
                concurrency_config = {"reserved_concurrent_executions": None}

            function_config = {
                # Basic Info
                "name": function_name,
                "arn": f.get("FunctionArn"),
                "description": f.get("Description"),
                "role": f.get("Role"),
                # Runtime Configuration
                "runtime": f.get("Runtime"),
                "handler": f.get("Handler"),
                "code_size": f.get("CodeSize"),
                "code_sha256": f.get("CodeSha256"),
                # Resource Configuration
                "memory_size": f.get("MemorySize"),  # MB
                "timeout": f.get("Timeout"),  # seconds
                "ephemeral_storage": f.get("EphemeralStorage", {}).get("Size"),  # MB
                # Concurrency
                "reserved_concurrent_executions": concurrency_config.get(
                    "reserved_concurrent_executions"
                ),
                # Environment Variables
                "environment_variables": f.get("Environment", {}).get("Variables", {}),
                # Layers
                "layers": [
                    {
                        "arn": layer.get("Arn"),
                        "code_size": layer.get("CodeSize"),
                    }
                    for layer in f.get("Layers", [])
                ],
                # VPC Configuration
                "vpc_config": {
                    "subnet_ids": f.get("VpcConfig", {}).get("SubnetIds", []),
                    "security_group_ids": f.get("VpcConfig", {}).get("SecurityGroupIds", []),
                    "vpc_id": f.get("VpcConfig", {}).get("VpcId"),
                }
                if f.get("VpcConfig")
                else None,
                # Architecture
                "architectures": f.get("Architectures", []),  # x86_64 or arm64
                "package_type": f.get("PackageType"),  # Zip or Image
                # State & Version
                "state": f.get("State"),
                "state_reason": f.get("StateReason"),
                "last_modified": f.get("LastModified"),
                "version": f.get("Version"),
                # Logging
                "logging_config": {
                    "log_format": f.get("LoggingConfig", {}).get("LogFormat"),
                    "log_group": f.get("LoggingConfig", {}).get("LogGroup"),
                },
                # Dead Letter Queue
                "dead_letter_config": f.get("DeadLetterConfig"),
                # Tracing
                "tracing_config": f.get("TracingConfig", {}).get("Mode"),
                # Image Config (for container-based functions)
                "image_config": f.get("ImageConfigResponse"),
            }

            functions.append(function_config)

        return functions

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

    def _get_cloudwatch_client(self):
        """Get CloudWatch client (lazy initialization)."""
        if not self.cloudwatch:
            self.cloudwatch = self.factory.get_client("cloudwatch")
        return self.cloudwatch

    def _collect_cloudwatch_metrics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        period_hours: int = 24,
    ) -> dict[str, Any] | None:
        """
        Collect CloudWatch metrics for a resource.

        Args:
            namespace: AWS namespace (AWS/EC2, AWS/Lambda, etc.)
            metric_name: Metric name
            dimensions: Dimensions for the metric
            period_hours: How many hours of history to analyze

        Returns:
            Dict with metric statistics or None
        """
        try:
            cloudwatch = self._get_cloudwatch_client()
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=period_hours)

            response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour granularity
                Statistics=["Average", "Maximum", "Minimum"],
            )

            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return None

            # Calculate statistics
            avg_values = [dp.get("Average", 0) for dp in datapoints]
            max_values = [dp.get("Maximum", 0) for dp in datapoints]
            min_values = [dp.get("Minimum", 0) for dp in datapoints]

            return {
                "average": sum(avg_values) / len(avg_values) if avg_values else 0,
                "maximum": max(max_values) if max_values else 0,
                "minimum": min(min_values) if min_values else 0,
                "period_hours": period_hours,
                "captured_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.debug(f"Could not collect metric {metric_name}: {e}")
            return None

    async def _add_ec2_metrics(self, instance: dict[str, Any]) -> dict[str, Any]:
        """Add CloudWatch metrics to EC2 instance config."""
        instance_id = instance.get("id")
        if not instance_id or instance.get("state") not in ["running", "stopped"]:
            return instance

        dimensions = [{"Name": "InstanceId", "Value": instance_id}]

        metrics = {}
        metric_names = [
            "CPUUtilization",
            "NetworkIn",
            "NetworkOut",
            "DiskReadBytes",
            "DiskWriteBytes",
        ]

        for metric_name in metric_names:
            stat = self._collect_cloudwatch_metrics("AWS/EC2", metric_name, dimensions)
            if stat:
                metrics[metric_name.lower()] = stat

        if metrics:
            instance["metrics_baseline"] = metrics

        return instance

    async def _add_lambda_metrics(self, function: dict[str, Any]) -> dict[str, Any]:
        """Add CloudWatch metrics to Lambda function config."""
        function_name = function.get("name")
        if not function_name:
            return function

        dimensions = [{"Name": "FunctionName", "Value": function_name}]

        metrics = {}
        metric_names = ["Invocations", "Duration", "Errors", "Throttles", "ConcurrentExecutions"]

        for metric_name in metric_names:
            stat = self._collect_cloudwatch_metrics("AWS/Lambda", metric_name, dimensions)
            if stat:
                metrics[metric_name.lower()] = stat

        if metrics:
            function["metrics_baseline"] = metrics

        return function

    async def _add_rds_metrics(self, instance: dict[str, Any]) -> dict[str, Any]:
        """Add CloudWatch metrics to RDS instance config."""
        db_instance_id = instance.get("id")
        if not db_instance_id or instance.get("status") != "available":
            return instance

        dimensions = [{"Name": "DBInstanceIdentifier", "Value": db_instance_id}]

        metrics = {}
        metric_names = [
            "CPUUtilization",
            "DatabaseConnections",
            "FreeableMemory",
            "ReadIOPS",
            "WriteIOPS",
        ]

        for metric_name in metric_names:
            stat = self._collect_cloudwatch_metrics("AWS/RDS", metric_name, dimensions)
            if stat:
                metrics[metric_name.lower()] = stat

        if metrics:
            instance["metrics_baseline"] = metrics

        return instance

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

            # Calculate diff (excludes metrics_baseline automatically)
            diff = self._calculate_diff(baseline_resource, current_resource)

            # Only create drift if there are actual configuration changes
            # (metrics_baseline is already excluded by _calculate_diff)
            if diff:  # Only if there are real config changes
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
        """
        Calculate differences between baseline and current.

        Excludes metrics_baseline from drift detection since metrics are
        monitoring data that naturally changes and cannot be reverted.
        """
        diff = {}

        # Keys to exclude from drift detection
        excluded_keys = {
            "metrics_baseline",  # CloudWatch metrics - monitoring only
            "captured_at",  # Timestamp fields
            "timestamp",  # Timestamp fields
        }

        all_keys = set(baseline.keys()) | set(current.keys())
        # Filter out excluded keys
        all_keys = all_keys - excluded_keys

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
        include_history: bool = True,
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

        # Enrich with change history (who/when/what changed)
        change_history = None
        if include_history:
            try:
                history = self.history_collector.get_enriched_history(
                    resource_id, resource_type, region
                )
                if history and history.get("timeline"):
                    change_history = {
                        "last_modified_by": history.get("last_modified_by"),
                        "last_modified_at": history.get("last_modified_at"),
                        "recent_events": history["timeline"][:5],  # Last 5 events
                        "total_events": len(history["timeline"]),
                    }
                    logger.info(
                        f"Enriched drift with change history: "
                        f"{change_history['total_events']} events found"
                    )
            except Exception as e:
                logger.warning(f"Could not enrich with change history: {e}")

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
            change_history=change_history,  # NEW: WHO/WHEN/WHAT changed
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
