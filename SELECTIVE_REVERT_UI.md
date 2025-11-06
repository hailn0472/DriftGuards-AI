# Selective Revert UI - Dashboard Integration

## ✅ What's New

The dashboard now includes a **Selective Revert UI** that allows you to choose exactly which fields to revert, instead of reverting everything at once.

## 🎯 Features

### 1. **Revert Options Expander**
Each drift now has a "🔄 Revert Options" expander with:
- **Revert Mode Selection**: Choose between `selective` or `full` mode
- **Field Checkboxes**: Select individual fields to revert
- **Quick Actions**: Buttons for common selections

### 2. **Two Revert Modes**

#### Selective Mode (Default)
- ✅ Choose specific fields to revert
- ✅ Shows current → baseline values for each field
- ✅ Preview what will change before applying

#### Full Mode
- ✅ Revert everything at once (old behavior)
- ✅ Uses baseline configuration

### 3. **Quick Action Buttons**

| Button | Action |
|--------|--------|
| **✓ All** | Select all available fields |
| **✗ None** | Deselect all fields |
| **🏷️ Tags** | Select only tag fields |

### 4. **Field Display Format**

Fields are shown with their changes:
```
☐ state: stopping → running
☐ instance_type: t2.small → t2.micro
☐ tags.Name: my-ec2-instance1 → my-ec2-instance
☐ tags.Environment: dev → production
```

## 📋 Usage Example

### Scenario: Only Revert Name Tag

1. **Scan for Drift** - Run a scan to detect changes
2. **View Drift Details** - Click on a drift to expand details
3. **Open Revert Options** - Click "🔄 Revert Options" expander
4. **Select Mode** - Choose "selective" (default)
5. **Select Field** - Check only `tags.Name`
6. **Apply** - Click "🔄 Apply Selective Revert"

Result:
```
✅ Selectively reverted EC2 i-03fd43cd135f6135d
✓ Changed tag 'Name': 'my-ec2-instance1' → 'my-ec2-instance'
📝 Reverted fields: tags.Name
```

### Scenario: Revert Multiple Fields

1. Select multiple checkboxes:
   - ✅ `state`
   - ✅ `tags.Name`
   - ✅ `tags.Environment`

2. Click "🔄 Apply Selective Revert"

Result:
```
✅ Selectively reverted EC2 i-03fd43cd135f6135d
✓ Changed state: stopped → running
✓ Changed tag 'Name': 'old-name' → 'new-name'
✓ Changed tag 'Environment': 'dev' → 'production'
📝 Reverted fields: state, tags.Name, tags.Environment
```

## 🔧 Supported Fields by Resource Type

### EC2 Instances
- `state` - running/stopped
- `instance_type` - t2.micro, t2.small, etc.
- `tags` - All tags
- `tags.Name` - Name tag only
- `tags.Environment` - Environment tag only
- `tags.*` - Any other tag

### S3 Buckets
- `versioning` - Enabled/Disabled
- `encryption` - Enabled/Disabled
- `public_access_blocked` - True/False

### RDS Instances
- `publicly_accessible` - True/False
- `backup_retention_period` - Days
- `multi_az` - True/False

## 🎨 UI Screenshot (Text Representation)

```
┌─────────────────────────────────────────────────────┐
│ 🔴 CRITICAL | Resource: i-03fd43cd135f6135d         │
│                                                     │
│ Type: ec2_instances | Region: ap-southeast-1       │
│                                                     │
│ Diff:                                               │
│ {                                                   │
│   "state": {                                        │
│     "baseline": "running",                          │
│     "current": "stopped"                            │
│   },                                                │
│   "tags": {                                         │
│     "baseline": [{"Key": "Name", ...}],            │
│     "current": [{"Key": "Name", ...}]              │
│   }                                                 │
│ }                                                   │
│                                                     │
│ ┌──────────────────────────────────────────────┐  │
│ │ ✅ Approve Drift  │ 🔄 Revert Options ▼     │  │
│ └──────────────────────────────────────────────┘  │
│                                                     │
│ 🔄 Revert Options                                  │
│ ┌─────────────────────────────────────────────┐   │
│ │ Revert Mode:                                 │   │
│ │ ○ selective  ● full                          │   │
│ │                                               │   │
│ │ Select fields to revert:                     │   │
│ │ ┌──────────┬──────────┬──────────┐          │   │
│ │ │ ✓ All    │ ✗ None   │ 🏷️ Tags  │          │   │
│ │ └──────────┴──────────┴──────────┘          │   │
│ │                                               │   │
│ │ ☐ state: stopped → running                   │   │
│ │ ☑ tags.Name: my-ec2-old → my-ec2            │   │
│ │                                               │   │
│ │ ┌─────────────────────────────────────┐     │   │
│ │ │  🔄 Apply Selective Revert           │     │   │
│ │ └─────────────────────────────────────┘     │   │
│ └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 💡 Tips

1. **Preview Changes** - Hover over checkboxes to see current → baseline values
2. **Tags Only** - Use the "🏷️ Tags" quick button to revert only tags
3. **Partial Revert** - You can revert some fields now and others later
4. **Full Revert** - Switch to "full" mode for the old behavior
5. **State Changes** - Some changes (like instance type) require stopping the instance

## ⚠️ Important Notes

- **No Undo**: Revert operations cannot be undone
- **State Dependencies**: Changing instance type requires stopping the instance
- **Validation**: The system validates state transitions (e.g., can't start a terminated instance)
- **Partial Success**: If some fields fail, successfully reverted fields are reported

## 🚀 Next Steps

To use the new selective revert:

1. **Run a scan** to detect drifts
2. **Click on a drift** to view details
3. **Expand "Revert Options"** 
4. **Select specific fields** you want to revert
5. **Apply the selective revert**

The system will only change the fields you selected, leaving everything else untouched!
