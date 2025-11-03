"""Detection Agent for drift detection using boto3 and driftctl."""

import asyncio
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agents.boto3_detection import Boto3DriftDetector
from app.config import get_settings
from app.models.drift import DriftRecord, DriftType, ScanRequest, Severity
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DetectionAgent:
    """Agent responsible for detecting infrastructure drift using boto3."""

    def __init__(self):
        """Initialize detection agent."""
        self.driftctl_path = Path(settings.driftctl_binary_path)
        self.working_dir = Path(settings.terraform_working_dir)
        self.boto3_detector = Boto3DriftDetector()  # Replace Terraform with boto3

    async def detect_drift(self, scan_request: ScanRequest) -> list[DriftRecord]:
        """
        Main entry point for drift detection.

        Args:
            scan_request: Scan configuration

        Returns:
            List of detected drift records
        """
        logger.info(f"Starting drift detection scan: {scan_request.dict()}")

        try:
            # Parallel execution for multiple accounts/regions
            tasks = []
            for account_id in scan_request.accounts:
                for region in scan_request.regions:
                    task = self._scan_account_region(
                        account_id=account_id,
                        region=region,
                        resource_types=scan_request.resource_types,
                        force_refresh=scan_request.force_refresh,
                    )
                    tasks.append(task)

            # Execute all scans in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten and filter valid results
            drift_records = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Scan failed with error: {result}")
                    continue
                if isinstance(result, list):
                    drift_records.extend(result)

            logger.info(f"Drift detection complete. Found {len(drift_records)} drifts")
            return drift_records

        except Exception as e:
            logger.error(f"Drift detection failed: {e}", exc_info=True)
            raise

    async def _scan_account_region(
        self,
        account_id: str,
        region: str,
        resource_types: list[str] | None = None,
        force_refresh: bool = False,
    ) -> list[DriftRecord]:
        """
        Scan a specific account and region for drift.

        Args:
            account_id: AWS account ID
            region: AWS region
            resource_types: Optional list of resource types to scan
            force_refresh: Force Terraform state refresh

        Returns:
            List of drift records for this account/region
        """
        logger.info(f"Scanning account {account_id} in region {region}")

        try:
            # Run both boto3 and driftctl scans in parallel
            boto3_task = self._boto3_scan(account_id, region)
            driftctl_task = self._driftctl_scan(account_id, region)

            boto3_drifts, driftctl_drifts = await asyncio.gather(
                boto3_task, driftctl_task, return_exceptions=True
            )

            # Combine and deduplicate results
            all_drifts = []

            if not isinstance(boto3_drifts, Exception):
                all_drifts.extend(boto3_drifts)
            else:
                logger.warning(f"boto3 scan failed: {boto3_drifts}")

            if not isinstance(driftctl_drifts, Exception):
                # Add driftctl drifts that aren't already detected by boto3
                all_drifts.extend(self._deduplicate_drifts(boto3_drifts, driftctl_drifts))
            else:
                logger.warning(f"driftctl scan failed: {driftctl_drifts}")

            # Filter by resource types if specified
            if resource_types:
                all_drifts = [
                    drift for drift in all_drifts if drift.resource_type in resource_types
                ]

            logger.info(f"Found {len(all_drifts)} drifts in {account_id}/{region}")
            return all_drifts

        except Exception as e:
            logger.error(f"Error scanning {account_id}/{region}: {e}", exc_info=True)
            return []

    async def _boto3_scan(self, account_id: str, region: str) -> list[DriftRecord]:
        """
        Perform boto3-based drift detection.

        Args:
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of drift records detected by boto3
        """
        logger.debug(f"Running boto3 scan for {account_id}/{region}")

        try:
            # Step 1: Load baseline (expected) state
            baseline_state = await self.boto3_detector.load_baseline_state()
            if not baseline_state:
                logger.warning("No baseline state found. Creating baseline from current state.")
                await self.boto3_detector.create_baseline(account_id, region)
                return []  # No drift on first run

            # Step 2: Discover current AWS state
            current_state = await self.boto3_detector.discover_current_state(account_id, region)

            # Step 3: Compare and detect drift
            drift_records = await self.boto3_detector.compare_states(
                baseline_state, current_state, account_id, region
            )

            if drift_records:
                logger.info(
                    f"Drift detected by boto3 in {account_id}/{region}: {len(drift_records)} changes"
                )
            else:
                logger.info(f"No drift detected by boto3 in {account_id}/{region}")

            return drift_records

        except Exception as e:
            logger.error(f"boto3 scan error: {e}", exc_info=True)
            raise

    async def _run_terraform_command(
        self, args: list[str], check_exit_code: bool = True
    ) -> tuple[int, str, str]:
        """
        Run a Terraform command.

        Args:
            args: Command arguments
            check_exit_code: Whether to raise on non-zero exit

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        cmd = [str(self.terraform_path)] + args

        logger.debug(f"Running command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir),
        )

        stdout, stderr = await process.communicate()
        exit_code = process.returncode or 0

        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        if check_exit_code and exit_code != 0:
            logger.error(f"Command failed: {stderr_str}")
            raise RuntimeError(f"Terraform command failed: {stderr_str}")

        return exit_code, stdout_str, stderr_str

    async def _parse_terraform_plan(
        self, plan_file: str, account_id: str, region: str
    ) -> list[DriftRecord]:
        """
        Parse Terraform plan output to extract drift records.

        Args:
            plan_file: Path to plan file
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of drift records
        """
        try:
            # Convert plan to JSON
            _, stdout, _ = await self._run_terraform_command(["show", "-json", plan_file])

            plan_data = json.loads(stdout)
            drift_records = []

            # Parse resource changes
            resource_changes = plan_data.get("resource_changes", [])

            for change in resource_changes:
                actions = change.get("change", {}).get("actions", [])

                # Skip create-only actions (not drift)
                if actions == ["create"]:
                    continue

                # Parse drift for update/delete actions
                if "update" in actions or "delete" in actions:
                    drift_record = self._create_drift_from_terraform_change(
                        change, account_id, region
                    )
                    if drift_record:
                        drift_records.append(drift_record)

            return drift_records

        except Exception as e:
            logger.error(f"Error parsing Terraform plan: {e}", exc_info=True)
            return []

    def _create_drift_from_terraform_change(
        self, change: dict[str, Any], account_id: str, region: str
    ) -> DriftRecord | None:
        """
        Create a DriftRecord from a Terraform resource change.

        Args:
            change: Resource change from Terraform plan
            account_id: AWS account ID
            region: AWS region

        Returns:
            DriftRecord or None
        """
        try:
            address = change.get("address", "")
            resource_type = change.get("type", "")

            change_data = change.get("change", {})
            actions = change_data.get("actions", [])
            before = change_data.get("before", {})
            after = change_data.get("after", {})

            # Determine drift type
            if "delete" in actions:
                drift_type = DriftType.DELETED
            elif "update" in actions:
                drift_type = DriftType.MODIFIED
            else:
                drift_type = DriftType.MODIFIED

            # Calculate diff
            diff = self._calculate_diff(before, after)

            # Generate unique drift ID
            drift_id = self._generate_drift_id(address, account_id, region)

            # Determine severity based on change type
            severity = self._calculate_severity(resource_type, diff, drift_type)

            # Extract resource ID from change
            resource_id = self._extract_resource_id(before, after, address)

            return DriftRecord(
                drift_id=drift_id,
                resource_id=resource_id,
                resource_type=resource_type,
                drift_type=drift_type,
                terraform_value=before,
                actual_value=after,
                diff=diff,
                detected_at=datetime.now(datetime.UTC),
                severity=severity,
                account_id=account_id,
                region=region,
                diff_hash=self._hash_diff(diff),
            )

        except Exception as e:
            logger.error(f"Error creating drift record: {e}", exc_info=True)
            return None

    async def _driftctl_scan(self, account_id: str, region: str) -> list[DriftRecord]:
        """
        Perform driftctl-based drift detection.

        Args:
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of drift records detected by driftctl
        """
        logger.debug(f"Running driftctl scan for {account_id}/{region}")

        try:
            # Run driftctl scan
            cmd = [
                str(self.driftctl_path),
                "scan",
                "--output",
                "json",
                "--to",
                f"aws+tf://region={region}",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **subprocess.os.environ,
                    "AWS_REGION": region,
                    "DCTL_CACHE_DIR": settings.driftctl_cache_dir,
                },
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning(f"driftctl scan had issues: {stderr.decode()}")

            # Parse driftctl output
            output = json.loads(stdout.decode())
            drift_records = self._parse_driftctl_output(output, account_id, region)

            return drift_records

        except Exception as e:
            logger.error(f"driftctl scan error: {e}", exc_info=True)
            raise

    def _parse_driftctl_output(
        self, output: dict[str, Any], account_id: str, region: str
    ) -> list[DriftRecord]:
        """
        Parse driftctl JSON output.

        Args:
            output: driftctl JSON output
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of drift records
        """
        drift_records = []

        # Parse unmanaged resources
        unmanaged = output.get("unmanaged", [])
        for resource in unmanaged:
            drift_record = self._create_drift_from_driftctl(
                resource, DriftType.UNMANAGED, account_id, region
            )
            if drift_record:
                drift_records.append(drift_record)

        # Parse missing resources (deleted from AWS)
        missing = output.get("missing", [])
        for resource in missing:
            drift_record = self._create_drift_from_driftctl(
                resource, DriftType.DELETED, account_id, region
            )
            if drift_record:
                drift_records.append(drift_record)

        # Parse changed resources
        changed = output.get("changed", [])
        for resource in changed:
            drift_record = self._create_drift_from_driftctl(
                resource, DriftType.MODIFIED, account_id, region
            )
            if drift_record:
                drift_records.append(drift_record)

        return drift_records

    def _create_drift_from_driftctl(
        self,
        resource: dict[str, Any],
        drift_type: DriftType,
        account_id: str,
        region: str,
    ) -> DriftRecord | None:
        """Create DriftRecord from driftctl resource data."""
        try:
            resource_id = resource.get("id", "")
            resource_type = resource.get("type", "")

            # Get before/after values if available
            terraform_value = resource.get("terraform", {})
            actual_value = resource.get("aws", {})

            diff = resource.get("diff", {})
            if not diff and terraform_value and actual_value:
                diff = self._calculate_diff(terraform_value, actual_value)

            drift_id = self._generate_drift_id(resource_id, account_id, region)
            severity = self._calculate_severity(resource_type, diff, drift_type)

            return DriftRecord(
                drift_id=drift_id,
                resource_id=resource_id,
                resource_type=resource_type,
                drift_type=drift_type,
                terraform_value=terraform_value,
                actual_value=actual_value,
                diff=diff,
                detected_at=datetime.now(datetime.UTC),
                severity=severity,
                account_id=account_id,
                region=region,
                diff_hash=self._hash_diff(diff),
            )

        except Exception as e:
            logger.error(f"Error creating drift from driftctl: {e}", exc_info=True)
            return None

    def _deduplicate_drifts(
        self, terraform_drifts: list[DriftRecord], driftctl_drifts: list[DriftRecord]
    ) -> list[DriftRecord]:
        """
        Deduplicate drifts from multiple sources.

        Args:
            terraform_drifts: Drifts from Terraform
            driftctl_drifts: Drifts from driftctl

        Returns:
            List of unique drifts from driftctl not in terraform
        """
        terraform_ids = {drift.resource_id for drift in terraform_drifts}

        unique_driftctl = [
            drift for drift in driftctl_drifts if drift.resource_id not in terraform_ids
        ]

        return unique_driftctl

    def _calculate_diff(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        """Calculate differences between before and after states."""
        diff = {}

        all_keys = set(before.keys()) | set(after.keys())

        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)

            if before_val != after_val:
                diff[key] = {"before": before_val, "after": after_val}

        return diff

    def _calculate_severity(
        self, _resource_type: str, diff: dict[str, Any], drift_type: DriftType
    ) -> Severity:
        """
        Calculate drift severity based on resource type and changes.

        Args:
            resource_type: Type of resource
            diff: Differences detected
            drift_type: Type of drift

        Returns:
            Severity level
        """
        # Critical severity for deletions
        if drift_type == DriftType.DELETED:
            return Severity.CRITICAL

        # Critical for security-sensitive changes
        security_fields = {"acl", "public", "encryption", "iam", "security_group", "policy"}
        for field in diff.keys():
            if any(sec in field.lower() for sec in security_fields):
                return Severity.CRITICAL

        # High for production resource modifications
        if "instance_type" in diff or "size" in diff:
            return Severity.HIGH

        # High for unmanaged resources
        if drift_type == DriftType.UNMANAGED:
            return Severity.HIGH

        # Medium for tag changes
        if set(diff.keys()) == {"tags"}:
            return Severity.MEDIUM

        # Default to medium
        return Severity.MEDIUM

    def _generate_drift_id(self, resource_id: str, account_id: str, region: str) -> str:
        """Generate unique drift ID."""
        now = datetime.now(datetime.UTC)
        timestamp = now.isoformat()
        unique_string = f"{resource_id}-{account_id}-{region}-{timestamp}"
        hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        return f"drift-{now.strftime('%Y%m%d')}-{hash_suffix}"

    def _hash_diff(self, diff: dict[str, Any]) -> str:
        """Generate hash of diff for deduplication."""
        diff_str = json.dumps(diff, sort_keys=True)
        return hashlib.sha256(diff_str.encode()).hexdigest()

    def _extract_resource_id(
        self, before: dict[str, Any], after: dict[str, Any], address: str
    ) -> str:
        """Extract resource ID from Terraform data."""
        # Try to get ID from before or after
        resource_id = before.get("id") or after.get("id")

        # If no ID, use the Terraform address
        if not resource_id:
            resource_id = address

        return resource_id or "unknown"
