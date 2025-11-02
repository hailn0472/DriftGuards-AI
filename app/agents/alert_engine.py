"""Alert Engine Agent for multi-channel intelligent alerting."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.models.analysis import DriftAnalysis
from app.models.drift import DriftRecord
from app.models.metrics import MetricsContext
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class Alert:
    """Alert record."""

    def __init__(
        self,
        alert_id: str,
        drift_id: str,
        severity: str,
        title: str,
        message: str,
        channels: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.alert_id = alert_id
        self.drift_id = drift_id
        self.severity = severity
        self.title = title
        self.message = message
        self.channels = channels
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.sent_at: Optional[datetime] = None


class AlertEngineAgent:
    """Agent responsible for intelligent, multi-channel alerting."""

    def __init__(self):
        """Initialize alert engine agent."""
        self.sns_client = None
        self.ses_client = None
        self.recent_alerts: Dict[str, datetime] = {}  # For deduplication

    def _get_sns_client(self):
        """Get SNS client."""
        if not self.sns_client:
            self.sns_client = boto3.client(
                "sns",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.sns_client

    def _get_ses_client(self):
        """Get SES client."""
        if not self.ses_client:
            self.ses_client = boto3.client(
                "ses",
                region_name=settings.ses_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
            )
        return self.ses_client

    async def send_alerts(
        self,
        drift_records: List[DriftRecord],
        analyses: List[DriftAnalysis],
        metrics_contexts: Optional[List[MetricsContext]] = None,
    ) -> List[Alert]:
        """
        Send alerts for drifts based on severity and escalation policy.

        Args:
            drift_records: List of drift records
            analyses: Corresponding AI analyses
            metrics_contexts: Optional metrics contexts

        Returns:
            List of alerts sent
        """
        logger.info(f"Processing alerts for {len(drift_records)} drifts")

        try:
            # Match drifts with analyses
            drift_analysis_pairs = []
            analyses_by_drift = {a.drift_id: a for a in analyses}

            for drift in drift_records:
                analysis = analyses_by_drift.get(drift.drift_id)
                if analysis:
                    drift_analysis_pairs.append((drift, analysis))

            # Filter drifts that need alerting (with deduplication)
            alertable_drifts = []
            for drift, analysis in drift_analysis_pairs:
                if self._should_alert(drift, analysis):
                    if not self._is_duplicate_alert(drift):
                        alertable_drifts.append((drift, analysis))
                    else:
                        logger.debug(f"Skipping duplicate alert for {drift.drift_id}")

            logger.info(f"Sending alerts for {len(alertable_drifts)} drifts")

            # Send alerts in parallel
            tasks = [
                self._send_alert_for_drift(drift, analysis)
                for drift, analysis in alertable_drifts
            ]

            alerts = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter valid alerts
            valid_alerts = []
            for alert in alerts:
                if isinstance(alert, Exception):
                    logger.error(f"Failed to send alert: {alert}")
                elif alert:
                    valid_alerts.append(alert)

            logger.info(f"Successfully sent {len(valid_alerts)} alerts")
            return valid_alerts

        except Exception as e:
            logger.error(f"Alert processing failed: {e}", exc_info=True)
            raise

    def _should_alert(self, drift: DriftRecord, analysis: DriftAnalysis) -> bool:
        """
        Determine if an alert should be sent for this drift.

        Args:
            drift: Drift record
            analysis: AI analysis

        Returns:
            True if alert should be sent
        """
        # Always alert on critical severity
        if drift.severity.value == "critical":
            return True

        # Alert on high severity
        if drift.severity.value == "high":
            return True

        # Alert on medium severity if confidence is high
        if drift.severity.value == "medium" and analysis.confidence_score >= 70:
            return True

        # Don't alert on low severity
        return False

    def _is_duplicate_alert(self, drift: DriftRecord) -> bool:
        """
        Check if this drift was already alerted recently (deduplication).

        Args:
            drift: Drift record

        Returns:
            True if duplicate
        """
        # Create alert fingerprint
        fingerprint = self._create_alert_fingerprint(drift)

        # Check if we've alerted on this in the last hour
        if fingerprint in self.recent_alerts:
            last_alert_time = self.recent_alerts[fingerprint]
            if datetime.utcnow() - last_alert_time < timedelta(hours=1):
                return True

        # Mark as alerted
        self.recent_alerts[fingerprint] = datetime.utcnow()

        # Clean up old entries (older than 2 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        self.recent_alerts = {
            fp: ts for fp, ts in self.recent_alerts.items() if ts > cutoff_time
        }

        return False

    def _create_alert_fingerprint(self, drift: DriftRecord) -> str:
        """Create unique fingerprint for alert deduplication."""
        fingerprint_data = f"{drift.resource_id}-{drift.drift_type.value}-{drift.diff_hash}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()

    async def _send_alert_for_drift(
        self, drift: DriftRecord, analysis: DriftAnalysis
    ) -> Alert:
        """
        Send alerts for a single drift via appropriate channels.

        Args:
            drift: Drift record
            analysis: AI analysis

        Returns:
            Alert record
        """
        logger.debug(f"Sending alert for drift {drift.drift_id}")

        try:
            # Determine alert channels based on severity
            channels = self._determine_alert_channels(drift)

            # Create alert
            alert = self._create_alert(drift, analysis, channels)

            # Send to each channel
            tasks = []
            for channel in channels:
                if channel == "email":
                    tasks.append(self._send_email_alert(alert, drift, analysis))
                elif channel == "slack":
                    tasks.append(self._send_slack_alert(alert, drift, analysis))
                elif channel == "sns":
                    tasks.append(self._send_sns_alert(alert, drift, analysis))
                elif channel == "pagerduty":
                    tasks.append(self._send_pagerduty_alert(alert, drift, analysis))

            # Execute all channel sends in parallel
            await asyncio.gather(*tasks, return_exceptions=True)

            alert.sent_at = datetime.utcnow()

            logger.info(
                f"Alert {alert.alert_id} sent to channels: {', '.join(channels)}"
            )

            return alert

        except Exception as e:
            logger.error(f"Error sending alert for {drift.drift_id}: {e}", exc_info=True)
            raise

    def _determine_alert_channels(self, drift: DriftRecord) -> List[str]:
        """
        Determine which channels to use based on severity.

        Args:
            drift: Drift record

        Returns:
            List of channel names
        """
        severity = drift.severity.value

        # Escalation policy
        if severity == "critical":
            channels = ["email", "sns"]
            if settings.alert_slack_webhook_url:
                channels.append("slack")
            if settings.alert_pagerduty_api_key:
                channels.append("pagerduty")
        elif severity == "high":
            channels = ["email"]
            if settings.alert_slack_webhook_url:
                channels.append("slack")
        elif severity == "medium":
            channels = ["email"]
        else:  # low
            channels = []

        return channels

    def _create_alert(
        self, drift: DriftRecord, analysis: DriftAnalysis, channels: List[str]
    ) -> Alert:
        """Create alert record."""
        alert_id = f"alert-{drift.drift_id}-{int(datetime.utcnow().timestamp())}"

        title = f"🚨 Drift Detected: {drift.resource_type} ({drift.severity.value.upper()})"

        message = f"""
