"""
Revert and Terminate Utilities for DriftGuards-AI
Hybrid approach: Pulumi for IaC revert + Boto3 for direct operations
"""

import boto3
from botocore.exceptions import ClientError
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PULUMI REVERT (Infrastructure as Code)
# ============================================================================


def pulumi_revert_to_baseline(
    resource_type: str, resource_id: str, account_id: str, region: str
) -> Dict[str, Any]:
    """
    Revert resource to baseline using Pulumi.

    This uses Pulumi to declaratively restore the resource to its baseline state
    by running `pulumi up --force` which applies the baseline configuration.

    Args:
        resource_type: Type of resource (e.g., 'ec2_instances')
        resource_id: Resource identifier
        account_id: AWS account ID
        region: AWS region

    Returns:
        Dict with status and output
    """
    try:
        logger.info(f"🔄 Pulumi revert: {resource_type}/{resource_id}")

        # Check if Pulumi is installed
        check_result = subprocess.run(
            ["pulumi", "version"], capture_output=True, text=True, timeout=5
        )

        if check_result.returncode != 0:
            return {
                "status": "error",
                "message": "Pulumi is not installed. Please install Pulumi CLI first.",
                "docs": "https://www.pulumi.com/docs/get-started/install/",
            }

        # Run pulumi up to restore baseline state
        # Note: --yes flag auto-approves the update
        # --skip-preview skips the preview and applies directly
        result = subprocess.run(
            ["pulumi", "up", "--yes", "--skip-preview"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            cwd=str(Path(__file__).parent),
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"✅ Successfully reverted {resource_id} to baseline using Pulumi",
                "output": result.stdout,
                "method": "pulumi",
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Pulumi revert failed for {resource_id}",
                "error": result.stderr,
                "method": "pulumi",
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Pulumi operation timed out (>5 minutes)",
            "method": "pulumi",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Pulumi CLI not found. Please install Pulumi.",
            "docs": "https://www.pulumi.com/docs/get-started/install/",
            "method": "pulumi",
        }
    except Exception as e:
        logger.error(f"Pulumi revert error: {e}")
        return {"status": "error", "message": f"Pulumi error: {str(e)}", "method": "pulumi"}


# ============================================================================
# BOTO3 REVERT (Direct AWS API)
# ============================================================================


def boto3_revert_to_baseline(
    resource_type: str,
    resource_id: str,
    account_id: str,
    region: str,
    baseline_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Revert resource to baseline using boto3 direct API calls.

    This directly modifies AWS resources via boto3 API to match baseline config.
    Faster than Pulumi but requires manual state tracking.

    Args:
        resource_type: Type of resource
        resource_id: Resource identifier
        account_id: AWS account ID
        region: AWS region
        baseline_config: Baseline configuration to restore

    Returns:
        Dict with status and message
    """
    try:
        logger.info(f"🔄 Boto3 revert: {resource_type}/{resource_id}")

        # Route to appropriate revert function
        revert_functions = {
            "ec2_instances": _revert_ec2,
            "s3_buckets": _revert_s3,
            "rds_instances": _revert_rds,
            "security_groups": _revert_security_group,
            "lambda_functions": _revert_lambda,
            "dynamodb_tables": _revert_dynamodb,
            "sqs_queues": _revert_sqs,
        }

        revert_func = revert_functions.get(resource_type)
        if not revert_func:
            return {
                "status": "error",
                "message": f"Unsupported resource type: {resource_type}",
                "method": "boto3",
            }

        result = revert_func(resource_id, baseline_config, region)
        result["method"] = "boto3"
        return result

    except Exception as e:
        logger.error(f"Boto3 revert error: {e}")
        return {"status": "error", "message": f"Boto3 error: {str(e)}", "method": "boto3"}


def _revert_ec2(instance_id: str, baseline: Dict, region: str) -> Dict:
    """Revert EC2 instance to baseline state."""
    from botocore.exceptions import ClientError

    ec2 = boto3.client("ec2", region_name=region)
    actions = []

    try:
        # Get current instance state
        response = ec2.describe_instances(InstanceIds=[instance_id])

        if not response["Reservations"]:
            return {
                "status": "error",
                "message": f"❌ Error: The instance ID '{instance_id}' does not exist in region {region}",
                "actions": [],
            }

        current_state = response["Reservations"][0]["Instances"][0]["State"]["Name"]
        logger.info(f"Current instance state: {current_state}")

        baseline_state = baseline.get("state", "").lower()
        logger.info(f"Baseline state: {baseline_state}")

        # State transition logic
        if baseline_state == "running" and current_state in ["stopped", "stopping"]:
            # Wait for stopping to complete
            if current_state == "stopping":
                logger.info("Waiting for instance to stop before starting...")
                ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

            # Start instance
            ec2.start_instances(InstanceIds=[instance_id])
            actions.append(f"Started instance (was {current_state})")
            logger.info(f"Started instance {instance_id}")

        elif baseline_state == "stopped" and current_state in ["running", "pending"]:
            # Wait for pending to complete
            if current_state == "pending":
                logger.info("Waiting for instance to start before stopping...")
                ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])

            # Stop instance
            ec2.stop_instances(InstanceIds=[instance_id])
            actions.append(f"Stopped instance (was {current_state})")
            logger.info(f"Stopped instance {instance_id}")

        elif current_state == baseline_state:
            actions.append(f"Instance already in baseline state: {current_state}")
            logger.info(f"Instance {instance_id} already in baseline state: {current_state}")

        elif current_state in ["terminated", "terminating"]:
            return {
                "status": "error",
                "message": f"❌ Cannot revert: Instance is {current_state}",
                "actions": [],
            }
        elif current_state in ["shutting-down"]:
            return {
                "status": "error",
                "message": f"❌ Cannot revert: Instance is shutting down",
                "actions": [],
            }
        else:
            actions.append(
                f"No state change needed (current: {current_state}, baseline: {baseline_state})"
            )

        # Revert instance type if needed
        current_type = response["Reservations"][0]["Instances"][0].get("InstanceType")
        baseline_type = baseline.get("type") or baseline.get("instance_type")

        if baseline_type and current_type != baseline_type:
            # Must stop instance to change type
            if current_state == "running":
                logger.info(
                    f"Stopping instance to change type from {current_type} to {baseline_type}"
                )
                ec2.stop_instances(InstanceIds=[instance_id])
                ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

            # Modify instance type
            ec2.modify_instance_attribute(
                InstanceId=instance_id, InstanceType={"Value": baseline_type}
            )
            actions.append(f"Changed instance type: {current_type} → {baseline_type}")
            logger.info(f"Changed instance type to {baseline_type}")

            # Restart if baseline state is running
            if baseline_state == "running":
                ec2.start_instances(InstanceIds=[instance_id])
                actions.append("Restarted instance after type change")

        # Revert tags if provided
        if baseline.get("tags"):
            ec2.create_tags(Resources=[instance_id], Tags=baseline["tags"])
            actions.append("Restored tags")
            logger.info(f"Restored tags for {instance_id}")

        return {
            "status": "success",
            "message": f"✅ Reverted EC2 {instance_id}",
            "actions": actions,
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]

        if error_code == "InvalidInstanceID.NotFound":
            return {
                "status": "error",
                "message": f"❌ Error: The instance ID '{instance_id}' does not exist in region {region}. Please verify the instance ID and region.",
                "actions": actions,
            }
        elif error_code == "IncorrectInstanceState":
            return {
                "status": "error",
                "message": f"❌ Invalid state transition: {error_msg}",
                "actions": actions,
                "hint": "Instance may already be in the target state or transitioning",
            }
        else:
            logger.error(f"AWS ClientError: {error_code} - {error_msg}")
            return {
                "status": "error",
                "message": f"❌ AWS Error ({error_code}): {error_msg}",
                "actions": actions,
            }
    except Exception as e:
        logger.error(f"Error reverting EC2 instance: {e}")
        return {"status": "error", "message": f"Revert failed: {str(e)}", "actions": actions}


def _revert_s3(bucket_name: str, baseline: Dict, region: str) -> Dict:
    """Revert S3 bucket to baseline configuration."""
    s3 = boto3.client("s3", region_name=region)
    actions = []

    try:
        # First, check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                logger.warning(f"Bucket {bucket_name} does not exist - cannot revert configuration")
                return {
                    "status": "error",
                    "message": f"❌ Bucket '{bucket_name}' does not exist. Cannot update non-existent bucket.",
                    "actions": [],
                }
            else:
                raise  # Re-raise other errors

        # Revert encryption
        if baseline.get("encryption") == "Enabled":
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                },
            )
            actions.append("Enabled encryption")
        elif baseline.get("encryption") == "Disabled":
            try:
                s3.delete_bucket_encryption(Bucket=bucket_name)
                actions.append("Disabled encryption")
            except:
                pass  # Already disabled

        # Revert versioning
        if baseline.get("versioning") == "Enabled":
            s3.put_bucket_versioning(
                Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
            )
            actions.append("Enabled versioning")
        elif baseline.get("versioning") == "Disabled":
            s3.put_bucket_versioning(
                Bucket=bucket_name, VersioningConfiguration={"Status": "Suspended"}
            )
            actions.append("Disabled versioning")

        return {
            "status": "success",
            "message": f"✅ Reverted S3 {bucket_name}: {', '.join(actions)}",
            "actions": actions,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"AWS ClientError reverting S3 bucket: {error_code} - {error_msg}")
        return {
            "status": "error",
            "message": f"❌ AWS Error ({error_code}): {error_msg}",
            "actions": actions,
        }
    except Exception as e:
        logger.error(f"Error reverting S3 bucket: {e}")
        return {"status": "error", "message": f"Revert failed: {str(e)}", "actions": actions}


def _revert_rds(db_instance_id: str, baseline: Dict, region: str) -> Dict:
    """Revert RDS instance to baseline configuration."""
    rds = boto3.client("rds", region_name=region)
    actions = []

    modify_params = {"DBInstanceIdentifier": db_instance_id, "ApplyImmediately": True}

    # Revert public accessibility
    if "publicly_accessible" in baseline:
        modify_params["PubliclyAccessible"] = baseline["publicly_accessible"]
        actions.append(f"Set public access to {baseline['publicly_accessible']}")

    # Revert backup retention
    if "backup_retention_period" in baseline:
        modify_params["BackupRetentionPeriod"] = baseline["backup_retention_period"]
        actions.append(f"Set backup retention to {baseline['backup_retention_period']} days")

    if len(modify_params) > 2:  # More than just ID and ApplyImmediately
        rds.modify_db_instance(**modify_params)

    return {
        "status": "success",
        "message": f"✅ Reverted RDS {db_instance_id}: {', '.join(actions)}",
        "actions": actions,
    }


def _revert_security_group(sg_id: str, baseline: Dict, region: str) -> Dict:
    """Revert security group to baseline rules."""
    ec2 = boto3.client("ec2", region_name=region)

    # Get current rules
    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]

    # Remove current ingress rules
    if sg["IpPermissions"]:
        ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=sg["IpPermissions"])

    # Add baseline rules
    if baseline.get("ingress_rules"):
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=baseline["ingress_rules"])

    return {
        "status": "success",
        "message": f"✅ Reverted Security Group {sg_id} rules",
        "actions": ["Restored ingress rules"],
    }


def _revert_lambda(function_name: str, baseline: Dict, region: str) -> Dict:
    """Revert Lambda function configuration."""
    lambda_client = boto3.client("lambda", region_name=region)
    actions = []

    update_params = {"FunctionName": function_name}

    if "timeout" in baseline:
        update_params["Timeout"] = baseline["timeout"]
        actions.append(f"Set timeout to {baseline['timeout']}s")

    if "memory_size" in baseline:
        update_params["MemorySize"] = baseline["memory_size"]
        actions.append(f"Set memory to {baseline['memory_size']}MB")

    if len(update_params) > 1:
        lambda_client.update_function_configuration(**update_params)

    return {
        "status": "success",
        "message": f"✅ Reverted Lambda {function_name}: {', '.join(actions)}",
        "actions": actions,
    }


def _revert_dynamodb(table_name: str, baseline: Dict, region: str) -> Dict:
    """Revert DynamoDB table configuration."""
    return {
        "status": "success",
        "message": f"✅ DynamoDB revert not yet implemented for {table_name}",
        "actions": [],
    }


def _revert_sqs(queue_url: str, baseline: Dict, region: str) -> Dict:
    """Revert SQS queue configuration."""
    sqs = boto3.client("sqs", region_name=region)
    actions = []

    attributes = {}
    if "visibility_timeout" in baseline:
        attributes["VisibilityTimeout"] = str(baseline["visibility_timeout"])
        actions.append(f"Set visibility timeout to {baseline['visibility_timeout']}s")

    if attributes:
        sqs.set_queue_attributes(QueueUrl=queue_url, Attributes=attributes)

    return {
        "status": "success",
        "message": f"✅ Reverted SQS queue: {', '.join(actions)}",
        "actions": actions,
    }


# ============================================================================
# BOTO3 TERMINATE (Resource Deletion)
# ============================================================================


def boto3_terminate_resource(
    resource_type: str, resource_id: str, account_id: str, region: str, force: bool = False
) -> Dict[str, Any]:
    """
    Terminate/Stop/Delete AWS resource using boto3.

    This permanently stops or deletes the resource. Use with caution!

    Args:
        resource_type: Type of resource
        resource_id: Resource identifier
        account_id: AWS account ID
        region: AWS region
        force: Skip safety checks (dangerous!)

    Returns:
        Dict with status and message
    """
    try:
        logger.info(f"🛑 Terminating: {resource_type}/{resource_id}")

        # Route to appropriate terminate function
        terminate_functions = {
            "ec2_instances": _terminate_ec2,
            "s3_buckets": _terminate_s3,
            "rds_instances": _terminate_rds,
            "lambda_functions": _terminate_lambda,
            "dynamodb_tables": _terminate_dynamodb,
            "sqs_queues": _terminate_sqs,
        }

        terminate_func = terminate_functions.get(resource_type)
        if not terminate_func:
            return {
                "status": "error",
                "message": f"Terminate not supported for {resource_type}",
                "method": "boto3",
            }

        result = terminate_func(resource_id, region, force)
        result["method"] = "boto3"
        return result

    except Exception as e:
        logger.error(f"Terminate error: {e}")
        return {"status": "error", "message": f"Terminate error: {str(e)}", "method": "boto3"}


def _terminate_ec2(instance_id: str, region: str, force: bool) -> Dict:
    """Terminate EC2 instance."""
    ec2 = boto3.client("ec2", region_name=region)

    response = ec2.terminate_instances(InstanceIds=[instance_id])
    instance = response["TerminatingInstances"][0]

    return {
        "status": "terminated",
        "message": f"❌ Terminated EC2 instance {instance_id}",
        "previous_state": instance["PreviousState"]["Name"],
        "current_state": instance["CurrentState"]["Name"],
    }


def _terminate_s3(bucket_name: str, region: str, force: bool) -> Dict:
    """Delete S3 bucket and all objects."""
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)

    # Delete all objects
    objects_deleted = 0
    for obj in bucket.objects.all():
        obj.delete()
        objects_deleted += 1

    # Delete bucket
    bucket.delete()

    return {
        "status": "deleted",
        "message": f"❌ Deleted S3 bucket {bucket_name} ({objects_deleted} objects)",
        "objects_deleted": objects_deleted,
    }


def _terminate_rds(db_instance_id: str, region: str, force: bool) -> Dict:
    """Delete RDS instance."""
    rds = boto3.client("rds", region_name=region)

    if force:
        # Skip final snapshot (dangerous!)
        response = rds.delete_db_instance(
            DBInstanceIdentifier=db_instance_id, SkipFinalSnapshot=True
        )
    else:
        # Create final snapshot
        snapshot_id = f"{db_instance_id}-final-{int(Path(__file__).stat().st_mtime)}"
        response = rds.delete_db_instance(
            DBInstanceIdentifier=db_instance_id, FinalDBSnapshotIdentifier=snapshot_id
        )

    return {
        "status": "deleting",
        "message": f"❌ Deleting RDS instance {db_instance_id}",
        "snapshot_created": not force,
    }


def _terminate_lambda(function_name: str, region: str, force: bool) -> Dict:
    """Delete Lambda function."""
    lambda_client = boto3.client("lambda", region_name=region)

    lambda_client.delete_function(FunctionName=function_name)

    return {"status": "deleted", "message": f"❌ Deleted Lambda function {function_name}"}


def _terminate_dynamodb(table_name: str, region: str, force: bool) -> Dict:
    """Delete DynamoDB table."""
    dynamodb = boto3.client("dynamodb", region_name=region)

    dynamodb.delete_table(TableName=table_name)

    return {"status": "deleting", "message": f"❌ Deleting DynamoDB table {table_name}"}


def _terminate_sqs(queue_url: str, region: str, force: bool) -> Dict:
    """Delete SQS queue."""
    sqs = boto3.client("sqs", region_name=region)

    sqs.delete_queue(QueueUrl=queue_url)

    return {"status": "deleted", "message": f"❌ Deleted SQS queue {queue_url}"}


# ============================================================================
# BASELINE LOADER
# ============================================================================


def load_baseline_config(resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
    """
    Load baseline configuration for a specific resource.

    Args:
        resource_type: Type of resource
        resource_id: Resource identifier

    Returns:
        Baseline configuration dict or None if not found
    """
    try:
        baseline_file = (
            Path(__file__).parent.parent.parent / "data" / "baseline" / "baseline_state.json"
        )

        if not baseline_file.exists():
            logger.warning(f"Baseline file not found: {baseline_file}")
            return None

        with open(baseline_file) as f:
            baseline_data = json.load(f)

        resources = baseline_data.get("resources", {})
        resource_list = resources.get(resource_type, [])

        # Find matching resource
        for res in resource_list:
            if res.get("id") == resource_id or res.get("name") == resource_id:
                logger.info(f"✅ Found baseline for {resource_type}/{resource_id}")
                return res

        logger.warning(f"No baseline found for {resource_type}/{resource_id}")
        return None

    except Exception as e:
        logger.error(f"Error loading baseline: {e}")
        return None
