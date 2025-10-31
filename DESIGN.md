# DriftGuards - AWS IaC Drift Analyzer Design Document

**Version:** 1.0  
**Date:** October 31, 2025  
**Status:** Design Phase

---

## 📋 Executive Summary

**DriftGuards** is an intelligent AWS Infrastructure-as-Code (IaC) drift detection and remediation system that combines multi-agent AI workflows with comprehensive AWS resource monitoring. The system provides continuous drift detection, context-aware AI analysis, and automated remediation capabilities.

### Key Differentiators
- **Proactive Intelligence**: Context-aware AI analysis vs traditional reactive tools
- **Multi-Agent LLM Architecture**: Specialized agents for detection, analysis, and remediation
- **Policy-as-Code Prevention**: Proactive drift prevention using OPA/AWS Config Rules
- **Comprehensive Metrics**: Rich context from CloudWatch, Config, and Cost Explorer
- **Native Terraform Integration**: Leverages `terraform plan` and `driftctl` for accurate detection

---

## 🎯 Project Objectives

### Primary Goals
1. **Continuous Drift Detection**: Automated hourly scans of AWS infrastructure
2. **AI-Powered Analysis**: Context-aware explanations and recommendations
3. **Multi-Source Metrics**: CloudWatch performance, Config compliance, Cost Explorer data
4. **Automated Remediation**: Safe, audited, and reversible fix execution
5. **Proactive Prevention**: Policy enforcement to prevent risky changes

### Success Metrics
- Drift detection accuracy > 95%
- Mean time to detection (MTTD) < 1 hour
- Mean time to resolution (MTTR) < 15 minutes (for automated fixes)
- False positive rate < 5%
- AI recommendation acceptance rate > 70%

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Cloud Environment                     │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────────┐ │
│  │   EC2   │  │   S3    │  │   RDS    │  │  Lambda/ECS  │ │
│  └────┬────┘  └────┬────┘  └────┬─────┘  └──────┬───────┘ │
└───────┼────────────┼────────────┼────────────────┼─────────┘
        │            │            │                │
        └────────────┴────────────┴────────────────┘
                     │ (boto3)
        ┌────────────▼────────────────────────────┐
        │      DriftGuards Backend (Python)       │
        │                                          │
        │  ┌────────────────────────────────────┐ │
        │  │   LangGraph Multi-Agent System     │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  1. Detection Agent          │ │ │
        │  │  │  - Terraform Plan/Refresh    │ │ │
        │  │  │  - driftctl Integration      │ │ │
        │  │  │  - Live State Comparison     │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  2. Metrics Collector Agent  │ │ │
        │  │  │  - CloudWatch Metrics        │ │ │
        │  │  │  - AWS Config History        │ │ │
        │  │  │  - Cost Explorer Data        │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  3. AI Analyzer Agent        │ │ │
        │  │  │  - AWS Bedrock (Claude)      │ │ │
        │  │  │  - Structured Output Parser  │ │ │
        │  │  │  - Context Enrichment        │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  4. Policy Validator Agent   │ │ │
        │  │  │  - OPA Policy Engine         │ │ │
        │  │  │  - AWS Config Rules          │ │ │
        │  │  │  - Risk Assessment           │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  5. Alert Engine Agent       │ │ │
        │  │  │  - Multi-channel Alerts      │ │ │
        │  │  │  - De-duplication            │ │ │
        │  │  │  - Escalation Logic          │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  │                                    │ │
        │  │  ┌──────────────────────────────┐ │ │
        │  │  │  6. Remediation Agent        │ │ │
        │  │  │  - Terraform Apply           │ │ │
        │  │  │  - AWS API Reversion         │ │ │
        │  │  │  - Rollback Safety           │ │ │
        │  │  └──────────────────────────────┘ │ │
        │  └────────────────────────────────────┘ │
        │                                          │
        │  ┌────────────────────────────────────┐ │
        │  │         FastAPI Layer              │ │
        │  │  - /scan, /drifts, /action         │ │
        │  │  - Authentication & Rate Limiting  │ │
        │  └────────────────────────────────────┘ │
        └──────────────┬───────────────────────────┘
                       │
        ┌──────────────▼───────────────┐
        │  AWS Infrastructure          │
        │  ┌─────────────────────────┐ │
        │  │ EventBridge (Scheduler) │ │
        │  └─────────────────────────┘ │
        │  ┌─────────────────────────┐ │
        │  │ DynamoDB (State Store)  │ │
        │  └─────────────────────────┘ │
        │  ┌─────────────────────────┐ │
        │  │ S3 (Logs & Artifacts)   │ │
        │  └─────────────────────────┘ │
        │  ┌─────────────────────────┐ │
        │  │ SNS/SES (Alerts)        │ │
        │  └─────────────────────────┘ │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼───────────────┐
        │   Streamlit Dashboard        │
        │  - Drift Visualization       │
        │  - AI Insights Display       │
        │  - Action Execution UI       │
        └──────────────────────────────┘
