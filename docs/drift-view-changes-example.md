# Drift View Changes - Output Example

## Trước khi cập nhật (Thiếu thông tin người gây drift)

```json
{
    "tags": {
        "baseline": { "Name": "my-ec2-instance-da" },
        "current": { "Name": "my-ec2-instance-dam" }
    },
    "name": {
        "baseline": "my-ec2-instance-da",
        "current": "my-ec2-instance-dam"
    },
    "_baseline_context": {
        "created_by": "cloud_drift_AI",
        "created_by_arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
        "created_by_type": "user",
        "created_at": "2025-11-21T01:44:14.932868"
    }
}
```

**Vấn đề**: Chỉ có thông tin người tạo baseline, không có người gây ra drift!

---

## Sau khi cập nhật (Có đầy đủ thông tin)

```json
{
    "tags": {
        "baseline": { "Name": "my-ec2-instance-da" },
        "current": { "Name": "my-ec2-instance-dam" }
    },
    "name": {
        "baseline": "my-ec2-instance-da",
        "current": "my-ec2-instance-dam"
    },
    "_drift_metadata": {
        "updated_by": "quy",
        "updated_at": "2025-11-21T01:47:15+07:00",
        "drift_causing_event": "CreateTags"
    },
    "_baseline_context": {
        "created_by": "cloud_drift_AI",
        "created_by_arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
        "created_by_type": "user",
        "created_at": "2025-11-21T01:44:14.932868"
    }
}
```

**Giải pháp**: Thêm `_drift_metadata` với thông tin người gây ra drift!

---

## UI Display Suggestion

### View Changes Panel

```
┌─────────────────────────────────────────────────────────┐
│ 📋 Drift Changes                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 👤 Changed by: quy                                      │
│ 🕐 Changed at: 2025-11-21 01:47:15                     │
│ 🔧 Action: CreateTags                                   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Field: tags.Name                                        │
│   Baseline: "my-ec2-instance-da"                       │
│   Current:  "my-ec2-instance-dam"                      │
│                                                         │
│ Field: name                                             │
│   Baseline: "my-ec2-instance-da"                       │
│   Current:  "my-ec2-instance-dam"                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ ℹ️ Baseline created by: cloud_drift_AI                 │
│    at 2025-11-21 01:44:14                              │
└─────────────────────────────────────────────────────────┘
```

---

## Cấu trúc Diff đầy đủ

```json
{
    // Actual changes
    "tags": {
        "baseline": { "Name": "my-ec2-instance-da" },
        "current": { "Name": "my-ec2-instance-dam" }
    },
    "name": {
        "baseline": "my-ec2-instance-da",
        "current": "my-ec2-instance-dam"
    },

    // WHO caused the drift (NEW!)
    "_drift_metadata": {
        "updated_by": "quy",
        "updated_at": "2025-11-21T01:47:15+07:00",
        "drift_causing_event": "CreateTags"
    },

    // WHO created the baseline
    "_baseline_context": {
        "created_by": "cloud_drift_AI",
        "created_by_arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
        "created_by_type": "user",
        "created_at": "2025-11-21T01:44:14.932868"
    }
}
```

---

## Code để hiển thị trong UI

```javascript
// Frontend code example
function renderDriftChanges(diff) {
    const driftMetadata = diff._drift_metadata;
    const baselineContext = diff._baseline_context;

    // Show who caused the drift (IMPORTANT!)
    if (driftMetadata) {
        console.log(`Changed by: ${driftMetadata.updated_by}`);
        console.log(`Changed at: ${driftMetadata.updated_at}`);
        console.log(`Action: ${driftMetadata.drift_causing_event}`);
    }

    // Show actual changes
    Object.keys(diff).forEach((key) => {
        if (!key.startsWith("_")) {
            // Skip metadata fields
            const change = diff[key];
            console.log(`${key}: ${change.baseline} → ${change.current}`);
        }
    });

    // Show baseline info (less important)
    if (baselineContext) {
        console.log(`Baseline by: ${baselineContext.created_by}`);
    }
}
```

---

## Python code để truy cập

```python
# Backend code example
drift_record = detector.compare_states(baseline, current, account_id, region)

# Quick access (recommended)
print(f"Updated by: {drift_record.updated_by}")
print(f"Updated at: {drift_record.updated_at}")

# From diff (for UI)
drift_metadata = drift_record.diff.get("_drift_metadata", {})
print(f"Updated by: {drift_metadata.get('updated_by')}")
print(f"Event: {drift_metadata.get('drift_causing_event')}")

# Baseline info
baseline_context = drift_record.diff.get("_baseline_context", {})
print(f"Baseline by: {baseline_context.get('created_by')}")
```
