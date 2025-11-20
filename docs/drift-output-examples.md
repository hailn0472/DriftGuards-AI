# Drift Detection Output Examples

## 1. EC2 Instance - Name Tag Changed

### Scenario

User "quy" thay đổi Name tag từ "my-ec2-instance-d" → "my-ec2-instance-da"

### Output JSON

```json
{
  "drift_id": "drift-boto3-20251121-abc12345",
  "resource_id": "i-0b86f8c040592073e",
  "resource_type": "ec2_instances",
  "drift_type": "modified",
  "severity": "medium",
  "account_id": "961639320333",
  "region": "ap-southeast-1",
  "detected_at": "2025-11-21T01:31:31.733968Z",

  "updated_by": "quy",
  "updated_at": "2025-11-21T01:17:31+07:00",

  "diff": {
    "tags": {
      "baseline": {"Name": "my-ec2-instance-d"},
      "current": {"Name": "my-ec2-instance-da"}
    },
    "name": {
      "baseline": "my-ec2-instance-d",
      "current": "my-ec2-instance-da"
    },
    "_baseline_context": {
      "created_by": "cloud_drift_AI",
      "created_by_arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
      "created_by_type": "user",
      "created_at": "2025-11-21T01:16:48.598281"
    }
  },

  "change_history": {
    "last_modified_by": "quy",
    "last_modified_at": "2025-11-21T01:17:31+07:00",
    "total_events": 8,
```