```

---

## 🧩 Component Design

### 1️⃣ Detection Agent

#### Purpose
Identify configuration drift between Terraform state and actual AWS resources using native Terraform tooling and driftctl.

#### Implementation Strategy

**A. Terraform Native Approach (Primary)**
```python
# Leverage terraform refresh + plan
terraform refresh -input=false
terraform plan -detailed-exitcode -out=plan.tfplan
terraform show -json plan.tfplan > drift_report.json
```

**B. driftctl Integration (Secondary)**
```python
# Cross-validate with driftctl for comprehensive coverage
driftctl scan --output json --to aws+tf > driftctl_report.json
```

#### Features
- **Resource Coverage**: EC2, S3, RDS, Lambda, VPC, IAM, ECS, EKS, CloudFront, Route53
- **Cross-Account Support**: AssumeRole for multi-account scanning
- **State Backend**: Support for S3, Terraform Cloud, local backends
- **Ignore Patterns**: Configurable exclusions for expected drift (e.g., auto-scaling)

#### Data Model
```python
@dataclass
class DriftRecord:
    resource_id: str
    resource_type: str
    drift_type: str  # 'modified', 'deleted', 'unmanaged'
    terraform_value: dict
    actual_value: dict
    diff: dict
    detected_at: datetime
    severity: str  # 'critical', 'high', 'medium', 'low'
    account_id: str
    region: str
```

#### Optimization
- Parallel resource scanning using `asyncio`
- Incremental state refresh (only changed resources)
- Caching of Terraform state (5-minute TTL)

---

### 2️⃣ Metrics Collector Agent

#### Purpose
Enrich drift data with comprehensive AWS metrics for context-aware AI analysis.

#### Data Sources

**A. CloudWatch Metrics**
- EC2: CPUUtilization, NetworkIn/Out, DiskReadOps, StatusCheckFailed
- RDS: DatabaseConnections, ReadLatency, WriteLatency
- Lambda: Invocations, Errors, Duration, ConcurrentExecutions
- S3: BucketSizeBytes, NumberOfObjects

**B. AWS Config History**
```python
config.get_resource_config_history(
    resourceType='AWS::EC2::Instance',
    resourceId=resource_id,
    laterTime=datetime.now() - timedelta(days=7)
)
```
- Configuration change timeline
- Compliance status changes
- Related events correlation

**C. Cost Explorer Data**
```python
ce.get_cost_and_usage(
    TimePeriod={'Start': '2025-10-01', 'End': '2025-10-31'},
    Granularity='DAILY',
    Metrics=['UnblendedCost', 'UsageQuantity'],
    Filter={'Dimensions': {'Key': 'RESOURCE_ID', 'Values': [resource_id]}}
)
```
- 30-day cost trend
- Cost anomaly detection
- Budget impact assessment

#### Data Model
```python
@dataclass
class MetricsContext:
    resource_id: str
    cloudwatch_metrics: Dict[str, List[float]]
    config_history: List[ConfigChange]
    cost_data: CostAnalysis
    performance_baseline: PerformanceBaseline
    compliance_violations: List[ComplianceViolation]
    related_changes: List[RelatedChange]
```

---

### 3️⃣ AI Analyzer Agent

#### Purpose
Provide human-readable explanations, root cause analysis, and actionable recommendations using AWS Bedrock.

#### LLM Integration

**Model Selection**: AWS Bedrock - Claude 3 Sonnet (balance of speed/quality)

**Structured Output Format**
```python
class DriftAnalysis(BaseModel):
    resource_id: str
    explanation: str  # Human-readable description
    root_cause: str  # Why the drift occurred
    business_impact: str  # Risk and operational impact
    recommended_action: Literal["update_terraform", "revert_aws", "ignore", "manual_review"]
    alternative_actions: List[ActionOption]
    confidence_score: int  # 0-100
    severity: Literal["critical", "high", "medium", "low"]
    estimated_fix_time: str  # e.g., "5 minutes"
    rollback_complexity: Literal["simple", "moderate", "complex"]
    blast_radius: str  # Potential impact scope
```

#### Prompt Engineering Strategy

**System Prompt**
```
You are a cloud infrastructure expert specializing in AWS and Terraform.
Analyze drift reports with full context (metrics, history, costs).
Provide actionable insights focusing on:
1. Root cause identification
2. Business impact assessment
3. Safe remediation paths
4. Risk mitigation strategies

Always prioritize safety and provide confidence scores.
```

**User Prompt Template**
```python
prompt = f"""
DRIFT DETECTED:
Resource: {drift.resource_type} ({drift.resource_id})
Account: {drift.account_id} | Region: {drift.region}

CHANGES:
{json.dumps(drift.diff, indent=2)}

PERFORMANCE METRICS (Last 24h):
{json.dumps(metrics.cloudwatch_metrics, indent=2)}

CONFIGURATION HISTORY (Last 7 days):
{json.dumps(metrics.config_history, indent=2)}

COST IMPACT:
{json.dumps(metrics.cost_data, indent=2)}

COMPLIANCE STATUS:
{json.dumps(metrics.compliance_violations, indent=2)}

GIT CONTEXT (if available):
Last Terraform commit: {git_context.last_commit}
Author: {git_context.author}
Commit message: {git_context.message}

Analyze this drift and provide:
1. What changed and why
2. Business and operational impact
3. Recommended action with justification
4. Risk assessment and blast radius
5. Step-by-step remediation plan
"""
```

#### Anti-Hallucination Measures
- Enforce JSON schema validation with Pydantic
- Temperature = 0.1 (deterministic outputs)
- Few-shot examples in system prompt
- Cross-validation of recommendations with policy engine
- Confidence thresholds for automated actions

---

### 4️⃣ Policy Validator Agent

#### Purpose
Proactive drift prevention and risk assessment using policy-as-code.

#### Policy Engines

**A. Open Policy Agent (OPA)**
```rego
# Example policy: Prevent production instance type changes
package driftguards.policies

