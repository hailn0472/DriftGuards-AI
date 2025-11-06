# How Drift Detection Works - Baseline vs Actual

## Overview
The DriftGuards AI agent compares **baseline configuration** (expected state) against **actual AWS configuration** (current state) to detect infrastructure drift.

## 🔍 Detection Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. LOAD BASELINE                            │
│                                                                 │
│  ┌─────────────────────────────────────┐                      │
│  │  baseline_state.json                │                      │
│  │  ├── account_id: 961639320333       │                      │
│  │  ├── region: ap-southeast-1         │                      │
│  │  └── resources:                     │                      │
│  │      ├── ec2_instances:             │                      │
│  │      │   └── id: i-03fd43cd135f6135d│                      │
│  │      │       type: t2.micro         │                      │
│  │      │       state: running         │                      │
│  │      ├── s3_buckets:                │                      │
│  │      ├── rds_instances:             │                      │
│  │      └── ...                         │                      │
│  └─────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  2. SCAN CURRENT STATE                          │
│                                                                 │
│  ┌─────────────────────────────────────┐                      │
│  │  AWS API Calls (boto3)              │                      │
│  │  ├── ec2.describe_instances()       │                      │
│  │  ├── s3.list_buckets()              │                      │
│  │  ├── rds.describe_db_instances()    │                      │
│  │  ├── lambda.list_functions()        │                      │
│  │  └── dynamodb.list_tables()         │                      │
│  └─────────────────────────────────────┘                      │
│                                                                 │
│  Returns: Current State Dictionary                             │
│  {                                                              │
│    "resources": {                                               │
│      "ec2_instances": [                                         │
│        {                                                        │
│          "id": "i-03fd43cd135f6135d",                          │
│          "type": "t2.small",  ← CHANGED!                       │
│          "state": "stopped"    ← CHANGED!                      │
│        }                                                        │
│      ]                                                          │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. COMPARE STATES                            │
│                                                                 │
│  For each resource type:                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Baseline Resources vs Current Resources                │  │
│  │                                                          │  │
│  │  Detection Logic:                                        │  │
│  │  ├── DELETED: In baseline but not in current           │  │
│  │  ├── UNMANAGED: In current but not in baseline         │  │
│  │  └── MODIFIED: In both but different values            │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    4. CREATE DRIFT RECORDS                      │
│                                                                 │
│  Example Drift Record:                                          │
│  {                                                              │
│    "drift_id": "drift-boto3-20251106-a3f8c912",               │
│    "resource_id": "i-03fd43cd135f6135d",                      │
│    "resource_type": "ec2_instances",                          │
│    "drift_type": "MODIFIED",                                  │
│    "severity": "HIGH",                                        │
│    "baseline_value": {                                        │
│      "type": "t2.micro",                                      │
│      "state": "running"                                       │
│    },                                                          │
│    "current_value": {                                         │
│      "type": "t2.small",                                      │
│      "state": "stopped"                                       │
│    },                                                          │
│    "diff": {                                                  │
│      "type": {                                                │
│        "baseline": "t2.micro",                                │
│        "current": "t2.small"                                  │
│      },                                                        │
│      "state": {                                               │
│        "baseline": "running",                                 │
│        "current": "stopped"                                   │
│      }                                                         │
│    }                                                           │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Key Components

### 1. Baseline State (`baseline_state.json`)
**Location**: Root directory  
**Purpose**: Stores the expected/approved configuration  
**Structure**:
```json
{
  "account_id": "961639320333",
  "region": "ap-southeast-1",
  "timestamp": "2025-11-06T10:00:00",
  "resources": {
    "ec2_instances": [...],
    "s3_buckets": [...],
    "rds_instances": [...],
    ...
  }
}
```

### 2. Current State Discovery (`boto3_detection.py`)
**Method**: `discover_current_state(account_id, region)`  
**Process**:
- Calls AWS APIs using boto3
- Retrieves current configuration for all resources
- Returns standardized data structure

**Resource Types Scanned**:
- ✅ VPCs
- ✅ EC2 Instances
- ✅ EKS Clusters
- ✅ ECS Clusters
- ✅ RDS Instances
- ✅ RDS Clusters
- ✅ S3 Buckets (with encryption, versioning, public access)
- ✅ DynamoDB Tables
- ✅ SQS Queues
- ✅ Lambda Functions
- ✅ Security Groups

### 3. State Comparison (`compare_states()`)
**Algorithm**:

#### Step 1: Create Resource Lookups
```python
# Convert lists to dictionaries for O(1) lookup
baseline_dict = {resource_id: resource for resource in baseline}
current_dict = {resource_id: resource for resource in current}
```

#### Step 2: Detect Deleted Resources
```python
for resource_id in baseline_dict:
    if resource_id not in current_dict:
        # Drift Type: DELETED
        # Severity: CRITICAL
        create_drift_record(...)
```

#### Step 3: Detect New/Unmanaged Resources
```python
for resource_id in current_dict:
    if resource_id not in baseline_dict:
        # Drift Type: UNMANAGED
        # Severity: HIGH
        create_drift_record(...)
```

#### Step 4: Detect Modified Resources
```python
for resource_id in (baseline_dict.keys() & current_dict.keys()):
    if baseline_dict[resource_id] != current_dict[resource_id]:
        # Drift Type: MODIFIED
        # Severity: Calculated based on changes
        diff = calculate_diff(baseline, current)
        create_drift_record(..., diff=diff)
```

### 4. Diff Calculation (`_calculate_diff()`)
**Purpose**: Find specific fields that changed

```python
def _calculate_diff(baseline, current):
    diff = {}
    all_keys = set(baseline.keys()) | set(current.keys())
    
    for key in all_keys:
        baseline_val = baseline.get(key)
        current_val = current.get(key)
        
        if baseline_val != current_val:
            diff[key] = {
                "baseline": baseline_val,
                "current": current_val
            }
    
    return diff
```

**Example Output**:
```json
{
  "type": {
    "baseline": "t2.micro",
    "current": "t2.small"
  },
  "state": {
    "baseline": "running",
    "current": "stopped"
  }
}
```

## 🎯 Severity Calculation

The agent automatically calculates severity based on drift type and changed fields:

### CRITICAL Severity
- 🔴 Resource deleted (`drift_type == DELETED`)
- 🔴 Security-sensitive changes:
  - `encryption` modified
  - `acl` changed
  - `public_access` changed
  - `iam` policy modified
  - `security_group` rules changed

### HIGH Severity
- 🟠 Unmanaged resources (`drift_type == UNMANAGED`)
- 🟠 Instance size changes:
  - `instance_type` modified
  - `instance_class` changed
  - Resource `size` changed

### MEDIUM Severity
- 🟡 Tag-only changes
- 🟡 Configuration changes (default)

### LOW Severity
- 🟢 Minor metadata changes

## 🔄 Detection Workflow Steps

### Step 1: User Initiates Scan
```python
# From dashboard.py
asyncio.run(run_scan(accounts, regions, resource_types))
```

### Step 2: Create Scan Request
```python
scan_request = ScanRequest(
    accounts=["961639320333"],
    regions=["ap-southeast-1"],
    resource_types=["ec2_instances", "s3_buckets", ...],
    force_refresh=False
)
```

### Step 3: Detection Agent Processes
```python
# detection.py
async def detect_drift(scan_request):
    # For each account/region
    for account_id in accounts:
        for region in regions:
            # 1. Load baseline
            baseline = await load_baseline_state()
            
            # 2. Discover current state
            current = await discover_current_state(account_id, region)
            
            # 3. Compare states
            drifts = await compare_states(baseline, current, account_id, region)
            
    return drift_records
```

### Step 4: Results Displayed
- Drift records stored in session state
- Dashboard shows:
  - Severity counts (Critical/High/Medium/Low)
  - Drift details with diff
  - Action buttons (Approve/Revert/Terminate)

## 📊 Real Example

### Baseline State
```json
{
  "resources": {
    "ec2_instances": [
      {
        "id": "i-03fd43cd135f6135d",
        "type": "t2.micro",
        "state": "running",
        "tags": [{"Key": "Environment", "Value": "Production"}]
      }
    ]
  }
}
```

### Current State (Scanned via boto3)
```json
{
  "resources": {
    "ec2_instances": [
      {
        "id": "i-03fd43cd135f6135d",
        "type": "t2.small",          ← Changed!
        "state": "stopped",          ← Changed!
        "tags": [{"Key": "Environment", "Value": "Production"}]
      }
    ]
  }
}
```

### Detected Drift
```json
{
  "drift_id": "drift-boto3-20251106-a3f8c912",
  "resource_id": "i-03fd43cd135f6135d",
  "resource_type": "ec2_instances",
  "drift_type": "MODIFIED",
  "severity": "HIGH",
  "diff": {
    "type": {
      "baseline": "t2.micro",
      "current": "t2.small"
    },
    "state": {
      "baseline": "running",
      "current": "stopped"
    }
  }
}
```

## 🔧 Code Locations

| Component | File | Function |
|-----------|------|----------|
| Load Baseline | `app/agents/boto3_detection.py` | `load_baseline_state()` |
| Scan Current | `app/agents/boto3_detection.py` | `discover_current_state()` |
| Compare States | `app/agents/boto3_detection.py` | `compare_states()` |
| Calculate Diff | `app/agents/boto3_detection.py` | `_calculate_diff()` |
| Main Detection | `app/agents/detection.py` | `detect_drift()` |
| Dashboard Trigger | `dashboard.py` | `run_scan()` |

## 🛠️ How to Update Baseline

### Option 1: Manual Update
Edit `baseline_state.json` directly:
```json
{
  "resources": {
    "ec2_instances": [
      {
        "id": "i-03fd43cd135f6135d",
        "type": "t2.small",     ← Update to match current
        "state": "stopped"       ← Update to match current
      }
    ]
  }
}
```

### Option 2: Create New Baseline
Run discovery script:
```bash
python scripts/discover_aws_resources.py
```

### Option 3: Approve Drift
When you approve a drift in the dashboard, you should update the baseline to reflect the new approved state.

## 🎯 Key Features

### 1. Real-time Comparison
- ✅ No Terraform state file needed
- ✅ Direct boto3 API calls
- ✅ Fast parallel scanning
- ✅ Multi-account/region support

### 2. Comprehensive Detection
- ✅ Deleted resources
- ✅ New/unmanaged resources
- ✅ Modified configurations
- ✅ Security-sensitive changes

### 3. Detailed Diffs
- ✅ Field-level comparison
- ✅ Before/after values
- ✅ Severity calculation
- ✅ Change categorization

### 4. AI Analysis
- ✅ Root cause detection
- ✅ Business impact assessment
- ✅ Remediation recommendations
- ✅ Confidence scoring

## 🚀 Future Enhancements

### Planned Features
1. **Automated Baseline Updates**: Approve drift → auto-update baseline
2. **Drift History**: Track drift over time
3. **Change Approval Workflow**: Multi-level approvals
4. **Scheduled Baseline Snapshots**: Automatic baseline versioning
5. **Drift Prediction**: ML-based drift forecasting
6. **Cost Impact Analysis**: Calculate cost of drifts
7. **Compliance Mapping**: Map drifts to compliance standards

### Advanced Detection
- Deep inspection of resource configurations
- Cross-resource dependency analysis
- Network topology drift detection
- IAM permission drift tracking
- Tag compliance validation

## 📚 Related Documentation
- [Revert Utilities](./revert_utils.py) - How to revert drifts
- [Baseline State](./baseline_state.json) - Current baseline
- [Dashboard](./dashboard.py) - User interface
- [Detection Agent](./app/agents/detection.py) - Core detection logic
- [Boto3 Detection](./app/agents/boto3_detection.py) - AWS scanning logic
