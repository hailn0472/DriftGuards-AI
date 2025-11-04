"""AI Analyzer Agent using AWS Bedrock for drift analysis."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.models.analysis import ActionOption, DriftAnalysis
from app.models.drift import DriftRecord
from app.models.metrics import MetricsContext
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AIAnalyzerAgent:
    """Agent responsible for AI-powered drift analysis using AWS Bedrock."""

    def __init__(self):
        """Initialize AI analyzer agent."""
        self.bedrock_client = None
        self.model_id = settings.bedrock_model_id
        self.temperature = settings.bedrock_temperature
        self.max_tokens = settings.bedrock_max_tokens

    def _get_bedrock_client(self):
        """Get Bedrock runtime client."""
        if not self.bedrock_client:
            self.bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=settings.bedrock_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.bedrock_client

    async def analyze_drifts(
        self,
        drift_records: List[DriftRecord],
        metrics_contexts: List[MetricsContext],
    ) -> List[DriftAnalysis]:
        """
        Analyze multiple drifts with AI in parallel.

        Args:
            drift_records: List of drift records
            metrics_contexts: Corresponding metrics contexts

        Returns:
            List of AI analyses
        """
        logger.info(f"Analyzing {len(drift_records)} drifts with AI")

        try:
            # Match drifts with their metrics
            drift_metrics_pairs = []
            metrics_by_resource = {m.resource_id: m for m in metrics_contexts}

            for drift in drift_records:
                metrics = metrics_by_resource.get(drift.resource_id)
                drift_metrics_pairs.append((drift, metrics))

            # Analyze in parallel with rate limiting
            tasks = [
                self._analyze_drift_with_context(drift, metrics)
                for drift, metrics in drift_metrics_pairs
            ]

            analyses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_analyses = []
            for i, analysis in enumerate(analyses):
                if isinstance(analysis, Exception):
                    logger.error(
                        f"Failed to analyze drift {drift_records[i].drift_id}: {analysis}"
                    )
                else:
                    valid_analyses.append(analysis)

            logger.info(f"Successfully analyzed {len(valid_analyses)} drifts")
            return valid_analyses

        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            raise

    async def _analyze_drift_with_context(
        self,
        drift: DriftRecord,
        metrics: Optional[MetricsContext] = None,
    ) -> DriftAnalysis:
        """
        Analyze a single drift with full context using AI.

        Args:
            drift: Drift record
            metrics: Optional metrics context

        Returns:
            AI analysis result
        """
        logger.debug(f"Analyzing drift {drift.drift_id} with AI")

        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(drift, metrics)

            # Call Bedrock
            response = await self._call_bedrock(prompt)

            # Parse structured output
            analysis = self._parse_analysis_response(response, drift)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing drift {drift.drift_id}: {e}", exc_info=True)
            raise

    def _build_analysis_prompt(
        self,
        drift: DriftRecord,
        metrics: Optional[MetricsContext] = None,
    ) -> str:
        """
        Build comprehensive analysis prompt with all context.

        Args:
            drift: Drift record
            metrics: Optional metrics context

        Returns:
            Formatted prompt string
        """
        # Build metrics summary
        metrics_summary = "No metrics available"
        if metrics:
            metrics_summary = self._format_metrics_summary(metrics)

        prompt = f"""You are a cloud infrastructure expert specializing in AWS and Terraform.
Analyze the following infrastructure drift with full context and provide actionable insights.

DRIFT DETECTED:
Resource ID: {drift.resource_id}
Resource Type: {drift.resource_type}
Drift Type: {drift.drift_type.value}
Account: {drift.account_id}
Region: {drift.region}
Detected At: {drift.detected_at.isoformat()}

CHANGES DETECTED:
Terraform Expected State:
{json.dumps(drift.terraform_value, indent=2)}

Actual AWS State:
{json.dumps(drift.actual_value, indent=2)}

Differences:
{json.dumps(drift.diff, indent=2)}

METRICS & CONTEXT:
{metrics_summary}

ANALYSIS REQUIRED:
Please provide a comprehensive analysis in the following JSON format:

