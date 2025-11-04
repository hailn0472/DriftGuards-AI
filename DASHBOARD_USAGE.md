# 🚀 Dashboard Usage Guide - Real Data Workflow

## 📋 Prerequisites

```powershell
# Install dependencies
pip install streamlit boto3

# Configure AWS credentials
aws configure
```

## 🔄 Complete Workflow

### **Step 1: Run Detection Workflow**

```powershell
# Run the example workflow to generate real drift data
python examples/run_workflow_example.py
```

**What happens:**
- ✅ Connects to AWS account `123456789012`
- ✅ Scans region `us-east-1`
- ✅ Detects drifts in EC2 and S3 resources
- ✅ Runs AI analysis on drifts
- ✅ Checks policy violations
- ✅ Saves 4 JSON files to `output/` directory:
  - `detection_results_YYYYMMDD_HHMMSS.json`
  - `analysis_results_YYYYMMDD_HHMMSS.json`
  - `policy_violations_YYYYMMDD_HHMMSS.json`
  - `metrics_context_YYYYMMDD_HHMMSS.json`

---

### **Step 2: Launch Dashboard**

```powershell
# Start Streamlit dashboard
streamlit run dashboard.py
```

Dashboard opens at: **http://localhost:8501**

---

## 📊 Dashboard Features

### **1. Load Baseline & Run Detection**

**Sidebar → "📋 Load Baseline & Run Scan"**

```
┌─────────────────────────────┐
│ 📋 Load Baseline & Run Scan │
│ ┌─────────────────────────┐ │
│ │ 📥 Load Baseline & Detect│ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**What happens:**
1. Reads `baseline_state.json`
2. Extracts account ID: `123456789012`
3. Extracts region: `us-east-1`
4. Runs full drift detection workflow
5. Shows results in dashboard

---

### **2. Load Previous Scan Results**

**Sidebar → "📂 Load Previous Scan"**

```
┌─────────────────────────────┐
│ 📂 Load Previous Scan       │
│ ┌─────────────────────────┐ │
│ │ detection_results_      │ │
│ │ 20241104_103522.json [▼]│ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 📥 Load Scan Results    │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**What happens:**
1. Select a scan file from dropdown
2. Click "Load Scan Results"
3. Loads 3 files automatically:
   - Detection results (drifts)
   - AI analysis results
   - Policy violations
4. Shows success message: "✅ Loaded X drifts"

---

### **3. View Drift Details**

**Main Content → Drift Cards**

```
╔═══════════════════════════════════════╗
║ 🔴 i-03fd43cd135f6135d                ║
║ Type: ec2_instances | Drift: MODIFIED ║
║ Account: 123456789012 | Region: us-... ║
║ Severity: CRITICAL                    ║
║                                       ║
║ 📋 View Changes ▼                     ║
║ 🤖 AI Analysis ▼                      ║
║ ⚖️ Policy Violations (2) ▼            ║
║                                       ║
║ [✅ Approve] [🔄 Remediate] [❌ Suppress]║
╚═══════════════════════════════════════╝
```

**Click to expand:**
- **📋 View Changes** - Shows JSON diff
- **🤖 AI Analysis** - Shows:
  - Root Cause
  - Business Impact
  - Recommended Action
  - Confidence Score
  - Remediation Steps
- **⚖️ Policy Violations** - Shows:
  - Policy ID
  - Violation Message
  - Severity
  - Action Required

---

## 🎯 Example Usage Scenarios

### **Scenario 1: First Time Setup**

```powershell
# 1. Create baseline
python examples/run_workflow_example.py

# 2. Start dashboard
streamlit run dashboard.py

# 3. In dashboard sidebar:
#    - Click "📥 Load Baseline & Detect"
#    - Wait 30-60 seconds
#    - View detected drifts
```

---

### **Scenario 2: Daily Monitoring**

```powershell
# 1. Run morning scan
python examples/run_workflow_example.py

# 2. Open dashboard
streamlit run dashboard.py

# 3. In sidebar:
#    - Select latest scan file from dropdown
#    - Click "📥 Load Scan Results"
#    - Review drifts by severity
#    - Take actions on CRITICAL drifts
```

---

### **Scenario 3: Historical Analysis**

```powershell
# 1. Open dashboard
streamlit run dashboard.py

# 2. In sidebar:
#    - Select older scan file
#    - Click "Load Scan Results"
#    - Compare with recent scans
#    - Track drift trends over time
```

---

## 📂 Output Files Structure