deny[msg] {
    input.resource_type == "aws_instance"
    input.environment == "production"
    input.drift.attribute == "instance_type"
    msg := "Production instance type changes require approval"
}

deny[msg] {
    input.resource_type == "aws_s3_bucket"
    input.drift.attribute == "acl"
    input.actual_value == "public-read"
    msg := "Public S3 bucket access is prohibited"
}
```

**B. AWS Config Rules Integration**
- Leverage existing AWS Config managed rules
- Custom Lambda-based rules for specific policies
- Automatic compliance checking

#### Policy Categories
1. **Security Policies**: IAM, encryption, network exposure
2. **Cost Policies**: Instance types, storage classes, reserved instances
3. **Compliance Policies**: HIPAA, PCI-DSS, SOC2 requirements
4. **Operational Policies**: Tagging, naming conventions, backup policies

#### Risk Scoring Algorithm
```python
def calculate_risk_score(drift: DriftRecord, violations: List[PolicyViolation]) -> int:
    base_score = 0
    
    # Severity multiplier
    severity_weights = {'critical': 40, 'high': 25, 'medium': 15, 'low': 5}
    base_score += severity_weights.get(drift.severity, 0)
    
    # Environment multiplier
    env_multipliers = {'production': 2.0, 'staging': 1.5, 'development': 1.0}
    base_score *= env_multipliers.get(drift.environment, 1.0)
    
    # Policy violations
    base_score += len(violations) * 10
    
    # Blast radius
    if drift.has_downstream_dependencies:
        base_score *= 1.5
    
    return min(base_score, 100)
```

---

### 5️⃣ Alert Engine Agent

#### Purpose
Multi-channel, intelligent alerting with de-duplication and escalation.

#### Alert Channels

**A. Email (AWS SES)**
- Rich HTML templates with drift visualizations
- Actionable links directly to remediation UI
- Digest mode for non-critical alerts

**B. Slack/Teams Integration**
```python
{
    "blocks": [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 Drift Detected"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Resource:* {resource_id}"},
                {"type": "mrkdwn", "text": f"*Severity:* {severity}"}
            ]
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "View Details"}},
                {"type": "button", "text": {"type": "plain_text", "text": "Fix Now"}}
            ]
        }
    ]
}
```

**C. PagerDuty/Opsgenie**
- Critical severity → immediate page
- Incident auto-creation with context

**D. AWS SNS**
- Fan-out for multiple subscribers
- Lambda trigger for custom workflows

#### De-duplication Strategy
```python
def is_duplicate_alert(new_drift: DriftRecord) -> bool:
    # Check for same resource + drift type within 1 hour
    recent_alerts = get_alerts_last_n_hours(1)
    
    for alert in recent_alerts:
        if (alert.resource_id == new_drift.resource_id and
            alert.drift_type == new_drift.drift_type and
            alert.diff_hash == new_drift.diff_hash):
            return True
    
    return False
```

#### Escalation Policy
```yaml
escalation:
  - level: 1
    severity: [low, medium]
    channels: [email]
    delay: 0
  
  - level: 2
    severity: [high]
    channels: [slack, email]
    delay: 0
  
  - level: 3
    severity: [critical]
    channels: [pagerduty, slack, email]
    delay: 0
    escalate_after: 15m  # If unacknowledged
```

---

### 6️⃣ Remediation Agent

#### Purpose
Safe, audited, and reversible automated fixes with rollback capabilities.

#### Remediation Actions

**A. Update Terraform (Preferred)**
```python
async def update_terraform(drift: DriftRecord):
    # 1. Generate patch file
    patch = generate_terraform_patch(drift)
    
    # 2. Create feature branch
    branch_name = f"drift-fix/{drift.resource_id}/{timestamp}"
    git.checkout("-b", branch_name)
    
    # 3. Apply patch
    apply_patch(patch)
    
    # 4. Validate with terraform plan
    plan_result = run_terraform_plan()
    
    # 5. Create PR with AI analysis context
    pr = create_pull_request(
        title=f"Fix drift: {drift.resource_id}",
        body=generate_pr_body(drift, analysis),
        labels=["drift-remediation", "automated"]
    )
    
    # 6. Audit log
    log_remediation_action(drift, "update_terraform", pr.url)
```

**B. Revert AWS (Quick Fix)**
```python
async def revert_aws_resource(drift: DriftRecord):
    # 1. Pre-flight checks
    validate_revert_safety(drift)
    
    # 2. Create snapshot/backup
    backup = create_resource_backup(drift.resource_id)
    
    # 3. Apply reversion
    boto3_client = get_client(drift.resource_type)
    
    try:
        if drift.resource_type == "aws_instance":
            ec2.modify_instance_attribute(
                InstanceId=drift.resource_id,
                InstanceType={'Value': drift.terraform_value['instance_type']}
            )
        elif drift.resource_type == "aws_s3_bucket":
            s3.put_bucket_acl(
                Bucket=drift.resource_id,
                ACL=drift.terraform_value['acl']
            )
        
        # 4. Verify reversion
        verify_resource_state(drift.resource_id, drift.terraform_value)
        
        # 5. Audit log
        log_remediation_action(drift, "revert_aws", backup.id)
        
    except Exception as e:
        # Rollback to backup
        restore_from_backup(backup)
        raise RemediationError(f"Revert failed: {e}")
