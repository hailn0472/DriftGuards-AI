# 🛡️ DriftGuards AI Dashboard - Quick Start Guide

## 📋 Prerequisites

```powershell
# Install Streamlit
pip install streamlit

# Or install all requirements
pip install -r requirements.txt
```

## 🚀 Run Dashboard

```powershell
# Start the dashboard
streamlit run dashboard.py
```

Dashboard sẽ mở tự động tại: **http://localhost:8501**

## 📊 Dashboard Features

### 1. **🔍 Scan for Drifts**
- **Configure scan** in the sidebar:
  - Enter AWS Account IDs (comma-separated)
  - Select regions to scan
  - Choose resource types to check
- Click **"Start Scan"** button
- Wait for results

### 2. **📋 View Drifts**
- See drift summary with severity counts:
  - 🔴 **Critical** - Immediate action required
  - 🟠 **High** - Important security/cost issues
  - 🟡 **Medium** - Configuration changes
  - 🟢 **Low** - Minor drifts

### 3. **🎯 Filter Drifts**
- Filter by:
  - **Severity:** Critical, High, Medium, Low
  - **Resource Type:** EC2, RDS, S3, etc.
  - **Drift Type:** DELETED, MODIFIED, UNMANAGED

### 4. **⚡ Take Actions**
Each drift has 4 action buttons:
- **✅ Approve** - Accept the drift
- **🔄 Remediate** - Auto-fix the drift
- **❌ Suppress** - Ignore this drift
- **📊 Details** - View full details

### 5. **📂 Load Previous Scans**
- Select from previous scan results in sidebar
- Click **"Load"** to view historical data

## 🎨 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🛡️ DriftGuards AI - Drift Detection Dashboard              │
│  Last scan: 2024-11-04 10:35:22                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📊 Drift Summary                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │🔴 Critical│ │🟠 High   │ │🟡 Medium │ │🟢 Low    │      │
│  │    12     │ │    34    │ │    56    │ │    23    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🎯 Filters                                                  │
│  Severity: [All ▼]  Resource: [All ▼]  Type: [All ▼]       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Detected Drifts (125)                                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔴 reporting-postgres                                │   │
│  │ Type: rds_instances | Drift: MODIFIED               │   │
│  │ Severity: CRITICAL                                   │   │
│  │                                                       │   │
│  │ 📋 View Changes ▼                                    │   │
│  │ {"publicly_accessible": "false → true"}              │   │
│  │                                                       │   │
│  │ [✅ Approve] [🔄 Remediate] [❌ Suppress] [📊 Details]│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🟠 user-profiles                                     │   │
│  │ ... (more drifts)                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📖 Usage Examples

### Example 1: First Time Scan

```
1. Open dashboard: streamlit run dashboard.py
2. In sidebar:
   - Enter Account ID: 961639320333
   - Select Region: us-east-1
   - Select Resource Types: EC2, RDS, S3
3. Click "Start Scan"
4. Wait for results (30-60 seconds)
5. Review drifts
6. Take actions
```

### Example 2: Load Previous Scan

```
1. In sidebar, go to "Load Previous Scan"
2. Select file: detection_results_20241104_103522.json
3. Click "Load"
4. View historical drifts
5. Apply filters to focus on specific issues
```

### Example 3: Handle Critical Drift

```
1. See 🔴 Critical drift: "reporting-postgres"
2. Click "📋 View Changes" to see what changed
3. Read: "publicly_accessible: false → true"
4. Click "🔄 Remediate" to auto-fix
5. Confirm remediation
6. Drift status updates to "Resolved"
```

## 🎯 Color Coding

| Color | Severity | Action Required |
|-------|----------|----------------|
| 🔴 Red | CRITICAL | Immediate action needed |
| 🟠 Orange | HIGH | Fix within 24 hours |
| 🟡 Yellow | MEDIUM | Review and plan fix |
| 🟢 Green | LOW | Monitor or approve |

## 📂 Output Files

Scan results are saved to `output/` directory:

```
output/
├── detection_results_20241104_103522.json  # Drift details
├── analysis_results_20241104_103522.json   # AI analysis
├── policy_violations_20241104_103522.json  # Policy violations
└── metrics_context_20241104_103522.json    # CloudWatch metrics
```

## 🔧 Troubleshooting

### Dashboard won't start
```powershell
# Install Streamlit
pip install streamlit

# Verify installation
streamlit --version
```

### Scan button disabled
- Check that you've entered:
  - At least one AWS Account ID
  - At least one region
  - At least one resource type

### No drifts found
- Verify AWS credentials are configured
- Check that resources exist in selected regions
- Try different resource types

### Error loading previous scan
- Ensure JSON files exist in `output/` directory
- Check file format is correct
- Verify file is not corrupted

## 📱 Keyboard Shortcuts

- **R** - Rerun the app
- **C** - Clear cache
- **Esc** - Close sidebar

## 🚀 Next Steps

1. **Set up automated scans** - Schedule regular drift detection
2. **Configure alerts** - Get notified of critical drifts
3. **Integrate with CI/CD** - Run scans on deployment
4. **Custom policies** - Define your own drift policies

## 💡 Tips

- Use filters to focus on high-priority drifts
- Review AI analysis for remediation guidance
- Export results for compliance reports
- Monitor drift trends over time

---

**Need help?** Check the main README.md or open an issue on GitHub.
