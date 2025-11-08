"""Simple Streamlit Dashboard for DriftGuards AI."""

# Load .env file FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()  # This loads AWS credentials from .env

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.drift import ScanRequest
from app.models.approval import ApprovalRequest
from app.services.approval_service import ApprovalService
from app.workflows import DriftGuardsWorkflow

# Import revert utilities from new location
from app.revert.boto3_revert import (
    boto3_revert_to_baseline,
    boto3_terminate_resource,
    load_baseline_config,
)
from app.revert.selective_revert import (
    selective_revert,
    get_available_fields,
    parse_diff_from_drift,
)

# Constants
DEFAULT_CRON_EXPRESSION = "0 * * * *"  # Every hour


# Helper function to safely print Unicode (emojis) on Windows
def safe_print(message):
    """Print message, handling Unicode encoding errors on Windows."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remove emojis and special characters, keep the text
        import re

        ascii_message = re.sub(r"[^\x00-\x7F]+", "", message)
        print(ascii_message)


# Page config
st.set_page_config(
    page_title="DriftGuards AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .drift-critical {
        background-color: #fee;
        border-left: 5px solid #dc2626;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .drift-high {
        background-color: #fff4e6;
        border-left: 5px solid #ea580c;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .drift-medium {
        background-color: #fffbeb;
        border-left: 5px solid #ca8a04;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .drift-low {
        background-color: #f0fdf4;
        border-left: 5px solid #16a34a;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "drifts" not in st.session_state:
    st.session_state.drifts = []
if "analyses" not in st.session_state:
    st.session_state.analyses = []
if "violations" not in st.session_state:
    st.session_state.violations = []
if "scanning" not in st.session_state:
    st.session_state.scanning = False
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None
if "auto_scan_enabled" not in st.session_state:
    st.session_state.auto_scan_enabled = False
if "scan_schedule" not in st.session_state:
    st.session_state.scan_schedule = "hourly"
if "cron_expression" not in st.session_state:
    st.session_state.cron_expression = DEFAULT_CRON_EXPRESSION
if "notifications_enabled" not in st.session_state:
    st.session_state.notifications_enabled = True
if "auto_remediation" not in st.session_state:
    st.session_state.auto_remediation = False
if "next_auto_scan" not in st.session_state:
    st.session_state.next_auto_scan = None
if "auto_scan_accounts" not in st.session_state:
    st.session_state.auto_scan_accounts = ["961639320333"]
if "auto_scan_regions" not in st.session_state:
    st.session_state.auto_scan_regions = ["ap-southeast-1"]
if "auto_scan_resource_types" not in st.session_state:
    st.session_state.auto_scan_resource_types = [
        "ec2_instances",
        "rds_instances",
        "rds_clusters",
        "s3_buckets",
        "dynamodb_tables",
        "sqs_queues",
        "lambda_functions",
        "ecs_clusters",
        "eks_clusters",
    ]


def get_severity_color(severity):
    """Get color for severity level."""
    colors = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }
    return colors.get(severity, "⚪")


def get_severity_class(severity):
    """Get CSS class for severity."""
    return f"drift-{severity.lower()}"


async def run_scan(accounts, regions, resource_types):
    """Run drift detection scan."""
    import pytz

    st.session_state.scanning = True

    # Create workflow
    workflow = DriftGuardsWorkflow()

    # Create scan request
    scan_request = ScanRequest(
        accounts=accounts,
        regions=regions,
        resource_types=resource_types,
        force_refresh=False,
    )

    # Run workflow
    try:
        with st.spinner("🔍 Scanning for drifts..."):
            final_state = await workflow.run(scan_request)

        # Store results with UTC+7 timezone
        utc_plus_7 = pytz.timezone("Asia/Bangkok")
        st.session_state.drifts = final_state.get("drift_records", [])
        st.session_state.analyses = final_state.get("ai_analysis", [])
        st.session_state.violations = final_state.get("policy_violations", [])
        st.session_state.last_scan = datetime.now(utc_plus_7)
        st.session_state.scanning = False

        # Show success message
        if len(st.session_state.drifts) == 0:
            st.success(
                "✅ Scan completed successfully! No drifts detected. Your infrastructure is in sync with baseline."
            )
        else:
            st.warning(f"⚠️ Scan completed: {len(st.session_state.drifts)} drift(s) detected")

        return True
    except Exception as e:
        st.error(f"❌ Scan failed: {str(e)}")
        st.session_state.scanning = False
        return False


def display_drift_card(drift, analysis=None):
    """Display a drift card."""
    severity_class = get_severity_class(drift.severity.value)
    severity_icon = get_severity_color(drift.severity.value)

    st.markdown(f'<div class="{severity_class}">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.markdown(f"### {severity_icon} {drift.resource_id}")
        st.caption(f"**Type:** {drift.resource_type} | **Drift:** {drift.drift_type.value}")

    with col2:
        st.metric("Severity", drift.severity.value)

    with col3:
        st.caption(f"**Account:** {drift.account_id}")
        st.caption(f"**Region:** {drift.region}")

    # Show diff
    if drift.diff:
        with st.expander("📋 View Changes"):
            st.json(drift.diff)

    # Show AI analysis
    if analysis:
        with st.expander("🤖 AI Analysis"):
            st.markdown(f"**Root Cause:** {analysis.root_cause}")
            st.markdown(f"**Business Impact:** {analysis.business_impact}")
            st.markdown(f"**Recommended Action:** {analysis.recommended_action}")
            st.markdown(f"**Confidence:** {analysis.confidence_score}%")

            if analysis.remediation_steps:
                st.markdown("**Remediation Steps:**")
                for i, step in enumerate(analysis.remediation_steps, 1):
                    st.markdown(f"{i}. {step}")

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Approve", key=f"approve_{drift.drift_id}"):
            st.success("Drift approved!")
    with col2:
        if st.button("🔄 Remediate", key=f"remediate_{drift.drift_id}"):
            st.info("Remediation initiated...")
    with col3:
        if st.button("❌ Suppress", key=f"suppress_{drift.drift_id}"):
            st.warning("Drift suppressed")
    with col4:
        if st.button("📊 Details", key=f"details_{drift.drift_id}"):
            st.info("Opening detailed view...")

    st.markdown("</div>", unsafe_allow_html=True)


def check_and_run_auto_scan():
    """Check if auto-scan should run and execute it."""
    from datetime import datetime, timedelta
    import pytz

    if not st.session_state.auto_scan_enabled:
        return False

    if st.session_state.scanning:
        return False  # Already scanning

    # Use UTC+7 timezone
    utc_plus_7 = pytz.timezone("Asia/Bangkok")
    now = datetime.now(utc_plus_7)

    # Calculate next scan time based on schedule
    if st.session_state.last_scan:
        schedule_intervals = {
            "1min": timedelta(minutes=1),
            "15min": timedelta(minutes=15),
            "30min": timedelta(minutes=30),
            "hourly": timedelta(hours=1),
            "6hours": timedelta(hours=6),
            "12hours": timedelta(hours=12),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }

        schedule = st.session_state.scan_schedule
        interval = schedule_intervals.get(schedule, timedelta(hours=1))

        # Make sure last_scan is timezone-aware
        last_scan = st.session_state.last_scan
        if last_scan.tzinfo is None:
            last_scan = utc_plus_7.localize(last_scan)

        next_scan = last_scan + interval

        # Store next scan time
        st.session_state.next_auto_scan = next_scan

        # Check if it's time to scan
        if now >= next_scan:
            return True
        else:
            return False
    else:
        # No previous scan - don't auto-run, wait for manual trigger
        return False

    return False


# Main app
def main():
    """Main dashboard."""
    # Load latest auto-scan results if available
    auto_scan_file = Path(__file__).parent / "latest_auto_scan.json"
    if auto_scan_file.exists():
        try:
            import pytz

            with open(auto_scan_file) as f:
                auto_results = json.load(f)

            # Check if results are newer than current session
            scan_time_str = auto_results.get("scan_time")
            if scan_time_str:
                scan_time = datetime.fromisoformat(scan_time_str)

                # Only load if newer than current last_scan
                if not st.session_state.last_scan or scan_time > st.session_state.last_scan:
                    # Convert dict results back to proper format
                    st.session_state.drifts = auto_results.get("drifts", [])
                    st.session_state.analyses = auto_results.get("analyses", [])
                    st.session_state.violations = auto_results.get("violations", [])

                    # Make timezone-aware
                    utc_plus_7 = pytz.timezone("Asia/Bangkok")
                    if scan_time.tzinfo is None:
                        scan_time = utc_plus_7.localize(scan_time)
                    st.session_state.last_scan = scan_time

                    # Show notification about auto-scan
                    if auto_results.get("status") == "success":
                        drift_count = auto_results.get("drift_count", 0)
                        if drift_count > 0:
                            st.info(f"🔄 Auto-scan completed: {drift_count} drift(s) detected")
        except Exception as e:
            # Silently fail if file is corrupted
            pass

    # Auto-refresh for checking new scan results (every 30 seconds)
    if st.session_state.auto_scan_enabled:
        import time

        # Add auto-refresh meta tag
        refresh_interval = 30  # seconds
        st.markdown(
            f'<meta http-equiv="refresh" content="{refresh_interval}">',
            unsafe_allow_html=True,
        )

    # Header
    st.title("🛡️ DriftGuards AI - Drift Detection Dashboard")

    if st.session_state.last_scan:
        st.caption(f"Last scan: {st.session_state.last_scan.strftime('%Y-%m-%d %H:%M:%S')}")

    # Sidebar - Scan Configuration
    st.sidebar.header("🔧 Scan Configuration")

    # AWS Accounts
    accounts_input = st.sidebar.text_input(
        "AWS Account IDs",
        value="961639320333",
        help="Comma-separated account IDs",
    )
    accounts = [acc.strip() for acc in accounts_input.split(",") if acc.strip()]

    # Regions
    regions = st.sidebar.multiselect(
        "Regions",
        ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
        default=["ap-southeast-1"],
    )

    # Resource Types - Auto fetch all
    resource_types = [
        "ec2_instances",
        "rds_instances",
        "rds_clusters",
        "s3_buckets",
        "dynamodb_tables",
        "sqs_queues",
        "lambda_functions",
        "ecs_clusters",
        "eks_clusters",
    ]
    st.sidebar.caption("📦 Resources: All types (auto)")

    # Scan button
    if st.sidebar.button("🔍 Start Scan", type="primary", disabled=st.session_state.scanning):
        if not accounts:
            st.sidebar.error("Please enter at least one AWS account ID")
        elif not regions:
            st.sidebar.error("Please select at least one region")
        else:
            # Save scan parameters for auto-scan
            st.session_state.auto_scan_accounts = accounts
            st.session_state.auto_scan_regions = regions
            st.session_state.auto_scan_resource_types = resource_types

            asyncio.run(run_scan(accounts, regions, resource_types))
            st.rerun()

    st.sidebar.markdown("---")

    # Configuration section
    st.sidebar.header("⚙️ Configuration")

    # Auto-scan toggle
    auto_scan = st.sidebar.toggle(
        "🔄 Auto Scan",
        value=st.session_state.auto_scan_enabled,
        help="Enable automatic drift scanning on schedule",
    )
    st.session_state.auto_scan_enabled = auto_scan

    if auto_scan:
        # Schedule selector
        schedule_options = {
            "Every 1 minute": "1min",
            "Every 15 minutes": "15min",
            "Every 30 minutes": "30min",
            "Hourly": "hourly",
            "Every 6 hours": "6hours",
            "Every 12 hours": "12hours",
            "Daily": "daily",
            "Weekly": "weekly",
        }

        selected_schedule = st.sidebar.selectbox(
            "📅 Scan Schedule",
            options=list(schedule_options.keys()),
            index=3,  # Default to "Hourly"
            help="How often to automatically scan for drifts",
        )
        st.session_state.scan_schedule = schedule_options[selected_schedule]

        # Show next scan time
        if st.session_state.last_scan:
            import pytz
            from datetime import timedelta

            schedule_intervals = {
                "1min": timedelta(minutes=1),
                "15min": timedelta(minutes=15),
                "30min": timedelta(minutes=30),
                "hourly": timedelta(hours=1),
                "6hours": timedelta(hours=6),
                "12hours": timedelta(hours=12),
                "daily": timedelta(days=1),
                "weekly": timedelta(weeks=1),
            }

            schedule = st.session_state.scan_schedule
            interval = schedule_intervals.get(schedule, timedelta(hours=1))

            # Make sure last_scan is timezone-aware (UTC+7)
            utc_plus_7 = pytz.timezone("Asia/Bangkok")
            last_scan = st.session_state.last_scan
            if last_scan.tzinfo is None:
                last_scan = utc_plus_7.localize(last_scan)

            next_scan = last_scan + interval

            st.session_state.next_auto_scan = next_scan

            # Show next scan time with countdown
            now = datetime.now(utc_plus_7)
            time_until_scan = next_scan - now
            seconds_remaining = int(time_until_scan.total_seconds())

            if seconds_remaining > 0:
                if seconds_remaining < 60:
                    time_str = f"{seconds_remaining}s"
                elif seconds_remaining < 3600:
                    time_str = f"{seconds_remaining // 60}m {seconds_remaining % 60}s"
                else:
                    hours = seconds_remaining // 3600
                    minutes = (seconds_remaining % 3600) // 60
                    time_str = f"{hours}h {minutes}m"

                st.sidebar.success(f"⏰ Next scan: {next_scan.strftime('%H:%M:%S')}")
                st.sidebar.caption(f"⏳ In {time_str}")
            else:
                st.sidebar.warning("⏰ Scan overdue - will run on next refresh")

    # Notifications toggle
    notifications = st.sidebar.toggle(
        "🔔 Notifications",
        value=st.session_state.notifications_enabled,
        help="Send alerts when drifts are detected",
    )
    st.session_state.notifications_enabled = notifications

    if notifications:
        notification_channels = st.sidebar.multiselect(
            "Notification Channels",
            ["Email", "Slack", "MS Teams", "SNS"],
            default=["Email"],
            help="Where to send drift alerts",
        )

    # Auto-remediation toggle (dangerous!)
    auto_remediation = st.sidebar.toggle(
        "⚡ Auto Remediation",
        value=st.session_state.auto_remediation,
        help="⚠️ Automatically revert drifts (use with caution!)",
    )
    st.session_state.auto_remediation = auto_remediation

    if auto_remediation:
        st.sidebar.warning(
            "⚠️ Auto-remediation is enabled! Low severity drifts will be automatically reverted."
        )
        auto_remediation_severity = st.sidebar.multiselect(
            "Auto-remediate severities",
            ["LOW", "MEDIUM"],
            default=["LOW"],
            help="Which severity levels to automatically remediate",
        )

    # Save configuration button
    if st.sidebar.button("💾 Save Configuration", use_container_width=True):
        try:
            config = {
                "auto_scan_enabled": st.session_state.auto_scan_enabled,
                "scan_schedule": st.session_state.scan_schedule,
                "cron_expression": st.session_state.cron_expression,
                "notifications_enabled": st.session_state.notifications_enabled,
                "auto_remediation": st.session_state.auto_remediation,
                "auto_scan_accounts": st.session_state.auto_scan_accounts,
                "auto_scan_regions": st.session_state.auto_scan_regions,
                "auto_scan_resource_types": st.session_state.auto_scan_resource_types,
            }
            config_file = Path(__file__).parent / "drift_config.json"

            # Save with explicit encoding
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # Log the save operation (visible in terminal) - safe Unicode handling
            safe_print(f"✅ Configuration saved to {config_file}")
            safe_print(f"   Auto-scan enabled: {config['auto_scan_enabled']}")
            safe_print(f"   Schedule: {config['scan_schedule']}")
            safe_print(f"   Accounts: {config['auto_scan_accounts']}")
            safe_print(f"   Regions: {config['auto_scan_regions']}")

            # Show detailed success message
            st.sidebar.success("✅ Configuration saved!")
            st.sidebar.info(f"📁 Saved to: drift_config.json")

            # Show configuration summary
            with st.sidebar.expander("📋 Saved Configuration", expanded=True):
                st.write(
                    f"**Auto-scan**: {'✅ Enabled' if config['auto_scan_enabled'] else '❌ Disabled'}"
                )
                st.write(f"**Schedule**: {config['scan_schedule']}")
                st.write(f"**Accounts**: {', '.join(config['auto_scan_accounts'])}")
                st.write(f"**Regions**: {', '.join(config['auto_scan_regions'])}")
                st.write(f"**Resource types**: {len(config['auto_scan_resource_types'])} types")

                if config["auto_scan_enabled"]:
                    st.success("🚀 Auto-scan is active! Run the scheduler:")
                    st.code("python app/dashboard/auto_scheduler.py", language="bash")
                else:
                    st.warning("⏸️ Auto-scan is disabled")

        except Exception as e:
            # Use safe print for error logging
            safe_print(f"❌ Error saving configuration: {e}")

            st.sidebar.error(f"❌ Error saving configuration: {str(e)}")
            import traceback

            safe_print(traceback.format_exc())
            st.sidebar.code(traceback.format_exc())

    # Load from file button
    output_dir = Path(__file__).parent / "output"
    if output_dir.exists():
        json_files = sorted(output_dir.glob("detection_results_*.json"), reverse=True)
        if json_files:
            selected_file = st.sidebar.selectbox(
                "Select scan file",
                json_files,
                format_func=lambda x: x.name,
            )
            if st.sidebar.button("📥 Load Scan Results"):
                try:
                    # Load detection results
                    with open(selected_file) as f:
                        detection_data = json.load(f)
                        st.session_state.drifts = detection_data.get("drifts", [])
                        st.session_state.last_scan = datetime.fromisoformat(
                            detection_data["metadata"]["timestamp"]
                        )

                    # Try to load AI analysis results
                    timestamp = selected_file.stem.replace("detection_results_", "")
                    analysis_file = output_dir / f"analysis_results_{timestamp}.json"
                    if analysis_file.exists():
                        with open(analysis_file) as f:
                            analysis_data = json.load(f)
                            st.session_state.analyses = analysis_data.get("analyses", [])

                    # Try to load policy violations
                    violations_file = output_dir / f"policy_violations_{timestamp}.json"
                    if violations_file.exists():
                        with open(violations_file) as f:
                            violations_data = json.load(f)
                            st.session_state.violations = violations_data.get("violations", [])

                    st.sidebar.success(f"✅ Loaded {len(st.session_state.drifts)} drifts")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Error loading scan: {str(e)}")

    # Main content
    if not st.session_state.drifts:
        # Check if a scan was recently completed
        if st.session_state.last_scan:
            # Scan was done but no drifts found
            st.success("✅ No drifts detected!")
            st.markdown("### 🎉 Your Infrastructure is Healthy")
            st.info(
                f"Last scan: {st.session_state.last_scan.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "All resources are in sync with baseline configuration."
            )

            # Show what was scanned
            st.markdown("---")
            st.markdown("### 📋 Scan Summary")
            st.markdown("- ✅ No configuration drifts detected")
            st.markdown("- ✅ All resources match baseline state")
            st.markdown("- ✅ No policy violations found")

            st.info("💡 Tip: Run periodic scans to ensure continued compliance")
        else:
            # No scan has been run yet
            st.info("👆 Click 'Start Scan' to detect drifts or load a previous scan")
            st.markdown("---")
            st.markdown("### 📊 Dashboard Features:")
            st.markdown("- **🔍 Scan:** Detect configuration drifts in your AWS infrastructure")
            st.markdown("- **📋 Drifts:** View all detected drifts with severity levels")
            st.markdown("- **🤖 AI Analysis:** Get intelligent recommendations for each drift")
            st.markdown("- **⚡ Actions:** Approve, remediate, or suppress drifts")
    else:
        # Summary metrics
        st.markdown("### 📊 Drift Summary")
        col1, col2, col3, col4 = st.columns(4)

        drifts = st.session_state.drifts

        # Handle both DriftRecord objects and dict
        def get_severity(d):
            if hasattr(d, "severity"):
                return (
                    d.severity.value.upper()
                    if hasattr(d.severity, "value")
                    else str(d.severity).upper()
                )
            return d.get("severity", "").upper()

        critical = sum(1 for d in drifts if get_severity(d) == "CRITICAL")
        high = sum(1 for d in drifts if get_severity(d) == "HIGH")
        medium = sum(1 for d in drifts if get_severity(d) == "MEDIUM")
        low = sum(1 for d in drifts if get_severity(d) == "LOW")

        with col1:
            st.metric("🔴 Critical", critical)
        with col2:
            st.metric("🟠 High", high)
        with col3:
            st.metric("🟡 Medium", medium)
        with col4:
            st.metric("🟢 Low", low)

        st.markdown("---")

        # Filters
        st.markdown("### 🎯 Filters")
        col1, col2, col3 = st.columns(3)

        with col1:
            severity_filter = st.multiselect(
                "Severity",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            )

        with col2:
            # Get resource types from drifts
            resource_types_in_drifts = list(
                {
                    d.resource_type if hasattr(d, "resource_type") else d.get("resource_type")
                    for d in drifts
                }
            )
            resource_filter = st.multiselect(
                "Resource Type",
                resource_types_in_drifts,
                default=resource_types_in_drifts,
            )

        with col3:
            # Get drift types from drifts
            drift_types_list = list(
                {
                    d.drift_type.value
                    if hasattr(d, "drift_type") and hasattr(d.drift_type, "value")
                    else (str(d.drift_type) if hasattr(d, "drift_type") else d.get("drift_type"))
                    for d in drifts
                }
            )
            drift_type_filter = st.multiselect(
                "Drift Type", drift_types_list, default=drift_types_list
            )

        # Filter drifts
        filtered_drifts = []
        for d in drifts:
            severity = get_severity(d)
            resource_type = (
                d.resource_type if hasattr(d, "resource_type") else d.get("resource_type")
            )
            drift_type = (
                d.drift_type.value
                if hasattr(d, "drift_type") and hasattr(d.drift_type, "value")
                else (str(d.drift_type) if hasattr(d, "drift_type") else d.get("drift_type"))
            )

            if (
                severity in severity_filter
                and resource_type in resource_filter
                and drift_type in drift_type_filter
            ):
                filtered_drifts.append(d)

        st.markdown("---")
        st.markdown(f"### ⚠️ Detected Drifts ({len(filtered_drifts)})")

        if not filtered_drifts:
            st.info("No drifts match the selected filters")
        else:
            # Display drifts (handle both DriftRecord objects and dicts)
            for drift in filtered_drifts:
                # Extract values - handle both objects and dicts
                if hasattr(drift, "drift_id"):
                    # It's a DriftRecord object
                    drift_id = drift.drift_id
                    resource_id = drift.resource_id
                    resource_type = drift.resource_type
                    drift_type_val = (
                        drift.drift_type.value
                        if hasattr(drift.drift_type, "value")
                        else str(drift.drift_type)
                    )
                    severity = (
                        drift.severity.value.upper()
                        if hasattr(drift.severity, "value")
                        else str(drift.severity).upper()
                    )
                    account_id = drift.account_id
                    region = drift.region
                    diff = drift.diff
                else:
                    # It's a dict
                    drift_id = drift.get("drift_id")
                    resource_id = drift.get("resource_id")
                    resource_type = drift.get("resource_type")
                    drift_type_val = drift.get("drift_type")
                    severity = drift.get("severity", "").upper()
                    account_id = drift.get("account_id")
                    region = drift.get("region")
                    diff = drift.get("diff")

                severity_icon = get_severity_color(severity)
                severity_class = get_severity_class(severity)

                st.markdown(f'<div class="{severity_class}">', unsafe_allow_html=True)

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"### {severity_icon} {resource_id}")
                    st.caption(f"**Type:** {resource_type} | **Drift:** {drift_type_val}")

                with col2:
                    st.metric("Severity", severity)

                with col3:
                    st.caption(f"**Account:** {account_id}")
                    st.caption(f"**Region:** {region}")

                # Show diff
                if diff:
                    with st.expander("📋 View Changes"):
                        st.json(diff)

                # Show AI Analysis if available
                matching_analysis = None
                for a in st.session_state.analyses:
                    a_drift_id = a.drift_id if hasattr(a, "drift_id") else a.get("drift_id")
                    if a_drift_id == drift_id:
                        matching_analysis = a
                        break

                if matching_analysis:
                    with st.expander("🤖 AI Analysis"):
                        # Handle both object and dict
                        if hasattr(matching_analysis, "root_cause"):
                            root_cause = matching_analysis.root_cause
                            business_impact = matching_analysis.business_impact
                            recommended_action = matching_analysis.recommended_action
                            confidence = matching_analysis.confidence_score
                            remediation_steps = matching_analysis.remediation_steps
                        else:
                            root_cause = matching_analysis.get("root_cause", "N/A")
                            business_impact = matching_analysis.get("business_impact", "N/A")
                            recommended_action = matching_analysis.get("recommended_action", "N/A")
                            confidence = matching_analysis.get("confidence_score", 0)
                            remediation_steps = matching_analysis.get("remediation_steps", [])

                        st.markdown(f"**Root Cause:** {root_cause}")
                        st.markdown(f"**Business Impact:** {business_impact}")
                        st.markdown(f"**Recommended Action:** {recommended_action}")
                        st.markdown(f"**Confidence:** {confidence}%")

                        if remediation_steps:
                            st.markdown("**Remediation Steps:**")
                            for i, step in enumerate(remediation_steps, 1):
                                st.markdown(f"{i}. {step}")

                # Show Policy Violations if available
                matching_violations = []
                for v in st.session_state.violations:
                    # Safely get drift_id from either object or dict
                    if hasattr(v, "drift_id"):
                        v_drift_id = v.drift_id
                    elif isinstance(v, dict):
                        v_drift_id = v.get("drift_id")
                    else:
                        continue  # Skip if neither object nor dict

                    if v_drift_id == drift_id:
                        matching_violations.append(v)
                if matching_violations:
                    with st.expander(f"⚖️ Policy Violations ({len(matching_violations)})"):
                        for violation in matching_violations:
                            # Handle both object and dict
                            if hasattr(violation, "policy_id"):
                                policy_id = violation.policy_id
                                message = violation.message
                                v_severity = violation.severity
                                action_required = violation.action_required
                            elif isinstance(violation, dict):
                                policy_id = violation.get("policy_id")
                                message = violation.get("message")
                                v_severity = violation.get("severity")
                                action_required = violation.get("action_required")
                            else:
                                continue  # Skip invalid violation

                            st.markdown(f"**{policy_id}:** {message}")
                            st.caption(f"Severity: {v_severity} | Action: {action_required}")

                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    # Check if approval form is open
                    approval_form_key = f"show_approval_form_{drift_id}"
                    if approval_form_key not in st.session_state:
                        st.session_state[approval_form_key] = False

                    if not st.session_state[approval_form_key]:
                        if st.button(
                            "✅ Approve Drift",
                            key=f"approve_btn_{drift_id}",
                            use_container_width=True,
                        ):
                            st.session_state[approval_form_key] = True
                            st.rerun()
                    else:
                        # Show approval form
                        with st.form(key=f"approval_form_{drift_id}"):
                            st.subheader("📝 Approve Drift")

                            # Get current user (from session/auth)
                            approved_by = st.text_input(
                                "Your Name/Email *",
                                value=st.session_state.get("username", ""),
                                key=f"approver_{drift_id}",
                                placeholder="admin@example.com",
                            )

                            # Approval reason
                            reason = st.text_area(
                                "Reason for Approval",
                                placeholder="Why is this change acceptable? (optional)",
                                key=f"reason_{drift_id}",
                                height=100,
                            )

                            # Options
                            st.markdown("**Options:**")
                            update_baseline = st.checkbox(
                                "Update baseline with this configuration",
                                value=True,
                                help="Make this the new expected state",
                                key=f"update_baseline_{drift_id}",
                            )

                            notify = st.checkbox(
                                "Send notifications",
                                value=False,
                                help="Notify team about this approval",
                                key=f"notify_{drift_id}",
                            )

                            # Submit buttons
                            col_submit, col_cancel = st.columns(2)

                            with col_submit:
                                submitted = st.form_submit_button(
                                    "✅ Confirm Approval", use_container_width=True, type="primary"
                                )

                            with col_cancel:
                                cancelled = st.form_submit_button(
                                    "❌ Cancel", use_container_width=True
                                )

                            if submitted:
                                if not approved_by:
                                    st.error("⚠️ Please enter your name or email")
                                else:
                                    try:
                                        # Initialize approval service
                                        approval_service = ApprovalService()

                                        # Create approval request
                                        approval_req = ApprovalRequest(
                                            drift_id=drift_id,
                                            approved_by=approved_by,
                                            reason=reason if reason else None,
                                            update_baseline=update_baseline,
                                            notify=notify,
                                        )

                                        # Process approval
                                        with st.spinner("⏳ Processing approval..."):
                                            approval = asyncio.run(
                                                approval_service.approve_drift(drift, approval_req)
                                            )

                                        st.success(
                                            f"✅ Drift approved by {approved_by}!\n\n"
                                            f"Approval ID: `{approval.approval_id}`"
                                        )

                                        if update_baseline:
                                            st.info("📝 Baseline updated with new configuration")

                                        if notify:
                                            st.info("📢 Notifications sent")

                                        # Reset form state
                                        st.session_state[approval_form_key] = False

                                        # Wait a moment then refresh
                                        import time

                                        time.sleep(1)
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"❌ Approval failed: {str(e)}")
                                        import traceback

                                        st.error(traceback.format_exc())

                            if cancelled:
                                st.session_state[approval_form_key] = False
                                st.rerun()

                with col2:
                    # Show selective revert expander
                    with st.expander("🔄 Revert Options", expanded=False):
                        # Get diff from drift
                        diff = (
                            drift.get("diff", {})
                            if isinstance(drift, dict)
                            else getattr(drift, "diff", {})
                        )

                        if not diff:
                            st.warning("⚠️ No diff information available for selective revert")
                            st.info("Using full revert mode")
                            revert_mode = "full"
                            selected_fields = []
                        else:
                            # Get available fields from diff
                            available_fields = get_available_fields(diff)

                            if not available_fields:
                                st.warning("⚠️ No fields available for selective revert")
                                revert_mode = "full"
                                selected_fields = []
                            else:
                                # Revert mode selection
                                revert_mode = st.radio(
                                    "Revert Mode:",
                                    options=["selective", "full"],
                                    index=0,
                                    key=f"revert_mode_{drift_id}",
                                    help="Selective: Choose specific fields | Full: Revert everything",
                                )

                                if revert_mode == "selective":
                                    st.markdown("**Select fields to revert:**")

                                    # Quick action buttons
                                    # Tags only button
                                    tag_fields = [
                                        f for f in available_fields if f.startswith("tags")
                                    ]
                                    if tag_fields and st.button(
                                        "🏷️ Tags Only", key=f"select_tags_{drift_id}"
                                    ):
                                        st.session_state[f"selected_fields_{drift_id}"] = tag_fields
                                        st.rerun()

                                    # Initialize selected fields in session state
                                    if f"selected_fields_{drift_id}" not in st.session_state:
                                        st.session_state[f"selected_fields_{drift_id}"] = []

                                    # Checkboxes for each field
                                    selected_fields = []
                                    for field in available_fields:
                                        is_selected = (
                                            field in st.session_state[f"selected_fields_{drift_id}"]
                                        )

                                        # Get baseline and current values for display
                                        field_parts = field.split(".")
                                        if len(field_parts) == 2 and field_parts[0] in diff:
                                            # Nested field like 'tags.Name'
                                            baseline_tags = (
                                                diff[field_parts[0]].get("baseline", []) or []
                                            )
                                            current_tags = (
                                                diff[field_parts[0]].get("current", []) or []
                                            )

                                            baseline_val = next(
                                                (
                                                    t.get("Value", "N/A")
                                                    for t in baseline_tags
                                                    if isinstance(t, dict)
                                                    and t.get("Key") == field_parts[1]
                                                ),
                                                "N/A",
                                            )
                                            current_val = next(
                                                (
                                                    t.get("Value", "N/A")
                                                    for t in current_tags
                                                    if isinstance(t, dict)
                                                    and t.get("Key") == field_parts[1]
                                                ),
                                                "N/A",
                                            )
                                            label = f"`{field}`: {current_val} → {baseline_val}"
                                        elif field in diff:
                                            # Simple field
                                            baseline_val = diff[field].get("baseline", "N/A")
                                            current_val = diff[field].get("current", "N/A")
                                            label = f"`{field}`: {current_val} → {baseline_val}"
                                        else:
                                            label = f"`{field}`"

                                        if st.checkbox(
                                            label,
                                            value=is_selected,
                                            key=f"field_{drift_id}_{field}",
                                        ):
                                            selected_fields.append(field)
                                            st.session_state[f"selected_fields_{drift_id}"] = (
                                                selected_fields
                                            )
                                        elif is_selected and field not in selected_fields:
                                            # Field was deselected
                                            st.session_state[f"selected_fields_{drift_id}"].remove(
                                                field
                                            )

                                    if not selected_fields:
                                        st.warning("⚠️ Please select at least one field to revert")
                                else:
                                    selected_fields = available_fields

                        # Revert button
                        if st.button(
                            f"� {'Apply Selective Revert' if revert_mode == 'selective' else 'Revert All to Baseline'}",
                            key=f"revert_btn_{drift_id}",
                            use_container_width=True,
                            type="primary",
                        ):
                            if revert_mode == "selective" and not selected_fields:
                                st.error("❌ Please select at least one field to revert")
                            else:
                                with st.spinner("⏳ Reverting configuration..."):
                                    st.info(f"🎯 Target: {resource_type} - {resource_id}")

                                    if revert_mode == "selective":
                                        st.info(
                                            f"🔧 Selective mode: Reverting {len(selected_fields)} field(s)"
                                        )
                                        st.caption(f"Fields: {', '.join(selected_fields)}")

                                        # Use selective revert
                                        result = selective_revert(
                                            resource_type=resource_type,
                                            resource_id=resource_id,
                                            region=region,
                                            diff=diff,
                                            selected_fields=selected_fields,
                                        )
                                    else:
                                        st.info("🔧 Full mode: Reverting all fields")

                                        # Load baseline config for full revert
                                        baseline = load_baseline_config(resource_type, resource_id)

                                        if not baseline:
                                            st.error(
                                                f"❌ No baseline configuration found for {resource_id}"
                                            )
                                            st.warning(
                                                "Please ensure baseline_state.json contains this resource"
                                            )
                                            result = None
                                        else:
                                            # Use boto3 for full revert
                                            result = boto3_revert_to_baseline(
                                                resource_type=resource_type,
                                                resource_id=resource_id,
                                                account_id=account_id,
                                                region=region,
                                                baseline_config=baseline,
                                            )

                                    if result:
                                        if result["status"] == "success":
                                            st.success(result["message"])
                                            if "actions" in result:
                                                for action in result["actions"]:
                                                    st.info(f"✓ {action}")
                                            if "reverted_fields" in result:
                                                st.success(
                                                    f"📝 Reverted fields: {', '.join(result['reverted_fields'])}"
                                                )
                                        elif result["status"] == "no_changes":
                                            st.warning(result["message"])
                                        else:
                                            st.error(result["message"])
                                            if "actions" in result and result["actions"]:
                                                st.info("Partial actions completed:")
                                                for action in result["actions"]:
                                                    st.info(f"• {action}")

                # Terminate button (separate row for emphasis)
                st.markdown("---")
                col_terminate = st.columns([3, 1])[0]
                with col_terminate:
                    terminate_key = f"terminate_{drift_id}"
                    if st.button(
                        "⛔ Stop/Terminate Resource",
                        key=terminate_key,
                        type="primary",
                        use_container_width=True,
                    ):
                        # Store confirmation request in session state
                        st.session_state[f"confirm_{terminate_key}"] = True
                        st.rerun()

                # Show confirmation dialog if requested
                confirm_key = f"confirm_terminate_{drift_id}"
                if st.session_state.get(confirm_key, False):
                    st.warning(
                        "⚠️ **DANGER ZONE** - Are you sure you want to STOP/TERMINATE this resource?"
                    )
                    st.error(f"Resource: {resource_id} ({resource_type})")

                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Yes, Terminate", key=f"yes_{terminate_key}"):
                            with st.spinner("⏳ Terminating resource..."):
                                st.info(f"🎯 Stopping/Terminating: {resource_id}")

                                # HYBRID APPROACH: Use boto3 for termination
                                result = boto3_terminate_resource(
                                    resource_type=resource_type,
                                    resource_id=resource_id,
                                    account_id=account_id,
                                    region=region,
                                    force=False,  # Create snapshots if applicable
                                )

                                if result["status"] in ["terminated", "deleted", "deleting"]:
                                    st.error(result["message"])
                                    st.warning("⚠️ This action cannot be undone!")
                                    if "snapshot_created" in result and result["snapshot_created"]:
                                        st.info("💾 Final snapshot created for safety")
                                else:
                                    st.error(result["message"])

                            # Clear confirmation
                            st.session_state[confirm_key] = False
                            st.rerun()

                    with col_no:
                        if st.button("❌ Cancel", key=f"no_{terminate_key}"):
                            st.session_state[confirm_key] = False
                            st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("")


if __name__ == "__main__":
    main()
