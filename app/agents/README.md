# DriftGuards Agents

This directory contains the multi-agent implementation for the DriftGuards system using LangGraph.

## Overview

The DriftGuards system uses a multi-agent architecture where each agent is responsible for a specific aspect of drift detection and remediation. All agents are orchestrated using LangGraph for stateful, sequential and conditional workflow execution.

## Agents

### 1. DetectionAgent (`detection.py`)

**Purpose**: Detect infrastructure drift between Terraform state and actual AWS resources.

**Key Features**:

- Dual detection strategy: Terraform native + driftctl
- Parallel scanning across multiple accounts and regions
- Support for multiple resource types (EC2, S3, RDS, Lambda, etc.)
- Drift deduplication and severity calculation
- Comprehensive diff generation

**Methods**:

- `detect_drift(scan_request)`: Main entry point for drift detection
- `_terraform_scan()`: Terraform-based detection
- `_driftctl_scan()`: driftctl-based detection
- `_parse_terraform_plan()`: Parse Terraform plan output
- `_calculate_severity()`: Determine drift severity

**Example**:

```python
from app.agents import DetectionAgent
from app.models.drift import ScanRequest

agent = DetectionAgent()
scan_request = ScanRequest(
    accounts=["123456789012"],
    regions=["us-east-1"],
    resource_types=["aws_instance"]
)
drifts = await agent.detect_drift(scan_request)
```

### 2. MetricsCollectorAgent (`metrics_collector.py`)

**Purpose**: Enrich drift data with comprehensive AWS metrics for context-aware analysis.

**Data Sources**:

- **CloudWatch Metrics**: Performance metrics (CPU, Network, Memory, etc.)
- **AWS Config**: Configuration history and compliance status
- **Cost Explorer**: Cost trends and budget impact
- **Performance Baselines**: Historical performance patterns

**Methods**:

- `collect_metrics(drift_records)`: Collect metrics for multiple drifts
- `_collect_cloudwatch_metrics()`: Gather CloudWatch data
- `_collect_config_history()`: Retrieve Config timeline
- `_collect_cost_data()`: Analyze cost impact
- `_collect_compliance_violations()`: Check compliance

**Example**:

```python
from app.agents import MetricsCollectorAgent

agent = MetricsCollectorAgent()
metrics = await agent.collect_metrics(drift_records)
```

### 3. AIAnalyzerAgent (`ai_analyzer.py`)

**Purpose**: Provide AI-powered analysis using AWS Bedrock (Claude 3) for context-aware recommendations.

**Key Features**:

- Claude 3 Sonnet integration via AWS Bedrock
- Structured output with Pydantic validation
- Context-aware prompts with metrics, history, and costs
- Confidence scoring and risk assessment
- Fallback analysis for error cases
- Anti-hallucination measures (low temperature, schema validation)

**Methods**:

- `analyze_drifts(drift_records, metrics_contexts)`: Analyze multiple drifts
- `_build_analysis_prompt()`: Generate comprehensive prompt
- `_call_bedrock()`: Invoke AWS Bedrock API
- `_parse_analysis_response()`: Parse and validate AI response

**Output**:

- Explanation of what changed
- Root cause analysis
- Business impact assessment
- Recommended action (update_terraform, revert_aws, ignore, manual_review)
- Alternative actions with risk levels
- Step-by-step remediation plan

**Example**:

```python
from app.agents import AIAnalyzerAgent

agent = AIAnalyzerAgent()
analyses = await agent.analyze_drifts(drift_records, metrics_contexts)
for analysis in analyses:
    print(f"Recommended: {analysis.recommended_action}")
    print(f"Confidence: {analysis.confidence_score}%")
```

### 4. PolicyValidatorAgent (`policy_validator.py`)

**Purpose**: Validate drifts against policies for proactive drift prevention and risk assessment.

**Policy Types**:

1. **Security Policies**: IAM, encryption, public access
2. **Cost Policies**: Instance types, budget thresholds
3. **Compliance Policies**: Required tags, regulatory requirements
4. **Operational Policies**: Change windows, production restrictions

**Features**:

