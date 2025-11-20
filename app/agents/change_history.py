"""
Change History Collector
Retrieves AWS CloudTrail and Config history to enrich drift analysis
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from app.services.aws_client import AWSClientFactory

logger = logging.getLogger(__name__)

# Debug file for change history
DEBUG_DIR = Path(__file__).parent.parent.parent / "data" / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


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
        lookback_hours: int = 24,  # 24 hours - optimized for performance
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
        debug_data = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "region": region,
            "lookback_hours": lookback_hours,
            "search_started_at": datetime.utcnow().isoformat(),
        }

        try:
            cloudtrail = self.factory.get_client("cloudtrail", region=region)

            # Map resource type to CloudTrail event names
            event_names = self._get_event_names_for_resource_type(resource_type)
            if not event_names:
                logger.debug(f"No CloudTrail events mapped for {resource_type}")
                debug_data["error"] = f"No event names mapped for {resource_type}"
                self._save_debug_file(resource_id, debug_data)
                return []

            debug_data["event_names_searched"] = event_names

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=lookback_hours)

            debug_data["time_range"] = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            }

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
            all_raw_events = []  # Store all events for debug
            next_token = None

            logger.debug(
                f"Searching CloudTrail for {resource_type} {resource_id} (last {lookback_hours}h)"
            )

            # CloudTrail pagination
            page_count = 0
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
                page_count += 1

                for event in response.get("Events", []):
                    # Parse CloudTrail event
                    cloud_trail_event = json.loads(event.get("CloudTrailEvent", "{}"))

                    # Store all events for debug
                    all_raw_events.append(
                        {
                            "event_name": event.get("EventName"),
                            "event_time": event.get("EventTime").isoformat()
                            if event.get("EventTime")
                            else None,
                            "username": event.get("Username"),
                            "resources": event.get("Resources", []),
                            "cloud_trail_event": cloud_trail_event,
                        }
                    )

                    # Check if event is for our resource
                    if self._is_event_for_resource(cloud_trail_event, resource_id, event_names):
                        parsed_event = {
                            "event_name": event.get("EventName"),
                            "event_time": event.get("EventTime").isoformat()
                            if event.get("EventTime")
                            else None,
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

            debug_data["pages_fetched"] = page_count
            debug_data["total_events_scanned"] = len(all_raw_events)
            debug_data["matched_events_count"] = len(events)
            debug_data["all_raw_events"] = all_raw_events[:100]  # First 100 for debug
            debug_data["matched_events"] = events

            logger.debug(
                f"Found {len(events)} CloudTrail events for {resource_id} "
                f"(scanned {len(all_raw_events)} total events)"
            )

            # Save debug file only if events found or error
            if events or len(all_raw_events) > 0:
                self._save_debug_file(resource_id, debug_data)

            return events

        except Exception as e:
            logger.warning(f"Could not get CloudTrail events: {e}")
            debug_data["error"] = str(e)
            debug_data["error_type"] = type(e).__name__
            self._save_debug_file(resource_id, debug_data)
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
        diff: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Get comprehensive change history from both CloudTrail and Config.
        If diff is provided, will try to find the specific event that caused the drift.

        Args:
            resource_id: Resource ID
            resource_type: Resource type
            region: AWS region
            diff: Optional drift diff to match against specific events

        Returns:
            Dict with timeline of changes including who/when/what
        """
        logger.debug(f"Getting enriched history for {resource_id} ({resource_type})")

        cloudtrail_events = self.get_cloudtrail_events(resource_id, resource_type, region)
        config_history = self.get_config_history(resource_id, resource_type, region)

        logger.debug(
            f"Retrieved {len(cloudtrail_events)} CloudTrail events and "
            f"{len(config_history)} Config changes for {resource_id}"
        )

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

        # Try to find the specific event that caused the drift
        drift_causing_event = None
        if diff and cloudtrail_events:
            drift_causing_event = self._find_drift_causing_event(cloudtrail_events, diff)
        elif not cloudtrail_events:
            logger.debug(f"No CloudTrail events found for {resource_id} in last 24h")

        # Determine who made the change
        if drift_causing_event:
            last_modified_by = drift_causing_event["username"]
            last_modified_at = drift_causing_event["event_time"]
            logger.info(
                f"✓ Drift caused by: {last_modified_by} at {last_modified_at} "
                f"({drift_causing_event['event_name']})"
            )
        else:
            last_modified_by = cloudtrail_events[0]["username"] if cloudtrail_events else None
            last_modified_at = timeline[0]["timestamp"] if timeline else None
            if last_modified_by:
                logger.debug(f"Using most recent event by: {last_modified_by}")

        enriched_history = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "cloudtrail_event_count": len(cloudtrail_events),
            "config_change_count": len(config_history),
            "timeline": timeline,
            "last_modified_by": last_modified_by,
            "last_modified_at": last_modified_at,
            "drift_causing_event": drift_causing_event,  # NEW: specific event that caused drift
        }

        # Save enriched history debug file only if we found events
        if cloudtrail_events or config_history:
            debug_data = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "region": region,
                "enriched_at": datetime.utcnow().isoformat(),
                "diff_provided": diff,
                "enriched_history": enriched_history,
            }
            self._save_debug_file(f"{resource_id}_enriched", debug_data)

        logger.debug(
            f"Enriched history for {resource_id}: "
            f"last_modified_by={enriched_history.get('last_modified_by')}, "
            f"timeline_count={len(timeline)}"
        )

        return enriched_history

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

    def _find_drift_causing_event(
        self, cloudtrail_events: list[dict[str, Any]], diff: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Find the specific CloudTrail event that caused the drift.

        Args:
            cloudtrail_events: List of CloudTrail events
            diff: Drift diff with baseline and current values

        Returns:
            The event that caused the drift, or None
        """
        logger.debug(f"Searching for drift-causing event in {len(cloudtrail_events)} events")
        logger.debug(f"Drift diff keys: {list(diff.keys())}")

        for event in cloudtrail_events:
            event_name = event.get("event_name")
            request_params = event.get("request_parameters", {})

            # Check if this event matches the drift
            if self._event_matches_drift(event_name, request_params, diff):
                logger.debug(f"✓ Matched event: {event_name} at {event.get('event_time')}")
                return event

        logger.debug("No specific drift-causing event found, using most recent")
        return None

    def _event_matches_drift(
        self, event_name: str, request_params: dict[str, Any], diff: dict[str, Any]
    ) -> bool:
        """
        Check if a CloudTrail event matches the drift changes.

        Args:
            event_name: CloudTrail event name
            request_params: Event request parameters
            diff: Drift diff

        Returns:
            True if event matches the drift
        """
        # Handle tag changes (most common drift)
        if "tags" in diff or "Name" in diff:
            if event_name == "CreateTags":
                # Check if the new tag value matches current value in diff
                tag_set = request_params.get("tagSet", {}).get("items", [])
                for tag in tag_set:
                    tag_key = tag.get("key")
                    tag_value = tag.get("value")

                    # Check if this tag change matches the drift
                    if tag_key in diff:
                        current_val = diff[tag_key].get("current")
                        if tag_value == current_val:
                            logger.debug(
                                f"Tag match: {tag_key}={tag_value} matches drift current value"
                            )
                            return True

                    # Also check nested tags structure
                    if "tags" in diff:
                        tags_diff = diff["tags"]
                        if isinstance(tags_diff, dict):
                            current_tags = tags_diff.get("current", {})
                            if isinstance(current_tags, dict) and current_tags.get(
                                tag_key
                            ) == tag_value:
                                logger.debug(
                                    f"Nested tag match: {tag_key}={tag_value} matches drift"
                                )
                                return True

        # Handle instance type changes
        if "type" in diff or "instance_type" in diff:
            if event_name == "ModifyInstanceAttribute":
                instance_type = request_params.get("instanceType", {}).get("value")
                if instance_type:
                    current_type = diff.get("type", {}).get("current") or diff.get(
                        "instance_type", {}
                    ).get("current")
                    if instance_type == current_type:
                        logger.debug(f"Instance type match: {instance_type}")
                        return True

        # Handle security group changes
        if "security_groups" in diff:
            if event_name in ["ModifyInstanceAttribute", "ModifyNetworkInterfaceAttribute"]:
                # Check if security groups in request match current state
                groups = request_params.get("groupSet", {}).get("items", [])
                if groups:
                    current_sgs = diff["security_groups"].get("current", [])
                    # Simple check: if any group ID matches
                    for group in groups:
                        group_id = group.get("groupId")
                        if any(sg.get("id") == group_id for sg in current_sgs):
                            logger.debug(f"Security group match: {group_id}")
                            return True

        # Handle IAM profile changes
        if "iam_profile" in diff:
            if event_name == "AssociateIamInstanceProfile":
                iam_profile = request_params.get("iamInstanceProfile", {})
                profile_name = iam_profile.get("name") or iam_profile.get("arn", "").split("/")[
                    -1
                ]
                current_profile = diff["iam_profile"].get("current")
                if profile_name == current_profile:
                    logger.debug(f"IAM profile match: {profile_name}")
                    return True

        # Handle volume changes
        if "volumes" in diff:
            if event_name in ["AttachVolume", "DetachVolume", "ModifyVolume"]:
                # Check if volume ID in request matches any volume in diff
                volume_id = request_params.get("volumeId")
                if volume_id:
                    current_volumes = diff["volumes"].get("current", [])
                    if any(vol.get("id") == volume_id for vol in current_volumes):
                        logger.debug(f"Volume match: {volume_id}")
                        return True

        # Handle EBS optimized changes
        if "ebs_optimized" in diff:
            if event_name == "ModifyInstanceAttribute":
                ebs_optimized = request_params.get("ebsOptimized", {}).get("value")
                if ebs_optimized is not None:
                    current_val = diff["ebs_optimized"].get("current")
                    if ebs_optimized == current_val:
                        logger.debug(f"EBS optimized match: {ebs_optimized}")
                        return True

        return False

    def _save_debug_file(self, resource_id: str, debug_data: dict[str, Any]) -> None:
        """Save debug data to file for troubleshooting."""
        try:
            # Sanitize resource_id for filename
            safe_resource_id = resource_id.replace("/", "_").replace(":", "_")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            debug_file = DEBUG_DIR / f"change_history_{safe_resource_id}_{timestamp}.json"

            with open(debug_file, "w") as f:
                json.dump(debug_data, f, indent=2, default=str)

            logger.debug(f"Debug data saved to {debug_file}")
        except Exception as e:
            logger.warning(f"Could not save debug file: {e}")

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
