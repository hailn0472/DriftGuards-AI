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
        self.baseline_file = Path("data/baseline/baseline_state.json")
        self.approval_log_dir = Path("data/approvals")
        self.approval_log_dir.mkdir(parents=True, exist_ok=True)
    
    async def approve_drift(
        self, 
        drift: DriftRecord, 
        request: ApprovalRequest
    ) -> ApprovalRecord:
        """
        Approve a drift and update baseline.
        
        Steps:
        1. Create approval record
        2. Update drift status
        3. Update baseline state (if requested)
        4. Save audit log
        5. Send notifications (if requested)
        
        Args:
            drift: Drift record to approve
            request: Approval request details
            
        Returns:
            ApprovalRecord with approval details
        """
        logger.info(f"Processing approval for drift {drift.drift_id}")
        
        # Load current baseline
        previous_baseline = self._load_baseline()
        
        # Create approval record
        approval = ApprovalRecord(
            approval_id=f"approval-{uuid.uuid4().hex[:8]}",
            drift_id=drift.drift_id,
            resource_id=drift.resource_id,
            resource_type=drift.resource_type,
            approved_by=request.approved_by,
            approved_at=datetime.utcnow(),
            approval_reason=request.reason,
            previous_baseline=self._get_resource_baseline(
                previous_baseline, drift.resource_id, drift.resource_type
            ),
            new_baseline=drift.actual_value,
            environment=drift.environment,
            tags=drift.tags,
        )
        
        # Update drift record
        drift.status = DriftStatus.RESOLVED
        drift.approved = True
        drift.approved_by = request.approved_by
        drift.approved_at = approval.approved_at
        drift.approval_reason = request.reason
        drift.resolved_at = approval.approved_at
        
        # Update baseline if requested
        if request.update_baseline:
            self._update_baseline(drift, previous_baseline)
            logger.info(f"✅ Baseline updated for {drift.resource_id}")
        
        # Save approval log
        self._save_approval_log(approval)
        logger.info(f"📝 Approval logged: {approval.approval_id}")
        
        # Send notifications if requested
        if request.notify:
            await self._send_approval_notification(drift, approval)
        
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
    
    def _get_resource_baseline(
        self, 
        baseline: dict, 
        resource_id: str, 
        resource_type: str
    ) -> dict:
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
            if resource.get("id") == resource_id:
                return resource
        
        logger.warning(f"Resource {resource_id} not found in baseline")
        return {}
    
    def _update_baseline(self, drift: DriftRecord, current_baseline: dict):
        """Update baseline with approved state."""
        logger.info(f"Updating baseline for drift: {drift.drift_id}")
        logger.info(f"  Resource: {drift.resource_id} ({drift.resource_type})")
        logger.info(f"  Drift type: {drift.drift_type}")
        logger.info(f"  Actual value keys: {list(drift.actual_value.keys())}")
        
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
        
        key = type_mapping.get(drift.resource_type, drift.resource_type)
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
        
        # Find and update resource
        updated = False
        for i, resource in enumerate(resources):
            if resource.get("id") == drift.resource_id:
                # Merge actual_value into baseline
                resources[i] = {**resource, **drift.actual_value}
                updated = True
                logger.info(f"✅ Updated existing resource in baseline: {drift.resource_id}")
                break
        
        # Add if not exists
        if not updated:
            new_resource = {
                "id": drift.resource_id,
                **drift.actual_value
            }
            resources.append(new_resource)
            logger.info(f"✅ Added new resource to baseline: {drift.resource_id}")
            logger.info(f"  Resource data: {json.dumps(new_resource, indent=2)}")
        
        logger.info(f"  Baseline now has {len(resources)} {key}")
        
        # Save updated baseline
        self._save_baseline(current_baseline)
    
    def _save_baseline(self, baseline: dict):
        """Save baseline to file."""
        try:
            # Backup current baseline
            if self.baseline_file.exists():
                backup_file = self.baseline_file.parent / "baseline_state.backup.json"
                backup_file.write_text(self.baseline_file.read_text())
                logger.info(f"Created baseline backup: {backup_file}")
            
            # Save new baseline
            with open(self.baseline_file, 'w') as f:
                json.dump(baseline, f, indent=2)
            
            logger.info(f"Baseline saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            raise
    
    def _save_approval_log(self, approval: ApprovalRecord):
        """Save approval to audit log."""
        try:
            log_file = self.approval_log_dir / f"{approval.approval_id}.json"
            with open(log_file, 'w') as f:
                # Convert datetime objects to string for JSON serialization
                approval_dict = approval.dict()
                approval_dict['approved_at'] = approval_dict['approved_at'].isoformat()
                json.dump(approval_dict, f, indent=2)
            
            logger.info(f"Approval log saved: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save approval log: {e}")
            # Don't raise - approval should succeed even if logging fails
    
    async def _send_approval_notification(
        self, 
        drift: DriftRecord, 
        approval: ApprovalRecord
    ):
        """Send notification about approval."""
        # TODO: Integrate with AlertEngineAgent or SNS
        logger.info(
            f"📢 Approval notification: {drift.resource_id} ({drift.resource_type}) "
            f"approved by {approval.approved_by}"
        )
        if approval.approval_reason:
            logger.info(f"Reason: {approval.approval_reason}")
    
    def get_approval_history(
        self, 
        resource_id: Optional[str] = None,
        limit: int = 50
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
                        if 'approved_at' in data and isinstance(data['approved_at'], str):
                            data['approved_at'] = datetime.fromisoformat(data['approved_at'])
                        
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
                if 'approved_at' in data and isinstance(data['approved_at'], str):
                    data['approved_at'] = datetime.fromisoformat(data['approved_at'])
                
                return ApprovalRecord(**data)
                
        except Exception as e:
            logger.error(f"Failed to get approval {approval_id}: {e}")
            return None
