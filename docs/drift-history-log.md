# Drift History Log

## Mục đích

Ghi lại tất cả các drift đã phát hiện để:

-   **Audit trail**: Theo dõi lịch sử thay đổi
-   **Compliance**: Đáp ứng yêu cầu audit
-   **Analytics**: Phân tích xu hướng drift
-   **Accountability**: Biết ai thực hiện thay đổi nào

## Vị trí file

```
data/drift_history/drift_history_YYYY-MM-DD.jsonl
```

Ví dụ:

-   `data/drift_history/drift_history_2025-11-21.jsonl`
-   `data/drift_history/drift_history_2025-11-22.jsonl`

## Format

Mỗi drift được ghi thành 1 dòng JSON (JSONL format):

```json
{
    "timestamp": "2025-11-21T01:50:15.123456",
    "drift_id": "drift-boto3-20251121-abc12345",
    "resource_id": "i-0b86f8c040592073e",
    "resource_type": "ec2_instances",
    "drift_type": "modified",
    "severity": "medium",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": "quy",
    "updated_at": "2025-11-21T01:47:15+07:00",
    "detected_at": "2025-11-21T01:50:15.123456",
    "diff_summary": {
        "tags": {
            "from": "{'Name': 'my-ec2-instance-da'}",
            "to": "{'Name': 'my-ec2-instance-dam'}"
        },
        "name": {
            "from": "my-ec2-instance-da",
            "to": "my-ec2-instance-dam"
        }
    }
}
```

## Fields

| Field           | Type     | Description                                       |
| --------------- | -------- | ------------------------------------------------- |
| `timestamp`     | ISO 8601 | Thời điểm ghi log                                 |
| `drift_id`      | string   | ID duy nhất của drift                             |
| `resource_id`   | string   | AWS resource ID                                   |
| `resource_type` | string   | Loại resource (ec2_instances, s3_buckets, etc.)   |
| `drift_type`    | string   | Loại drift (modified, deleted, unmanaged)         |
| `severity`      | string   | Mức độ nghiêm trọng (critical, high, medium, low) |
| `account_id`    | string   | AWS account ID                                    |
| `region`        | string   | AWS region                                        |
| `updated_by`    | string   | IAM user/role thực hiện thay đổi                  |
| `updated_at`    | ISO 8601 | Thời điểm thay đổi (từ CloudTrail)                |
| `detected_at`   | ISO 8601 | Thời điểm phát hiện drift                         |
| `diff_summary`  | object   | Tóm tắt thay đổi                                  |

## Ví dụ thực tế

### 1. Tag Change by User

```json
{
    "timestamp": "2025-11-21T01:50:15.123456",
    "drift_id": "drift-boto3-20251121-abc12345",
    "resource_id": "i-0b86f8c040592073e",
    "resource_type": "ec2_instances",
    "drift_type": "modified",
    "severity": "medium",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": "quy",
    "updated_at": "2025-11-21T01:47:15+07:00",
    "detected_at": "2025-11-21T01:50:15.123456",
    "diff_summary": {
        "tags": {
            "from": "{'Name': 'my-ec2-instance-da'}",
            "to": "{'Name': 'my-ec2-instance-dam'}"
        }
    }
}
```

### 2. Instance Type Change

```json
{
    "timestamp": "2025-11-21T02:15:30.456789",
    "drift_id": "drift-boto3-20251121-def67890",
    "resource_id": "i-0b86f8c040592073e",
    "resource_type": "ec2_instances",
    "drift_type": "modified",
    "severity": "high",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": "quy",
    "updated_at": "2025-11-21T00:43:12+07:00",
    "detected_at": "2025-11-21T02:15:30.456789",
    "diff_summary": {
        "type": { "from": "t3a.small", "to": "t3a.medium" }
    }
}
```

### 3. Security Group Change (Critical)

```json
{
    "timestamp": "2025-11-21T03:20:45.789012",
    "drift_id": "drift-boto3-20251121-ghi34567",
    "resource_id": "i-0b86f8c040592073e",
    "resource_type": "ec2_instances",
    "drift_type": "modified",
    "severity": "critical",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": "admin",
    "updated_at": "2025-11-21T03:18:30+07:00",
    "detected_at": "2025-11-21T03:20:45.789012",
    "diff_summary": {
        "security_groups": {
            "from": "[{'id': 'sg-123', 'name': 'default'}]",
            "to": "[{'id': 'sg-456', 'name': 'open-all'}]"
        }
    }
}
```

