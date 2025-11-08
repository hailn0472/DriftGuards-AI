"""DriftGuards LangGraph Multi-Agent Workflow."""

import asyncio
import time
from typing import Any, Literal, TypedDict

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
    scan_request: dict[str, Any]

    # Detection phase
    drift_records: list[DriftRecord]

    # Metrics phase
    metrics_context: list[MetricsContext]

    # AI Analysis phase
    ai_analysis: list[DriftAnalysis]

    # Policy Validation phase
    policy_violations: list[PolicyViolation]

    # Alert phase
    alerts_sent: list[Alert]

    # Remediation phase
    remediations: list[RemediationResult]

    # Workflow control
    should_alert: bool
    should_remediate: bool
    error: str | None
    detection_status: str  # Track detection status for retry logic

    # Observability & retry tracking
    node_execution_times: dict[str, float]
    retry_count: int
    detection_start_time: float
    total_execution_time: float


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

        # Observability: Track metrics across runs
        self.metrics = {
            "total_runs": 0,
            "node_execution_times": {},
            "node_success_rates": {},
            "node_error_counts": {},
        }

        # Build the workflow graph
        self.workflow = self._build_workflow()

        # Persistent checkpointing for state recovery (optional for now)
        # Note: Checkpointing disabled temporarily due to API compatibility
        # To enable: install langgraph-checkpoint-sqlite and update implementation
        self.app = self.workflow.compile()

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with error recovery.

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

        # Error recovery nodes
        workflow.add_node("retry_detection", self._retry_detection_node)
        workflow.add_node("fallback_analysis", self._fallback_analysis_node)

        # Define the workflow edges
        workflow.set_entry_point("detection")

        # Conditional: detection → metrics (with retry on failure)
        workflow.add_conditional_edges(
            "detection",
            self._check_detection_status,
            {
                "success": "metrics_collector",
                "retry": "retry_detection",
                "fail": END,
            },
        )

        # Retry detection → detection (with limit)
        workflow.add_edge("retry_detection", "detection")

        # Linear flow: metrics → AI
        workflow.add_edge("metrics_collector", "ai_analyzer")

        # Conditional: AI → policy (with fallback on failure)
        workflow.add_conditional_edges(
            "ai_analyzer",
            self._check_ai_status,
            {
                "success": "policy_validator",
                "fallback": "fallback_analysis",
            },
        )

        # Fallback analysis → policy
        workflow.add_edge("fallback_analysis", "policy_validator")

        # Conditional: policy → alert (if violations found)
        workflow.add_conditional_edges(
            "policy_validator",
            self._should_send_alerts,
            {
                "alert": "alert_engine",
                "remediate": "remediation",
                "end": END,
            },
        )

        # Conditional: alert → remediate (if auto-remediation approved)
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
        Enhanced with parallel multi-region detection.

        Args:
            state: Current workflow state

        Returns:
            Updated state with drift records
        """
        logger.info("=== DETECTION PHASE ===")
        start_time = time.time()
        state["detection_start_time"] = start_time

        try:
            scan_request_dict = state["scan_request"]
            scan_request = ScanRequest(**scan_request_dict)

            # Parallel detection across regions
            drift_records = await self._parallel_detection(scan_request)

            # Track metrics
            execution_time = time.time() - start_time
            if "node_execution_times" not in state:
                state["node_execution_times"] = {}
            state["node_execution_times"]["detection"] = execution_time

            logger.info(f"Detected {len(drift_records)} drifts in {execution_time:.2f}s")

            # Update state with successful detection
            state["drift_records"] = drift_records
            state["detection_status"] = "success"
            state["retry_count"] = 0
            state["error"] = None

            logger.info(f"Setting detection_status=success in state")

            return state

        except Exception as e:
            logger.error(f"Detection phase failed: {e}", exc_info=True)

            # Update state with error
            state["drift_records"] = []
            state["detection_status"] = "error"
            state["error"] = str(e)

            logger.error("Setting detection_status=error in state")

            return state

    async def _parallel_detection(self, scan_request: ScanRequest) -> list[DriftRecord]:
        """
        Perform parallel drift detection across multiple regions/accounts.

        Args:
            scan_request: Scan configuration

        Returns:
            Combined drift records from all regions
        """
        tasks = []

        # Create detection tasks for each account/region combination
        for account in scan_request.accounts:
            for region in scan_request.regions:
                # Create region-specific scan request
                region_request = ScanRequest(
                    accounts=[account],
                    regions=[region],
                    resource_types=scan_request.resource_types,
                    tags_filter=scan_request.tags_filter,
                    force_refresh=scan_request.force_refresh,
                )
                tasks.append(self._detect_region(region_request))

        # Execute all tasks in parallel
        logger.info(f"Launching {len(tasks)} parallel detection tasks")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results, filtering out errors
        all_drift_records = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Region detection failed: {result}")
                continue
            all_drift_records.extend(result)

        return all_drift_records

    async def _detect_region(self, scan_request: ScanRequest) -> list[DriftRecord]:
        """
        Detect drift in a single region.

        Args:
            scan_request: Single-region scan request

        Returns:
            Drift records for this region
        """
        # Detection agent's detect_drift is already async, just await it
        return await self.detection_agent.detect_drift(scan_request)

    async def _retry_detection_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Retry detection with exponential backoff.

        Args:
            state: Current workflow state

        Returns:
            Updated state ready for retry
        """
        retry_count = state.get("retry_count", 0)
        max_retries = 3

        if retry_count >= max_retries:
            logger.error(f"Max retries ({max_retries}) reached for detection")
            state["detection_status"] = "failed"
            return state

        # Exponential backoff: 2^retry_count seconds
        wait_time = 2**retry_count
        logger.warning(
            f"Retrying detection (attempt {retry_count + 1}/{max_retries}) after {wait_time}s"
        )

        await asyncio.sleep(wait_time)

        state["retry_count"] = retry_count + 1
        state["detection_status"] = "retry"

        logger.info(f"Updated retry_count={retry_count + 1}, detection_status=retry")

        return state

    async def _fallback_analysis_node(self, state: DriftGuardsState) -> DriftGuardsState:
        """
        Fallback analysis using rule-based detection when AI fails.

        Args:
            state: Current workflow state

        Returns:
            Updated state with rule-based analyses
        """
        logger.warning("AI analysis failed, using rule-based fallback")

        drift_records = state.get("drift_records", [])
        analyses = []

        # Simple rule-based analysis
        for drift in drift_records:
            severity = self._calculate_severity(drift)

            analysis = DriftAnalysis(
                analysis_id=f"analysis-{drift.drift_id}-fallback",
                resource_id=drift.resource_id,
                drift_id=drift.drift_id,
                explanation=f"Drift detected in {drift.resource_type} ({drift.resource_id}). Manual review required as AI analysis is unavailable.",
                root_cause="Unable to determine automatically",
                business_impact="Unknown - manual assessment required",
                recommended_action="manual_review",
                alternative_actions=[],
                confidence_score=0,  # Lower confidence for rule-based
                severity=severity,
                estimated_fix_time="Unknown",
                rollback_complexity="complex",
                blast_radius="Unknown - requires manual assessment",
                remediation_steps=[
                    "Review drift details",
                    "Consult with team",
                    "Decide on action",
                ],
                prerequisites=["Manual review required"],
                rollback_steps=["Depends on chosen action"],
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                model_version="fallback",
            )
            analyses.append(analysis)

        logger.info(f"Fallback analysis completed for {len(analyses)} drifts")

        state["ai_analysis"] = analyses
        return state

    def _calculate_severity(self, drift: DriftRecord) -> str:
        """
        Calculate severity based on drift characteristics.

        Args:
            drift: Drift record to analyze

        Returns:
            Severity level (critical/high/medium/low)
        """
        # Security-related resources = critical
        security_types = {"SecurityGroup", "IamRole", "IamPolicy", "KmsKey"}
        if drift.resource_type in security_types:
            return "critical"

        # Multiple changes = high (check diff dictionary depth)
        if drift.diff and len(drift.diff) > 3:
            return "high"

        # Default to medium
        return "medium"

    def _check_detection_status(self, state: DriftGuardsState) -> str:
        """
        Determine next step after detection.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute (success/retry/fail)
        """
        status = state.get("detection_status", "error")
        retry_count = state.get("retry_count", 0)

        logger.info(f"Checking detection status: status={status}, retry_count={retry_count}")

        if status == "success":
            logger.info("Detection successful, proceeding to metrics")
            return "success"
        elif status == "error" and retry_count < 3:
            logger.warning(f"Detection failed, will retry (attempt {retry_count + 1}/3)")
            return "retry"
        else:
            logger.error("Detection failed after max retries")
            return "fail"

    def _check_ai_status(self, state: DriftGuardsState) -> str:
        """
        Determine if AI analysis succeeded.

        Args:
            state: Current workflow state

        Returns:
            Next node to execute (success/fallback)
        """
        ai_analysis = state.get("ai_analysis", [])

        # If we have analysis and it's not from fallback, AI succeeded
        if ai_analysis and not any(
            analysis.model_version == "fallback" for analysis in ai_analysis
        ):
            return "success"
        else:
            return "fallback"

    async def _instrumented_node(
        self, node_name: str, node_func, state: DriftGuardsState
    ) -> DriftGuardsState:
        """
        Wrapper to track node execution metrics.

        Args:
            node_name: Name of the node being executed
            node_func: The actual node function to execute
            state: Current workflow state

        Returns:
            Updated state from node execution
        """
        start_time = time.time()

        try:
            # Execute the node
            result_state = await node_func(state)

            # Track success
            execution_time = time.time() - start_time

            # Update metrics
            self.metrics["node_execution_times"][node_name] = self.metrics[
                "node_execution_times"
            ].get(node_name, []) + [execution_time]

            success_count = self.metrics["node_success_rates"].get(node_name, 0) + 1
            self.metrics["node_success_rates"][node_name] = success_count

            logger.debug(
                f"Node '{node_name}' completed in {execution_time:.2f}s",
                extra={"node": node_name, "execution_time": execution_time},
            )

            # Add to state
            if "node_execution_times" not in result_state:
                result_state["node_execution_times"] = {}
            result_state["node_execution_times"][node_name] = execution_time

            return result_state

        except Exception as e:
            execution_time = time.time() - start_time

            # Track error
            error_count = self.metrics["node_error_counts"].get(node_name, 0) + 1
            self.metrics["node_error_counts"][node_name] = error_count

            logger.error(
                f"Node '{node_name}' failed after {execution_time:.2f}s: {e}",
                exc_info=True,
                extra={"node": node_name, "execution_time": execution_time, "error": str(e)},
            )

            raise  # Re-raise to let workflow handle it

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
            metrics_contexts = await self.metrics_collector_agent.collect_metrics(drift_records)

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
            analyses = await self.ai_analyzer_agent.analyze_drifts(drift_records, metrics_contexts)

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
            violations = await self.policy_validator_agent.validate_drifts(drift_records, analyses)

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
            remediations = await self.remediation_agent.remediate_drifts(drift_records, analyses)

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

    def _should_send_alerts(self, state: DriftGuardsState) -> Literal["alert", "remediate", "end"]:
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

    def _should_auto_remediate(self, state: DriftGuardsState) -> Literal["remediate", "end"]:
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

    async def run(
        self, scan_request: ScanRequest, thread_id: str | None = None
    ) -> DriftGuardsState:
        """
        Execute the complete DriftGuards workflow with checkpointing.

        Args:
            scan_request: Scan configuration
            thread_id: Optional thread ID for resuming workflows

        Returns:
            Final workflow state
        """
        logger.info("=" * 80)
        logger.info("STARTING DRIFTGUARDS WORKFLOW")
        logger.info("=" * 80)

        workflow_start = time.time()
        self.metrics["total_runs"] += 1

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
                "node_execution_times": {},
                "retry_count": 0,
                "detection_start_time": workflow_start,
                "total_execution_time": 0.0,
                "detection_status": "pending",  # Initialize detection status
            }

            # Execute workflow (checkpointing disabled)
            final_state = await self.app.ainvoke(initial_state)

            # Calculate total execution time
            total_time = time.time() - workflow_start
            final_state["total_execution_time"] = total_time

            # Log comprehensive metrics
            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETED")
            logger.info("=" * 80)
            logger.info(f"Total execution time: {total_time:.2f}s")
            logger.info(f"Drifts detected: {len(final_state.get('drift_records', []))}")
            logger.info(f"Analyses performed: {len(final_state.get('ai_analysis', []))}")
            logger.info(f"Alerts sent: {len(final_state.get('alerts_sent', []))}")
            logger.info(f"Remediations executed: {len(final_state.get('remediations', []))}")

            # Log node execution times
            node_times = final_state.get("node_execution_times", {})
            if node_times:
                logger.info("Node execution times:")
                for node, exec_time in node_times.items():
                    logger.info(f"  - {node}: {exec_time:.2f}s")

            # Log retry information
            retry_count = final_state.get("retry_count", 0)
            if retry_count > 0:
                logger.info(f"Detection retries: {retry_count}")

            if final_state.get("error"):
                logger.error(f"Workflow error: {final_state['error']}")

            return final_state

        except Exception as e:
            total_time = time.time() - workflow_start
            logger.error(
                f"Workflow execution failed after {total_time:.2f}s: {e}",
                exc_info=True,
                extra={"execution_time": total_time},
            )
            raise

    def get_workflow_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive workflow metrics.

        Returns:
            Dictionary containing all tracked metrics
        """
        metrics = {
            "total_runs": self.metrics["total_runs"],
            "node_statistics": {},
        }

        # Calculate average execution times per node
        for node, times in self.metrics["node_execution_times"].items():
            avg_time = sum(times) / len(times) if times else 0
            success_count = self.metrics["node_success_rates"].get(node, 0)
            error_count = self.metrics["node_error_counts"].get(node, 0)
            total_executions = success_count + error_count

            metrics["node_statistics"][node] = {
                "average_execution_time": round(avg_time, 2),
                "total_executions": total_executions,
                "successful_executions": success_count,
                "failed_executions": error_count,
                "success_rate": round(success_count / total_executions * 100, 2)
                if total_executions > 0
                else 0,
            }

        return metrics

    async def run_detection_only(self, scan_request: ScanRequest) -> list[DriftRecord]:
        """
        Run only the detection phase (for testing).

        Args:
            scan_request: Scan configuration

        Returns:
            List of drift records
        """
        logger.info("Running detection only (no analysis or remediation)")
        return await self.detection_agent.detect_drift(scan_request)

    async def run_analysis_for_drift(self, drift_record: DriftRecord) -> DriftAnalysis:
        """
        Run AI analysis for a single drift (for API endpoints).

        Args:
            drift_record: Drift record to analyze

        Returns:
            AI analysis
        """
        logger.info(f"Running analysis for drift {drift_record.drift_id}")

        # Collect metrics first
        metrics_contexts = await self.metrics_collector_agent.collect_metrics([drift_record])

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

        results = await self.remediation_agent.remediate_drifts([drift_record], [analysis])

        return results[0] if results else None


# Global workflow instance
_workflow_instance = None


def get_workflow() -> DriftGuardsWorkflow:
    """Get singleton workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = DriftGuardsWorkflow()
    return _workflow_instance