{{
    "explanation": "Clear, human-readable explanation of what changed and when",
    "root_cause": "Why this drift occurred (e.g., manual change, automation, auto-scaling)",
    "business_impact": "Impact on operations, performance, security, and costs",
    "recommended_action": "ONE OF THE FOLLOWING (exactly as written):
        - 'update_terraform': Update Terraform code to match the current AWS state (accept the drift)
        - 'revert_aws': Revert AWS resources back to match Terraform state (undo the drift)
        - 'ignore': Acknowledge drift but take no action (low risk)
        - 'manual_review': Requires human decision (complex or uncertain cases)",
    "alternative_actions": [
        {{
            "action": "action_name",
            "description": "What this action does",
            "risk": "low | medium | high",
            "reason": "Why this risk level",
            "estimated_duration": "time estimate"
        }}
    ],
    "confidence_score": 85,
    "severity": "critical | high | medium | low",
    "estimated_fix_time": "e.g., 5 minutes",
    "rollback_complexity": "simple | moderate | complex",
    "blast_radius": "Description of potential impact scope",
    "remediation_steps": [
        "Step 1: ...",
        "Step 2: ..."
    ],
    "prerequisites": [
        "Prerequisite 1: ...",
        "Prerequisite 2: ..."
    ],
    "rollback_steps": [
        "Rollback step 1: ...",
        "Rollback step 2: ..."
    ]
}}

Focus on:
1. Root cause identification (check metrics for performance issues, costs, etc.)
2. Business and operational impact assessment
3. Safe remediation paths with risk mitigation
4. Confidence scoring based on available evidence

