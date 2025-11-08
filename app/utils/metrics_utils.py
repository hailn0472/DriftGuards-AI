"""
Metrics Analysis Utilities
Extracts and analyzes CloudWatch metrics for behavioral drift detection
"""

from typing import Any


def extract_metrics(resource: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract metrics_baseline from a resource.

    Args:
        resource: Resource dict that may contain metrics_baseline

    Returns:
        Metrics dict or None if not present
    """
    return resource.get("metrics_baseline")


def compare_metrics(
    baseline_metrics: dict[str, Any], current_metrics: dict[str, Any]
) -> dict[str, Any]:
    """
    Compare baseline and current metrics to detect anomalies.

    Args:
        baseline_metrics: Baseline metrics from stored state
        current_metrics: Current metrics from latest scan

    Returns:
        Dict with anomaly analysis results
    """
    anomalies = []

    # Thresholds for anomaly detection
    THRESHOLDS = {
        "cpuutilization": {"multiplier": 2.0, "severity": "high"},
        "networkin": {"multiplier": 3.0, "severity": "high"},
        "networkout": {"multiplier": 3.0, "severity": "high"},
        "invocations": {"multiplier": 10.0, "severity": "critical"},
        "errors": {"multiplier": 5.0, "severity": "high"},
        "throttles": {"multiplier": 2.0, "severity": "medium"},
        "databaseconnections": {"multiplier": 10.0, "severity": "medium"},
        "diskreadbytes": {"multiplier": 5.0, "severity": "medium"},
        "diskwritebytes": {"multiplier": 5.0, "severity": "medium"},
    }

    # Compare each metric
    for metric_name in baseline_metrics.keys():
        if metric_name not in current_metrics:
            continue

        baseline = baseline_metrics[metric_name]
        current = current_metrics[metric_name]

        # Skip if not dict (shouldn't happen)
        if not isinstance(baseline, dict) or not isinstance(current, dict):
            continue

        baseline_avg = baseline.get("average", 0)
        current_avg = current.get("average", 0)
        baseline_max = baseline.get("maximum", 0)
        current_max = current.get("maximum", 0)

        # Get threshold for this metric
        threshold_config = THRESHOLDS.get(metric_name, {"multiplier": 2.0, "severity": "medium"})
        multiplier = threshold_config["multiplier"]

        # Check for anomalies
        is_anomaly = False
        reason = None

        # Average increased significantly
        if baseline_avg > 0 and current_avg > (baseline_avg * multiplier):
            is_anomaly = True
            change_percent = ((current_avg - baseline_avg) / baseline_avg) * 100
            reason = f"Average {metric_name} increased {change_percent:.1f}% ({baseline_avg:.2f} → {current_avg:.2f})"

        # Max spiked beyond baseline max
        elif current_max > (baseline_max * 1.5):
            is_anomaly = True
            reason = f"Maximum {metric_name} spiked ({baseline_max:.2f} → {current_max:.2f})"

        if is_anomaly:
            anomalies.append(
                {
                    "metric": metric_name,
                    "severity": threshold_config["severity"],
                    "baseline_avg": baseline_avg,
                    "current_avg": current_avg,
                    "baseline_max": baseline_max,
                    "current_max": current_max,
                    "multiplier": current_avg / baseline_avg if baseline_avg > 0 else 0,
                    "reason": reason,
                }
            )

    return {
        "has_anomalies": len(anomalies) > 0,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "risk_level": _calculate_risk_level(anomalies),
    }


def _calculate_risk_level(anomalies: list[dict[str, Any]]) -> str:
    """Calculate overall risk level from anomalies."""
    if not anomalies:
        return "none"

    # Count by severity
    critical_count = sum(1 for a in anomalies if a.get("severity") == "critical")
    high_count = sum(1 for a in anomalies if a.get("severity") == "high")
    medium_count = sum(1 for a in anomalies if a.get("severity") == "medium")

    if critical_count > 0:
        return "critical"
    elif high_count >= 2:
        return "high"
    elif high_count > 0 or medium_count >= 3:
        return "medium"
    else:
        return "low"


def get_metrics_summary(resource: dict[str, Any]) -> str:
    """
    Get human-readable metrics summary for AI analysis.

    Args:
        resource: Resource dict with metrics_baseline

    Returns:
        Formatted string summary of metrics
    """
    metrics = extract_metrics(resource)
    if not metrics:
        return "No metrics available"

    lines = ["Metrics Baseline (24h average):"]

    metric_labels = {
        "cpuutilization": "CPU Utilization",
        "networkin": "Network In",
        "networkout": "Network Out",
        "diskreadbytes": "Disk Read",
        "diskwritebytes": "Disk Write",
        "invocations": "Invocations",
        "duration": "Duration",
        "errors": "Errors",
        "throttles": "Throttles",
        "concurrentexecutions": "Concurrent Executions",
        "databaseconnections": "DB Connections",
        "freeablememory": "Free Memory",
    }

    for metric_name, metric_data in metrics.items():
        if not isinstance(metric_data, dict):
            continue

        label = metric_labels.get(metric_name, metric_name.title())
        avg = metric_data.get("average", 0)
        max_val = metric_data.get("maximum", 0)

        # Format based on metric type
        if "cpu" in metric_name.lower():
            lines.append(f"  • {label}: {avg:.1f}% avg, {max_val:.1f}% max")
        elif "network" in metric_name.lower() or "disk" in metric_name.lower():
            lines.append(f"  • {label}: {_format_bytes(avg)} avg, {_format_bytes(max_val)} max")
        elif "duration" in metric_name.lower():
            lines.append(f"  • {label}: {avg:.0f}ms avg, {max_val:.0f}ms max")
        elif "memory" in metric_name.lower():
            lines.append(f"  • {label}: {_format_bytes(avg)}")
        else:
            lines.append(f"  • {label}: {avg:.1f} avg, {max_val:.1f} max")

    return "\n".join(lines)


def _format_bytes(bytes_val: float) -> str:
    """Format bytes into human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}PB"


def should_alert_on_metrics(
    baseline_resource: dict[str, Any], current_resource: dict[str, Any]
) -> tuple[bool, str]:
    """
    Check if metrics anomalies warrant an alert.

    Args:
        baseline_resource: Baseline resource with metrics
        current_resource: Current resource with metrics

    Returns:
        Tuple of (should_alert, reason)
    """
    baseline_metrics = extract_metrics(baseline_resource)
    current_metrics = extract_metrics(current_resource)

    if not baseline_metrics or not current_metrics:
        return False, "No metrics to compare"

    analysis = compare_metrics(baseline_metrics, current_metrics)

    if not analysis["has_anomalies"]:
        return False, "No anomalies detected"

    risk_level = analysis["risk_level"]
    anomaly_count = analysis["anomaly_count"]

    if risk_level in ["critical", "high"]:
        reasons = [a["reason"] for a in analysis["anomalies"]]
        return True, f"{anomaly_count} {risk_level} anomalies: " + "; ".join(reasons)

    return False, "Anomalies below alert threshold"