- OPA (Open Policy Agent) integration ready
- Built-in policy checks
- Risk scoring algorithm
- Enforcement levels: ignore, warn, block

**Methods**:

- `validate_drifts(drift_records, analyses)`: Validate all drifts
- `_run_opa_policies()`: Execute OPA policy checks
- `_run_builtin_policies()`: Run built-in validations
- `_calculate_risk_score()`: Calculate drift risk score
- `should_block_drift()`: Determine if drift should be blocked

**Example**:

```python
from app.agents import PolicyValidatorAgent

agent = PolicyValidatorAgent()
violations = await agent.validate_drifts(drift_records, analyses)
for violation in violations:
    print(f"Policy {violation.policy_id}: {violation.message}")
```

### 5. AlertEngineAgent (`alert_engine.py`)

**Purpose**: Multi-channel intelligent alerting with deduplication and escalation.

**Alert Channels**:

- **Email** (AWS SES): Rich HTML templates
- **Slack**: Interactive messages with action buttons
- **SNS**: Fan-out for multiple subscribers
- **PagerDuty**: Critical incidents (when configured)

**Features**:

- Alert deduplication (1-hour window)
- Severity-based escalation
- Rich formatting for each channel
- Alert fingerprinting for dedup
- Configurable escalation policies

**Methods**:

- `send_alerts(drift_records, analyses, metrics)`: Send all alerts
- `_determine_alert_channels()`: Select channels by severity
- `_send_email_alert()`: Send via SES
- `_send_slack_alert()`: Send to Slack
- `_send_sns_alert()`: Publish to SNS
- `_is_duplicate_alert()`: Check for duplicates

**Escalation Policy**:

- **Critical**: Email + SNS + Slack + PagerDuty
- **High**: Email + Slack
- **Medium**: Email only
- **Low**: No alerts

**Example**:

```python
from app.agents import AlertEngineAgent

agent = AlertEngineAgent()
alerts = await agent.send_alerts(drift_records, analyses, metrics)
```

### 6. RemediationAgent (`remediation.py`)

**Purpose**: Safe, audited, and reversible automated drift remediation.

**Remediation Actions**:

1. **Update Terraform** (Preferred): Generate PR with Terraform changes
2. **Revert AWS**: Revert AWS resource to Terraform state
3. **Ignore/Suppress**: Suppress alert for expected drift
4. **Manual Review**: Escalate to human review

**Safety Mechanisms**:

- Pre-flight safety checks
- Backup creation before changes
- Rollback capability
- Business hours validation
- Change freeze detection
- Concurrent change prevention
- Dry-run mode

**Methods**:

- `remediate_drifts(drift_records, analyses)`: Execute remediations
- `_update_terraform()`: Generate Terraform patches and PRs
- `_revert_aws_resource()`: Revert AWS changes
- `_suppress_drift()`: Suppress alerts
- `_validate_remediation_safety()`: Pre-flight checks
- `_create_backup()`: Backup current state

**Example**:

```python
from app.agents import RemediationAgent

agent = RemediationAgent()
results = await agent.remediate_drifts(drift_records, analyses)
for result in results:
    print(f"{result.drift_id}: {result.status.value}")
```

## LangGraph Workflow

The agents are orchestrated using LangGraph in `app/workflows/drift_workflow.py`.

### Workflow Flow

```
┌─────────────┐
│  Detection  │ - Scan AWS resources
└──────┬──────┘
       │
       v
┌─────────────┐
│   Metrics   │ - Collect CloudWatch, Config, Cost data
└──────┬──────┘
       │
       v
┌─────────────┐
│ AI Analyzer │ - Analyze with AWS Bedrock (Claude)
└──────┬──────┘
       │
       v
┌─────────────┐
│   Policy    │ - Validate against policies
└──────┬──────┘
       │
       v
   Conditional
    ┌───┴───┐
    │       │
    v       v
┌────────┐  ┌────────┐
│ Alert  │  │  End   │
└───┬────┘  └────────┘
    │
    v
Conditional
 ┌───┴───┐
 │       │
 v       v
┌──────────┐  ┌────────┐
│Remediate │  │  End   │
└──────────┘  └────────┘
```

