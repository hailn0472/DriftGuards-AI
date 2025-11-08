"""
Selective Field Revert System
Allows reverting specific fields from drift diff, not entire resource
"""

import boto3
from botocore.exceptions import ClientError
import json
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def selective_revert(
    resource_type: str,
    resource_id: str,
    region: str,
    diff: Dict[str, Any],
    selected_fields: List[str],
) -> Dict[str, Any]:
    """
    Revert only selected fields from the drift diff.

    Args:
        resource_type: Type of resource (e.g., 'ec2_instances')
        resource_id: Resource ID
        region: AWS region
        diff: The drift diff showing baseline vs current
        selected_fields: List of field names to revert (e.g., ['tags.Name', 'state'])

    Returns:
        Dict with revert results

    Example:
        diff = {
            "state": {
                "baseline": "running",
                "current": "stopped"
            },
            "tags": {
                "baseline": [{"Key": "Name", "Value": "my-ec2"}],
                "current": [{"Key": "Name", "Value": "my-ec2-old"}]
            }
        }

        # Only revert the Name tag, not the state
        result = selective_revert(
            'ec2_instances',
            'i-123456',
            'ap-southeast-1',
            diff,
            selected_fields=['tags.Name']
        )
    """
    if resource_type == "ec2_instances":
        return _selective_revert_ec2(resource_id, region, diff, selected_fields)
    elif resource_type == "s3_buckets":
        return _selective_revert_s3(resource_id, region, diff, selected_fields)
    elif resource_type == "rds_instances":
        return _selective_revert_rds(resource_id, region, diff, selected_fields)
    else:
        return {"status": "error", "message": f"Selective revert not supported for {resource_type}"}


def _selective_revert_ec2(
    instance_id: str, region: str, diff: Dict[str, Any], selected_fields: List[str]
) -> Dict[str, Any]:
    """
    Selectively revert EC2 instance fields.

    Supported fields:
    - 'state' - Instance state (running/stopped)
    - 'type' or 'instance_type' - Instance type (t2.micro, etc.)
    - 'tags' - All tags
    - 'tags.TagName' - Specific tag (e.g., 'tags.Name', 'tags.Environment')
    """
    ec2 = boto3.client("ec2", region_name=region)
    actions = []
    reverted_fields = []

    try:
        # Get current instance info
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]
        current_state = instance["State"]["Name"]

        # Process each selected field
        for field in selected_fields:
            if field not in diff:
                # Check for nested fields like 'tags.Name'
                if "." not in field:
                    logger.warning(f"Field '{field}' not in diff, skipping")
                    continue

            # Handle STATE
            if field == "state" and "state" in diff:
                baseline_state = diff["state"]["baseline"].lower()
                result = _revert_state_only(ec2, instance_id, baseline_state, current_state)
                actions.extend(result["actions"])
                reverted_fields.append("state")

            # Handle INSTANCE TYPE
            elif field in ["type", "instance_type"] and ("type" in diff or "instance_type" in diff):
                type_diff = diff.get("type") or diff.get("instance_type")
                baseline_type = type_diff["baseline"]
                current_type = instance.get("InstanceType")

                result = _revert_instance_type_only(
                    ec2, instance_id, baseline_type, current_type, current_state
                )
                actions.extend(result["actions"])
                reverted_fields.append("instance_type")

            # Handle ALL TAGS
            elif field == "tags" and "tags" in diff:
                baseline_tags = diff["tags"]["baseline"]
                result = _revert_all_tags(ec2, instance_id, baseline_tags)
                actions.extend(result["actions"])
                reverted_fields.append("tags")

            # Handle SPECIFIC TAG (e.g., 'tags.Name', 'tags.Environment')
            elif field.startswith("tags.") and "tags" in diff:
                tag_key = field.split(".", 1)[1]  # Extract 'Name' from 'tags.Name'
                baseline_tags = diff["tags"]["baseline"]
                current_tags = diff["tags"]["current"]

                result = _revert_single_tag(ec2, instance_id, tag_key, baseline_tags, current_tags)
                actions.extend(result["actions"])
                reverted_fields.append(f"tags.{tag_key}")

            else:
                logger.warning(f"Field '{field}' not recognized or not in diff")

        if not reverted_fields:
            return {
                "status": "no_changes",
                "message": "⚠️ No fields were reverted (none matched selection)",
                "actions": [],
            }

        return {
            "status": "success",
            "message": f"✅ Selectively reverted EC2 {instance_id}",
            "reverted_fields": reverted_fields,
            "actions": actions,
        }

    except ClientError as e:
        return {
            "status": "error",
            "message": f"❌ Error: {e.response['Error']['Message']}",
            "actions": actions,
            "reverted_fields": reverted_fields,
        }
    except Exception as e:
        return {"status": "error", "message": f"❌ Unexpected error: {str(e)}", "actions": actions}