### 4. Unknown User (Old Change)

```json
{
    "timestamp": "2025-11-21T04:10:00.123456",
    "drift_id": "drift-boto3-20251121-jkl89012",
    "resource_id": "i-0xyz123456789abcd",
    "resource_type": "ec2_instances",
    "drift_type": "modified",
    "severity": "medium",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": null,
    "updated_at": null,
    "detected_at": "2025-11-21T04:10:00.123456",
    "diff_summary": {
        "state": { "from": "running", "to": "stopped" }
    }
}
```

### 5. Deleted Resource

```json
{
    "timestamp": "2025-11-21T05:30:15.234567",
    "drift_id": "drift-boto3-20251121-mno45678",
    "resource_id": "i-0deleted123456789",
    "resource_type": "ec2_instances",
    "drift_type": "deleted",
    "severity": "critical",
    "account_id": "961639320333",
    "region": "ap-southeast-1",
    "updated_by": "root",
    "updated_at": "2025-11-21T05:28:00+07:00",
    "detected_at": "2025-11-21T05:30:15.234567",
    "diff_summary": {}
}
```

## Sử dụng

### Đọc drift history

```python
import json
from pathlib import Path

# Đọc drift history của ngày hôm nay
history_file = Path("data/drift_history/drift_history_2025-11-21.jsonl")

with open(history_file) as f:
    for line in f:
        drift = json.loads(line)
        print(f"{drift['timestamp']}: {drift['resource_id']} changed by {drift['updated_by']}")
```

### Phân tích drift theo user

```python
from collections import Counter

user_drifts = Counter()

with open(history_file) as f:
    for line in f:
        drift = json.loads(line)
        user = drift.get('updated_by') or 'Unknown'
        user_drifts[user] += 1

print("Drifts by user:")
for user, count in user_drifts.most_common():
    print(f"  {user}: {count} drifts")
```

### Tìm critical drifts

```python
critical_drifts = []

with open(history_file) as f:
    for line in f:
        drift = json.loads(line)
        if drift['severity'] == 'critical':
            critical_drifts.append(drift)

print(f"Found {len(critical_drifts)} critical drifts")
for drift in critical_drifts:
    print(f"  {drift['resource_id']}: {drift['drift_type']} by {drift['updated_by']}")
```

## Retention Policy

Khuyến nghị:

-   **Keep**: 90 ngày gần nhất
-   **Archive**: Sau 90 ngày, nén và lưu trữ
-   **Delete**: Sau 1 năm (hoặc theo compliance requirements)

```bash
# Archive old logs (older than 90 days)
find data/drift_history -name "*.jsonl" -mtime +90 -exec gzip {} \;

# Delete very old logs (older than 1 year)
find data/drift_history -name "*.jsonl.gz" -mtime +365 -delete
```

## Integration với Monitoring

### Send to CloudWatch Logs

```python
import boto3

logs_client = boto3.client('logs')

with open(history_file) as f:
    for line in f:
        drift = json.loads(line)
        logs_client.put_log_events(
            logGroupName='/aws/driftguards/history',
            logStreamName='drift-events',
            logEvents=[{
                'timestamp': int(datetime.fromisoformat(drift['timestamp']).timestamp() * 1000),
                'message': json.dumps(drift)
            }]
        )
```

### Send to Elasticsearch

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['localhost:9200'])

with open(history_file) as f:
    for line in f:
        drift = json.loads(line)
        es.index(index='drift-history', document=drift)
```

## Benefits

1. **Complete Audit Trail**: Mọi drift đều được ghi lại
2. **User Accountability**: Biết ai thực hiện thay đổi nào
3. **Trend Analysis**: Phân tích xu hướng drift theo thời gian
4. **Compliance**: Đáp ứng yêu cầu audit và compliance
5. **Forensics**: Điều tra sự cố dễ dàng hơn
