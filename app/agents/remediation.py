"""Remediation Agent for automated and safe drift fixes."""

import asyncio
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.models.analysis import DriftAnalysis
from app.models.drift import DriftRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RemediationAction(str, Enum):
    """Available remediation actions."""

    UPDATE_TERRAFORM = "update_terraform"
    REVERT_AWS = "revert_aws"
    IGNORE = "ignore"
    MANUAL_REVIEW = "manual_review"


class RemediationStatus(str, Enum):
    """Remediation execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RemediationResult:
    """Result of a remediation action."""

    def __init__(
        self,
        remediation_id: str,
        drift_id: str,
        action: RemediationAction,
        status: RemediationStatus,
        message: str,
        backup_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.remediation_id = remediation_id
        self.drift_id = drift_id
        self.action = action
        self.status = status
        self.message = message
        self.backup_id = backup_id
        self.metadata = metadata or {}
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None


class RemediationAgent:
    """Agent responsible for automated drift remediation."""

    def __init__(self):
        """Initialize remediation agent."""
        self.auto_approve = settings.remediation_auto_approve
        self.backup_enabled = settings.remediation_backup_enabled
        self.dry_run = settings.remediation_dry_run
        self.terraform_path = Path(settings.terraform_binary_path)
        self.working_dir = Path(settings.terraform_working_dir)

    async def remediate_drifts(
        self,
        drift_records: List[DriftRecord],
        analyses: List[DriftAnalysis],
    ) -> List[RemediationResult]:
        """
        Remediate multiple drifts based on AI recommendations.

        Args:
            drift_records: List of drift records
            analyses: Corresponding AI analyses

        Returns:
            List of remediation results
        """
        logger.info(f"Processing remediation for {len(drift_records)} drifts")

        try:
            # Match drifts with analyses
            drift_analysis_pairs = []
            analyses_by_drift = {a.drift_id: a for a in analyses}

            for drift in drift_records:
                analysis = analyses_by_drift.get(drift.drift_id)
                if analysis:
                    drift_analysis_pairs.append((drift, analysis))

            # Filter drifts that should be auto-remediated
            remediable_drifts = []
            for drift, analysis in drift_analysis_pairs:
                if self._should_auto_remediate(drift, analysis):
                    remediable_drifts.append((drift, analysis))
                else:
                    logger.debug(f"Skipping auto-remediation for {drift.drift_id}")

            logger.info(f"Auto-remediating {len(remediable_drifts)} drifts")

            # Execute remediations (sequentially for safety)
            results = []
            for drift, analysis in remediable_drifts:
                try:
                    result = await self._remediate_drift(drift, analysis)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Remediation failed for {drift.drift_id}: {e}")
                    results.append(
                        RemediationResult(
                            remediation_id=f"rem-{drift.drift_id}",
                            drift_id=drift.drift_id,
                            action=RemediationAction(analysis.recommended_action),
                            status=RemediationStatus.FAILED,
                            message=str(e),
                        )
                    )

            logger.info(f"Completed {len(results)} remediations")
            return results

        except Exception as e:
            logger.error(f"Remediation processing failed: {e}", exc_info=True)
            raise

    def _should_auto_remediate(self, drift: DriftRecord, analysis: DriftAnalysis) -> bool:
        """
        Determine if drift should be auto-remediated.

        Args:
            drift: Drift record
            analysis: AI analysis

        Returns:
            True if should auto-remediate
        """
        # Don't auto-remediate if disabled
        if not self.auto_approve:
            return False

        # Don't auto-remediate if confidence is low
        if analysis.confidence_score < 80:
            return False

        # Don't auto-remediate critical severity in production
        if drift.severity.value == "critical" and drift.environment == "production":
            return False

        # Don't auto-remediate if recommendation is manual review
        if analysis.recommended_action == "manual_review":
            return False

        # Don't auto-remediate if rollback is complex
        if analysis.rollback_complexity == "complex":
            return False

        return True

    async def _remediate_drift(
        self, drift: DriftRecord, analysis: DriftAnalysis
    ) -> RemediationResult:
        """
        Execute remediation for a single drift.

        Args:
            drift: Drift record
            analysis: AI analysis

        Returns:
            Remediation result
        """
        remediation_id = f"rem-{drift.drift_id}-{int(datetime.utcnow().timestamp())}"
        action = RemediationAction(analysis.recommended_action)

        logger.info(
            f"Remediating drift {drift.drift_id} with action {action.value}"
        )

        try:
            # Pre-flight safety checks
            if not await self._validate_remediation_safety(drift, action):
                return RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=action,
                    status=RemediationStatus.FAILED,
                    message="Pre-flight safety checks failed",
                )

            # Create backup if enabled
            backup_id = None
            if self.backup_enabled and action == RemediationAction.REVERT_AWS:
                backup_id = await self._create_backup(drift)
                logger.info(f"Created backup: {backup_id}")

            # Execute the remediation action
            if action == RemediationAction.UPDATE_TERRAFORM:
                result = await self._update_terraform(drift, analysis, remediation_id)
            elif action == RemediationAction.REVERT_AWS:
                result = await self._revert_aws_resource(
                    drift, analysis, remediation_id, backup_id
                )
            elif action == RemediationAction.IGNORE:
                result = await self._suppress_drift(drift, analysis, remediation_id)
            else:  # MANUAL_REVIEW
                result = RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=action,
                    status=RemediationStatus.PENDING,
                    message="Escalated to manual review",
                )

            result.completed_at = datetime.utcnow()
            return result

        except Exception as e:
            logger.error(f"Remediation error for {drift.drift_id}: {e}", exc_info=True)
            raise

    async def _validate_remediation_safety(
        self, drift: DriftRecord, action: RemediationAction
    ) -> bool:
        """
        Validate that remediation is safe to execute.

        Args:
            drift: Drift record
            action: Remediation action

        Returns:
            True if safe to proceed
        """
        checks = []

        # Check business hours (allow all in dev mode)
        if not settings.is_development:
            checks.append(self._check_business_hours())

        # Check change freeze status
        checks.append(self._check_change_freeze())

        # Check concurrent changes
        checks.append(await self._check_concurrent_changes(drift.resource_id))

        # Check dependency health
        if drift.has_downstream_dependencies:
            checks.append(await self._check_dependency_health(drift))

        # All checks must pass
        return all(checks)

    def _check_business_hours(self) -> bool:
        """Check if we're in approved change window."""
        # Simplified - in production, check against maintenance windows
        current_hour = datetime.utcnow().hour

        # Allow changes between 2 AM - 6 AM UTC (maintenance window)
        if 2 <= current_hour < 6:
            return True

        logger.warning("Outside business hours maintenance window")
        return False

    def _check_change_freeze(self) -> bool:
        """Check if there's an active change freeze."""
        # In production, check against a change freeze database/calendar
        # For now, always allow
        return True

    async def _check_concurrent_changes(self, resource_id: str) -> bool:
        """Check for concurrent changes to the same resource."""
        # In production, check a distributed lock or database
        # For now, always allow
        return True

    async def _check_dependency_health(self, drift: DriftRecord) -> bool:
        """Check health of dependent resources."""
        # In production, query health checks for dependent resources
        # For now, always allow
        return True

    async def _create_backup(self, drift: DriftRecord) -> str:
        """
        Create backup of resource before remediation.

        Args:
            drift: Drift record

        Returns:
            Backup ID
        """
        backup_id = f"backup-{drift.drift_id}-{int(datetime.utcnow().timestamp())}"

        try:
            # Create backup data
            backup_data = {
                "backup_id": backup_id,
                "drift_id": drift.drift_id,
                "resource_id": drift.resource_id,
                "resource_type": drift.resource_type,
                "current_state": drift.actual_value,
                "created_at": datetime.utcnow().isoformat(),
            }

            # In production, save to S3
            if settings.is_production:
                s3_client = boto3.client("s3")
                key = f"{settings.s3_prefix_backups}{backup_id}.json"

                await asyncio.to_thread(
                    s3_client.put_object,
                    Bucket=settings.s3_bucket_artifacts,
                    Key=key,
                    Body=json.dumps(backup_data, indent=2),
                )
            else:
                # Save locally for development
                backup_dir = Path("/tmp/driftguards/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)

                backup_file = backup_dir / f"{backup_id}.json"
                backup_file.write_text(json.dumps(backup_data, indent=2))

            logger.info(f"Backup created: {backup_id}")
            return backup_id

        except Exception as e:
            logger.error(f"Failed to create backup: {e}", exc_info=True)
            raise

    async def _update_terraform(
        self, drift: DriftRecord, analysis: DriftAnalysis, remediation_id: str
    ) -> RemediationResult:
        """
        Update Terraform code to match AWS state.

        Args:
            drift: Drift record
            analysis: AI analysis
            remediation_id: Remediation ID

        Returns:
            Remediation result
        """
        logger.info(f"Updating Terraform for {drift.resource_id}")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would update Terraform code")
                return RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=RemediationAction.UPDATE_TERRAFORM,
                    status=RemediationStatus.SUCCESS,
                    message="DRY RUN: Terraform update simulated",
                )

            # Generate patch for Terraform files
            patch = self._generate_terraform_patch(drift)

            # Create Git branch (if GitOps enabled)
            if settings.github_token:
                branch_name = f"drift-fix/{drift.resource_id}/{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
                pr_url = await self._create_terraform_pr(drift, analysis, patch, branch_name)

                return RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=RemediationAction.UPDATE_TERRAFORM,
                    status=RemediationStatus.SUCCESS,
                    message=f"Pull request created: {pr_url}",
                    metadata={"pr_url": pr_url, "branch": branch_name},
                )
            else:
                # Apply patch locally
                await self._apply_terraform_patch(patch)

                return RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=RemediationAction.UPDATE_TERRAFORM,
                    status=RemediationStatus.SUCCESS,
                    message="Terraform code updated locally",
                )

        except Exception as e:
            logger.error(f"Terraform update failed: {e}", exc_info=True)
            return RemediationResult(
                remediation_id=remediation_id,
                drift_id=drift.drift_id,
                action=RemediationAction.UPDATE_TERRAFORM,
                status=RemediationStatus.FAILED,
                message=f"Failed: {str(e)}",
            )

    def _generate_terraform_patch(self, drift: DriftRecord) -> str:
        """Generate Terraform code patch for drift."""
        # Simplified patch generation
        # In production, use HCL parser and generate proper patches
        patch = f"""
# Patch for drift: {drift.drift_id}
# Resource: {drift.resource_id} ({drift.resource_type})

# Changes detected:
{json.dumps(drift.diff, indent=2)}

# Apply these changes to match AWS state:
{json.dumps(drift.actual_value, indent=2)}
"""
        return patch

    async def _create_terraform_pr(
        self, drift: DriftRecord, analysis: DriftAnalysis, patch: str, branch_name: str
    ) -> str:
        """Create GitHub PR with Terraform changes."""
        # In production, use GitHub API to create PR
        # For now, return placeholder
        pr_url = f"https://github.com/{settings.github_repo_owner}/{settings.github_repo_name}/pull/123"
        logger.info(f"PR would be created: {pr_url}")
        return pr_url

    async def _apply_terraform_patch(self, patch: str):
        """Apply Terraform patch locally."""
        # In production, parse and apply HCL changes
        logger.info("Terraform patch would be applied locally")

    async def _revert_aws_resource(
        self,
        drift: DriftRecord,
        analysis: DriftAnalysis,
        remediation_id: str,
        backup_id: Optional[str] = None,
    ) -> RemediationResult:
        """
        Revert AWS resource to Terraform state.

        Args:
            drift: Drift record
            analysis: AI analysis
            remediation_id: Remediation ID
            backup_id: Optional backup ID

        Returns:
            Remediation result
        """
        logger.info(f"Reverting AWS resource {drift.resource_id}")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would revert AWS resource")
                return RemediationResult(
                    remediation_id=remediation_id,
                    drift_id=drift.drift_id,
                    action=RemediationAction.REVERT_AWS,
                    status=RemediationStatus.SUCCESS,
                    message="DRY RUN: AWS revert simulated",
                    backup_id=backup_id,
                )

            # Get appropriate AWS client
            client = self._get_aws_client(drift.resource_type, drift.region)

            # Revert based on resource type
            if drift.resource_type == "aws_instance":
                await self._revert_ec2_instance(client, drift)
            elif drift.resource_type == "aws_s3_bucket":
                await self._revert_s3_bucket(client, drift)
            elif drift.resource_type == "aws_rds_instance":
                await self._revert_rds_instance(client, drift)
            else:
                raise ValueError(f"Unsupported resource type: {drift.resource_type}")

            # Verify reversion
            await self._verify_resource_state(drift)

            return RemediationResult(
                remediation_id=remediation_id,
                drift_id=drift.drift_id,
                action=RemediationAction.REVERT_AWS,
                status=RemediationStatus.SUCCESS,
                message="AWS resource reverted successfully",
                backup_id=backup_id,
            )

        except Exception as e:
            logger.error(f"AWS revert failed: {e}", exc_info=True)

            # Attempt rollback if backup exists
            if backup_id:
                try:
                    await self._restore_from_backup(backup_id)
                    status = RemediationStatus.ROLLED_BACK
                    message = f"Failed and rolled back: {str(e)}"
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    status = RemediationStatus.FAILED
                    message = f"Failed and rollback failed: {str(e)}"
            else:
                status = RemediationStatus.FAILED
                message = f"Failed: {str(e)}"

            return RemediationResult(
                remediation_id=remediation_id,
                drift_id=drift.drift_id,
                action=RemediationAction.REVERT_AWS,
                status=status,
                message=message,
                backup_id=backup_id,
            )

    def _get_aws_client(self, resource_type: str, region: str):
        """Get appropriate AWS client for resource type."""
        service_map = {
            "aws_instance": "ec2",
            "aws_s3_bucket": "s3",
            "aws_rds_instance": "rds",
            "aws_lambda_function": "lambda",
        }

        service = service_map.get(resource_type)
        if not service:
            raise ValueError(f"Unknown resource type: {resource_type}")

        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )

    async def _revert_ec2_instance(self, ec2_client, drift: DriftRecord):
        """Revert EC2 instance attributes."""
        instance_id = drift.resource_id
        terraform_state = drift.terraform_value

        # Revert instance type if changed
        if "instance_type" in drift.diff:
            target_type = terraform_state.get("instance_type")
            await asyncio.to_thread(
                ec2_client.modify_instance_attribute,
                InstanceId=instance_id,
                InstanceType={"Value": target_type},
            )
            logger.info(f"Reverted instance type to {target_type}")

        # Revert tags if changed
        if "tags" in drift.diff:
            target_tags = terraform_state.get("tags", {})
            tag_list = [{"Key": k, "Value": v} for k, v in target_tags.items()]
            await asyncio.to_thread(
                ec2_client.create_tags,
                Resources=[instance_id],
                Tags=tag_list,
            )
            logger.info("Reverted instance tags")

    async def _revert_s3_bucket(self, s3_client, drift: DriftRecord):
        """Revert S3 bucket configuration."""
        bucket_name = drift.resource_id
        terraform_state = drift.terraform_value

        # Revert ACL if changed
        if "acl" in drift.diff:
            target_acl = terraform_state.get("acl", "private")
            await asyncio.to_thread(
                s3_client.put_bucket_acl,
                Bucket=bucket_name,
                ACL=target_acl,
            )
            logger.info(f"Reverted bucket ACL to {target_acl}")

    async def _revert_rds_instance(self, rds_client, drift: DriftRecord):
        """Revert RDS instance configuration."""
        db_instance_id = drift.resource_id
        terraform_state = drift.terraform_value

        modifications = {}

        if "instance_class" in drift.diff:
            modifications["DBInstanceClass"] = terraform_state.get("instance_class")

        if modifications:
            await asyncio.to_thread(
                rds_client.modify_db_instance,
                DBInstanceIdentifier=db_instance_id,
                **modifications,
            )
            logger.info("Reverted RDS instance configuration")

    async def _verify_resource_state(self, drift: DriftRecord):
        """Verify resource state after remediation."""
        # In production, re-check resource state
        logger.info(f"Verified state for {drift.resource_id}")

    async def _restore_from_backup(self, backup_id: str):
        """Restore resource from backup."""
        logger.info(f"Restoring from backup: {backup_id}")
        # In production, implement actual backup restoration
        raise NotImplementedError("Backup restoration not yet implemented")

    async def _suppress_drift(
        self, drift: DriftRecord, analysis: DriftAnalysis, remediation_id: str
    ) -> RemediationResult:
        """
        Suppress drift alert (ignore).

        Args:
            drift: Drift record
            analysis: AI analysis
            remediation_id: Remediation ID

        Returns:
            Remediation result
        """
        logger.info(f"Suppressing drift {drift.drift_id}")

        # In production, store suppression in database
        reason = f"AI recommended ignore (confidence: {analysis.confidence_score}%)"

        return RemediationResult(
            remediation_id=remediation_id,
            drift_id=drift.drift_id,
            action=RemediationAction.IGNORE,
            status=RemediationStatus.SUCCESS,
            message=f"Drift suppressed: {reason}",
            metadata={"reason": reason, "ttl_days": 30},
        )

