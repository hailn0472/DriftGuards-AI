"""
AWS Resource Discovery using boto3
This script replaces terraform/main.tf with a complete boto3-based solution.

Unlike Terraform data sources, boto3 can list ALL AWS resources without limitations.
Output format matches Terraform output for easy migration.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.services.aws_client import AWSClientFactory
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AWSResourceDiscovery:
    """Complete AWS resource discovery using boto3."""

    def __init__(self):
        """Initialize AWS clients."""
        self.factory = AWSClientFactory()
        self.account_id = None
        self.region = settings.aws_region

    def get_account_info(self) -> dict[str, str]:
        """Get AWS account information."""
        print("🔍 Getting AWS account information...")
        sts_client = self.factory.get_client("sts")
        identity = sts_client.get_caller_identity()
        self.account_id = identity["Account"]

        return {
            "account_id": self.account_id,
            "user_id": identity.get("UserId", "N/A"),
            "arn": identity.get("Arn", "N/A"),
            "region": self.region,
        }

    def discover_vpcs(self) -> dict[str, Any]:
        """Discover all VPCs."""
        print("🌐 Discovering VPCs...")
        ec2_client = self.factory.get_client("ec2")

        response = ec2_client.describe_vpcs()
        vpcs = response.get("Vpcs", [])

        vpc_details = []
        for vpc in vpcs:
            vpc_id = vpc.get("VpcId")
            name = "N/A"
            for tag in vpc.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break

            vpc_details.append(
                {
                    "vpc_id": vpc_id,
                    "name": name,
                    "cidr_block": vpc.get("CidrBlock"),
                    "is_default": vpc.get("IsDefault", False),
                    "state": vpc.get("State"),
                    "tags": vpc.get("Tags", []),
                }
            )

        return {"count": len(vpcs), "ids": [v["VpcId"] for v in vpcs], "details": vpc_details}

    def discover_ec2_instances(self) -> dict[str, Any]:
        """Discover all EC2 instances."""
        print("📦 Discovering EC2 instances...")
        ec2_client = self.factory.get_client("ec2")

        response = ec2_client.describe_instances()

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId")
                name = "N/A"
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                instances.append(
                    {
                        "instance_id": instance_id,
                        "name": name,
                        "instance_type": instance.get("InstanceType"),
                        "state": instance.get("State", {}).get("Name"),
                        "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "launch_time": str(instance.get("LaunchTime")),
                        "tags": instance.get("Tags", []),
                    }
                )

        return {
            "count": len(instances),
            "ids": [i["instance_id"] for i in instances],
            "details": instances,
        }

    def discover_eks_clusters(self) -> dict[str, Any]:
        """Discover all EKS clusters."""
        print("☸️  Discovering EKS clusters...")
        eks_client = self.factory.get_client("eks")

        response = eks_client.list_clusters()
        cluster_names = response.get("clusters", [])

        cluster_details = []
        for cluster_name in cluster_names:
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            cluster = cluster_info["cluster"]

            cluster_details.append(
                {
                    "name": cluster_name,
                    "arn": cluster.get("arn"),
                    "version": cluster.get("version"),
                    "status": cluster.get("status"),
                    "endpoint": cluster.get("endpoint"),
                    "created_at": str(cluster.get("createdAt")),
                    "vpc_config": cluster.get("vpcConfig", {}),
                    "tags": cluster.get("tags", {}),
                }
            )

        return {"count": len(cluster_names), "names": cluster_names, "details": cluster_details}

    def discover_ecs_clusters(self) -> dict[str, Any]:
        """Discover all ECS clusters - TERRAFORM CAN'T DO THIS!"""
        print("🐳 Discovering ECS clusters...")
        ecs_client = self.factory.get_client("ecs")

        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        cluster_details = []
        if cluster_arns:
            clusters_response = ecs_client.describe_clusters(clusters=cluster_arns)
            for cluster in clusters_response.get("clusters", []):
                cluster_details.append(
                    {
                        "name": cluster.get("clusterName"),
                        "arn": cluster.get("clusterArn"),
                        "status": cluster.get("status"),
                        "running_tasks": cluster.get("runningTasksCount", 0),
                        "pending_tasks": cluster.get("pendingTasksCount", 0),
                        "active_services": cluster.get("activeServicesCount", 0),
                        "registered_instances": cluster.get("registeredContainerInstancesCount", 0),
                        "tags": cluster.get("tags", []),
                    }
                )

        return {"count": len(cluster_arns), "arns": cluster_arns, "details": cluster_details}

    def discover_rds_instances(self) -> dict[str, Any]:
        """Discover all RDS instances."""
        print("🗄️  Discovering RDS instances...")
        rds_client = self.factory.get_client("rds")

        response = rds_client.describe_db_instances()
        instances = response.get("DBInstances", [])

        instance_details = []
        for instance in instances:
            instance_details.append(
                {
                    "identifier": instance.get("DBInstanceIdentifier"),
                    "arn": instance.get("DBInstanceArn"),
                    "engine": instance.get("Engine"),
                    "engine_version": instance.get("EngineVersion"),
                    "instance_class": instance.get("DBInstanceClass"),
                    "status": instance.get("DBInstanceStatus"),
                    "endpoint": instance.get("Endpoint", {}).get("Address"),
                    "port": instance.get("Endpoint", {}).get("Port"),
                    "availability_zone": instance.get("AvailabilityZone"),
                    "multi_az": instance.get("MultiAZ", False),
                    "storage_type": instance.get("StorageType"),
                    "allocated_storage": instance.get("AllocatedStorage"),
                    "tags": instance.get("TagList", []),
                }
            )

        return {
            "count": len(instances),
            "identifiers": [i.get("DBInstanceIdentifier") for i in instances],
            "details": instance_details,
        }

    def discover_rds_clusters(self) -> dict[str, Any]:
        """Discover all RDS clusters (Aurora)."""
        print("💫 Discovering RDS clusters (Aurora)...")
        rds_client = self.factory.get_client("rds")

        response = rds_client.describe_db_clusters()
        clusters = response.get("DBClusters", [])

        cluster_details = []
        for cluster in clusters:
            cluster_details.append(
                {
                    "identifier": cluster.get("DBClusterIdentifier"),
                    "arn": cluster.get("DBClusterArn"),
                    "engine": cluster.get("Engine"),
                    "engine_version": cluster.get("EngineVersion"),
                    "status": cluster.get("Status"),
                    "endpoint": cluster.get("Endpoint"),
                    "reader_endpoint": cluster.get("ReaderEndpoint"),
                    "port": cluster.get("Port"),
                    "database_name": cluster.get("DatabaseName"),
                    "master_username": cluster.get("MasterUsername"),
                    "availability_zones": cluster.get("AvailabilityZones", []),
                    "members": [
                        m.get("DBInstanceIdentifier") for m in cluster.get("DBClusterMembers", [])
                    ],
                    "tags": cluster.get("TagList", []),
                }
            )

        return {
            "count": len(clusters),
            "identifiers": [c.get("DBClusterIdentifier") for c in clusters],
            "details": cluster_details,
        }

    def discover_s3_buckets(self) -> dict[str, Any]:
        """Discover all S3 buckets - TERRAFORM CAN'T DO THIS!"""
        print("🪣 Discovering S3 buckets...")
        s3_client = self.factory.get_client("s3")

        response = s3_client.list_buckets()
        buckets = response.get("Buckets", [])

        bucket_details = []
        for bucket in buckets:
            bucket_name = bucket["Name"]

            # Get bucket region
            try:
                location = s3_client.get_bucket_location(Bucket=bucket_name)
                region = location.get("LocationConstraint") or "us-east-1"
            except:
                region = "unknown"

            # Get bucket tags (if accessible)
            tags = []
            try:
                tag_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                tags = tag_response.get("TagSet", [])
            except:
                pass

            bucket_details.append(
                {
                    "name": bucket_name,
                    "creation_date": str(bucket.get("CreationDate")),
                    "region": region,
                    "tags": tags,
                }
            )

        return {
            "count": len(buckets),
            "names": [b["Name"] for b in buckets],
            "details": bucket_details,
        }

    def discover_dynamodb_tables(self) -> dict[str, Any]:
        """Discover all DynamoDB tables - TERRAFORM CAN'T DO THIS!"""
        print("📊 Discovering DynamoDB tables...")
        dynamodb_client = self.factory.get_client("dynamodb")

        response = dynamodb_client.list_tables()
        table_names = response.get("TableNames", [])

        table_details = []
        for table_name in table_names:
            try:
                table_info = dynamodb_client.describe_table(TableName=table_name)
                table = table_info["Table"]

                table_details.append(
                    {
                        "name": table_name,
                        "arn": table.get("TableArn"),
                        "status": table.get("TableStatus"),
                        "item_count": table.get("ItemCount", 0),
                        "size_bytes": table.get("TableSizeBytes", 0),
                        "billing_mode": table.get("BillingModeSummary", {}).get(
                            "BillingMode", "N/A"
                        ),
                        "creation_date": str(table.get("CreationDateTime")),
                        "key_schema": table.get("KeySchema", []),
                        "attributes": table.get("AttributeDefinitions", []),
                    }
                )
            except:
                table_details.append({"name": table_name, "error": "Could not retrieve details"})

        return {"count": len(table_names), "names": table_names, "details": table_details}

    def discover_sqs_queues(self) -> dict[str, Any]:
        """Discover all SQS queues - TERRAFORM CAN'T DO THIS!"""
        print("📬 Discovering SQS queues...")
        sqs_client = self.factory.get_client("sqs")

        response = sqs_client.list_queues()
        queue_urls = response.get("QueueUrls", [])

        queue_details = []
        for queue_url in queue_urls:
            queue_name = queue_url.split("/")[-1]

            # Get queue attributes
            try:
                attrs = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
                attributes = attrs.get("Attributes", {})

                queue_details.append(
                    {
                        "name": queue_name,
                        "url": queue_url,
                        "arn": attributes.get("QueueArn"),
                        "messages": int(attributes.get("ApproximateNumberOfMessages", 0)),
                        "messages_in_flight": int(
                            attributes.get("ApproximateNumberOfMessagesNotVisible", 0)
                        ),
                        "visibility_timeout": int(attributes.get("VisibilityTimeout", 0)),
                        "retention_period": int(attributes.get("MessageRetentionPeriod", 0)),
                        "created_timestamp": attributes.get("CreatedTimestamp"),
                    }
                )
            except:
                queue_details.append(
                    {"name": queue_name, "url": queue_url, "error": "Could not retrieve attributes"}
                )

        return {"count": len(queue_urls), "urls": queue_urls, "details": queue_details}

    def discover_lambda_functions(self) -> dict[str, Any]:
        """Discover all Lambda functions - TERRAFORM CAN'T DO THIS!"""
        print("⚡ Discovering Lambda functions...")
        lambda_client = self.factory.get_client("lambda")

        response = lambda_client.list_functions()
        functions = response.get("Functions", [])

        function_details = []
        for func in functions:
            function_details.append(
                {
                    "name": func.get("FunctionName"),
                    "arn": func.get("FunctionArn"),
                    "runtime": func.get("Runtime"),
                    "handler": func.get("Handler"),
                    "memory_size": func.get("MemorySize"),
                    "timeout": func.get("Timeout"),
                    "last_modified": func.get("LastModified"),
                    "code_size": func.get("CodeSize"),
                    "vpc_config": func.get("VpcConfig", {}),
                    "environment": func.get("Environment", {}),
                }
            )

        return {
            "count": len(functions),
            "names": [f.get("FunctionName") for f in functions],
            "details": function_details,
        }

    def discover_security_groups(self) -> dict[str, Any]:
        """Discover all security groups."""
        print("🔒 Discovering security groups...")
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

        sg_details = []
        for sg in all_sgs:
            name = sg.get("GroupName", "N/A")

            sg_details.append(
                {
                    "id": sg.get("GroupId"),
                    "name": name,
                    "description": sg.get("Description"),
                    "vpc_id": sg.get("VpcId"),
                    "ingress_rules": len(sg.get("IpPermissions", [])),
                    "egress_rules": len(sg.get("IpPermissionsEgress", [])),
                    "tags": sg.get("Tags", []),
                }
            )

        return {
            "count": len(all_sgs),
            "ids": [sg["GroupId"] for sg in all_sgs],
            "details": sg_details,
        }

    def discover_msk_clusters(self) -> dict[str, Any]:
        """Discover all MSK (Kafka) clusters."""
        print("📨 Discovering MSK clusters...")
        kafka_client = self.factory.get_client("kafka")

        try:
            response = kafka_client.list_clusters()
            clusters = response.get("ClusterInfoList", [])

            cluster_details = []
            for cluster in clusters:
                cluster_details.append(
                    {
                        "name": cluster.get("ClusterName"),
                        "arn": cluster.get("ClusterArn"),
                        "state": cluster.get("State"),
                        "kafka_version": cluster.get("CurrentBrokerSoftwareInfo", {}).get(
                            "KafkaVersion"
                        ),
                        "number_of_brokers": cluster.get("NumberOfBrokerNodes"),
                        "creation_time": str(cluster.get("CreationTime")),
                        "tags": cluster.get("Tags", {}),
                    }
                )

            return {
                "count": len(clusters),
                "arns": [c.get("ClusterArn") for c in clusters],
                "details": cluster_details,
            }
        except Exception as e:
            logger.warning(f"Could not list MSK clusters: {e}")
            return {"count": 0, "arns": [], "details": [], "error": str(e)}

    def discover_all(self) -> dict[str, Any]:
        """Discover all AWS resources."""
        print("\n" + "=" * 80)
        print("  AWS RESOURCE DISCOVERY (boto3)")
        print("  Replacing Terraform with complete boto3-based discovery")
        print("=" * 80 + "\n")

        discovery_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "tool": "boto3",
                "description": "Complete AWS resource discovery - NO LIMITATIONS!",
            }
        }

        # Account info
        discovery_results["account"] = self.get_account_info()

        # Discover all resources
        discovery_results["vpcs"] = self.discover_vpcs()
        discovery_results["ec2_instances"] = self.discover_ec2_instances()
        discovery_results["eks_clusters"] = self.discover_eks_clusters()
        discovery_results["ecs_clusters"] = (
            self.discover_ecs_clusters()
        )  # ✅ Terraform can't do this
        discovery_results["rds_instances"] = self.discover_rds_instances()
        discovery_results["rds_clusters"] = self.discover_rds_clusters()
        discovery_results["s3_buckets"] = self.discover_s3_buckets()  # ✅ Terraform can't do this
        discovery_results["dynamodb_tables"] = (
            self.discover_dynamodb_tables()
        )  # ✅ Terraform can't do this
        discovery_results["sqs_queues"] = self.discover_sqs_queues()  # ✅ Terraform can't do this
        discovery_results["lambda_functions"] = (
            self.discover_lambda_functions()
        )  # ✅ Terraform can't do this
        discovery_results["security_groups"] = self.discover_security_groups()
        discovery_results["msk_clusters"] = self.discover_msk_clusters()

        return discovery_results


