"""DriftGuards LangGraph Multi-Agent Workflow."""

import asyncio
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents import (
    AIAnalyzerAgent,
    Alert,
    AlertEngineAgent,
    DetectionAgent,
    MetricsCollectorAgent,
    PolicyValidatorAgent,
    PolicyViolation,
    RemediationAgent,
    RemediationResult,
)
from app.config import get_settings
from app.models.analysis import DriftAnalysis
from app.models.drift import DriftRecord, ScanRequest
from app.models.metrics import MetricsContext
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DriftGuardsState(TypedDict):
    """State definition for DriftGuards workflow."""

    # Input
    scan_request: Dict[str, Any]

    # Detection phase
    drift_records: List[DriftRecord]

    # Metrics phase
    metrics_context: List[MetricsContext]

    # AI Analysis phase
    ai_analysis: List[DriftAnalysis]

    # Policy Validation phase
    policy_violations: List[PolicyViolation]

    # Alert phase
    alerts_sent: List[Alert]

    # Remediation phase
    remediations: List[RemediationResult]

    # Workflow control
    should_alert: bool
    should_remediate: bool
    error: str | None


class DriftGuardsWorkflow:
    """Main LangGraph workflow for DriftGuards."""

    def __init__(self):
        """Initialize the workflow with all agents."""
        self.detection_agent = DetectionAgent()
        self.metrics_collector_agent = MetricsCollectorAgent()
        self.ai_analyzer_agent = AIAnalyzerAgent()
        self.policy_validator_agent = PolicyValidatorAgent()
        self.alert_engine_agent = AlertEngineAgent()
        self.remediation_agent = RemediationAgent()

        # Build the workflow graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Returns:
            Compiled workflow graph
        """
        # Define the graph with state
        workflow = StateGraph(DriftGuardsState)

        # Add nodes for each agent
        workflow.add_node("detection", self._detection_node)
        workflow.add_node("metrics_collector", self._metrics_collector_node)
        workflow.add_node("ai_analyzer", self._ai_analyzer_node)
        workflow.add_node("policy_validator", self._policy_validator_node)
        workflow.add_node("alert_engine", self._alert_engine_node)
        workflow.add_node("remediation", self._remediation_node)

        # Define the workflow edges
        workflow.set_entry_point("detection")

        # Linear flow: detection -> metrics -> AI -> policy
        workflow.add_edge("detection", "metrics_collector")
        workflow.add_edge("metrics_collector", "ai_analyzer")
        workflow.add_edge("ai_analyzer", "policy_validator")

        # Conditional: policy -> alert (if violations found)
        workflow.add_conditional_edges(
            "policy_validator",
            self._should_send_alerts,
            {
                "alert": "alert_engine",
                "remediate": "remediation",
                "end": END,
            },
        )

        # Conditional: alert -> remediate (if auto-remediation approved)
        workflow.add_conditional_edges(
            "alert_engine",
            self._should_auto_remediate,
            {
                "remediate": "remediation",
                "end": END,
            },
        )

        # Remediation ends the workflow
        workflow.add_edge("remediation", END)

        return workflow

    async def _detection_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Detection agent node - detects infrastructure drift.

        Args:
            state: Current workflow state

        Returns:
            Updated state with drift records
        """
        logger.info("=== DETECTION PHASE ===")

        try:
            scan_request_dict = state["scan_request"]
            scan_request = ScanRequest(**scan_request_dict)

            # Run detection
            drift_records = await self.detection_agent.detect_drift(scan_request)

            logger.info(f"Detected {len(drift_records)} drifts")

            return {
                **state,
                "drift_records": drift_records,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Detection phase failed: {e}", exc_info=True)
            return {
                **state,
                "drift_records": [],
                "error": str(e),
            }

    async def _metrics_collector_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Metrics collector agent node - enriches drifts with AWS metrics.

        Args:
            state: Current workflow state

        Returns:
            Updated state with metrics context
        """
        logger.info("=== METRICS COLLECTION PHASE ===")

        try:
            drift_records = state.get("drift_records", [])

            if not drift_records:
                logger.info("No drifts to collect metrics for")
                return {
                    **state,
                    "metrics_context": [],
                }

            # Collect metrics
            metrics_contexts = await self.metrics_collector_agent.collect_metrics(
                drift_records
            )

            logger.info(f"Collected metrics for {len(metrics_contexts)} resources")

            return {
                **state,
                "metrics_context": metrics_contexts,
            }

        except Exception as e:
            logger.error(f"Metrics collection phase failed: {e}", exc_info=True)
            return {
                **state,
                "metrics_context": [],
            }

    async def _ai_analyzer_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        AI analyzer agent node - provides AI-powered analysis.

        Args:
            state: Current workflow state

        Returns:
            Updated state with AI analyses
        """
        logger.info("=== AI ANALYSIS PHASE ===")

        try:
            drift_records = state.get("drift_records", [])
            metrics_contexts = state.get("metrics_context", [])

            if not drift_records:
                logger.info("No drifts to analyze")
                return {
                    **state,
                    "ai_analysis": [],
                }

            # Analyze drifts
            analyses = await self.ai_analyzer_agent.analyze_drifts(
                drift_records, metrics_contexts
            )

            logger.info(f"Analyzed {len(analyses)} drifts with AI")

            # Log summary
            for analysis in analyses:
                logger.info(
                    f"  {analysis.resource_id}: {analysis.recommended_action} "
                    f"(confidence: {analysis.confidence_score}%)"
                )

            return {
                **state,
                "ai_analysis": analyses,
            }

        except Exception as e:
            logger.error(f"AI analysis phase failed: {e}", exc_info=True)
            return {
                **state,
                "ai_analysis": [],
            }

    async def _policy_validator_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Policy validator agent node - validates against policies.

        Args:
            state: Current workflow state

        Returns:
            Updated state with policy violations
        """
        logger.info("=== POLICY VALIDATION PHASE ===")

        try:
            drift_records = state.get("drift_records", [])
            analyses = state.get("ai_analysis", [])

            if not drift_records:
                logger.info("No drifts to validate")
                return {
                    **state,
                    "policy_violations": [],
                    "should_alert": False,
                    "should_remediate": False,
                }

            # Validate against policies
            violations = await self.policy_validator_agent.validate_drifts(
                drift_records, analyses
            )

            logger.info(f"Found {len(violations)} policy violations")

            # Determine next steps
            should_alert = len(drift_records) > 0
            should_remediate = settings.remediation_auto_approve and len(analyses) > 0

            return {
                **state,
                "policy_violations": violations,
                "should_alert": should_alert,
                "should_remediate": should_remediate,
            }

        except Exception as e:
            logger.error(f"Policy validation phase failed: {e}", exc_info=True)
            return {
                **state,
                "policy_violations": [],
                "should_alert": False,
                "should_remediate": False,
            }

    async def _alert_engine_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Alert engine agent node - sends multi-channel alerts.

        Args:
            state: Current workflow state

        Returns:
            Updated state with alerts sent
        """
        logger.info("=== ALERT PHASE ===")

        try:
            drift_records = state.get("drift_records", [])
            analyses = state.get("ai_analysis", [])
            metrics_contexts = state.get("metrics_context", [])

            if not drift_records:
                logger.info("No drifts to alert on")
                return {
                    **state,
                    "alerts_sent": [],
                }

            # Send alerts
            alerts = await self.alert_engine_agent.send_alerts(
                drift_records, analyses, metrics_contexts
            )

            logger.info(f"Sent {len(alerts)} alerts")

            return {
                **state,
                "alerts_sent": alerts,
            }

        except Exception as e:
            logger.error(f"Alert phase failed: {e}", exc_info=True)
            return {
                **state,
                "alerts_sent": [],
            }

    async def _remediation_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Remediation agent node - executes automated fixes.

        Args:
            state: Current workflow state

        Returns:
            Updated state with remediation results
        """
        logger.info("=== REMEDIATION PHASE ===")

        try:
            drift_records = state.get("drift_records", [])
            analyses = state.get("ai_analysis", [])

            if not drift_records or not analyses:
                logger.info("No drifts to remediate")
                return {
                    **state,
                    "remediations": [],
                }

            # Execute remediations
            remediations = await self.remediation_agent.remediate_drifts(
                drift_records, analyses
            )

            logger.info(f"Completed {len(remediations)} remediations")

            # Log summary
            for remediation in remediations:
                logger.info(
                    f"  {remediation.drift_id}: {remediation.action.value} "
                    f"-> {remediation.status.value}"
                )

            return {
                **state,
                "remediations": remediations,
            }

        except Exception as e:
            logger.error(f"Remediation phase failed: {e}", exc_info=True)
            return {
                **state,
                "remediations": [],
            }

    def _should_send_alerts(
        self, state: DriftGuardsState
    ) -> Literal["alert", "remediate", "end"]:
        """
        Determine if alerts should be sent.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute
        """
        drift_records = state.get("drift_records", [])
        should_alert = state.get("should_alert", False)
        should_remediate = state.get("should_remediate", False)

        if not drift_records:
            logger.info("No drifts found - ending workflow")
            return "end"

        if should_alert:
            logger.info("Proceeding to alert phase")
            return "alert"

        if should_remediate:
            logger.info("Proceeding directly to remediation (no alerts)")
            return "remediate"

        logger.info("No alerts or remediations needed - ending workflow")
        return "end"

    def _should_auto_remediate(
        self, state: DriftGuardsState
    ) -> Literal["remediate", "end"]:
        """
        Determine if auto-remediation should be performed.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute
        """
        should_remediate = state.get("should_remediate", False)

        if should_remediate:
            logger.info("Proceeding to remediation phase")
            return "remediate"

        logger.info("No auto-remediation - ending workflow")
        return "end"

    async def run(self, scan_request: ScanRequest) -> DriftGuardsState:
        """
        Execute the complete DriftGuards workflow.

        Args:
            scan_request: Scan configuration

        Returns:
            Final workflow state
        """
        logger.info("=" * 80)
        logger.info("STARTING DRIFTGUARDS WORKFLOW")
        logger.info("=" * 80)

        try:
            # Initialize state
            initial_state: DriftGuardsState = {
                "scan_request": scan_request.dict(),
                "drift_records": [],
                "metrics_context": [],
                "ai_analysis": [],
                "policy_violations": [],
                "alerts_sent": [],
                "remediations": [],
                "should_alert": False,
                "should_remediate": False,
                "error": None,
            }

            # Execute workflow
            final_state = await self.app.ainvoke(initial_state)

            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETED")
            logger.info("=" * 80)
            logger.info(f"Drifts detected: {len(final_state.get('drift_records', []))}")
            logger.info(f"Analyses performed: {len(final_state.get('ai_analysis', []))}")
            logger.info(f"Alerts sent: {len(final_state.get('alerts_sent', []))}")
            logger.info(f"Remediations executed: {len(final_state.get('remediations', []))}")

            if final_state.get("error"):
                logger.error(f"Workflow error: {final_state['error']}")

            return final_state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            raise

    async def run_detection_only(self, scan_request: ScanRequest) -> List[DriftRecord]:
        """
        Run only the detection phase (for testing).

        Args:
            scan_request: Scan configuration

        Returns:
            List of drift records
        """
        logger.info("Running detection only (no analysis or remediation)")
        return await self.detection_agent.detect_drift(scan_request)

    async def run_analysis_for_drift(
        self, drift_record: DriftRecord
    ) -> DriftAnalysis:
        """
        Run AI analysis for a single drift (for API endpoints).

        Args:
            drift_record: Drift record to analyze

        Returns:
            AI analysis
        """
        logger.info(f"Running analysis for drift {drift_record.drift_id}")

        # Collect metrics first
        metrics_contexts = await self.metrics_collector_agent.collect_metrics(
            [drift_record]
        )

        metrics_context = metrics_contexts[0] if metrics_contexts else None

        # Analyze
        analyses = await self.ai_analyzer_agent.analyze_drifts(
            [drift_record], [metrics_context] if metrics_context else []
        )

        return analyses[0] if analyses else None

    async def run_remediation_for_drift(
        self,
        drift_record: DriftRecord,
        analysis: DriftAnalysis,
    ) -> RemediationResult:
        """
        Run remediation for a single drift (for API endpoints).

        Args:
            drift_record: Drift record
            analysis: AI analysis

        Returns:
            Remediation result
        """
        logger.info(f"Running remediation for drift {drift_record.drift_id}")

        results = await self.remediation_agent.remediate_drifts(
            [drift_record], [analysis]
        )

        return results[0] if results else None


# Global workflow instance
_workflow_instance = None


def get_workflow() -> DriftGuardsWorkflow:
    """Get singleton workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = DriftGuardsWorkflow()
    return _workflow_instance