```

**C. Ignore/Suppress**
```python
async def suppress_drift(drift: DriftRecord, reason: str, ttl: int = 30):
    """
    Suppress drift alert for specified days
    Used for expected drift (e.g., auto-scaling, blue-green deployments)
    """
    suppression = DriftSuppression(
        drift_id=drift.id,
        reason=reason,
        suppressed_by=current_user,
        expires_at=datetime.now() + timedelta(days=ttl)
    )
    
    db.session.add(suppression)
    db.session.commit()
    
    log_remediation_action(drift, "suppress", reason)
```

**D. Manual Review Queue**
```python
async def escalate_to_manual(drift: DriftRecord):
    """
    Complex drifts requiring human judgment
    """
    ticket = create_jira_ticket(
        summary=f"Manual drift review: {drift.resource_id}",
        description=generate_ticket_body(drift, analysis),
        priority=map_severity_to_priority(drift.severity)
    )
    
    notify_on_call_engineer(ticket)
    log_remediation_action(drift, "manual_review", ticket.url)
```

#### Safety Mechanisms

**Pre-Flight Checks**
```python
def validate_remediation_safety(drift: DriftRecord, action: str) -> bool:
    checks = [
        check_policy_compliance(drift, action),
        check_blast_radius(drift),
        check_business_hours(),  # Critical changes only in maintenance windows
        check_change_freeze(),  # Block during freeze periods
        check_concurrent_changes(drift.resource_id),
        check_dependency_health(drift)
    ]
    
    return all(checks)
```

**Rollback Plan**
Every remediation must have a documented rollback:
```python
@dataclass
class RemediationPlan:
    action: str
    steps: List[str]
    backup_created: bool
    backup_id: str
    rollback_steps: List[str]
    estimated_duration: int  # seconds
    max_retries: int
    timeout: int  # seconds
```

---

### 7️⃣ API Layer (FastAPI)

#### Endpoints

**Drift Management**
```python
# Trigger manual scan
POST /api/v1/scan
{
    "accounts": ["123456789012"],
    "regions": ["us-east-1", "us-west-2"],
    "resource_types": ["aws_instance", "aws_s3_bucket"]
}

# List all drifts
GET /api/v1/drifts
Query params: severity, resource_type, status, account_id, limit, offset

# Get specific drift details
GET /api/v1/drifts/{drift_id}

# Get AI analysis for drift
GET /api/v1/drifts/{drift_id}/analysis
```

**Remediation**
```python
# Execute remediation action
POST /api/v1/drifts/{drift_id}/remediate
{
    "action": "update_terraform",
    "confirm": true,
    "dry_run": false
}

# Get remediation status
GET /api/v1/remediations/{remediation_id}

# Rollback remediation
POST /api/v1/remediations/{remediation_id}/rollback
```

**Metrics & Analytics**
```python
# Drift statistics
GET /api/v1/analytics/drift-stats
Response: {
    "total_drifts": 42,
    "by_severity": {"critical": 3, "high": 8, ...},
    "by_resource_type": {"aws_instance": 15, ...},
    "trend": [...] 
}

# Cost impact analysis
GET /api/v1/analytics/cost-impact
```

**Policy Management**
```python
# List policies
GET /api/v1/policies

# Create/update policy
POST /api/v1/policies
PUT /api/v1/policies/{policy_id}

# Validate drift against policies
POST /api/v1/policies/validate
```

#### Security

**Authentication**
- API Key authentication for service-to-service
- OAuth2/JWT for user sessions
- IAM role assumption for AWS API calls

**Rate Limiting**
```python
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    limiter = RateLimiter(
        requests_per_minute=60,
        requests_per_hour=1000
    )
    
    if not limiter.allow(request.client.host):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return await call_next(request)
```

**Authorization**
- RBAC with roles: admin, operator, viewer
- Resource-level permissions
- Audit logging for all actions

---

### 8️⃣ Streamlit Dashboard

#### Views

**A. Overview Dashboard**
- Real-time drift count by severity
- Trend chart (last 30 days)
- Top drifting resources
- Cost impact summary
- Quick action buttons

**B. Drift Explorer**
```python
# Interactive table with filters
- Resource ID, Type, Severity, Detected At, Status
- Expandable rows showing full diff
- AI analysis panel
- Action buttons (Fix, Ignore, Details)
```

**C. Drift Details Page**
- Side-by-side diff view (Terraform vs Actual)
- AI explanation and recommendations
- Metrics timeline (CloudWatch, costs)
- Configuration history
- Remediation options with confirmation

**D. Analytics & Insights**
- Drift frequency heatmap
- Resource type distribution
- Mean time to detection/resolution
- AI recommendation acceptance rate
- Cost savings from automated fixes

**E. Audit Log**
- All scans, detections, and remediations
- User actions and API calls
- Searchable and filterable
- Export to CSV

---

## 🗄️ Data Management

### Storage Architecture

**A. DynamoDB Tables**

**DriftRecords Table**
```
Partition Key: resource_id
Sort Key: detected_at
Attributes: resource_type, drift_type, severity, status, account_id, region
GSI-1: status-detected_at-index
GSI-2: severity-detected_at-index
```

**RemediationLog Table**
```
Partition Key: remediation_id
Sort Key: timestamp
Attributes: drift_id, action, status, user, result
```

**PolicyViolations Table**
```
Partition Key: drift_id
Sort Key: policy_id
Attributes: violation_type, severity, message
```

**B. S3 Buckets**

```
driftguards-artifacts/
├── terraform-states/       # Cached Terraform states
├── drift-reports/          # JSON reports per scan
├── logs/                   # Application and audit logs
├── backups/                # Resource backups before remediation
└── metrics/                # CloudWatch/Cost Explorer dumps
```

**C. Local SQLite (Development)**
- Same schema as DynamoDB for local testing
- Easy seeding with test data

---

## 🔄 LangGraph Workflow Design

### Multi-Agent Graph Structure

```python
from langgraph.graph import Graph, StateGraph
from typing import TypedDict, Annotated

