"""Example of running the DriftGuards workflow."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.drift import ScanRequest
from app.workflows import DriftGuardsWorkflow
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Run example workflow."""
    logger.info("Starting DriftGuards workflow example")

    # Create workflow instance
    workflow = DriftGuardsWorkflow()

    # Create scan request
    scan_request = ScanRequest(
        accounts=["123456789012"],
        regions=["us-east-1"],
        resource_types=["aws_instance", "aws_s3_bucket"],
        force_refresh=False,
    )

    logger.info(f"Scan request: {scan_request.dict()}")

    # Run workflow
    try:
        final_state = await workflow.run(scan_request)

        logger.info("\n" + "=" * 80)
        logger.info("WORKFLOW RESULTS")
        logger.info("=" * 80)

        # Print results
        drift_records = final_state.get("drift_records", [])
        logger.info(f"\nDrifts Detected: {len(drift_records)}")
        for drift in drift_records:
            logger.info(f"  - {drift.resource_id} ({drift.resource_type}): {drift.severity.value}")

        analyses = final_state.get("ai_analysis", [])
        logger.info(f"\nAI Analyses: {len(analyses)}")
        for analysis in analyses:
            logger.info(
                f"  - {analysis.resource_id}: {analysis.recommended_action} "
                f"(confidence: {analysis.confidence_score}%)"
            )

        violations = final_state.get("policy_violations", [])
        logger.info(f"\nPolicy Violations: {len(violations)}")
        for violation in violations:
            logger.info(f"  - {violation.policy_id}: {violation.message}")

        alerts = final_state.get("alerts_sent", [])
        logger.info(f"\nAlerts Sent: {len(alerts)}")
        for alert in alerts:
            logger.info(f"  - {alert.alert_id}: {alert.title}")

        remediations = final_state.get("remediations", [])
        logger.info(f"\nRemediations: {len(remediations)}")
        for remediation in remediations:
            logger.info(
                f"  - {remediation.drift_id}: {remediation.action.value} "
                f"-> {remediation.status.value}"
            )

        if final_state.get("error"):
            logger.error(f"\nWorkflow Error: {final_state['error']}")

        logger.info("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

