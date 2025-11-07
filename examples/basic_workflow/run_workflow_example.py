"""Example of running the DriftGuards workflow."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.drift import ScanRequest
from app.workflows import DriftGuardsWorkflow
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    """Run example workflow."""
    logger.info("Starting DriftGuards workflow example")

    # Create workflow instance
    workflow = DriftGuardsWorkflow()

    # Create scan request
    scan_request = ScanRequest(
        accounts=["123456789012"],
        regions=["us-east-1"],
        resource_types=["ec2_instances", "s3_buckets"],
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

        # alerts = final_state.get("alerts_sent", [])
        # logger.info(f"\nAlerts Sent: {len(alerts)}")
        # for alert in alerts:
        #     logger.info(f"  - {alert.alert_id}: {alert.title}")

        # remediations = final_state.get("remediations", [])
        # logger.info(f"\nRemediations: {len(remediations)}")
        # for remediation in remediations:
        #     logger.info(
        #         f"  - {remediation.drift_id}: {remediation.action.value} "
        #         f"-> {remediation.status.value}"
        #     )

        if final_state.get("error"):
            logger.error(f"\nWorkflow Error: {final_state['error']}")

        logger.info("\n" + "=" * 80)

        # Save results to JSON files
        logger.info("Saving results to output directory...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detection results
        detection_file = OUTPUT_DIR / f"detection_results_{timestamp}.json"
        detection_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "scan_request": scan_request.dict(),
                "total_drifts": len(drift_records),
            },
            "drifts": [
                {
                    "drift_id": d.drift_id,
                    "resource_id": d.resource_id,
                    "resource_type": d.resource_type,
                    "drift_type": d.drift_type.value,
                    "severity": d.severity.value,
                    "account_id": d.account_id,
                    "region": d.region,
                    "detected_at": d.detected_at.isoformat(),
                    "terraform_value": d.terraform_value,
                    "actual_value": d.actual_value,
                    "diff": d.diff,
                }
                for d in drift_records
            ],
        }
        with open(detection_file, "w", encoding="utf-8") as f:
            json.dump(detection_data, f, indent=2, default=str)
        logger.info(f"✅ Detection results saved: {detection_file}")

        # Save AI analysis results
        if analyses:
            analysis_file = OUTPUT_DIR / f"analysis_results_{timestamp}.json"
            analysis_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_analyses": len(analyses),
                },
                "analyses": [
                    {
                        "analysis_id": a.analysis_id,
                        "resource_id": a.resource_id,
                        "drift_id": a.drift_id,
                        "explanation": a.explanation,
                        "root_cause": a.root_cause,
                        "business_impact": a.business_impact,
                        "recommended_action": a.recommended_action,
                        "confidence_score": a.confidence_score,
                        "severity": a.severity,
                        "estimated_fix_time": a.estimated_fix_time,
                        "rollback_complexity": a.rollback_complexity,
                        "blast_radius": a.blast_radius,
                        "remediation_steps": a.remediation_steps,
                        "analyzed_at": a.analyzed_at.isoformat(),
                        "model_id": a.model_id,
                    }
                    for a in analyses
                ],
            }
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(analysis_data, f, indent=2, default=str)
            logger.info(f"✅ AI analysis results saved: {analysis_file}")

        # Save policy violations
        if violations:
            violations_file = OUTPUT_DIR / f"policy_violations_{timestamp}.json"
            violations_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_violations": len(violations),
                },
                "violations": [
                    {
                        "policy_id": v.policy_id,
                        "drift_id": v.drift_id,
                        "violation_type": v.violation_type,
                        "severity": v.severity,
                        "message": v.message,
                        "action_required": v.action_required,
                    }
                    for v in violations
                ],
            }
            with open(violations_file, "w", encoding="utf-8") as f:
                json.dump(violations_data, f, indent=2, default=str)
            logger.info(f"✅ Policy violations saved: {violations_file}")

        # Save metrics context
        metrics_contexts = final_state.get("metrics_context", [])
        if metrics_contexts:
            metrics_file = OUTPUT_DIR / f"metrics_context_{timestamp}.json"
            metrics_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_resources": len(metrics_contexts),
                },
                "metrics": [
                    {
                        "resource_id": m.resource_id,
                        "resource_type": m.resource_type,
                        "cloudwatch_metrics": {
                            name: {
                                "metric_name": metric.metric_name,
                                "namespace": metric.namespace,
                                "statistics": metric.statistics,
                                "unit": metric.unit,
                            }
                            for name, metric in m.cloudwatch_metrics.items()
                        },
                        "config_history": [
                            {
                                "change_id": ch.change_id,
                                "timestamp": ch.timestamp.isoformat(),
                                "user": ch.user,
                                "action": ch.action,
                                "compliance_type": ch.compliance_type,
                            }
                            for ch in m.config_history
                        ],
                        "cost_data": {
                            "current_cost": m.cost_data.current_cost,
                            "projected_cost": m.cost_data.projected_cost,
                            "cost_change": m.cost_data.cost_change,
                            "cost_change_percent": m.cost_data.cost_change_percent,
                        }
                        if m.cost_data
                        else None,
                        "compliance_violations": [
                            {
                                "violation_id": cv.violation_id,
                                "rule_name": cv.rule_name,
                                "compliance_type": cv.compliance_type,
                                "severity": cv.severity,
                                "message": cv.message,
                            }
                            for cv in m.compliance_violations
                        ],
                        "collected_at": m.collected_at.isoformat(),
                    }
                    for m in metrics_contexts
                ],
            }
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2, default=str)
            logger.info(f"✅ Metrics context saved: {metrics_file}")

        logger.info("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
