"""Policy Validator Agent for drift policy enforcement using OPA."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.models.analysis import DriftAnalysis
from app.models.drift import DriftRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class PolicyViolation:
    """Policy violation record."""

    def __init__(
        self,
        policy_id: str,
        drift_id: str,
        violation_type: str,
        severity: str,
        message: str,
        action_required: str = "review",
    ):
        self.policy_id = policy_id
        self.drift_id = drift_id
        self.violation_type = violation_type
        self.severity = severity
        self.message = message
        self.action_required = action_required


class PolicyValidatorAgent:
    """Agent responsible for policy validation and risk assessment."""

    def __init__(self):
        """Initialize policy validator agent."""
        self.policy_dir = Path(settings.opa_policy_dir)
        self.opa_enabled = settings.opa_enabled
        self.enforcement_level = settings.policy_enforcement_level

    async def validate_drifts(
        self,
        drift_records: List[DriftRecord],
        analyses: List[DriftAnalysis],
    ) -> List[PolicyViolation]:
        """
        Validate drifts against policies.

        Args:
            drift_records: List of drift records
            analyses: Corresponding AI analyses

        Returns:
            List of policy violations
        """
        logger.info(f"Validating {len(drift_records)} drifts against policies")

        if not self.opa_enabled:
            logger.info("OPA policy validation is disabled")
            return []

        try:
            # Match drifts with their analyses
            drift_analysis_pairs = []
            analyses_by_drift = {a.drift_id: a for a in analyses}

            for drift in drift_records:
                analysis = analyses_by_drift.get(drift.drift_id)
                drift_analysis_pairs.append((drift, analysis))

            # Validate in parallel
            tasks = [
                self._validate_drift(drift, analysis)
                for drift, analysis in drift_analysis_pairs
            ]

            violations_lists = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten violations
            all_violations = []
            for violations in violations_lists:
                if isinstance(violations, Exception):
                    logger.error(f"Policy validation failed: {violations}")
                elif isinstance(violations, list):
                    all_violations.extend(violations)

            logger.info(f"Found {len(all_violations)} policy violations")
            return all_violations

        except Exception as e:
            logger.error(f"Policy validation failed: {e}", exc_info=True)
            raise

    async def _validate_drift(
        self,
        drift: DriftRecord,
        analysis: Optional[DriftAnalysis] = None,
    ) -> List[PolicyViolation]:
        """
        Validate a single drift against all policies.

        Args:
            drift: Drift record
            analysis: Optional AI analysis

        Returns:
            List of policy violations for this drift
        """
        logger.debug(f"Validating drift {drift.drift_id} against policies")

        try:
            violations = []

            # Run OPA policy checks
            if self.opa_enabled:
                opa_violations = await self._run_opa_policies(drift, analysis)
                violations.extend(opa_violations)

            # Run built-in policy checks
            builtin_violations = await self._run_builtin_policies(drift, analysis)
            violations.extend(builtin_violations)

            # Calculate risk score
            risk_score = self._calculate_risk_score(drift, violations)
            logger.debug(f"Drift {drift.drift_id} risk score: {risk_score}")

            return violations

        except Exception as e:
            logger.error(f"Error validating drift {drift.drift_id}: {e}", exc_info=True)
            return []

    async def _run_opa_policies(
        self,
        drift: DriftRecord,
        analysis: Optional[DriftAnalysis] = None,
    ) -> List[PolicyViolation]:
        """
        Run OPA policy engine checks.

        Args:
            drift: Drift record
            analysis: Optional AI analysis

        Returns:
            List of policy violations from OPA
        """
        try:
            # Prepare input data for OPA
            input_data = {
                "resource_id": drift.resource_id,
                "resource_type": drift.resource_type,
                "drift_type": drift.drift_type.value,
                "severity": drift.severity.value,
                "environment": drift.environment or "unknown",
                "terraform_value": drift.terraform_value,
                "actual_value": drift.actual_value,
                "diff": drift.diff,
                "account_id": drift.account_id,
                "region": drift.region,
                "has_downstream_dependencies": drift.has_downstream_dependencies,
            }

            # Add analysis data if available
            if analysis:
                input_data["ai_analysis"] = {
                    "recommended_action": analysis.recommended_action,
                    "confidence_score": analysis.confidence_score,
                    "business_impact": analysis.business_impact,
                }

            # Call OPA (would normally use OPA REST API or library)
            # For now, use simplified policy checks
            violations = []

            # Security policies
            if self._check_security_policy_violation(input_data):
                violations.append(
                    PolicyViolation(
                        policy_id="security-001",
                        drift_id=drift.drift_id,
                        violation_type="security",
                        severity="critical",
                        message="Security-sensitive configuration changed",
                        action_required="block",
                    )
                )

            # Cost policies
            if self._check_cost_policy_violation(input_data, analysis):
                violations.append(
                    PolicyViolation(
                        policy_id="cost-001",
                        drift_id=drift.drift_id,
                        violation_type="cost",
                        severity="high",
                        message="Cost increase exceeds threshold",
                        action_required="review",
                    )
                )

            # Compliance policies
            if self._check_compliance_policy_violation(input_data):
                violations.append(
                    PolicyViolation(
                        policy_id="compliance-001",
                        drift_id=drift.drift_id,
                        violation_type="compliance",
                        severity="high",
                        message="Change violates compliance requirements",
                        action_required="block",
                    )
                )

            # Operational policies
            if self._check_operational_policy_violation(input_data):
                violations.append(
                    PolicyViolation(
                        policy_id="operational-001",
                        drift_id=drift.drift_id,
                        violation_type="operational",
                        severity="medium",
                        message="Change violates operational policies",
                        action_required="review",
                    )
                )

            return violations

        except Exception as e:
            logger.error(f"OPA policy check error: {e}", exc_info=True)
            return []

    async def _run_builtin_policies(
        self,
        drift: DriftRecord,
        analysis: Optional[DriftAnalysis] = None,
    ) -> List[PolicyViolation]:
        """
        Run built-in policy checks (non-OPA).

        Args:
            drift: Drift record
            analysis: Optional AI analysis

        Returns:
            List of policy violations from built-in checks
        """
        violations = []

        try:
            # Check for manual changes in production
            if drift.environment == "production":
                violations.append(
                    PolicyViolation(
                        policy_id="manual-change-production",
                        drift_id=drift.drift_id,
                        violation_type="governance",
                        severity="high",
                        message="Manual changes to production resources are prohibited",
                        action_required="review",
                    )
                )

            # Check for critical severity drifts
            if drift.severity.value == "critical":
                violations.append(
                    PolicyViolation(
                        policy_id="critical-drift-alert",
                        drift_id=drift.drift_id,
                        violation_type="severity",
                        severity="critical",
                        message="Critical severity drift requires immediate attention",
                        action_required="alert",
                    )
                )

            # Check for low confidence AI recommendations
            if analysis and analysis.confidence_score < 50:
                violations.append(
                    PolicyViolation(
                        policy_id="low-confidence-ai",
                        drift_id=drift.drift_id,
                        violation_type="confidence",
                        severity="medium",
                        message="AI analysis has low confidence - manual review required",
                        action_required="review",
                    )
                )

            return violations

        except Exception as e:
            logger.error(f"Built-in policy check error: {e}", exc_info=True)
            return []

    def _check_security_policy_violation(self, input_data: Dict[str, Any]) -> bool:
        """Check if drift violates security policies."""
        # Check for public access changes
        diff = input_data.get("diff", {})
        actual = input_data.get("actual_value", {})

        security_fields = {"acl", "public", "encryption", "iam", "security_group", "policy"}

        # Check if any security-sensitive field changed
        for field in diff.keys():
            if any(sec in field.lower() for sec in security_fields):
                return True

        # Check for public S3 buckets
        if input_data.get("resource_type") == "aws_s3_bucket":
            acl = actual.get("acl", "")
            if "public" in acl.lower():
                return True

        # Check for unencrypted RDS in production
        if input_data.get("resource_type") == "aws_db_instance":
            if input_data.get("environment") == "production":
                if not actual.get("storage_encrypted", False):
                    return True

        return False

    def _check_cost_policy_violation(
        self, input_data: Dict[str, Any], analysis: Optional[DriftAnalysis]
    ) -> bool:
        """Check if drift violates cost policies."""
        # Check for instance type upgrades
        diff = input_data.get("diff", {})

        if "instance_type" in diff:
            # Simple heuristic: check if it's an upgrade
            before = diff["instance_type"].get("before", "")
            after = diff["instance_type"].get("after", "")

            # Check if moving to larger instance family
            if before and after:
                # e.g., t2.micro -> t3.medium
                before_family = before.split(".")[0] if "." in before else ""
                after_family = after.split(".")[0] if "." in after else ""

                # Very simplified check
                if before_family != after_family:
                    return True

        return False

    def _check_compliance_policy_violation(self, input_data: Dict[str, Any]) -> bool:
        """Check if drift violates compliance policies."""
        # Check for required tags
        actual = input_data.get("actual_value", {})
        tags = actual.get("tags", {})

        required_tags = {"Environment", "Owner", "Project"}
        missing_tags = required_tags - set(tags.keys())

        if missing_tags:
            return True

        return False

    def _check_operational_policy_violation(self, input_data: Dict[str, Any]) -> bool:
        """Check if drift violates operational policies."""
        # Check for changes during business hours (simplified)
        # In production, you'd check against change windows

        environment = input_data.get("environment", "")
        drift_type = input_data.get("drift_type", "")

        # Deletions in production require approval
        if environment == "production" and drift_type == "deleted":
            return True

        return False

    def _calculate_risk_score(
        self, drift: DriftRecord, violations: List[PolicyViolation]
    ) -> int:
        """
        Calculate risk score for drift.

        Args:
            drift: Drift record
            violations: List of policy violations

        Returns:
            Risk score (0-100)
        """
        base_score = 0

        # Severity multiplier
        severity_weights = {
            "critical": 40,
            "high": 25,
            "medium": 15,
            "low": 5,
        }
        base_score += severity_weights.get(drift.severity.value, 0)

        # Environment multiplier
        env_multipliers = {
            "production": 2.0,
            "staging": 1.5,
            "development": 1.0,
        }
        multiplier = env_multipliers.get(drift.environment or "development", 1.0)
        base_score = int(base_score * multiplier)

        # Policy violations
        base_score += len(violations) * 10

        # Blast radius
        if drift.has_downstream_dependencies:
            base_score = int(base_score * 1.5)

        # Cap at 100
        return min(base_score, 100)

    def should_block_drift(self, violations: List[PolicyViolation]) -> bool:
        """
        Determine if drift should be blocked based on violations.

        Args:
            violations: List of policy violations

        Returns:
            True if drift should be blocked
        """
        if self.enforcement_level == "ignore":
            return False

        if self.enforcement_level == "warn":
            # Only block critical violations
            return any(
                v.severity == "critical" and v.action_required == "block"
                for v in violations
            )

        if self.enforcement_level == "block":
            # Block any violations that require blocking
            return any(v.action_required == "block" for v in violations)

        return False

