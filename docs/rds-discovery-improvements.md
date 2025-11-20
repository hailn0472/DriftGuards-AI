# RDS Discovery Improvements

## Cải tiến cho RDS Instances & Clusters

### 1. RDS Instances Discovery

#### Trước (Basic)

```python
response = rds_client.describe_db_instances()
for i in response.get("DBInstances", []):
    # Basic fields only
```

#### Sau (Enhanced + Paginated)

```python
paginator = rds_client.get_paginator("describe_db_instances")
for page in paginator.paginate():
    for i in page.get("DBInstances", []):
        # Comprehensive fields with comments
```

### 2. Key Improvements

#### A. Pagination

-   **Trước**: Chỉ lấy 100 instances đầu tiên
-   **Sau**: Lấy TẤT CẢ instances với pagination

#### B. Aurora Cluster Linking

```python
"cluster_id": i.get("DBClusterIdentifier")  # Link instance to cluster
```

-   Quan trọng để hiểu topology Aurora
-   Biết instance nào thuộc cluster nào

#### C. Critical Security Fields

```python
"publicly_accessible": i.get("PubliclyAccessible")  # FORBIDDEN in Enterprise
"ca_certificate_id": i.get("CACertificateIdentifier")  # Drift breaks SSL
```

#### D. Cost-Related Fields

```python
"instance_class": i.get("DBInstanceClass")  # Drift costs money
"max_allocated_storage": i.get("MaxAllocatedStorage")  # Autoscaling
```

#### E. Sorted Collections

```python
"vpc_security_groups": sorted([...], key=lambda x: x["id"])
"parameter_groups": sorted([...], key=lambda x: x["name"])
```

-   Đảm bảo thứ tự nhất quán
-   Tránh false positive drift

---

## RDS Clusters (Aurora)

### Cải tiến chính

#### 1. Pagination

```python
paginator = rds_client.get_paginator("describe_db_clusters")
```

#### 2. Engine Mode

```python
"engine_mode": c.get("EngineMode")  # provisioned / serverless
```

-   Phân biệt Aurora Provisioned vs Serverless
-   Quan trọng cho cost và performance

#### 3. Deletion Protection

```python
"deletion_protection": c.get("DeletionProtection")
```

-   Dev hay tắt để xóa dễ → RỦI RO
-   Critical drift cần alert

#### 4. Backup & RPO/RTO

```python
"backup_retention_period": c.get("BackupRetentionPeriod")  # 1-35 days
"preferred_backup_window": c.get("PreferredBackupWindow")
"copy_tags_to_snapshot": c.get("CopyTagsToSnapshot")
```

#### 5. Reader Endpoint

```python
"endpoint": c.get("Endpoint")  # Writer endpoint
"reader_endpoint": c.get("ReaderEndpoint")  # Reader endpoint
```

-   Quan trọng cho read scaling
-   Drift ở đây ảnh hưởng application

#### 6. Tags as Dict

```python
"tags": {t["Key"]: t["Value"] for t in c.get("TagList", [])}
```

-   Dễ truy cập hơn
-   Consistent với EC2 instances

---

## Drift Detection Scenarios

### Scenario 1: Instance Class Change (Cost Impact)

```json
{
    "instance_class": {
        "baseline": "db.t3.micro",
        "current": "db.r5.large"
    }
}
```

**Impact**: Chi phí tăng ~10x

### Scenario 2: Public Access Enabled (Security Risk)

```json
{
    "publicly_accessible": {
        "baseline": false,
        "current": true
    }
}
```

**Impact**: CRITICAL - Database exposed to internet

### Scenario 3: Deletion Protection Disabled

```json
{
    "deletion_protection": {
        "baseline": true,
        "current": false
    }
}
```

**Impact**: HIGH - Risk of accidental deletion

### Scenario 4: CA Certificate Changed

```json
{
    "ca_certificate_id": {
        "baseline": "rds-ca-2019",
        "current": "rds-ca-rsa2048-g1"
    }
}
```

**Impact**: Application SSL errors if not updated

### Scenario 5: Backup Retention Reduced

```json
{
    "backup_retention_period": {
        "baseline": 7,
        "current": 1
    }
}
```

**Impact**: Reduced RPO, compliance violation

### Scenario 6: Security Group Changed

```json
{
    "vpc_security_groups": {
        "baseline": [{ "id": "sg-123", "status": "active" }],
        "current": [{ "id": "sg-456", "status": "active" }]
    }
}
```

**Impact**: Network access rules changed

---

## CloudTrail Events for RDS

### Instance Changes

-   `ModifyDBInstance`: Instance class, storage, etc.
-   `StartDBInstance` / `StopDBInstance`: State changes
-   `DeleteDBInstance`: Deletion
-   `AddTagsToResource` / `RemoveTagsFromResource`: Tags

### Cluster Changes

-   `ModifyDBCluster`: Cluster configuration
-   `CreateDBCluster` / `DeleteDBCluster`: Lifecycle
-   `FailoverDBCluster`: Failover events

---

## Benefits

1. ✅ **Complete Coverage**: Pagination ensures no instances missed
2. ✅ **Aurora Support**: Proper cluster-instance linking
3. ✅ **Security Focus**: Track critical security settings
4. ✅ **Cost Awareness**: Monitor cost-impacting changes
5. ✅ **Consistent Ordering**: Avoid false positive drifts
6. ✅ **Better Context**: More fields for better analysis

---

## Example Baseline Entry

### RDS Instance

```json
{
    "id": "mysql-db-abc123",
    "arn": "arn:aws:rds:ap-southeast-1:961639320333:db:mysql-db-abc123",
    "cluster_id": null,
    "engine": "mysql",
    "engine_version": "8.0.35",
    "status": "available",
    "instance_class": "db.t3.micro",
    "storage_type": "gp2",
    "allocated_storage": 20,
    "publicly_accessible": false,
    "storage_encrypted": true,
    "ca_certificate_id": "rds-ca-rsa2048-g1",
    "vpc_security_groups": [{ "id": "sg-0abc123", "status": "active" }],
    "multi_az": false,
    "deletion_protection": true,
    "backup_retention_period": 7
}
```

### Aurora Cluster

```json
{
    "id": "aurora-cluster-xyz789",
    "arn": "arn:aws:rds:ap-southeast-1:961639320333:cluster:aurora-cluster-xyz789",
    "status": "available",
    "engine": "aurora-mysql",
    "engine_mode": "provisioned",
    "engine_version": "8.0.mysql_aurora.3.04.0",
    "storage_encrypted": true,
    "deletion_protection": true,
    "backup_retention_period": 7,
    "endpoint": "aurora-cluster-xyz789.cluster-abc.ap-southeast-1.rds.amazonaws.com",
    "reader_endpoint": "aurora-cluster-xyz789.cluster-ro-abc.ap-southeast-1.rds.amazonaws.com",
    "members": ["aurora-instance-1", "aurora-instance-2"],
    "tags": {
        "Environment": "production",
        "Application": "api"
    }
}
```