class DriftGuardsState(TypedDict):
    scan_request: dict
    drift_records: List[DriftRecord]
    metrics_context: List[MetricsContext]
    ai_analysis: List[DriftAnalysis]
    policy_violations: List[PolicyViolation]
    alerts_sent: List[Alert]
    remediations: List[RemediationResult]

# Define the graph
workflow = StateGraph(DriftGuardsState)

# Add nodes
workflow.add_node("detection", detection_agent)
workflow.add_node("metrics_collector", metrics_collector_agent)
workflow.add_node("ai_analyzer", ai_analyzer_agent)
workflow.add_node("policy_validator", policy_validator_agent)
workflow.add_node("alert_engine", alert_engine_agent)
workflow.add_node("remediation", remediation_agent)

# Define edges
workflow.set_entry_point("detection")

workflow.add_edge("detection", "metrics_collector")
workflow.add_edge("metrics_collector", "ai_analyzer")
workflow.add_edge("ai_analyzer", "policy_validator")

workflow.add_conditional_edges(
    "policy_validator",
    should_alert,
    {
        True: "alert_engine",
        False: "remediation"
    }
)

workflow.add_conditional_edges(
    "alert_engine",
    should_auto_remediate,
    {
        True: "remediation",
        False: END
    }
)

workflow.add_edge("remediation", END)

# Compile
app = workflow.compile()
```

### Agent Implementations

**Detection Agent**
```python
async def detection_agent(state: DriftGuardsState) -> DriftGuardsState:
    """
    Runs Terraform refresh/plan and driftctl to detect drift
    """
    scan_request = state["scan_request"]
    
    # Parallel execution for multiple accounts/regions
    tasks = []
    for account in scan_request["accounts"]:
        for region in scan_request["regions"]:
            tasks.append(scan_account_region(account, region))
    
    drift_records = await asyncio.gather(*tasks)
    
    return {
        **state,
        "drift_records": flatten(drift_records)
    }
```

**Metrics Collector Agent**
```python
async def metrics_collector_agent(state: DriftGuardsState) -> DriftGuardsState:
    """
    Enriches drift records with CloudWatch, Config, and Cost data
    """
    drift_records = state["drift_records"]
    
    metrics_tasks = [
        collect_metrics_for_resource(drift) 
        for drift in drift_records
    ]
    
    metrics_context = await asyncio.gather(*metrics_tasks)
    
    return {
        **state,
        "metrics_context": metrics_context
    }
```

**AI Analyzer Agent**
```python
async def ai_analyzer_agent(state: DriftGuardsState) -> DriftGuardsState:
    """
    Uses AWS Bedrock to analyze drift and provide recommendations
    """
    drift_records = state["drift_records"]
    metrics_context = state["metrics_context"]
    
    analysis_tasks = [
        analyze_drift_with_ai(drift, metrics)
        for drift, metrics in zip(drift_records, metrics_context)
    ]
    
    ai_analysis = await asyncio.gather(*analysis_tasks)
    
    return {
        **state,
        "ai_analysis": ai_analysis
    }
