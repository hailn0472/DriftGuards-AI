"""Simple SMTP email service for sending alerts."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import asyncio

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SMTPEmailService:
    """Simple SMTP email service."""

    def __init__(self):
        """Initialize SMTP email service."""
        self.smtp_host = getattr(settings, "smtp_host", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "smtp_port", 587)
        self.smtp_username = getattr(settings, "smtp_username", None)
        self.smtp_password = getattr(settings, "smtp_password", None)
        self.smtp_use_tls = getattr(settings, "smtp_use_tls", True)
        self.from_email = settings.alert_email_from

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body

        Returns:
            True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Attach plain text
            msg.attach(MIMEText(body_text, "plain"))

            # Attach HTML if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Send email in thread pool to avoid blocking
            await asyncio.to_thread(self._send_smtp, msg, to_email)

            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"[{timestamp}] Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _send_smtp(self, msg: MIMEMultipart, to_email: str):
        """Send email via SMTP (blocking operation)."""
        # Connect to SMTP server
        if self.smtp_use_tls:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)

        try:
            # Login if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.send_message(msg)
            logger.debug(f"SMTP send successful to {to_email}")

        finally:
            server.quit()

    async def send_drift_alert(
        self,
        to_email: str,
        drift_id: str,
        resource_id: str,
        resource_type: str,
        severity: str,
        account_id: str,
        region: str,
        explanation: str,
        root_cause: str,
        business_impact: str,
        recommended_action: str,
        confidence_score: int,
    ) -> bool:
        """
        Send drift alert email.

        Args:
            to_email: Recipient email
            drift_id: Drift ID
            resource_id: AWS resource ID
            resource_type: Resource type
            severity: Drift severity
            account_id: AWS account ID
            region: AWS region
            explanation: AI explanation
            root_cause: Root cause analysis
            business_impact: Business impact
            recommended_action: Recommended action
            confidence_score: AI confidence score

        Returns:
            True if sent successfully
        """
        # Determine severity emoji and color
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }

        emoji = severity_emoji.get(severity.lower(), "⚪")
        color = severity_colors.get(severity.lower(), "#6c757d")

        # Email subject
        subject = f"{emoji} {severity.upper()} Drift Detected - {resource_id}"

        # Plain text body
        body_text = f"""
Drift Detected in AWS Resource

Resource: {resource_id}
Type: {resource_type}
Severity: {severity.upper()}
Account: {account_id}
Region: {region}

AI Analysis:
{explanation}

Root Cause:
{root_cause}

Business Impact:
{business_impact}

Recommended Action:
{recommended_action}

Confidence: {confidence_score}%

Drift ID: {drift_id}

---
DriftGuards AI - Infrastructure Drift Detection
        """.strip()

        # HTML body
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: {color};
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .header h2 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 0 0 8px 8px;
            border: 1px solid #dee2e6;
        }}
        .section {{
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border-left: 4px solid {color};
        }}
        .label {{
            font-weight: bold;
            color: #495057;
            margin-bottom: 5px;
        }}
        .value {{
            color: #212529;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .info-item {{
            padding: 10px;
            background: white;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }}
        .footer {{
            margin-top: 20px;
            padding: 15px;
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}
        .confidence {{
            display: inline-block;
            padding: 5px 10px;
            background: #e7f3ff;
            color: #0066cc;
            border-radius: 3px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{emoji} Drift Detected</h2>
            <p style="margin: 5px 0 0 0;">Severity: {severity.upper()}</p>
        </div>
        <div class="content">
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">Resource</div>
                    <div class="value">{resource_id}</div>
                </div>
                <div class="info-item">
                    <div class="label">Type</div>
                    <div class="value">{resource_type}</div>
                </div>
                <div class="info-item">
                    <div class="label">Account</div>
                    <div class="value">{account_id}</div>
                </div>
                <div class="info-item">
                    <div class="label">Region</div>
                    <div class="value">{region}</div>
                </div>
            </div>

            <div class="section">
                <div class="label">🤖 AI Analysis</div>
                <div class="value">{explanation}</div>
            </div>

            <div class="section">
                <div class="label">🔍 Root Cause</div>
                <div class="value">{root_cause}</div>
            </div>

            <div class="section">
                <div class="label">💼 Business Impact</div>
                <div class="value">{business_impact}</div>
            </div>

            <div class="section">
                <div class="label">✅ Recommended Action</div>
                <div class="value">{recommended_action}</div>
                <div style="margin-top: 10px;">
                    <span class="confidence">Confidence: {confidence_score}%</span>
                </div>
            </div>

            <div class="footer">
                <p>Drift ID: {drift_id}</p>
                <p>DriftGuards AI - Infrastructure Drift Detection</p>
            </div>
        </div>
    </div>
</body>
</html>
        """

        return await self.send_email(to_email, subject, body_text, body_html)


# Convenience function
async def send_drift_alert_email(
    drift_id: str,
    resource_id: str,
    resource_type: str,
    severity: str,
    account_id: str,
    region: str,
    explanation: str,
    root_cause: str,
    business_impact: str,
    recommended_action: str,
    confidence_score: int,
    to_email: Optional[str] = None,
) -> bool:
    """
    Send drift alert email using SMTP.

    Args:
        drift_id: Drift ID
        resource_id: AWS resource ID
        resource_type: Resource type
        severity: Drift severity
        account_id: AWS account ID
        region: AWS region
        explanation: AI explanation
        root_cause: Root cause
        business_impact: Business impact
        recommended_action: Recommended action
        confidence_score: AI confidence score
        to_email: Optional recipient email (uses settings.alert_email_to if not provided)

    Returns:
        True if sent successfully
    """
    service = SMTPEmailService()
    recipient = to_email or settings.alert_email_to

    return await service.send_drift_alert(
        to_email=recipient,
        drift_id=drift_id,
        resource_id=resource_id,
        resource_type=resource_type,
        severity=severity,
        account_id=account_id,
        region=region,
        explanation=explanation,
        root_cause=root_cause,
        business_impact=business_impact,
        recommended_action=recommended_action,
        confidence_score=confidence_score,
    )