Respond ONLY with the JSON object, no additional text."""

        return prompt

    def _format_metrics_summary(self, metrics: MetricsContext) -> str:
        """Format metrics context into readable summary."""
        summary_parts = []

        # CloudWatch metrics
        if metrics.cloudwatch_metrics:
            summary_parts.append("CloudWatch Metrics (Last 24h):")
            for metric_name, metric_data in metrics.cloudwatch_metrics.items():
                stats = metric_data.statistics
                summary_parts.append(
                    f"  {metric_name}: Avg={stats.get('Average', 0):.2f}, "
                    f"Max={stats.get('Maximum', 0):.2f}, "
                    f"Min={stats.get('Minimum', 0):.2f}"
                )

        # Config history
        if metrics.config_history:
            summary_parts.append(f"\nConfiguration Changes (Last 7 days): {len(metrics.config_history)} changes")
            for change in metrics.config_history[:3]:  # Show last 3
                summary_parts.append(
                    f"  {change.timestamp.isoformat()}: {change.action} by {change.user or 'unknown'}"
                )

        # Cost data
        if metrics.cost_data:
            summary_parts.append("\nCost Analysis:")
            summary_parts.append(
                f"  Current Daily Cost: ${metrics.cost_data.current_cost:.2f}"
            )
            summary_parts.append(
                f"  Monthly Projection: ${metrics.cost_data.projected_cost:.2f}"
            )
            summary_parts.append(
                f"  Cost Change: {metrics.cost_data.cost_change_percent:+.1f}%"
            )
            if metrics.cost_data.budget_impact:
                summary_parts.append(f"  Impact: {metrics.cost_data.budget_impact}")

        # Compliance violations
        if metrics.compliance_violations:
            summary_parts.append(f"\nCompliance Violations: {len(metrics.compliance_violations)}")
            for violation in metrics.compliance_violations[:3]:
                summary_parts.append(
                    f"  {violation.rule_name}: {violation.compliance_type} ({violation.severity})"
                )

        return "\n".join(summary_parts) if summary_parts else "No metrics available"

    async def _call_bedrock(self, prompt: str) -> Dict[str, Any]:
        """
        Call AWS Bedrock API with the analysis prompt.

        Args:
            prompt: Analysis prompt

        Returns:
            Bedrock response
        """
        try:
            bedrock = self._get_bedrock_client()

            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }

            # Call Bedrock
            response = await asyncio.to_thread(
                bedrock.invoke_model,
                modelId=self.model_id,
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            return response_body

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Bedrock API call failed: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Bedrock: {e}", exc_info=True)
            raise

    def _parse_analysis_response(
        self, response: Dict[str, Any], drift: DriftRecord
    ) -> DriftAnalysis:
        """
        Parse Bedrock response into structured analysis.

        Args:
            response: Bedrock API response
            drift: Original drift record

        Returns:
            Structured drift analysis
        """
        try:
            # Extract content from Claude response
            content = response.get("content", [])
            if not content:
                raise ValueError("Empty response from Bedrock")

            # Get the text content
            text_content = content[0].get("text", "")

            # Parse JSON from response
            # Claude sometimes wraps JSON in markdown, so we need to extract it
            json_start = text_content.find("{")
            json_end = text_content.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = text_content[json_start:json_end]
            analysis_data = json.loads(json_str)

            # Generate analysis ID
            analysis_id = f"analysis-{drift.drift_id}-{int(datetime.utcnow().timestamp())}"

            # Parse alternative actions
            alternative_actions = []
            for action_data in analysis_data.get("alternative_actions", []):
                alternative_actions.append(
                    ActionOption(
                        action=action_data.get("action", ""),
                        description=action_data.get("description", ""),
                        risk=action_data.get("risk", "medium"),
                        reason=action_data.get("reason", ""),
                        estimated_duration=action_data.get("estimated_duration"),
                    )
                )

            # Create DriftAnalysis object
            analysis = DriftAnalysis(
                analysis_id=analysis_id,
                resource_id=drift.resource_id,
                drift_id=drift.drift_id,
                explanation=analysis_data.get("explanation", "No explanation provided"),
                root_cause=analysis_data.get("root_cause", "Unknown"),
                business_impact=analysis_data.get("business_impact", "Unknown impact"),
                recommended_action=analysis_data.get("recommended_action", "manual_review"),
                alternative_actions=alternative_actions,
                confidence_score=analysis_data.get("confidence_score", 50),
                severity=analysis_data.get("severity", "medium"),
                estimated_fix_time=analysis_data.get("estimated_fix_time", "Unknown"),
                rollback_complexity=analysis_data.get("rollback_complexity", "moderate"),
                blast_radius=analysis_data.get("blast_radius", "Unknown"),
                remediation_steps=analysis_data.get("remediation_steps", []),
                prerequisites=analysis_data.get("prerequisites", []),
                rollback_steps=analysis_data.get("rollback_steps", []),
                analyzed_at=datetime.utcnow(),
                model_id=self.model_id,
                model_version=response.get("model_version"),
            )

            logger.debug(
                f"Successfully parsed analysis for {drift.drift_id}, "
                f"confidence: {analysis.confidence_score}%"
            )

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Bedrock response: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(drift)
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}", exc_info=True)
            return self._create_fallback_analysis(drift)

    def _create_fallback_analysis(self, drift: DriftRecord) -> DriftAnalysis:
        """
        Create a fallback analysis when AI analysis fails.

        Args:
            drift: Drift record

        Returns:
            Basic drift analysis
        """
        analysis_id = f"analysis-{drift.drift_id}-fallback"

        return DriftAnalysis(
            analysis_id=analysis_id,
            resource_id=drift.resource_id,
            drift_id=drift.drift_id,
            explanation=f"Drift detected in {drift.resource_type} ({drift.resource_id}). "
            f"Manual review required as AI analysis was unavailable.",
            root_cause="Unable to determine automatically",
            business_impact="Unknown - manual assessment required",
            recommended_action="manual_review",
            alternative_actions=[],
            confidence_score=0,
            severity=drift.severity.value,
            estimated_fix_time="Unknown",
            rollback_complexity="complex",
            blast_radius="Unknown - requires manual assessment",
            remediation_steps=["Review drift details", "Consult with team", "Decide on action"],
            prerequisites=["Manual review required"],
            rollback_steps=["Depends on chosen action"],
            analyzed_at=datetime.utcnow(),
            model_id=self.model_id,
            model_version="fallback",
        )