```
output/
├── detection_results_20241104_103522.json
│   ├── metadata
│   │   ├── timestamp
│   │   ├── scan_request
│   │   └── total_drifts
│   └── drifts[]
│       ├── drift_id
│       ├── resource_id
│       ├── resource_type
│       ├── drift_type
│       ├── severity
│       ├── account_id
│       ├── region
│       ├── detected_at
│       ├── terraform_value
│       ├── actual_value
│       └── diff
│
├── analysis_results_20241104_103522.json
│   ├── metadata
│   └── analyses[]
│       ├── analysis_id
│       ├── resource_id
│       ├── drift_id
│       ├── explanation
│       ├── root_cause
│       ├── business_impact
│       ├── recommended_action
│       ├── confidence_score
│       ├── severity
│       ├── estimated_fix_time
│       ├── rollback_complexity
│       ├── blast_radius
│       ├── remediation_steps[]
│       ├── analyzed_at
│       └── model_id
│
└── policy_violations_20241104_103522.json
    ├── metadata
    └── violations[]
        ├── policy_id
        ├── drift_id
        ├── violation_type
        ├── severity
        ├── message
        └── action_required
```

---

## 🎨 Dashboard Layout

```
┌────────────────┬─────────────────────────────────────────┐
│  SIDEBAR       │  MAIN CONTENT                           │
│                │                                         │
│  🔧 Scan       │  🛡️ DriftGuards AI Dashboard           │
│  Configuration │  Last scan: 2024-11-04 10:35:22        │
│                │                                         │
│  Account ID    │  📊 Drift Summary                       │
│  [123456789012]│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│                │  │🔴 12│ │🟠 34│ │🟡 56│ │🟢 23│      │
│  Regions       │  └─────┘ └─────┘ └─────┘ └─────┘      │
│  [us-east-1 ▼] │                                         │
│                │  🎯 Filters                             │
│  📦 Resources: │  [Severity] [Resource] [Drift Type]    │
│  All types     │                                         │
│                │  ⚠️ Detected Drifts (125)               │
│  🔍 START SCAN │  ╔════════════════════════════════╗    │
│                │  ║ 🔴 i-03fd43cd135f6135d         ║    │
│  ───────────── │  ║ ec2_instances | MODIFIED       ║    │
│                │  ║ 📋 View Changes ▼              ║    │
│  📋 Load       │  ║ 🤖 AI Analysis ▼               ║    │
│  Baseline      │  ║ ⚖️ Policy Violations (2) ▼     ║    │
│  📥 LOAD       │  ║ [✅] [🔄] [❌] [📊]             ║    │
│                │  ╚════════════════════════════════╝    │
│  ───────────── │                                         │
│                │  ╔════════════════════════════════╗    │
│  📂 Load       │  ║ 🟠 assets-bucket-0e84de4       ║    │
│  Previous Scan │  ║ aws_s3_bucket | MODIFIED       ║    │
│  [Select ▼]    │  ║ ...                            ║    │
│  📥 LOAD       │  ╚════════════════════════════════╝    │
└────────────────┴─────────────────────────────────────────┘
```

---

## 🔍 Real Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. baseline_state.json                                     │
│     ↓                                                        │
│  2. run_workflow_example.py                                 │
│     - Reads baseline                                         │
│     - Scans AWS account                                      │
│     - Detects drifts                                         │
│     - Runs AI analysis                                       │
│     - Checks policies                                        │
│     ↓                                                        │
│  3. output/*.json                                           │
│     - detection_results                                      │
│     - analysis_results                                       │
│     - policy_violations                                      │
│     - metrics_context                                        │
│     ↓                                                        │
│  4. dashboard.py                                            │
│     - Loads output files                                     │
│     - Displays drifts                                        │
│     - Shows AI analysis                                      │
│     - Shows violations                                       │
│     - Provides actions                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Verification

**After running workflow, check:**

```powershell
# Check output directory
ls output/

# Should see:
# detection_results_20241104_103522.json
# analysis_results_20241104_103522.json
# policy_violations_20241104_103522.json
# metrics_context_20241104_103522.json
```

**In dashboard, verify:**
- ✅ Drift summary shows correct counts
- ✅ AI Analysis expander shows recommendations
- ✅ Policy Violations expander shows violations
- ✅ Action buttons are clickable
- ✅ Filters work correctly

---

## 🐛 Troubleshooting

### **No drifts showing**
```powershell
# 1. Check if output files exist
ls output/

# 2. If no files, run workflow first
python examples/run_workflow_example.py

# 3. Verify AWS credentials
aws sts get-caller-identity
```

### **Dashboard shows "No data"**
```
# 1. Check baseline file exists
ls baseline_state.json

# 2. Click "Load Baseline & Detect" button

# 3. Or load previous scan from dropdown
```

### **AI Analysis not showing**
```
# Verify analysis_results file exists
ls output/analysis_results_*.json

# If missing, AI analyzer may have failed
# Check logs in run_workflow_example.py output
```

---

## 🎉 Success Criteria

**Dashboard is working correctly when:**
1. ✅ Loads baseline and runs detection
2. ✅ Shows drifts with correct severity colors
3. ✅ Displays AI analysis with recommendations
4. ✅ Shows policy violations
5. ✅ Action buttons respond to clicks
6. ✅ Can load multiple previous scans
7. ✅ Filters work correctly

**Ready to monitor your AWS infrastructure!** 🛡️