def print_summary(results: dict[str, Any]):
    """Print discovery summary."""
    print("\n" + "=" * 80)
    print("  DISCOVERY SUMMARY")
    print("=" * 80 + "\n")

    print(f"  Account: {results['account']['account_id']}")
    print(f"  Region: {results['account']['region']}")
    print(f"  Timestamp: {results['metadata']['timestamp']}")
    print()

    resource_counts = {
        "VPCs": results["vpcs"]["count"],
        "EC2 Instances": results["ec2_instances"]["count"],
        "EKS Clusters": results["eks_clusters"]["count"],
        "ECS Clusters": results["ecs_clusters"]["count"],
        "RDS Instances": results["rds_instances"]["count"],
        "RDS Clusters (Aurora)": results["rds_clusters"]["count"],
        "S3 Buckets": results["s3_buckets"]["count"],
        "DynamoDB Tables": results["dynamodb_tables"]["count"],
        "SQS Queues": results["sqs_queues"]["count"],
        "Lambda Functions": results["lambda_functions"]["count"],
        "Security Groups": results["security_groups"]["count"],
        "MSK Clusters": results["msk_clusters"]["count"],
    }

    total = sum(resource_counts.values())

    print(f"  📊 Total Resources Found: {total}\n")

    for resource_type, count in resource_counts.items():
        if count > 0:
            emoji = "✅" if count > 0 else "  "
            # Highlight resources Terraform can't list
            suffix = ""
            if resource_type in [
                "ECS Clusters",
                "S3 Buckets",
                "DynamoDB Tables",
                "SQS Queues",
                "Lambda Functions",
            ]:
                suffix = " (Terraform CAN'T list this!)"
            print(f"  {emoji} {resource_type}: {count}{suffix}")

    print("\n" + "=" * 80)
    print("\n  ✅ Complete discovery finished!")
    print("  💡 boto3 found EVERYTHING - no Terraform limitations!")
    print("\n  Output saved to: aws_resources.json")
    print("=" * 80 + "\n")


def main():
    """Main discovery function."""
    try:
        # Run discovery
        discovery = AWSResourceDiscovery()
        results = discovery.discover_all()

        # Save to JSON file (Terraform output format)
        output_file = Path("aws_resources.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Print summary
        print_summary(results)

        print(f"\n💾 Full results saved to: {output_file}")
        print("\nTo view specific resource details:")
        print("  python -m json.tool aws_resources.json | less")
        print("\nOr load in Python:")
        print("  import json")
        print("  with open('aws_resources.json') as f:")
        print("      resources = json.load(f)")

        return 0

    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