```

---

## ⚙️ Deployment Architecture

### Containerization (Docker)

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    terraform \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install driftctl
RUN curl -L https://github.com/snyk/driftctl/releases/latest/download/driftctl_linux_amd64 \
    -o /usr/local/bin/driftctl && chmod +x /usr/local/bin/driftctl

# Copy application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### AWS Deployment Options

**Option 1: ECS Fargate (Recommended for MVP)**
```yaml
# Task definition
{
  "family": "driftguards",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/DriftGuardsTaskRole",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ECSTaskExecutionRole",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "driftguards-api",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/driftguards:latest",
      "memory": 2048,
      "cpu": 1024,
      "essential": true,
      "portMappings": [{"containerPort": 8000}],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/driftguards",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

**Option 2: Lambda + Step Functions (Future)**
- Detection: Lambda (15-min timeout)
- Orchestration: Step Functions
- Cost-optimized for sporadic scans

### Scheduling

**EventBridge Rule**
```json
{
  "Name": "DriftGuardsHourlyScan",
  "ScheduleExpression": "rate(1 hour)",
  "State": "ENABLED",
  "Targets": [
    {
      "Arn": "arn:aws:ecs:us-east-1:ACCOUNT:cluster/driftguards",
      "RoleArn": "arn:aws:iam::ACCOUNT:role/EventBridgeECSRole",
      "EcsParameters": {
        "TaskDefinitionArn": "arn:aws:ecs:us-east-1:ACCOUNT:task-definition/driftguards:1",
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
          "awsvpcConfiguration": {
            "Subnets": ["subnet-xxx"],
            "SecurityGroups": ["sg-xxx"],
            "AssignPublicIp": "ENABLED"
          }
        }
      }
    }
  ]
}
```

---

## 📊 Monitoring & Observability

### Metrics (CloudWatch)

**Application Metrics**
- Drift detection rate (drifts/hour)
- AI analysis latency (p50, p99)
- Remediation success rate
- API response times
- Error rates by component

**Business Metrics**
- Cost savings from automated fixes
- Mean time to detection (MTTD)
- Mean time to resolution (MTTR)
- Policy violation rate
- Alert fatigue score (alerts/day)

### Logging Strategy

**Structured Logging (JSON)**
```python
{
    "timestamp": "2025-10-31T10:30:45Z",
    "level": "INFO",
    "logger": "driftguards.detection",
    "message": "Drift detected",
    "context": {
        "drift_id": "drift-123",
        "resource_id": "i-0abc123",
        "resource_type": "aws_instance",
        "severity": "high",
        "account_id": "123456789012"
    }
}
```

**Log Aggregation**
- CloudWatch Logs Insights for querying
- Optional: Export to Elasticsearch/OpenSearch
- Retention: 30 days (90 days for audit logs)

### Tracing (AWS X-Ray)

```python
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture("detect_drift")
async def detect_drift(account_id: str):
    # Automatic tracing of AWS SDK calls
    # Manual subsegments for custom logic
    pass
```

---

## 🔒 Security Considerations

### IAM Roles & Permissions

**Task Role (ECS)**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:GetBucket*",
        "s3:ListBucket",
        "rds:Describe*",
        "cloudwatch:GetMetricStatistics",
        "config:GetResourceConfigHistory",
        "ce:GetCostAndUsage",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:ModifyInstanceAttribute",
        "s3:PutBucketAcl",
        "rds:ModifyDBInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/DriftGuards*"
    }
  ]
}
```

### Secrets Management

- AWS Secrets Manager for API keys, tokens
- IAM roles for AWS service access (no long-lived credentials)
- Encryption at rest for DynamoDB and S3

### Network Security

- Private VPC for ECS tasks
- Security groups restricting inbound to ALB only
- VPC endpoints for AWS services (no internet egress)

---

## 📈 Scalability & Performance

### Optimization Strategies

**1. Parallel Processing**
- Scan multiple accounts/regions concurrently
- Async I/O for AWS API calls
- Batch processing for metrics collection

**2. Caching**
- Terraform state caching (Redis/Elasticache)
- CloudWatch metrics caching (5-min TTL)
- AI analysis caching for identical drifts

**3. Rate Limiting**
- Respect AWS API throttling limits
- Exponential backoff for retries
- Request batching where possible

**4. Database Optimization**
- DynamoDB on-demand billing (auto-scaling)
- GSI for efficient queries
- TTL for old drift records (90 days)

### Load Testing Targets

- 1000 resources per account
- 10 accounts, 5 regions
- Scan completion < 10 minutes
- API response time < 500ms (p95)

---

## 🧪 Testing Strategy

### Unit Tests
- Individual agent logic
- Terraform parsing
- AWS API mocking (moto)
- Policy evaluation

### Integration Tests
- End-to-end LangGraph workflow
- Database operations
- External API integrations

### E2E Tests
- Terraform drift scenarios
- Remediation rollback
- Alert delivery
- UI interactions

### Chaos Engineering
- AWS API failure simulation
- Bedrock throttling
- Network partitions

---

## 📦 Project Structure

```
driftguards/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration management
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── detection.py           # Detection agent
│   │   ├── metrics_collector.py   # Metrics agent
│   │   ├── ai_analyzer.py         # AI analysis agent
│   │   ├── policy_validator.py    # Policy agent
│   │   ├── alert_engine.py        # Alert agent
│   │   └── remediation.py         # Remediation agent
│   ├── workflows/
│   │   ├── __init__.py
│   │   └── drift_workflow.py      # LangGraph orchestration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── drift.py               # Drift data models
│   │   ├── metrics.py             # Metrics data models
│   │   └── analysis.py            # AI analysis models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── terraform.py           # Terraform operations
│   │   ├── driftctl.py            # driftctl integration
│   │   ├── aws_client.py          # AWS SDK wrappers
│   │   └── bedrock.py             # Bedrock LLM client
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── dynamodb.py            # DynamoDB operations
│   │   ├── s3.py                  # S3 operations
│   │   └── sqlite.py              # SQLite for local dev
│   ├── policies/
│   │   ├── __init__.py
│   │   ├── opa/                   # OPA policy files
│   │   │   ├── security.rego
│   │   │   ├── cost.rego
│   │   │   └── compliance.rego
│   │   └── config_rules/          # AWS Config rules
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── drifts.py          # Drift endpoints
│   │   │   ├── remediations.py    # Remediation endpoints
│   │   │   ├── analytics.py       # Analytics endpoints
│   │   │   └── policies.py        # Policy endpoints
│   │   └── middleware/
│   │       ├── auth.py
│   │       ├── rate_limit.py
│   │       └── logging.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Structured logging
│       ├── parsers.py             # HCL/JSON parsers
│       └── diff.py                # Diff utilities
├── frontend/
│   ├── app.py                     # Streamlit app
│   ├── pages/
│   │   ├── 1_overview.py
│   │   ├── 2_drift_explorer.py
│   │   ├── 3_analytics.py
│   │   └── 4_audit_log.py
│   └── components/
│       ├── drift_card.py
│       ├── metrics_chart.py
│       └── action_button.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── terraform/                     # Sample IaC for testing
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── terraform/                 # Infrastructure for DriftGuards itself
│   │   ├── ecs.tf
│   │   ├── dynamodb.tf
│   │   ├── s3.tf
│   │   └── eventbridge.tf
│   └── helm/                      # For Kubernetes (future)
├── scripts/
│   ├── setup.sh                   # Development setup
│   ├── test.sh                    # Run tests
│   └── deploy.sh                  # Deployment script
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── policies.md
│   └── runbook.md
├── .env.example
├── requirements.txt
├── pyproject.toml                 # UV/Poetry config
├── Dockerfile
├── README.md
└── DESIGN.md                      # This document
```

---

## 🚀 Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)
- [ ] Project scaffolding (uv, FastAPI, LangGraph)
- [ ] Detection agent (Terraform plan integration)
- [ ] Metrics collector (CloudWatch only)
- [ ] Basic AI analyzer (AWS Bedrock)
- [ ] Simple alert engine (email via SES)
- [ ] DynamoDB + S3 storage
- [ ] Basic FastAPI endpoints
- [ ] Streamlit dashboard (overview + drift explorer)
- [ ] Docker containerization
- [ ] Unit tests

### Phase 2: Enhanced Intelligence (Weeks 5-6)
- [ ] driftctl integration
- [ ] AWS Config history enrichment
- [ ] Cost Explorer integration
- [ ] Policy validator agent (OPA)
- [ ] Multi-channel alerts (Slack, PagerDuty)
- [ ] Advanced AI prompting with structured outputs
- [ ] Confidence scoring and hallucination prevention

### Phase 3: Automated Remediation (Weeks 7-8)
- [ ] Remediation agent (all action types)
- [ ] Terraform patch generation
- [ ] AWS resource reversion
- [ ] Backup and rollback mechanisms
- [ ] Pre-flight safety checks
- [ ] Audit logging
- [ ] Integration tests

### Phase 4: Production Readiness (Weeks 9-10)
- [ ] ECS Fargate deployment
- [ ] EventBridge scheduling
- [ ] IAM role fine-tuning
- [ ] CloudWatch dashboards
- [ ] X-Ray tracing
- [ ] Load testing
- [ ] Security hardening
- [ ] Documentation and runbooks

### Phase 5: Advanced Features (Weeks 11-12)
- [ ] Cross-account support (AssumeRole)
- [ ] Multi-region scanning
- [ ] Policy-as-code library
- [ ] Custom Config rules
- [ ] Advanced analytics dashboard
- [ ] Export/import capabilities
- [ ] Webhook integrations
- [ ] E2E tests

---

## 💰 Cost Estimation

### AWS Services (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| ECS Fargate | 2 vCPU, 4GB, 24/7 | ~$60 |
| DynamoDB | 10GB storage, on-demand | ~$3 |
| S3 | 100GB storage | ~$3 |
| CloudWatch Logs | 10GB ingestion | ~$5 |
| Bedrock (Claude 3 Sonnet) | 1M input + 100K output tokens | ~$5 |
| SES | 10K emails | ~$1 |
| EventBridge | 1K rules | ~$1 |
| **Total** | | **~$78/month** |

*Note: Costs scale with number of resources and scan frequency*

---

## 🎓 Key Design Decisions

### 1. Why LangGraph?
- Native support for multi-agent workflows
- State management for complex pipelines
- Easy visualization and debugging
- Conditional branching for decision logic

### 2. Why Terraform Native + driftctl?
- Terraform plan provides authoritative drift detection
- driftctl adds coverage for unmanaged resources
- Avoids re-implementing Terraform logic
- Leverages battle-tested tools

### 3. Why AWS Bedrock (Claude)?
- No infrastructure management
- Strong reasoning capabilities
- Structured output support
- AWS native (no egress costs)

### 4. Why FastAPI?
- Async/await for high concurrency
- Automatic OpenAPI docs
- Type safety with Pydantic
- Easy integration with LangChain/LangGraph

### 5. Why DynamoDB + S3?
- Serverless, auto-scaling
- Pay-per-use pricing
- DynamoDB for structured queries
- S3 for large artifacts and logs

---

## 🔮 Future Enhancements

### Short-term
- GitOps integration (automatic PR creation)
- Drift prediction using ML
- Resource dependency graph visualization
- Custom notification templates

### Long-term
- Multi-cloud support (Azure, GCP)
- Drift prevention via pre-commit hooks
- Integration with ServiceNow/Jira
- Mobile app for on-call engineers
- Kubernetes drift detection
- Self-healing infrastructure

---

## 📚 References

### Tools & Libraries
- [Terraform](https://www.terraform.io/)
- [driftctl](https://github.com/snyk/driftctl)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)
- [Open Policy Agent](https://www.openpolicyagent.org/)

### AWS Documentation
- [AWS Config](https://docs.aws.amazon.com/config/)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [CloudWatch Metrics](https://docs.aws.amazon.com/cloudwatch/)
- [Cost Explorer API](https://docs.aws.amazon.com/cost-management/)

### Best Practices
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [Infrastructure Drift Detection Best Practices](https://www.devops.com/infrastructure-drift-detection/)

---

## 📝 Appendix

### A. Sample Drift Report

```json
{
  "drift_id": "drift-2025-10-31-001",
  "resource_id": "i-0abc123456def",
  "resource_type": "aws_instance",
  "account_id": "123456789012",
  "region": "us-east-1",
  "detected_at": "2025-10-31T10:30:45Z",
  "drift_type": "modified",
  "severity": "high",
  "terraform_value": {
    "instance_type": "t2.micro",
    "tags": {
      "Environment": "production",
      "Owner": "team-a"
    }
  },
  "actual_value": {
    "instance_type": "t3.medium",
    "tags": {
      "Environment": "production",
      "Owner": "team-a",
      "ManagedBy": "manual"
    }
  },
  "diff": {
    "instance_type": {
      "before": "t2.micro",
      "after": "t3.medium"
    },
    "tags.ManagedBy": {
      "before": null,
      "after": "manual"
    }
  },
  "metrics": {
    "cloudwatch": {
      "CPUUtilization": {"avg": 85.2, "max": 98.5},
      "NetworkIn": {"avg": 1234567, "max": 2345678}
    },
    "cost": {
      "daily_cost": 1.85,
      "monthly_projection": 55.50,
      "increase_percent": 120
    },
    "config_history": [
      {
        "timestamp": "2025-10-31T08:15:00Z",
        "user": "john.doe@company.com",
        "action": "ModifyInstanceAttribute",
        "changes": {"instance_type": "t3.medium"}
      }
    ]
  },
  "ai_analysis": {
    "explanation": "Instance type was manually upgraded from t2.micro to t3.medium, likely due to sustained high CPU utilization (avg 85%, max 98%) over the past 24 hours. The change was made by john.doe@company.com at 08:15 UTC.",
    "root_cause": "Application load increased beyond t2.micro capacity. Manual intervention during incident response.",
    "business_impact": "Performance improved but costs increased by 120%. This instance is in production and serves critical workloads.",
    "recommended_action": "update_terraform",
    "alternative_actions": [
      {
        "action": "revert_aws",
        "description": "Revert to t2.micro if load has decreased",
        "risk": "high",
        "reason": "May cause performance degradation"
      },
      {
        "action": "ignore",
        "description": "Accept the change and suppress alert for 30 days",
        "risk": "low",
        "reason": "If change is intentional and temporary"
      }
    ],
    "confidence_score": 92,
    "severity": "high",
    "estimated_fix_time": "5 minutes",
    "rollback_complexity": "simple",
    "blast_radius": "Single instance, no downstream dependencies detected"
  },
  "policy_violations": [
    {
      "policy_id": "manual-change-production",
      "violation_type": "governance",
      "message": "Manual changes to production resources are prohibited",
      "severity": "high"
    }
  ],
  "status": "open",
  "assigned_to": null,
  "remediation_plan": null
}
```

### B. Sample OPA Policy

```rego
package driftguards.policies.security

