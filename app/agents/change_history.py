"""
Change History Collector
Retrieves AWS CloudTrail and Config history to enrich drift analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from botocore.exceptions import ClientError

from app.services.aws_client import AWSClientFactory

logger = logging.getLogger(__name__)


class ChangeHistoryCollector:
    """Collect change history from CloudTrail and AWS Config."""

    def __init__(self):
        """Initialize change history collector."""
        self.factory = AWSClientFactory()

    def get_cloudtrail_events(
        self,
        resource_id: str,
        resource_type: str,
        region: str,
        lookback_hours: int = 0.5,  # 0.5 hour
    ) -> list[dict[str, Any]]:
        """
        Get CloudTrail events for a resource.

        Args:
            resource_id: Resource ID (e.g., i-12345)
            resource_type: Resource type (ec2_instances, lambda_functions, etc.)
            region: AWS region
            lookback_hours: How far back to look (default 7 days)

        Returns:
            List of CloudTrail events with who/when/what changed
        """
        try:
            cloudtrail = self.factory.get_client("cloudtrail", region=region)

            # Map resource type to CloudTrail event names
            event_names = self._get_event_names_for_resource_type(resource_type)
            if not event_names:
                logger.debug(f"No CloudTrail events mapped for {resource_type}")
                return []

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=lookback_hours)

            # Build lookup attributes - but make them optional
            # Sometimes using LookupAttributes filters out too many events
            lookup_attributes = []

            # For EC2, we'll search more broadly and filter in code
            # CloudTrail's ResourceName filter can miss events where instance is in a list
            use_lookup_filter = False  # Disable for broader search

            if use_lookup_filter and resource_type == "ec2_instances":
                lookup_attributes.append(
                    {
                        "AttributeKey": "ResourceName",
                        "AttributeValue": resource_id,
                    }
                )

            events = []
            next_token = None

            logger.info(
                f"Searching CloudTrail for {resource_type} {resource_id} (last {lookback_hours}h)"
            )

            # CloudTrail pagination
            while True:
                params = {
                    "StartTime": start_time,
                    "EndTime": end_time,
                    "MaxResults": 50,
                }

                if lookup_attributes:
                    params["LookupAttributes"] = lookup_attributes

                if next_token:
                    params["NextToken"] = next_token

                response = cloudtrail.lookup_events(**params)

                for event in response.get("Events", []):
                    # Parse CloudTrail event
                    import json

                    cloud_trail_event = json.loads(event.get("CloudTrailEvent", "{}"))

                    # Check if event is for our resource
                    if self._is_event_for_resource(cloud_trail_event, resource_id, event_names):
                        parsed_event = {
                            "event_name": event.get("EventName"),
                            "event_time": event.get("EventTime").isoformat(),
                            "username": event.get("Username"),
                            "user_identity": cloud_trail_event.get("userIdentity", {}),
                            "source_ip": cloud_trail_event.get("sourceIPAddress"),
                            "user_agent": cloud_trail_event.get("userAgent"),
                            "request_parameters": cloud_trail_event.get("requestParameters", {}),
                            "response_elements": cloud_trail_event.get("responseElements", {}),
                            "error_code": cloud_trail_event.get("errorCode"),
                            "error_message": cloud_trail_event.get("errorMessage"),
                        }
                        events.append(parsed_event)

                next_token = response.get("NextToken")
                if not next_token:
                    break

            logger.info(f"Found {len(events)} CloudTrail events for {resource_id}")
            return events

        except Exception as e:
            logger.warning(f"Could not get CloudTrail events: {e}")
            return []

    def get_config_history(
        self,
        resource_id: str,
        resource_type: str,
        region: str,
        lookback_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get AWS Config history for a resource.

        Args:
            resource_id: Resource ID
            resource_type: Resource type
            region: AWS region
            lookback_days: How far back to look (default 30 days)

        Returns:
            List of configuration changes with before/after values
        """
        try:
            config = self.factory.get_client("config", region=region)

            # Map resource type to AWS Config resource type
            config_resource_type = self._map_to_config_resource_type(resource_type)
            if not config_resource_type:
                logger.debug(f"No Config resource type mapping for {resource_type}")
                return []

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=lookback_days)

            response = config.get_resource_config_history(
                resourceType=config_resource_type,
                resourceId=resource_id,
                laterTime=end_time,
                earlierTime=start_time,
                limit=100,
            )

            config_items = response.get("configurationItems", [])
            changes = []

            # Process each configuration snapshot
            for i, item in enumerate(config_items):
                change = {
                    "capture_time": item.get("configurationItemCaptureTime"),
                    "status": item.get("configurationItemStatus"),
                    "configuration": item.get("configuration", {}),
                    "relationships": item.get("relationships", []),
                    "tags": item.get("tags", {}),
                }

                # Calculate what changed from previous state
                if i < len(config_items) - 1:
                    previous_item = config_items[i + 1]
                    change["changes"] = self._calculate_config_changes(
                        previous_item.get("configuration", {}),
                        item.get("configuration", {}),
                    )

                changes.append(change)

            logger.info(f"Found {len(changes)} Config changes for {resource_id}")
            return changes

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ResourceNotDiscoveredException":
                logger.debug(
                    f"Resource {resource_id} not discovered by AWS Config yet or Config not enabled for {resource_type}"
                )
            else:
                logger.warning(f"Could not get Config history: {e}")
            return []
        except Exception as e:
            logger.warning(f"Could not get Config history: {e}")
            return []

    def get_enriched_history(
        self,
        resource_id: str,
        resource_type: str,
        region: str,
    ) -> dict[str, Any]:
        """
        Get comprehensive change history from both CloudTrail and Config.

        Returns:
            Dict with timeline of changes including who/when/what
        """
        cloudtrail_events = self.get_cloudtrail_events(resource_id, resource_type, region)
        config_history = self.get_config_history(resource_id, resource_type, region)

        # Combine and sort by time
        timeline = []

        for event in cloudtrail_events:
            timeline.append(
                {
                    "source": "cloudtrail",
                    "timestamp": event["event_time"],
                    "event_name": event["event_name"],
                    "user": event["username"],
                    "user_identity": event["user_identity"],
                    "source_ip": event["source_ip"],
                    "changes": event.get("request_parameters", {}),
                }
            )

        for change in config_history:
            timeline.append(
                {
                    "source": "config",
                    "timestamp": change["capture_time"],
                    "status": change["status"],
                    "changes": change.get("changes", {}),
                }
            )

        # Sort by timestamp (newest first)
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "cloudtrail_event_count": len(cloudtrail_events),
            "config_change_count": len(config_history),
            "timeline": timeline,
            "last_modified_by": cloudtrail_events[0]["username"] if cloudtrail_events else None,
            "last_modified_at": timeline[0]["timestamp"] if timeline else None,
        }

    def _get_event_names_for_resource_type(self, resource_type: str) -> list[str]:
        """Map resource type to CloudTrail event names."""
        event_map = {
            "ec2_instances": [
                "RunInstances",
                "StartInstances",
                "StopInstances",
                "TerminateInstances",
                "ModifyInstanceAttribute",
                "CreateTags",
                "DeleteTags",
                "AttachVolume",
                "DetachVolume",
                "AssociateAddress",
                "DisassociateAddress",
            ],
            "lambda_functions": [
                "CreateFunction",
                "UpdateFunctionConfiguration",
                "UpdateFunctionCode",
                "DeleteFunction",
                "PutFunctionConcurrency",
                "TagResource",
                "UntagResource",
            ],
            "rds_instances": [
                "CreateDBInstance",
                "ModifyDBInstance",
                "DeleteDBInstance",
                "StartDBInstance",
                "StopDBInstance",
                "AddTagsToResource",
                "RemoveTagsFromResource",
            ],
            "s3_buckets": [
                "CreateBucket",
                "DeleteBucket",
                "PutBucketVersioning",
                "PutBucketEncryption",
                "DeleteBucketEncryption",
                "PutPublicAccessBlock",
                "PutBucketTagging",
            ],
        }
        return event_map.get(resource_type, [])

    def _map_to_config_resource_type(self, terraform_type: str) -> str | None:
        """Map resource type to AWS Config resource type."""
        mapping = {
            "ec2_instances": "AWS::EC2::Instance",
            "s3_buckets": "AWS::S3::Bucket",
            "rds_instances": "AWS::RDS::DBInstance",
            "lambda_functions": "AWS::Lambda::Function",
            "security_groups": "AWS::EC2::SecurityGroup",
        }
        return mapping.get(terraform_type)

    def _is_event_for_resource(
        self,
        event: dict[str, Any],
        resource_id: str,
        event_names: list[str],
    ) -> bool:
        """Check if CloudTrail event is for the specified resource."""
        event_name = event.get("eventName")
        if event_name not in event_names:
            return False

        # Check if resource ID is in the event
        request_params = event.get("requestParameters", {})
        response_elements = event.get("responseElements", {})

        # Helper function to recursively search for resource ID in nested structures
        def contains_resource_id(obj: Any) -> bool:
            """Recursively search for resource ID in any nested structure."""
            if obj == resource_id:
                return True
            if isinstance(obj, dict):
                return any(contains_resource_id(v) for v in obj.values())
            if isinstance(obj, list):
                return any(contains_resource_id(item) for item in obj)
            if isinstance(obj, str):
                return resource_id in obj
            return False

        # Check both request parameters and response elements
        if contains_resource_id(request_params) or contains_resource_id(response_elements):
            logger.debug(f"Event {event_name} matched resource {resource_id}")
            return True

        # Also check resources field (for some events)
        resources = event.get("resources", [])
        for resource in resources:
            resource_arn = resource.get("ARN", "")
            resource_name = resource.get("ResourceName", "")
            if resource_id in resource_arn or resource_id == resource_name:
                logger.debug(f"Event {event_name} matched resource {resource_id} via ARN/Name")
                return True

        return False

    def _calculate_config_changes(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate what changed between two Config snapshots."""
        changes = {}

        all_keys = set(previous.keys()) | set(current.keys())

        for key in all_keys:
            prev_val = previous.get(key)
            curr_val = current.get(key)

            if prev_val != curr_val:
                changes[key] = {
                    "from": prev_val,
                    "to": curr_val,
                }

        return changes

    def format_history_for_ai(self, history: dict[str, Any]) -> str:
        """
        Format change history as human-readable text for AI analysis.

        Args:
            history: Change history from get_enriched_history()

        Returns:
            Formatted string for AI prompt
        """
        if not history.get("timeline"):
            return "No change history available."

        lines = [
            f"Change History for {history['resource_id']}:",
            f"Total Events: {history['cloudtrail_event_count']} CloudTrail, {history['config_change_count']} Config",
            "",
        ]

        if history.get("last_modified_by"):
            lines.append(f"Last Modified By: {history['last_modified_by']}")
            lines.append(f"Last Modified At: {history['last_modified_at']}")
            lines.append("")

        lines.append("Recent Changes (newest first):")

        # Show last 10 events
        for event in history["timeline"][:10]:
            timestamp = event["timestamp"]
            source = event["source"].upper()

            if source == "CLOUDTRAIL":
                user = event.get("user", "Unknown")
                event_name = event.get("event_name", "Unknown")
                source_ip = event.get("source_ip", "N/A")
                lines.append(f"  [{timestamp}] {event_name}")
                lines.append(f"    User: {user} from {source_ip}")

                if event.get("changes"):
                    lines.append(f"    Changes: {event['changes']}")

            else:  # CONFIG
                if event.get("changes"):
                    lines.append(f"  [{timestamp}] Configuration Changed")
                    for field, change in event["changes"].items():
                        lines.append(f"    • {field}: {change.get('from')} → {change.get('to')}")

            lines.append("")

        return "\n".join(lines)