Drift detected in AWS resource:

Resource: {drift.resource_id}
Type: {drift.resource_type}
Severity: {drift.severity.value.upper()}
Account: {drift.account_id}
Region: {drift.region}

AI Analysis:
{analysis.explanation}

Root Cause:
{analysis.root_cause}

Business Impact:
{analysis.business_impact}

Recommended Action: {analysis.recommended_action}
Confidence: {analysis.confidence_score}%

View details: http://dashboard/drifts/{drift.drift_id}
""".strip()

        return Alert(
            alert_id=alert_id,
            drift_id=drift.drift_id,
            severity=drift.severity.value,
            title=title,
            message=message,
            channels=channels,
            metadata={
                "resource_id": drift.resource_id,
                "resource_type": drift.resource_type,
                "recommended_action": analysis.recommended_action,
            },
        )

    async def _send_email_alert(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> bool:
        """Send email alert via SES."""
        try:
            ses = self._get_ses_client()

            # Build HTML email
            html_body = self._build_html_email(alert, drift, analysis)

            response = await asyncio.to_thread(
                ses.send_email,
                Source=settings.ses_from_email,
                Destination={"ToAddresses": [settings.alert_email_to]},
                Message={
                    "Subject": {"Data": alert.title, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": alert.message, "Charset": "UTF-8"},
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                },
            )

            logger.info(f"Email alert sent: {response['MessageId']}")
            return True

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Email alert error: {e}", exc_info=True)
            return False

    async def _send_sns_alert(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> bool:
        """Send alert via SNS."""
        try:
            if not settings.sns_topic_arn:
                logger.debug("SNS topic ARN not configured")
                return False

            sns = self._get_sns_client()

            # Prepare message
            message_data = {
                "alert_id": alert.alert_id,
                "drift_id": drift.drift_id,
                "severity": drift.severity.value,
                "resource_id": drift.resource_id,
                "resource_type": drift.resource_type,
                "explanation": analysis.explanation,
                "recommended_action": analysis.recommended_action,
            }

            response = await asyncio.to_thread(
                sns.publish,
                TopicArn=settings.sns_topic_arn,
                Subject=alert.title,
                Message=json.dumps(message_data, indent=2),
            )

            logger.info(f"SNS alert sent: {response['MessageId']}")
            return True

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to send SNS alert: {e}")
            return False
        except Exception as e:
            logger.error(f"SNS alert error: {e}", exc_info=True)
            return False

    async def _send_slack_alert(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> bool:
        """Send alert to Slack via webhook."""
        try:
            if not settings.alert_slack_webhook_url:
                logger.debug("Slack webhook URL not configured")
                return False

            # Build Slack message
            slack_message = self._build_slack_message(alert, drift, analysis)

            # Send to webhook (would use aiohttp in production)
            import urllib.request

            req = urllib.request.Request(
                settings.alert_slack_webhook_url,
                data=json.dumps(slack_message).encode(),
                headers={"Content-Type": "application/json"},
            )

            await asyncio.to_thread(urllib.request.urlopen, req)

            logger.info(f"Slack alert sent for {alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"Slack alert error: {e}", exc_info=True)
            return False

    async def _send_pagerduty_alert(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> bool:
        """Send alert to PagerDuty."""
        try:
            if not settings.alert_pagerduty_api_key:
                logger.debug("PagerDuty API key not configured")
                return False

            # PagerDuty integration would go here
            logger.info(f"PagerDuty alert would be sent for {alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"PagerDuty alert error: {e}", exc_info=True)
            return False

    def _build_html_email(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> str:
        """Build HTML email body."""
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }

        color = severity_colors.get(drift.severity.value, "#6c757d")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
        .section {{ margin-bottom: 20px; }}
        .label {{ font-weight: bold; }}
        .button {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{alert.title}</h2>
        </div>
        <div class="content">
            <div class="section">
                <p class="label">Resource:</p>
                <p>{drift.resource_id} ({drift.resource_type})</p>
            </div>
            <div class="section">
                <p class="label">Location:</p>
                <p>Account: {drift.account_id} | Region: {drift.region}</p>
            </div>
            <div class="section">
                <p class="label">AI Analysis:</p>
                <p>{analysis.explanation}</p>
            </div>
            <div class="section">
                <p class="label">Root Cause:</p>
                <p>{analysis.root_cause}</p>
            </div>
            <div class="section">
                <p class="label">Business Impact:</p>
                <p>{analysis.business_impact}</p>
            </div>
            <div class="section">
                <p class="label">Recommended Action:</p>
                <p>{analysis.recommended_action} (Confidence: {analysis.confidence_score}%)</p>
            </div>
            <div class="section">
                <a href="http://dashboard/drifts/{drift.drift_id}" class="button">View Details</a>
            </div>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_slack_message(
        self, alert: Alert, drift: DriftRecord, analysis: DriftAnalysis
    ) -> Dict[str, Any]:
        """Build Slack message payload."""
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }

        emoji = severity_emoji.get(drift.severity.value, "⚪")

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Drift Detected",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Resource:*\n{drift.resource_id}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{drift.severity.value.upper()}"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{drift.resource_type}"},
                        {"type": "mrkdwn", "text": f"*Region:*\n{drift.region}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*AI Analysis:*\n{analysis.explanation}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommended Action:* {analysis.recommended_action}\n*Confidence:* {analysis.confidence_score}%",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "url": f"http://dashboard/drifts/{drift.drift_id}",
                        },
                    ],
                },
            ]
        }

