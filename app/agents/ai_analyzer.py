"""AI Analyzer Agent using AWS Bedrock for drift analysis."""

import asyncio
import json
from datetime import datetime
from typing import Any, List, Optional

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
                    logger.error(f"Failed to analyze drift {drift_records[i].drift_id}: {analysis}")
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

        # Build change history summary
        change_history_summary = "No change history available"
        if drift.change_history:
            change_history_summary = self._format_change_history(drift.change_history)

        # Extract drift metadata for better context
        drift_metadata = drift.diff.get("_drift_metadata", {})
        updated_by = drift_metadata.get("updated_by") or drift.updated_by
        updated_at = drift_metadata.get("updated_at") or drift.updated_at
        drift_event = drift_metadata.get("drift_causing_event")

        # Build WHO section with appropriate messaging
        if updated_by:
            who_section = f"""WHO MADE THE CHANGE:
Changed By: {updated_by} (IAM User/Role)
Changed At: {updated_at}
AWS Action: {drift_event or 'Not specified'}
Source: CloudTrail event logs"""
        else:
            who_section = """WHO MADE THE CHANGE:
Changed By: Unknown
Reason: No CloudTrail events found in the last 24 hours. The change may have occurred:
  - More than 24 hours ago (outside CloudTrail lookback window)
  - Before CloudTrail logging was enabled
  - By an AWS service (system-initiated change)
Note: Consider increasing CloudTrail lookback period if recent changes are not being captured."""

        prompt = f"""You are a cloud infrastructure expert specializing in AWS infrastructure drift detection.
Analyze the following infrastructure drift with full context and provide actionable insights.

DRIFT DETECTED:
Resource ID: {drift.resource_id}
Resource Type: {drift.resource_type}
Drift Type: {drift.drift_type.value}
Account: {drift.account_id}
Region: {drift.region}
Detected At: {drift.detected_at.isoformat()}

{who_section}

CHANGES DETECTED:
Baseline (Expected) State:
{json.dumps(drift.terraform_value, indent=2)}

Current AWS State:
{json.dumps(drift.actual_value, indent=2)}

Differences:
{json.dumps(drift.diff, indent=2)}

CHANGE HISTORY:
{change_history_summary}

METRICS & CONTEXT:
{metrics_summary}

ANALYSIS REQUIRED:
Please provide a comprehensive analysis in the following JSON format:

{{
    "explanation": "Clear, human-readable explanation of what changed and when",
    "root_cause": "Specific root cause including WHO made the change (use the actual IAM user/role name from 'Changed By' field), WHAT action they performed (from 'AWS Action' field), and WHEN (from 'Changed At' field). Be specific, not generic.",
    "business_impact": "Impact on operations, performance, security, and costs",
    "recommended_action": "ONE OF THE FOLLOWING (exactly as written):
        - 'update_baseline': Update baseline to accept this change (authorized drift)
        - 'revert_aws': Revert AWS resources back to baseline state (undo unauthorized drift)
        - 'ignore': Acknowledge drift but take no action (low risk, temporary)
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
1. Root cause identification - Use specific details from "WHO MADE THE CHANGE" section above
2. Business and operational impact assessment
3. Safe remediation paths with risk mitigation
4. Confidence scoring based on available evidence

CRITICAL: For root_cause field, you MUST:
- Reference the specific IAM user/role name from "Changed By" field (not generic terms like "an authorized user")
- Include the AWS action from "AWS Action" field
- Include the timestamp from "Changed At" field
- If "Changed By" is "Unknown", state that explicitly and explain why (e.g., change older than 24h, CloudTrail not enabled)

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
            summary_parts.append(
                f"\nConfiguration Changes (Last 7 days): {len(metrics.config_history)} changes"
            )
            for change in metrics.config_history[:3]:  # Show last 3
                summary_parts.append(
                    f"  {change.timestamp.isoformat()}: {change.action} by {change.user or 'unknown'}"
                )

        # Cost data
        if metrics.cost_data:
            summary_parts.append("\nCost Analysis:")
            summary_parts.append(f"  Current Daily Cost: ${metrics.cost_data.current_cost:.2f}")
            summary_parts.append(f"  Monthly Projection: ${metrics.cost_data.projected_cost:.2f}")
            summary_parts.append(f"  Cost Change: {metrics.cost_data.cost_change_percent:+.1f}%")
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

    def _format_change_history(self, change_history: dict[str, Any]) -> str:
        """Format change history into readable summary for AI."""
        if not change_history:
            return "No change history available"

        summary_parts = []

        # Last modified info - EMPHASIZE the user
        if change_history.get("last_modified_by"):
            summary_parts.append("=" * 60)
            summary_parts.append(
                f"⚠️  DRIFT CAUSED BY: {change_history['last_modified_by']} (IAM User/Role)"
            )
            summary_parts.append(f"⏰  TIME: {change_history['last_modified_at']}")
            summary_parts.append(f"📊  Total Change Events: {change_history.get('total_events', 0)}")
            summary_parts.append("=" * 60)
            summary_parts.append("")

        # Recent events
        recent_events = change_history.get("recent_events", [])
        if recent_events:
            summary_parts.append("Recent Change Events:")
            for event in recent_events[:5]:  # Show last 5 events
                timestamp = event.get("timestamp", "Unknown time")
                source = event.get("source", "unknown").upper()

                if source == "CLOUDTRAIL":
                    event_name = event.get("event_name", "Unknown")
                    user = event.get("user", "Unknown")
                    source_ip = event.get("source_ip", "Unknown")
                    summary_parts.append(f"  [{timestamp}] {event_name}")
                    summary_parts.append(f"    👤 IAM User/Role: {user}")
                    summary_parts.append(f"    🌐 Source IP: {source_ip}")

                    # Add user identity details if available
                    user_identity = event.get("user_identity", {})
                    if user_identity.get("type"):
                        identity_type = user_identity.get("type")
                        summary_parts.append(f"    🔑 Identity Type: {identity_type}")
                        if user_identity.get("arn"):
                            summary_parts.append(f"    📋 ARN: {user_identity.get('arn')}")
                else:  # CONFIG
                    summary_parts.append(f"  [{timestamp}] Configuration Change")
                    changes = event.get("changes", {})
                    if changes:
                        for field, change_detail in list(changes.items())[:3]:  # First 3 changes
                            from_val = change_detail.get("from", "N/A")
                            to_val = change_detail.get("to", "N/A")
                            summary_parts.append(f"    • {field}: {from_val} → {to_val}")

                summary_parts.append("")

        return "\n".join(summary_parts)

    async def _call_bedrock(self, prompt: str) -> dict[str, Any]:
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
        self, response: dict[str, Any], drift: DriftRecord
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
