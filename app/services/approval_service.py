"""Service for handling drift approvals."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.approval import ApprovalRecord, ApprovalRequest
from app.models.drift import DriftRecord, DriftStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ApprovalService:
    """Service for handling drift approvals."""

    def __init__(self):
        """Initialize approval service."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.baseline_file = project_root / "data" / "baseline" / "baseline_state.json"
        self.approval_log_dir = project_root / "data" / "approvals"

        # Ensure directories exist
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.approval_log_dir.mkdir(parents=True, exist_ok=True)

    async def approve_drift(self, drift: DriftRecord, request: ApprovalRequest) -> ApprovalRecord:
        """
        Approve a drift and update baseline.

        Steps:
        1. Create approval record
        2. Update drift status
        3. Update baseline state (if requested)
        4. Save audit log
        5. Send notifications (if requested)

        Args:
            drift: Drift record to approve (DriftRecord object or dict)
            request: Approval request details

        Returns:
            ApprovalRecord with approval details
        """
        # Handle both DriftRecord objects and dicts
        if hasattr(drift, "drift_id"):
            drift_id = drift.drift_id
            resource_id = drift.resource_id
            resource_type = drift.resource_type
            actual_value = drift.actual_value
            environment = drift.environment
            tags = drift.tags
            drift_type = str(drift.drift_type) if hasattr(drift, "drift_type") else None
        elif isinstance(drift, dict):
            drift_id = drift.get("drift_id")
            resource_id = drift.get("resource_id")
            resource_type = drift.get("resource_type")
            actual_value = drift.get("actual_value")
            environment = drift.get("environment")
            tags = drift.get("tags")
            drift_type = drift.get("drift_type")
        else:
            raise ValueError("drift must be a DriftRecord object or dict")

        logger.info(f"Processing approval for drift {drift_id}")

        # Load current baseline
        previous_baseline = self._load_baseline()

        # Create approval record
        approval = ApprovalRecord(
            approval_id=f"approval-{uuid.uuid4().hex[:8]}",
            drift_id=drift_id,
            resource_id=resource_id,
            resource_type=resource_type,
            approved_by=request.approved_by,
            approved_at=datetime.utcnow(),
            approval_reason=request.reason,
            previous_baseline=self._get_resource_baseline(
                previous_baseline, resource_id, resource_type
            ),
            new_baseline=actual_value,
            environment=environment,
            tags=tags,
        )

        # Update drift record status (only if it's an object)
        if hasattr(drift, "status"):
            drift.status = DriftStatus.RESOLVED
            drift.approved = True
            drift.approved_by = request.approved_by
            drift.approved_at = approval.approved_at
            drift.approval_reason = request.reason
            drift.resolved_at = approval.approved_at

        # Update baseline if requested
        if request.update_baseline:
            # Check if this is a deleted resource
            if drift_type and "DELETED" in str(drift_type).upper():
                # Remove from baseline for deleted resources
                self._remove_from_baseline(resource_id, resource_type, previous_baseline)
                logger.info(f"✅ Removed deleted resource from baseline: {resource_id}")
            else:
                # Update baseline with new values for modified resources
                self._update_baseline_from_values(
                    resource_id, resource_type, actual_value, previous_baseline
                )
                logger.info(f"✅ Baseline updated for {resource_id}")

        # Save approval log
        self._save_approval_log(approval)
        logger.info(f"📝 Approval logged: {approval.approval_id}")

        # Send notifications if requested
        if request.notify:
            await self._send_approval_notification(resource_id, resource_type, approval)

        logger.info(f"✅ Approval completed: {approval.approval_id}")
        return approval

    def _load_baseline(self) -> dict:
        """Load current baseline state."""
        if not self.baseline_file.exists():
            logger.warning(f"Baseline file not found: {self.baseline_file}")
            return {}

        try:
            with open(self.baseline_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return {}

    def _get_resource_baseline(self, baseline: dict, resource_id: str, resource_type: str) -> dict:
        """Extract specific resource from baseline."""
        # Map resource type to baseline key
        type_mapping = {
            "aws_instance": "ec2_instances",
            "aws_ec2_instance": "ec2_instances",
            "aws_s3_bucket": "s3_buckets",
            "aws_rds_instance": "rds_instances",
            "aws_rds_cluster": "rds_clusters",
            "aws_dynamodb_table": "dynamodb_tables",
            "aws_lambda_function": "lambda_functions",
            "aws_ecs_service": "ecs_services",
        }

        key = type_mapping.get(resource_type, resource_type)
        resources = baseline.get(key, [])

        for resource in resources:
            # Match by id or name
            if resource.get("id") == resource_id or resource.get("name") == resource_id:
                return resource

        logger.warning(f"Resource {resource_id} not found in baseline")
        return {}

    def _update_baseline(self, drift: DriftRecord, current_baseline: dict):
        """Update baseline with approved state."""
        logger.info(f"Updating baseline for drift: {drift.drift_id}")
        logger.info(f"  Resource: {drift.resource_id} ({drift.resource_type})")
        logger.info(f"  Drift type: {drift.drift_type}")
        logger.info(f"  Actual value keys: {list(drift.actual_value.keys())}")

        # Delegate to the value-based method
        self._update_baseline_from_values(
            drift.resource_id, drift.resource_type, drift.actual_value, current_baseline
        )

    def _update_baseline_from_values(
        self, resource_id: str, resource_type: str, actual_value: dict, current_baseline: dict
    ):
        """Update baseline with approved state using extracted values."""
        logger.info(f"Updating baseline for resource: {resource_id}")
        logger.info(f"  Resource type: {resource_type}")
        logger.info(f"  Actual value keys: {list(actual_value.keys())}")

        # Map resource type to baseline key
        type_mapping = {
            "aws_instance": "ec2_instances",
            "aws_ec2_instance": "ec2_instances",
            "aws_s3_bucket": "s3_buckets",
            "aws_rds_instance": "rds_instances",
            "aws_rds_cluster": "rds_clusters",
            "aws_dynamodb_table": "dynamodb_tables",
            "aws_lambda_function": "lambda_functions",
            "aws_ecs_service": "ecs_services",
            "ec2_instances": "ec2_instances",
            "s3_buckets": "s3_buckets",
            "vpcs": "vpcs",
            "security_groups": "security_groups",
        }

        key = type_mapping.get(resource_type, resource_type)
        logger.info(f"  Mapped to baseline key: {key}")

        # Priority: Use nested resources section if it exists, otherwise top-level
        # This prevents creating duplicate locations

        if "resources" in current_baseline and key in current_baseline["resources"]:
            # Use nested resources section
            resources = current_baseline["resources"][key]
            location = "resources section"
        elif key in current_baseline:
            # Use top-level
            resources = current_baseline[key]
            location = "top-level"
        elif "resources" in current_baseline:
            # Create in nested resources section (preferred)
            current_baseline["resources"][key] = []
            resources = current_baseline["resources"][key]
            location = "resources section (new)"
        else:
            # Create at top-level if no resources section exists
            current_baseline[key] = []
            resources = current_baseline[key]
            location = "top-level (new)"

        logger.info(f"  Using {location} for updates")
        logger.info(f"  Current baseline has {len(resources)} {key}")

        # Find and update resource (match by id or name)
        updated = False
        for i, resource in enumerate(resources):
            if resource.get("id") == resource_id or resource.get("name") == resource_id:
                # Merge actual_value into baseline (don't add 'id' if not present)
                resources[i] = {**resource, **actual_value}
                updated = True
                logger.info(f"✅ Updated existing resource in baseline: {resource_id}")
                break

        # Add if not exists
        if not updated:
            # Use actual_value as-is, don't force 'id' field
            new_resource = {**actual_value}
            resources.append(new_resource)
            logger.info(f"✅ Added new resource to baseline: {resource_id}")
            logger.info(f"  Resource data: {json.dumps(new_resource, indent=2)}")

        logger.info(f"  Baseline now has {len(resources)} {key}")

        # Save updated baseline
        self._save_baseline(current_baseline)

    def _remove_from_baseline(self, resource_id: str, resource_type: str, current_baseline: dict):
        """Remove a deleted resource from baseline."""
        logger.info(f"Removing deleted resource from baseline: {resource_id}")
        logger.info(f"  Resource type: {resource_type}")

        # Map resource type to baseline key
        type_mapping = {
            "aws_instance": "ec2_instances",
            "aws_ec2_instance": "ec2_instances",
            "aws_s3_bucket": "s3_buckets",
            "aws_rds_instance": "rds_instances",
            "aws_rds_cluster": "rds_clusters",
            "aws_dynamodb_table": "dynamodb_tables",
            "aws_lambda_function": "lambda_functions",
            "aws_ecs_service": "ecs_services",
            "ec2_instances": "ec2_instances",
            "s3_buckets": "s3_buckets",
            "vpcs": "vpcs",
            "security_groups": "security_groups",
        }

        key = type_mapping.get(resource_type, resource_type)
        logger.info(f"  Mapped to baseline key: {key}")

        # Find the resource list
        resources = None
        location = None

        if "resources" in current_baseline and key in current_baseline["resources"]:
            resources = current_baseline["resources"][key]
            location = "resources section"
        elif key in current_baseline:
            resources = current_baseline[key]
            location = "top-level"

        if resources is None:
            logger.warning(f"Resource list '{key}' not found in baseline")
            return

        logger.info(f"  Found {len(resources)} resources in {location}")

        # Remove all entries matching this resource_id
        initial_count = len(resources)
        resources[:] = [
            r for r in resources if r.get("id") != resource_id and r.get("name") != resource_id
        ]
        removed_count = initial_count - len(resources)

        if removed_count > 0:
            logger.info(f"✅ Removed {removed_count} entry(ies) for resource: {resource_id}")
            logger.info(f"  Baseline now has {len(resources)} {key}")

            # Save updated baseline
            self._save_baseline(current_baseline)
        else:
            logger.warning(f"Resource {resource_id} not found in baseline {key}")

    def _save_baseline(self, baseline: dict):
        """Save baseline to file."""
        try:
            # Ensure directory exists
            self.baseline_file.parent.mkdir(parents=True, exist_ok=True)

            # Backup current baseline
            if self.baseline_file.exists():
                backup_file = self.baseline_file.parent / "baseline_state.backup.json"
                backup_file.write_text(self.baseline_file.read_text())
                logger.info(f"Created baseline backup: {backup_file}")

            # Save new baseline
            with open(self.baseline_file, "w") as f:
                json.dump(baseline, f, indent=2)

            logger.info("Baseline saved successfully")

        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            raise

    def _save_approval_log(self, approval: ApprovalRecord):
        """Save approval to audit log."""
        try:
            log_file = self.approval_log_dir / f"{approval.approval_id}.json"
            with open(log_file, "w") as f:
                # Convert datetime objects to string for JSON serialization
                approval_dict = approval.dict()
                approval_dict["approved_at"] = approval_dict["approved_at"].isoformat()
                json.dump(approval_dict, f, indent=2)

            logger.info(f"Approval log saved: {log_file}")

        except Exception as e:
            logger.error(f"Failed to save approval log: {e}")
            # Don't raise - approval should succeed even if logging fails

    async def _send_approval_notification(
        self, resource_id: str, resource_type: str, approval: ApprovalRecord
    ):
        """Send notification about approval."""
        # TODO: Integrate with AlertEngineAgent or SNS
        logger.info(
            f"📢 Approval notification: {resource_id} ({resource_type}) "
            f"approved by {approval.approved_by}"
        )
        if approval.approval_reason:
            logger.info(f"Reason: {approval.approval_reason}")

    def get_approval_history(
        self, resource_id: Optional[str] = None, limit: int = 50
    ) -> list[ApprovalRecord]:
        """
        Get approval history.

        Args:
            resource_id: Optional filter by resource ID
            limit: Maximum number of records to return

        Returns:
            List of approval records
        """
        approvals = []

        try:
            for log_file in self.approval_log_dir.glob("*.json"):
                try:
                    with open(log_file) as f:
                        data = json.load(f)

                        # Convert ISO string back to datetime
                        if "approved_at" in data and isinstance(data["approved_at"], str):
                            data["approved_at"] = datetime.fromisoformat(data["approved_at"])

                        approval = ApprovalRecord(**data)

                        if resource_id is None or approval.resource_id == resource_id:
                            approvals.append(approval)

                except Exception as e:
                    logger.warning(f"Failed to load approval log {log_file}: {e}")
                    continue

            # Sort by approval time, most recent first
            approvals.sort(key=lambda x: x.approved_at, reverse=True)

            return approvals[:limit]

        except Exception as e:
            logger.error(f"Failed to get approval history: {e}")
            return []

    def get_approval_by_id(self, approval_id: str) -> Optional[ApprovalRecord]:
        """
        Get specific approval record.

        Args:
            approval_id: Approval ID

        Returns:
            ApprovalRecord or None
        """
        try:
            log_file = self.approval_log_dir / f"{approval_id}.json"
            if not log_file.exists():
                return None

            with open(log_file) as f:
                data = json.load(f)

                # Convert ISO string back to datetime
                if "approved_at" in data and isinstance(data["approved_at"], str):
                    data["approved_at"] = datetime.fromisoformat(data["approved_at"])

                return ApprovalRecord(**data)

        except Exception as e:
            logger.error(f"Failed to get approval {approval_id}: {e}")
            return None
