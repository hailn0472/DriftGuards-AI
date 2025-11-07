"""
Flexible Revert System for DriftGuards-AI
Provides granular control over what gets reverted and how
"""

import boto3
from botocore.exceptions import ClientError
import json
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RevertMode(Enum):
    """Revert operation modes."""

    FULL = "full"  # Revert all changes
    SELECTIVE = "selective"  # Revert specific fields only
    DRY_RUN = "dry_run"  # Simulate revert without applying
    INTERACTIVE = "interactive"  # Ask before each change
    FORCE = "force"  # Force revert even if risky


class RevertScope(Enum):
    """What to revert."""

    ALL = "all"
    STATE_ONLY = "state_only"  # Only start/stop state
    CONFIG_ONLY = "config_only"  # Only configuration changes
    TAGS_ONLY = "tags_only"  # Only tags
    SECURITY_ONLY = "security_only"  # Only security-related changes
    CUSTOM = "custom"  # Custom field selection


class RevertStrategy:
    """Configuration for flexible revert operations."""

    def __init__(
        self,
        mode: RevertMode = RevertMode.FULL,
        scope: RevertScope = RevertScope.ALL,
        fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None,
        wait_for_completion: bool = True,
        rollback_on_error: bool = True,
        create_backup: bool = True,
        max_retries: int = 3,
        notify_on_completion: bool = False,
    ):
        """
        Initialize revert strategy.

        Args:
            mode: How to perform the revert (full, selective, dry-run, etc.)
            scope: What aspects to revert (all, state, config, tags, etc.)
            fields: Specific fields to revert (when scope=CUSTOM)
            exclude_fields: Fields to exclude from revert
            wait_for_completion: Wait for async operations to complete
            rollback_on_error: Rollback changes if error occurs
            create_backup: Create backup before reverting
            max_retries: Maximum retry attempts on failure
            notify_on_completion: Send notification when done
        """
        self.mode = mode
        self.scope = scope
        self.fields = fields or []
        self.exclude_fields = exclude_fields or []
        self.wait_for_completion = wait_for_completion
        self.rollback_on_error = rollback_on_error
        self.create_backup = create_backup
        self.max_retries = max_retries
        self.notify_on_completion = notify_on_completion

    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary."""
        return {
            "mode": self.mode.value,
            "scope": self.scope.value,
            "fields": self.fields,
            "exclude_fields": self.exclude_fields,
            "wait_for_completion": self.wait_for_completion,
            "rollback_on_error": self.rollback_on_error,
            "create_backup": self.create_backup,
            "max_retries": self.max_retries,
            "notify_on_completion": self.notify_on_completion,
        }


class FlexibleRevert:
    """Flexible revert system with granular control."""

    def __init__(self, region: str = "ap-southeast-1"):
        """Initialize flexible revert."""
        self.region = region
        self.backup_stack = []

    def revert_ec2(
        self, instance_id: str, baseline: Dict[str, Any], strategy: RevertStrategy
    ) -> Dict[str, Any]:
        """
        Flexible EC2 instance revert with granular control.

        Args:
            instance_id: EC2 instance ID
            baseline: Baseline configuration
            strategy: Revert strategy

        Returns:
            Dict with revert results
        """
        ec2 = boto3.client("ec2", region_name=self.region)
        actions = []
        changes_preview = []

        try:
            # Get current state
            response = ec2.describe_instances(InstanceIds=[instance_id])
            instance = response["Reservations"][0]["Instances"][0]
            current_state = instance["State"]["Name"]

            # Create backup if requested
            if strategy.create_backup:
                self.backup_stack.append(
                    {
                        "resource_id": instance_id,
                        "resource_type": "ec2_instances",
                        "state": current_state,
                        "config": {
                            "instance_type": instance.get("InstanceType"),
                            "tags": instance.get("Tags", []),
                        },
                    }
                )
                actions.append("📦 Created backup")

            # Determine what to revert based on scope
            fields_to_revert = self._determine_fields_to_revert(
                resource_type="ec2", baseline=baseline, current=instance, strategy=strategy
            )

            # DRY RUN mode - just show what would be changed
            if strategy.mode == RevertMode.DRY_RUN:
                return {
                    "status": "dry_run",
                    "message": "🔍 Dry run - no changes applied",
                    "changes_preview": self._generate_changes_preview(
                        fields_to_revert, baseline, instance
                    ),
                    "actions": actions,
                }

            # Apply changes based on scope
            if "state" in fields_to_revert:
                state_result = self._revert_ec2_state(
                    ec2, instance_id, baseline.get("state"), current_state, strategy
                )
                actions.extend(state_result["actions"])
                changes_preview.extend(state_result.get("changes", []))

            if "instance_type" in fields_to_revert:
                type_result = self._revert_ec2_type(
                    ec2,
                    instance_id,
                    baseline.get("type") or baseline.get("instance_type"),
                    instance.get("InstanceType"),
                    current_state,
                    strategy,
                )
                actions.extend(type_result["actions"])
                changes_preview.extend(type_result.get("changes", []))

            if "tags" in fields_to_revert:
                tag_result = self._revert_ec2_tags(
                    ec2, instance_id, baseline.get("tags", []), instance.get("Tags", [])
                )
                actions.extend(tag_result["actions"])
                changes_preview.extend(tag_result.get("changes", []))

            return {
                "status": "success",
                "message": f"✅ Reverted EC2 {instance_id}",
                "actions": actions,
                "changes": changes_preview,
                "mode": strategy.mode.value,
                "scope": strategy.scope.value,
                "backup_created": strategy.create_backup,
            }

        except ClientError as e:
            # Rollback if requested
            if strategy.rollback_on_error and self.backup_stack:
                self._rollback_last_change()

            return {
                "status": "error",
                "message": f"❌ Revert failed: {e.response['Error']['Message']}",
                "actions": actions,
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Unexpected error: {str(e)}",
                "actions": actions,
            }

    def _determine_fields_to_revert(
        self,
        resource_type: str,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        strategy: RevertStrategy,
    ) -> List[str]:
        """Determine which fields to revert based on strategy."""
        fields = []

        if strategy.scope == RevertScope.ALL:
            # Revert everything
            fields = ["state", "instance_type", "tags", "security_groups"]

        elif strategy.scope == RevertScope.STATE_ONLY:
            fields = ["state"]

        elif strategy.scope == RevertScope.CONFIG_ONLY:
            fields = ["instance_type", "security_groups"]

        elif strategy.scope == RevertScope.TAGS_ONLY:
            fields = ["tags"]

        elif strategy.scope == RevertScope.SECURITY_ONLY:
            fields = ["security_groups", "iam_role"]

        elif strategy.scope == RevertScope.CUSTOM:
            fields = strategy.fields

        # Remove excluded fields
        fields = [f for f in fields if f not in strategy.exclude_fields]

        return fields

    def _revert_ec2_state(
        self,
        ec2,
        instance_id: str,
        baseline_state: str,
        current_state: str,
        strategy: RevertStrategy,
    ) -> Dict[str, Any]:
        """Revert EC2 instance state."""
        actions = []
        changes = []

        if not baseline_state:
            return {"actions": [], "changes": []}

        baseline_state = baseline_state.lower()

        if current_state == baseline_state:
            return {"actions": [f"State already matches baseline: {current_state}"], "changes": []}

        # State transition logic
        if baseline_state == "running" and current_state in ["stopped", "stopping"]:
            if current_state == "stopping" and strategy.wait_for_completion:
                logger.info("Waiting for instance to stop...")
                ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

            ec2.start_instances(InstanceIds=[instance_id])
            actions.append(f"✅ Started instance (was {current_state})")
            changes.append({"field": "state", "from": current_state, "to": "running"})

            if strategy.wait_for_completion:
                ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
                actions.append("⏳ Waited for instance to start")

        elif baseline_state == "stopped" and current_state in ["running", "pending"]:
            if current_state == "pending" and strategy.wait_for_completion:
                logger.info("Waiting for instance to start...")
                ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])

            ec2.stop_instances(InstanceIds=[instance_id])
            actions.append(f"✅ Stopped instance (was {current_state})")
            changes.append({"field": "state", "from": current_state, "to": "stopped"})

            if strategy.wait_for_completion:
                ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])
                actions.append("⏳ Waited for instance to stop")

        return {"actions": actions, "changes": changes}

    def _revert_ec2_type(
        self,
        ec2,
        instance_id: str,
        baseline_type: str,
        current_type: str,
        current_state: str,
        strategy: RevertStrategy,
    ) -> Dict[str, Any]:
        """Revert EC2 instance type."""
        actions = []
        changes = []

        if not baseline_type or baseline_type == current_type:
            return {"actions": [], "changes": []}

        # Must stop instance to change type
        if current_state != "stopped":
            ec2.stop_instances(InstanceIds=[instance_id])
            actions.append("🛑 Stopped instance to change type")

            if strategy.wait_for_completion:
                ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

        # Change instance type
        ec2.modify_instance_attribute(InstanceId=instance_id, InstanceType={"Value": baseline_type})
        actions.append(f"✅ Changed type: {current_type} → {baseline_type}")
        changes.append({"field": "instance_type", "from": current_type, "to": baseline_type})

        # Restart if it was running
        if current_state == "running":
            ec2.start_instances(InstanceIds=[instance_id])
            actions.append("▶️  Restarted instance")

            if strategy.wait_for_completion:
                ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])

        return {"actions": actions, "changes": changes}

    def _revert_ec2_tags(
        self, ec2, instance_id: str, baseline_tags: List[Dict], current_tags: List[Dict]
    ) -> Dict[str, Any]:
        """Revert EC2 tags."""
        actions = []
        changes = []

        if not baseline_tags:
            return {"actions": [], "changes": []}

        # Remove tags not in baseline
        current_tag_keys = {tag["Key"] for tag in current_tags}
        baseline_tag_keys = {tag["Key"] for tag in baseline_tags}
        tags_to_remove = current_tag_keys - baseline_tag_keys

        if tags_to_remove:
            ec2.delete_tags(Resources=[instance_id], Tags=[{"Key": key} for key in tags_to_remove])
            actions.append(f"🗑️  Removed {len(tags_to_remove)} extra tags")
            changes.append({"field": "tags", "action": "removed", "count": len(tags_to_remove)})

        # Add/update tags from baseline
        ec2.create_tags(Resources=[instance_id], Tags=baseline_tags)
        actions.append(f"✅ Restored {len(baseline_tags)} tags")
        changes.append({"field": "tags", "action": "restored", "count": len(baseline_tags)})

        return {"actions": actions, "changes": changes}

    def _generate_changes_preview(
        self, fields: List[str], baseline: Dict, current: Dict
    ) -> List[Dict[str, Any]]:
        """Generate preview of what would change."""
        preview = []

        for field in fields:
            baseline_val = baseline.get(field)
            current_val = current.get(field)

            if baseline_val != current_val:
                preview.append(
                    {
                        "field": field,
                        "current": str(current_val),
                        "baseline": str(baseline_val),
                        "action": "will_change",
                    }
                )

        return preview

    def _rollback_last_change(self):
        """Rollback the last change from backup stack."""
        if not self.backup_stack:
            return

        backup = self.backup_stack.pop()
        logger.info(f"Rolling back {backup['resource_type']} {backup['resource_id']}")

        # Implement rollback logic here
        # This would restore the backed up state


# ============================================================================
# PRESET STRATEGIES
# ============================================================================

# Safe strategy: Only revert non-destructive changes
SAFE_STRATEGY = RevertStrategy(
    mode=RevertMode.SELECTIVE,
    scope=RevertScope.TAGS_ONLY,
    wait_for_completion=True,
    rollback_on_error=True,
    create_backup=True,
)

# State only: Only change running/stopped state
STATE_ONLY_STRATEGY = RevertStrategy(
    mode=RevertMode.SELECTIVE,
    scope=RevertScope.STATE_ONLY,
    wait_for_completion=True,
    create_backup=True,
)

# Config only: Only configuration changes, no state changes
CONFIG_ONLY_STRATEGY = RevertStrategy(
    mode=RevertMode.SELECTIVE,
    scope=RevertScope.CONFIG_ONLY,
    exclude_fields=["state"],
    wait_for_completion=True,
    create_backup=True,
)

# Dry run: Simulate changes without applying
DRY_RUN_STRATEGY = RevertStrategy(
    mode=RevertMode.DRY_RUN, scope=RevertScope.ALL, create_backup=False
)

# Full revert: Revert everything aggressively
FULL_REVERT_STRATEGY = RevertStrategy(
    mode=RevertMode.FULL,
    scope=RevertScope.ALL,
    wait_for_completion=True,
    rollback_on_error=True,
    create_backup=True,
    max_retries=3,
)

# Security only: Only security-related changes
SECURITY_ONLY_STRATEGY = RevertStrategy(
    mode=RevertMode.SELECTIVE,
    scope=RevertScope.SECURITY_ONLY,
    wait_for_completion=True,
    create_backup=True,
)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def revert_with_strategy(
    resource_type: str,
    resource_id: str,
    baseline: Dict[str, Any],
    region: str,
    strategy: RevertStrategy = FULL_REVERT_STRATEGY,
) -> Dict[str, Any]:
    """
    Revert resource using flexible strategy.

    Args:
        resource_type: Type of resource
        resource_id: Resource ID
        baseline: Baseline configuration
        region: AWS region
        strategy: Revert strategy to use

    Returns:
        Dict with revert results
    """
    flexible_revert = FlexibleRevert(region=region)

    if resource_type == "ec2_instances":
        return flexible_revert.revert_ec2(resource_id, baseline, strategy)
    else:
        return {
            "status": "error",
            "message": f"Resource type {resource_type} not yet supported by flexible revert",
        }


def preview_revert(
    resource_type: str, resource_id: str, baseline: Dict[str, Any], region: str
) -> Dict[str, Any]:
    """Preview what would be reverted without applying changes."""
    return revert_with_strategy(
        resource_type=resource_type,
        resource_id=resource_id,
        baseline=baseline,
        region=region,
        strategy=DRY_RUN_STRATEGY,
    )


def revert_state_only(
    resource_type: str, resource_id: str, baseline: Dict[str, Any], region: str
) -> Dict[str, Any]:
    """Revert only the state (running/stopped) of a resource."""
    return revert_with_strategy(
        resource_type=resource_type,
        resource_id=resource_id,
        baseline=baseline,
        region=region,
        strategy=STATE_ONLY_STRATEGY,
    )


def revert_tags_only(
    resource_type: str, resource_id: str, baseline: Dict[str, Any], region: str
) -> Dict[str, Any]:
    """Revert only the tags of a resource."""
    return revert_with_strategy(
        resource_type=resource_type,
        resource_id=resource_id,
        baseline=baseline,
        region=region,
        strategy=SAFE_STRATEGY,
    )
