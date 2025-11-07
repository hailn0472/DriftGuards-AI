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

        # Store results
        st.session_state.drifts = final_state.get("drift_records", [])
        st.session_state.analyses = final_state.get("ai_analysis", [])
        st.session_state.violations = final_state.get("policy_violations", [])
        st.session_state.last_scan = datetime.now()
        st.session_state.scanning = False
        
        # Show success message
        if len(st.session_state.drifts) == 0:
            st.success("✅ Scan completed successfully! No drifts detected. Your infrastructure is in sync with baseline.")
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


# Main app
def main():
    """Main dashboard."""
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
        # Schedule type selector
        schedule_type = st.sidebar.radio(
            "Schedule Type",
            ["Preset", "Custom Cron"],
            help="Choose preset intervals or enter custom cron expression",
        )

        if schedule_type == "Preset":
            # Schedule selector
            schedule_options = {
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
                index=2,  # Default to "Hourly"
                help="How often to automatically scan for drifts",
            )
            st.session_state.scan_schedule = schedule_options[selected_schedule]
            st.session_state.cron_expression = None
        else:
            # Custom cron expression input
            cron_expr = st.sidebar.text_input(
                "⏰ Cron Expression",
                value=st.session_state.get("cron_expression", DEFAULT_CRON_EXPRESSION),
                help="Enter cron expression (minute hour day month weekday)",
                placeholder=DEFAULT_CRON_EXPRESSION,
            )
            st.session_state.cron_expression = cron_expr
            st.session_state.scan_schedule = "custom"

            # Show cron expression helper
            with st.sidebar.expander("📖 Cron Expression Guide"):
                st.markdown(
                    """
                **Format:** `minute hour day month weekday`
                
                **Examples:**
                - `*/15 * * * *` - Every 15 minutes
                - `0 * * * *` - Every hour
                - `0 */6 * * *` - Every 6 hours
                - `0 0 * * *` - Daily at midnight
                - `0 9 * * 1` - Every Monday at 9 AM
                - `0 0 1 * *` - First day of month
                - `0 0 * * 0` - Every Sunday
                
                **Fields:**
                - Minute: 0-59
                - Hour: 0-23
                - Day: 1-31
                - Month: 1-12
                - Weekday: 0-6 (0=Sunday)
                """
                )

            # Validate cron expression
            try:
                from croniter import croniter
                from datetime import datetime

                if croniter.is_valid(cron_expr):
                    st.sidebar.success("✅ Valid cron expression")

                    # Show next 3 run times
                    base = datetime.now()
                    cron = croniter(cron_expr, base)
                    st.sidebar.info("🔮 Next 3 runs:")
                    for i in range(3):
                        next_run = cron.get_next(datetime)
                        st.sidebar.caption(f"{i + 1}. {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    st.sidebar.error("❌ Invalid cron expression")
            except ImportError:
                st.sidebar.warning(
                    "⚠️ Install `croniter` for cron validation: `pip install croniter`"
                )
            except Exception as e:
                st.sidebar.error(f"❌ Invalid cron: {str(e)}")

        # Show next scan time
        if st.session_state.last_scan:
            from datetime import timedelta

            schedule_intervals = {
                "15min": timedelta(minutes=15),
                "30min": timedelta(minutes=30),
                "hourly": timedelta(hours=1),
                "6hours": timedelta(hours=6),
                "12hours": timedelta(hours=12),
                "daily": timedelta(days=1),
                "weekly": timedelta(weeks=1),
            }
            next_scan = (
                st.session_state.last_scan + schedule_intervals[st.session_state.scan_schedule]
            )
            st.sidebar.info(f"⏰ Next scan: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")

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
        config = {
            "auto_scan_enabled": st.session_state.auto_scan_enabled,
            "scan_schedule": st.session_state.scan_schedule,
            "cron_expression": st.session_state.cron_expression,
            "notifications_enabled": st.session_state.notifications_enabled,
            "auto_remediation": st.session_state.auto_remediation,
        }
        config_file = Path(__file__).parent / "drift_config.json"
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        st.sidebar.success("✅ Configuration saved!")

    # Load configuration button
    if st.sidebar.button("📂 Load Configuration", use_container_width=True):
        config_file = Path(__file__).parent / "drift_config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            st.session_state.auto_scan_enabled = config.get("auto_scan_enabled", False)
            st.session_state.scan_schedule = config.get("scan_schedule", "hourly")
            st.session_state.cron_expression = config.get(
                "cron_expression", DEFAULT_CRON_EXPRESSION
            )
            st.session_state.notifications_enabled = config.get("notifications_enabled", True)
            st.session_state.auto_remediation = config.get("auto_remediation", False)
            st.sidebar.success("✅ Configuration loaded!")
            st.rerun()
        else:
            st.sidebar.error("❌ No saved configuration found")

    st.sidebar.markdown("---")

    # Load baseline config button
    st.sidebar.header("📋 Load Baseline & Run Scan")
    if st.sidebar.button("📥 Load Baseline & Detect", type="secondary"):
        try:
            baseline_file = Path(__file__).parent / "baseline_state.json"
            if not baseline_file.exists():
                st.sidebar.error("❌ baseline_state.json not found")
            else:
                with open(baseline_file) as f:
                    baseline_data = json.load(f)

                # Extract account and region from baseline
                account_id = baseline_data.get("account_id")
                region = baseline_data.get("region")

                st.sidebar.info(f"📊 Running scan for account: {account_id}")

                # Run actual workflow with baseline data
                asyncio.run(run_scan([account_id], [region], resource_types))
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Error: {str(e)}")

    # Load from file button
    st.sidebar.markdown("---")
    st.sidebar.header("📂 Load Previous Scan")
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
                    v_drift_id = v.drift_id if hasattr(v, "drift_id") else v.get("drift_id")
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
                            else:
                                policy_id = violation.get("policy_id")
                                message = violation.get("message")
                                v_severity = violation.get("severity")
                                action_required = violation.get("action_required")

                            st.markdown(f"**{policy_id}:** {message}")
                            st.caption(f"Severity: {v_severity} | Action: {action_required}")

                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ Approve Drift", key=f"approve_{drift_id}", use_container_width=True
                    ):
                        st.success("✅ Drift approved - keeping current configuration")
                        st.info("📝 Drift marked as intentional change")

                with col2:
                    # Show selective revert expander
                    with st.expander("🔄 Revert Options", expanded=False):
                        # Get diff from drift
                        diff = drift.get("diff", {}) if isinstance(drift, dict) else getattr(drift, "diff", {})
                        
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
                                    help="Selective: Choose specific fields | Full: Revert everything"
                                )
                                
                                if revert_mode == "selective":
                                    st.markdown("**Select fields to revert:**")
                                    
                                    # Quick action buttons
                                    col_q1, col_q2, col_q3 = st.columns(3)
                                    with col_q1:
                                        if st.button("✓ All", key=f"select_all_{drift_id}"):
                                            st.session_state[f"selected_fields_{drift_id}"] = available_fields
                                            st.rerun()
                                    with col_q2:
                                        if st.button("✗ None", key=f"select_none_{drift_id}"):
                                            st.session_state[f"selected_fields_{drift_id}"] = []
                                            st.rerun()
                                    with col_q3:
                                        # Tags only button
                                        tag_fields = [f for f in available_fields if f.startswith('tags')]
                                        if tag_fields and st.button("🏷️ Tags", key=f"select_tags_{drift_id}"):
                                            st.session_state[f"selected_fields_{drift_id}"] = tag_fields
                                            st.rerun()
                                    
                                    # Initialize selected fields in session state
                                    if f"selected_fields_{drift_id}" not in st.session_state:
                                        st.session_state[f"selected_fields_{drift_id}"] = []
                                    
                                    # Checkboxes for each field
                                    selected_fields = []
                                    for field in available_fields:
                                        is_selected = field in st.session_state[f"selected_fields_{drift_id}"]
                                        
                                        # Get baseline and current values for display
                                        field_parts = field.split('.')
                                        if len(field_parts) == 2 and field_parts[0] in diff:
                                            # Nested field like 'tags.Name'
                                            baseline_tags = diff[field_parts[0]].get('baseline', []) or []
                                            current_tags = diff[field_parts[0]].get('current', []) or []
                                            
                                            baseline_val = next((t.get('Value', 'N/A') for t in baseline_tags if isinstance(t, dict) and t.get('Key') == field_parts[1]), 'N/A')
                                            current_val = next((t.get('Value', 'N/A') for t in current_tags if isinstance(t, dict) and t.get('Key') == field_parts[1]), 'N/A')
                                            label = f"`{field}`: {current_val} → {baseline_val}"
                                        elif field in diff:
                                            # Simple field
                                            baseline_val = diff[field].get('baseline', 'N/A')
                                            current_val = diff[field].get('current', 'N/A')
                                            label = f"`{field}`: {current_val} → {baseline_val}"
                                        else:
                                            label = f"`{field}`"
                                        
                                        if st.checkbox(label, value=is_selected, key=f"field_{drift_id}_{field}"):
                                            selected_fields.append(field)
                                            st.session_state[f"selected_fields_{drift_id}"] = selected_fields
                                        elif is_selected and field not in selected_fields:
                                            # Field was deselected
                                            st.session_state[f"selected_fields_{drift_id}"].remove(field)
                                    
                                    if not selected_fields:
                                        st.warning("⚠️ Please select at least one field to revert")
                                else:
                                    selected_fields = available_fields
                        
                        # Revert button
                        if st.button(
                            f"� {'Apply Selective Revert' if revert_mode == 'selective' else 'Revert All to Baseline'}",
                            key=f"revert_btn_{drift_id}",
                            use_container_width=True,
                            type="primary"
                        ):
                            if revert_mode == "selective" and not selected_fields:
                                st.error("❌ Please select at least one field to revert")
                            else:
                                with st.spinner("⏳ Reverting configuration..."):
                                    st.info(f"🎯 Target: {resource_type} - {resource_id}")
                                    
                                    if revert_mode == "selective":
                                        st.info(f"🔧 Selective mode: Reverting {len(selected_fields)} field(s)")
                                        st.caption(f"Fields: {', '.join(selected_fields)}")
                                        
                                        # Use selective revert
                                        result = selective_revert(
                                            resource_type=resource_type,
                                            resource_id=resource_id,
                                            region=region,
                                            diff=diff,
                                            selected_fields=selected_fields
                                        )
                                    else:
                                        st.info("🔧 Full mode: Reverting all fields")
                                        
                                        # Load baseline config for full revert
                                        baseline = load_baseline_config(resource_type, resource_id)
                                        
                                        if not baseline:
                                            st.error(f"❌ No baseline configuration found for {resource_id}")
                                            st.warning("Please ensure baseline_state.json contains this resource")
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
                                                st.success(f"📝 Reverted fields: {', '.join(result['reverted_fields'])}")
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