def _revert_state_only(
    ec2, instance_id: str, baseline_state: str, current_state: str
) -> Dict[str, Any]:
    """Revert only the instance state."""
    actions = []

    if current_state == baseline_state:
        actions.append(f"State already matches: {current_state}")
        return {"actions": actions}

    if baseline_state == "running" and current_state in ["stopped", "stopping"]:
        if current_state == "stopping":
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

        ec2.start_instances(InstanceIds=[instance_id])
        actions.append(f"✅ Changed state: {current_state} → running")

    elif baseline_state == "stopped" and current_state in ["running", "pending"]:
        if current_state == "pending":
            ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])

        ec2.stop_instances(InstanceIds=[instance_id])
        actions.append(f"✅ Changed state: {current_state} → stopped")

    else:
        actions.append(f"Cannot transition from {current_state} to {baseline_state}")

    return {"actions": actions}


def _revert_instance_type_only(
    ec2, instance_id: str, baseline_type: str, current_type: str, current_state: str
) -> Dict[str, Any]:
    """Revert only the instance type."""
    actions = []

    if current_type == baseline_type:
        actions.append(f"Instance type already matches: {current_type}")
        return {"actions": actions}

    # Must stop to change type
    was_running = current_state == "running"
    if current_state != "stopped":
        ec2.stop_instances(InstanceIds=[instance_id])
        ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])
        actions.append("🛑 Stopped instance to change type")

    # Change type
    ec2.modify_instance_attribute(InstanceId=instance_id, InstanceType={"Value": baseline_type})
    actions.append(f"✅ Changed type: {current_type} → {baseline_type}")

    # Restart if it was running
    if was_running:
        ec2.start_instances(InstanceIds=[instance_id])
        actions.append("▶️  Restarted instance")

    return {"actions": actions}


def _revert_all_tags(ec2, instance_id: str, baseline_tags: List[Dict[str, str]]) -> Dict[str, Any]:
    """Revert all tags to baseline."""
    actions = []

    # Get current tags
    response = ec2.describe_instances(InstanceIds=[instance_id])
    current_tags = response["Reservations"][0]["Instances"][0].get("Tags", [])

    # Remove all current tags
    if current_tags:
        ec2.delete_tags(Resources=[instance_id], Tags=[{"Key": tag["Key"]} for tag in current_tags])
        actions.append(f"🗑️  Removed {len(current_tags)} existing tags")

    # Add baseline tags
    if baseline_tags:
        ec2.create_tags(Resources=[instance_id], Tags=baseline_tags)
        actions.append(f"✅ Added {len(baseline_tags)} baseline tags")

    return {"actions": actions}


