# Drift User Tracking - Giải thích các fields

## Tổng quan

Khi phát hiện drift, hệ thống track 3 loại thông tin người dùng khác nhau:

## 1. `_baseline_context.created_by` - Người tạo Baseline

**Mục đích**: Biết ai tạo snapshot baseline ban đầu để so sánh

**Ví dụ**:

```json
{
    "_baseline_context": {
        "created_by": "cloud_drift_AI",
        "created_by_arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
        "created_by_type": "user",
        "created_at": "2025-11-21T01:16:48.598281"
    }
}
```

**Giải thích**:

-   User `cloud_drift_AI` (service account) đã chạy lệnh `create_baseline()`
-   Thời gian: 2025-11-21 01:16:48
-   Đây là thông tin về BASELINE, không phải về drift

---

## 2. `updated_by` / `updated_at` - Người gây ra Drift ⭐

**Mục đích**: Biết ai thực hiện thay đổi gây ra drift này

**Ví dụ**:

```json
{
    "drift_id": "drift-boto3-20251121-abc123",
    "resource_id": "i-0b86f8c040592073e",
    "updated_by": "quy",
    "updated_at": "2025-11-21T01:17:31+07:00",
    "diff": {
        "tags": {
            "baseline": { "Name": "my-ec2-instance-d" },
            "current": { "Name": "my-ec2-instance-da" }
        }
    }
}
```

**Giải thích**:

-   User `quy` đã thay đổi Name tag
-   Thời gian: 2025-11-21 01:17:31 (SAU khi baseline được tạo)
-   Đây là thông tin QUAN TRỌNG NHẤT - ai gây ra drift

**Cách lấy**:

-   Từ CloudTrail event match với diff cụ thể
-   Ví dụ: `CreateTags` event với value "my-ec2-instance-da"

---

## 3. `scanned_by` - Người chạy Drift Detection

**Mục đích**: Biết ai đang chạy tool drift detection

**Ví dụ**:

```json
{
    "scanned_by": {
        "arn": "arn:aws:iam::961639320333:user/cloud_drift_AI",
        "account_id": "961639320333",
        "user_id": "AIDA57ZRLRMGQLVYTPT3D",
        "type": "user",
        "name": "cloud_drift_AI",
        "timestamp": "2025-11-21T01:03:44.215936"
    }
}
```

**Giải thích**:

-   Service account `cloud_drift_AI` đang chạy drift detection
-   Thời gian: 2025-11-21 01:03:44
-   Đây là thông tin về TOOL, không phải về drift

---

## Timeline ví dụ

```
01:16:48 - cloud_drift_AI tạo baseline (Name = "my-ec2-instance-d")
           ↓
01:17:31 - quy thay đổi Name → "my-ec2-instance-da" ⚠️ DRIFT!
           ↓
01:31:31 - cloud_drift_AI chạy drift detection và phát hiện drift
```

---

## Sử dụng trong code

### Lấy người gây ra drift (RECOMMENDED):

```python
drift_record = detector.compare_states(baseline, current, account_id, region)
print(f"Drift caused by: {drift_record.updated_by}")
print(f"At: {drift_record.updated_at}")
```

### Lấy từ change_history (chi tiết hơn):

```python
if drift_record.change_history:
    print(f"Last modified by: {drift_record.change_history['last_modified_by']}")
    print(f"Drift causing event: {drift_record.change_history['drift_causing_event']}")
```

### Lấy người tạo baseline:

```python
baseline_creator = drift_record.diff.get("_baseline_context", {}).get("created_by")
print(f"Baseline created by: {baseline_creator}")
```

---

## Các loại drift có thể track được người modified

✅ **EC2**: Tags, Instance Type, Security Groups, IAM Profile, Volumes, EBS Optimized
✅ **Lambda**: Configuration, Code, Concurrency, Tags, VPC Config
✅ **RDS**: Instance Class, Storage, Backup, Multi-AZ, Public Access, Tags
✅ **S3**: Versioning, Encryption, Public Access, Tags, Lifecycle
✅ **Security Groups**: Ingress/Egress Rules, Tags
✅ **DynamoDB**: Billing Mode, Capacity, Tags
✅ **SQS**: Attributes, Tags

❌ **Không track được**: Auto-scaling changes, System-initiated changes, Spot interruptions

---

## Debug

Nếu `updated_by` là `None`, check debug files:

```
data/debug/change_history_{resource_id}_{timestamp}.json
data/debug/change_history_{resource_id}_enriched_{timestamp}.json
```

Xem:

-   `matched_events_count`: Có bao nhiêu CloudTrail events?
-   `drift_causing_event`: Event nào match với drift?
-   `last_modified_by`: Username từ event đó