### State Management

The workflow maintains a shared state:

- `scan_request`: Input configuration
- `drift_records`: Detected drifts
- `metrics_context`: AWS metrics
- `ai_analysis`: AI recommendations
- `policy_violations`: Policy violations
- `alerts_sent`: Alerts sent
- `remediations`: Remediation results
- Control flags: `should_alert`, `should_remediate`

### Running the Workflow

```python
from app.workflows import DriftGuardsWorkflow
from app.models.drift import ScanRequest

# Create workflow
workflow = DriftGuardsWorkflow()

# Create scan request
scan_request = ScanRequest(
    accounts=["123456789012"],
    regions=["us-east-1"],
    resource_types=["aws_instance", "aws_s3_bucket"]
)

# Run full workflow
final_state = await workflow.run(scan_request)

# Access results
drifts = final_state["drift_records"]
analyses = final_state["ai_analysis"]
alerts = final_state["alerts_sent"]
remediations = final_state["remediations"]
```

### Partial Workflow Execution

You can also run individual phases:

```python
# Detection only
drifts = await workflow.run_detection_only(scan_request)

# Analysis for specific drift
analysis = await workflow.run_analysis_for_drift(drift_record)

# Remediation for specific drift
result = await workflow.run_remediation_for_drift(drift_record, analysis)
```

## Configuration

All agents respect settings from `app/config.py`:

### Detection

- `terraform_binary_path`: Path to Terraform binary
- `driftctl_binary_path`: Path to driftctl binary
- `scan_parallel_workers`: Number of parallel scan workers

### AI Analysis

- `bedrock_model_id`: Bedrock model ID (default: Claude 3 Sonnet)
- `bedrock_temperature`: Temperature for AI generation (0.1 for deterministic)
- `bedrock_max_tokens`: Max tokens for AI response

### Metrics

- `cloudwatch_lookback_hours`: CloudWatch metrics lookback (24h)
- `config_lookback_days`: Config history lookback (7 days)
- `cost_explorer_lookback_days`: Cost data lookback (30 days)

### Alerts

- `alert_email_to`: Email recipient
- `alert_slack_webhook_url`: Slack webhook URL
- `sns_topic_arn`: SNS topic for alerts
- `alert_pagerduty_api_key`: PagerDuty API key

### Remediation

- `remediation_auto_approve`: Enable auto-remediation (default: false)
- `remediation_backup_enabled`: Create backups before changes (default: true)
- `remediation_dry_run`: Dry-run mode (default: true)

### Policy

- `opa_enabled`: Enable OPA policy validation
- `policy_enforcement_level`: ignore | warn | block
- `opa_policy_dir`: Directory with OPA policies

## Testing

Example test files are in `examples/`:

- `run_workflow_example.py`: Full workflow execution
- Individual agent tests (to be added)

## Dependencies

Key dependencies:

- `langgraph`: Multi-agent workflow orchestration
- `boto3`: AWS SDK
- `pydantic`: Data validation
- Terraform CLI (external)
- driftctl CLI (external)

## Error Handling

All agents implement robust error handling:

- Graceful degradation (continue workflow on non-critical errors)
- Detailed logging at each phase
- Exception capture in workflow state
- Fallback mechanisms (e.g., fallback AI analysis)

## Performance

Optimization strategies:

- Parallel execution where possible (detection, metrics collection, AI analysis)
- Async/await throughout for I/O operations
- Caching for Terraform state and metrics
- Rate limiting for AWS API calls

## Security

Security considerations:

- IAM roles for AWS access (no hardcoded credentials)
- Secrets in AWS Secrets Manager or environment variables
- Audit logging for all remediation actions
- Pre-flight safety checks before changes
- Backup creation before destructive operations

## Future Enhancements

Planned improvements:

- GitOps integration for automated PR creation
- Drift prediction using ML
- Custom OPA policy library
- Webhook integrations
- Multi-cloud support (Azure, GCP)
- Enhanced rollback mechanisms

---

**For more information, see:**

- Main design document: `DESIGN.md`
- Project README: `README.md`
- API documentation: `/docs` endpoint when running