# Deny public S3 buckets
deny[msg] {
    input.resource_type == "aws_s3_bucket"
    input.actual_value.acl == "public-read"
    msg := sprintf("S3 bucket %s has public-read ACL (security risk)", [input.resource_id])
}

# Deny unencrypted RDS instances
deny[msg] {
    input.resource_type == "aws_db_instance"
    input.actual_value.storage_encrypted == false
    input.environment == "production"
    msg := sprintf("Production RDS instance %s is not encrypted at rest", [input.resource_id])
}

# Require approval for production instance type changes
require_approval[msg] {
    input.resource_type == "aws_instance"
    input.environment == "production"
    input.drift.attribute == "instance_type"
    input.actual_value.instance_type != input.terraform_value.instance_type
    msg := sprintf("Instance type change in production requires manual approval: %s", [input.resource_id])
}

# Cost threshold policy
deny[msg] {
    input.metrics.cost.monthly_projection > 1000
    input.ai_analysis.confidence_score < 80
    msg := sprintf("Cost increase exceeds $1000/month with low AI confidence (%d%%)", [input.ai_analysis.confidence_score])
}
```

### C. Sample Terraform Patch

```hcl
# Generated patch for drift-2025-10-31-001

resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
- instance_type = "t2.micro"
+ instance_type = "t3.medium"  # Updated to match AWS state
  
  tags = {
    Environment = "production"
    Owner       = "team-a"
+   ManagedBy   = "terraform"  # Added to match AWS state
  }
}

# Reason: Manual instance resize detected due to high CPU utilization
# Recommended by: AI Analyzer (confidence: 92%)
# Approved by: john.doe@company.com
# Applied at: 2025-10-31T11:00:00Z
```

---

**End of Design Document**

*This document is a living specification and will be updated as the project evolves.*