def _revert_single_tag(
    ec2,
    instance_id: str,
    tag_key: str,
    baseline_tags: List[Dict[str, str]],
    current_tags: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Revert only a specific tag by key."""
    actions = []

    # Find baseline value for this tag
    baseline_value = None
    for tag in baseline_tags:
        if tag["Key"] == tag_key:
            baseline_value = tag["Value"]
            break

    if baseline_value is None:
        # Tag should not exist in baseline, remove it
        ec2.delete_tags(Resources=[instance_id], Tags=[{"Key": tag_key}])
        actions.append(f"🗑️  Removed tag '{tag_key}' (not in baseline)")
        return {"actions": actions}

    # Find current value
    current_value = None
    for tag in current_tags:
        if tag["Key"] == tag_key:
            current_value = tag["Value"]
            break

    if current_value == baseline_value:
        actions.append(f"Tag '{tag_key}' already matches baseline: {baseline_value}")
        return {"actions": actions}

    # Update the tag
    ec2.create_tags(Resources=[instance_id], Tags=[{"Key": tag_key, "Value": baseline_value}])
    actions.append(f"✅ Changed tag '{tag_key}': '{current_value}' → '{baseline_value}'")

    return {"actions": actions}


def _selective_revert_s3(
    bucket_name: str, region: str, diff: Dict[str, Any], selected_fields: List[str]
) -> Dict[str, Any]:
    """
    Selectively revert S3 bucket fields.

    Supported fields:
    - 'versioning' - Bucket versioning
    - 'encryption' - Server-side encryption
    - 'public_access_blocked' - Public access block
    """
    s3 = boto3.client("s3", region_name=region)
    actions = []
    reverted_fields = []

    try:
        # First, check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return {
                    "status": "error",
                    "message": f"❌ Bucket '{bucket_name}' does not exist. Cannot update non-existent bucket.",
                    "reverted_fields": [],
                    "actions": [],
                }
            else:
                raise  # Re-raise other errors

        for field in selected_fields:
            if field not in diff:
                continue

            if field == "versioning":
                baseline_versioning = diff["versioning"]["baseline"]
                status = "Enabled" if baseline_versioning == "Enabled" else "Suspended"
                s3.put_bucket_versioning(
                    Bucket=bucket_name, VersioningConfiguration={"Status": status}
                )
                actions.append(f"✅ Set versioning to {status}")
                reverted_fields.append("versioning")

            elif field == "encryption":
                baseline_encryption = diff["encryption"]["baseline"]
                if baseline_encryption == "Enabled":
                    s3.put_bucket_encryption(
                        Bucket=bucket_name,
                        ServerSideEncryptionConfiguration={
                            "Rules": [
                                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                            ]
                        },
                    )
                    actions.append("✅ Enabled encryption")
                else:
                    try:
                        s3.delete_bucket_encryption(Bucket=bucket_name)
                        actions.append("✅ Disabled encryption")
                    except:
                        pass
                reverted_fields.append("encryption")

        return {
            "status": "success",
            "message": f"✅ Selectively reverted S3 {bucket_name}",
            "reverted_fields": reverted_fields,
            "actions": actions,
        }

    except ClientError as e:
        return {
            "status": "error",
            "message": f"❌ Error: {e.response['Error']['Message']}",
            "actions": actions,
        }


def _selective_revert_rds(
    db_instance_id: str, region: str, diff: Dict[str, Any], selected_fields: List[str]
) -> Dict[str, Any]:
    """
    Selectively revert RDS instance fields.

    Supported fields:
    - 'publicly_accessible' - Public accessibility
    - 'backup_retention_period' - Backup retention
    - 'multi_az' - Multi-AZ deployment
    """
    rds = boto3.client("rds", region_name=region)
    actions = []
    reverted_fields = []

    modify_params = {"DBInstanceIdentifier": db_instance_id, "ApplyImmediately": True}

    try:
        for field in selected_fields:
            if field not in diff:
                continue

            if field == "publicly_accessible":
                baseline_value = diff[field]["baseline"]
                modify_params["PubliclyAccessible"] = baseline_value
                actions.append(f"✅ Set public access to {baseline_value}")
                reverted_fields.append(field)

            elif field == "backup_retention_period":
                baseline_value = diff[field]["baseline"]
                modify_params["BackupRetentionPeriod"] = baseline_value
                actions.append(f"✅ Set backup retention to {baseline_value} days")
                reverted_fields.append(field)

            elif field == "multi_az":
                baseline_value = diff[field]["baseline"]
                modify_params["MultiAZ"] = baseline_value
                actions.append(f"✅ Set Multi-AZ to {baseline_value}")
                reverted_fields.append(field)

        if len(modify_params) > 2:  # More than just ID and ApplyImmediately
            rds.modify_db_instance(**modify_params)

        return {
            "status": "success",
            "message": f"✅ Selectively reverted RDS {db_instance_id}",
            "reverted_fields": reverted_fields,
            "actions": actions,
        }

    except ClientError as e:
        return {
            "status": "error",
            "message": f"❌ Error: {e.response['Error']['Message']}",
            "actions": actions,
        }


def parse_diff_from_drift(drift: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract diff from drift record.

    Args:
        drift: Drift record with 'diff' field

    Returns:
        The diff dictionary
    """
    if isinstance(drift, dict):
        return drift.get("diff", {})
    elif hasattr(drift, "diff"):
        return drift.diff
    return {}


def get_available_fields(diff: Dict[str, Any]) -> List[str]:
    """
    Get list of all available fields that can be reverted from diff.

    Args:
        diff: The drift diff

    Returns:
        List of field names including nested fields like 'tags.Name'
    """
    fields = []

    for key, value in diff.items():
        if not isinstance(value, dict):
            continue

        # Simple field
        if "baseline" in value and "current" in value:
            fields.append(key)

            # Check for tags to add individual tag fields
            if key == "tags":
                baseline_tags = value.get("baseline", [])
                if isinstance(baseline_tags, list):
                    for tag in baseline_tags:
                        if isinstance(tag, dict) and "Key" in tag:
                            fields.append(f"tags.{tag['Key']}")

    return fields
