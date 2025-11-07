"""Alert Engine Agent - Simplified SMTP email only."""

import asyncio
import hashlib
from datetime import datetime, timedelta

from app.config import get_settings
from app.models.analysis import DriftAnalysis
from app.models.drift import DriftRecord
from app.models.metrics import MetricsContext
from app.services.smtp_email import send_drift_alert_email
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
        channels: list[str],
        metadata: dict | None = None,
    ):
        self.alert_id = alert_id
        self.drift_id = drift_id
        self.severity = severity
        self.title = title
        self.message = message
        self.channels = channels
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.sent_at: datetime | None = None


class AlertEngineAgent:
    """Agent for SMTP email alerting."""

    def __init__(self):
        self.recent_alerts: dict[str, datetime] = {}

    async def send_alerts(
        self,
        drift_records: list[DriftRecord],
        analyses: list[DriftAnalysis],
        metrics_contexts: list[MetricsContext] | None = None,
    ) -> list[Alert]:
        """Send alerts via email."""
        logger.info(f"Processing alerts for {len(drift_records)} drifts")
        try:
            drift_analysis_pairs = []
            analyses_by_drift = {a.drift_id: a for a in analyses}
            for drift in drift_records:
                analysis = analyses_by_drift.get(drift.drift_id)
                if analysis:
                    drift_analysis_pairs.append((drift, analysis))
            alertable_drifts = [
                (d, a)
                for d, a in drift_analysis_pairs
                if self._should_alert(d, a) and not self._is_duplicate_alert(d)
            ]
            tasks = [self._send_alert_for_drift(d, a) for d, a in alertable_drifts]
            alerts = await asyncio.gather(*tasks, return_exceptions=True)
            valid_alerts = [a for a in alerts if not isinstance(a, Exception) and a]
            logger.info(f"Sent {len(valid_alerts)} alerts")
            return valid_alerts
        except Exception as e:
            logger.error(f"Alert processing failed: {e}", exc_info=True)
            raise

    def _should_alert(self, drift: DriftRecord, analysis: DriftAnalysis) -> bool:
        if drift.severity.value in ["critical", "high"]:
            return True
        if drift.severity.value == "medium" and analysis.confidence_score >= 70:
            return True
        return False

    def _is_duplicate_alert(self, drift: DriftRecord) -> bool:
        fingerprint = hashlib.md5(
            f"{drift.resource_id}-{drift.drift_type.value}-{drift.diff_hash}".encode()
        ).hexdigest()
        if fingerprint in self.recent_alerts and datetime.utcnow() - self.recent_alerts[
            fingerprint
        ] < timedelta(hours=1):
            return True
        self.recent_alerts[fingerprint] = datetime.utcnow()
        return False

    async def _send_alert_for_drift(
        self, drift: DriftRecord, analysis: DriftAnalysis
    ) -> Alert | None:
        try:
            if drift.severity.value not in ["critical", "high", "medium"]:
                return None
            alert = Alert(
                alert_id=f"alert-{drift.drift_id}-{int(datetime.utcnow().timestamp())}",
                drift_id=drift.drift_id,
                severity=drift.severity.value,
                title=f"Drift: {drift.resource_type} ({drift.severity.value.upper()})",
                message=f"Resource: {drift.resource_id}",
                channels=["email"],
                metadata={"resource_id": drift.resource_id},
            )
            success = await send_drift_alert_email(
                drift_id=drift.drift_id,
                resource_id=drift.resource_id,
                resource_type=drift.resource_type,
                severity=drift.severity.value,
                account_id=drift.account_id,
                region=drift.region,
                explanation=analysis.explanation,
                root_cause=analysis.root_cause,
                business_impact=analysis.business_impact,
                recommended_action=analysis.recommended_action,
                confidence_score=analysis.confidence_score,
            )
            if success:
                alert.sent_at = datetime.utcnow()
                logger.info(f"Alert {alert.alert_id} sent")
            return alert
        except Exception as e:
            logger.error(f"Error sending alert: {e}", exc_info=True)
            raise
