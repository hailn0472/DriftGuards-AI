# Drift Detection Examples

This document shows how the enriched `aws_resources_base.json` data is used for drift detection.

## Overview

The boto3 drift detection compares **baseline state** (expected configuration) against **current state** (live AWS resources) to detect three types of drift:

1. **DELETED** - Resources that existed in baseline but are missing now
2. **UNMANAGED** - New resources that weren't in the baseline
3. **MODIFIED** - Resources with configuration changes

## Data Structure for Drift Detection

### ✅ **Configuration Fields** (Used for Drift Detection)
These fields are **static configuration** that should remain stable:

```json
{
  "id": "i-0a1b2c3d4e5f6g7h8",
  "instance_type": "t3.medium",        // ✅ Detect changes
  "state": "running",                   // ✅ Detect changes
  "availability_zone": "us-east-1a",    // ✅ Detect changes
  "vpc_id": "vpc-123",                  // ✅ Detect changes
  "security_groups": ["sg-123"],        // ✅ Detect changes
  "ami_id": "ami-abc123",               // ✅ Detect changes
  "publicly_accessible": false          // ✅ CRITICAL - detect changes
}
```

### ⚠️ **Metrics Fields** (Excluded from Drift Detection)
These fields are **dynamic metrics** that change frequently:

```json
{
  "metrics": {
    "cpu_utilization_percent": 45.7,    // ❌ Too volatile for drift
    "memory_used_percent": 62.3,        // ❌ Too volatile for drift
    "network_in_bytes_per_sec": 1048576 // ❌ Too volatile for drift
  },
  "launch_time": "2025-10-15T08:30:00Z", // ❌ Timestamp, not drift
  "uptime_days": 20,                      // ❌ Changes daily
  "monthly_cost_usd": 30.08               // ❌ Varies with usage
}
```

**Note**: The updated `_calculate_diff()` method now automatically excludes these volatile fields.

## Drift Detection Examples

### Example 1: DELETED Resource (CRITICAL)

**Baseline State:**
```json
{
  "s3_buckets": [
    {
      "name": "assets-bucket-0e84de4",
      "region": "us-east-1",
      "metrics": {
        "size_gb": 2.29,
        "object_count": 1243
      }
    }
  ]
}
```

**Current State:**
```json
{
  "s3_buckets": []  // Bucket was deleted!
}
```

**Drift Record:**
```json
{
  "drift_id": "drift-boto3-20251104-a1b2c3d4",
  "resource_id": "assets-bucket-0e84de4",
  "resource_type": "s3_buckets",
  "drift_type": "DELETED",
  "severity": "CRITICAL",
  "terraform_value": {"name": "assets-bucket-0e84de4", "region": "us-east-1"},
  "actual_value": {},
  "diff": {}
}
```

---

### Example 2: UNMANAGED Resource (HIGH)

**Baseline State:**
```json
{
  "ec2_instances": [
    {
      "id": "i-0a1b2c3d4e5f6g7h8",
      "name": "web-server-01",
      "instance_type": "t3.medium"
    }
  ]
}
```

**Current State:**
```json
{
  "ec2_instances": [
    {
      "id": "i-0a1b2c3d4e5f6g7h8",
      "name": "web-server-01",
      "instance_type": "t3.medium"
    },
    {
      "id": "i-NEW123456789",           // New instance appeared!
      "name": "unauthorized-server",
      "instance_type": "t3.large",
      "tags": []
    }
  ]
}
```

**Drift Record:**
```json
{
  "drift_id": "drift-boto3-20251104-e5f6g7h8",
  "resource_id": "i-NEW123456789",
  "resource_type": "ec2_instances",
  "drift_type": "UNMANAGED",
  "severity": "HIGH",
  "terraform_value": {},
  "actual_value": {
    "id": "i-NEW123456789",
    "name": "unauthorized-server",
    "instance_type": "t3.large"
  },
  "diff": {}
}
```

---

### Example 3: MODIFIED Resource - Instance Type Change (HIGH)

**Baseline State:**
```json
{
  "rds_instances": [
    {
      "db_instance_identifier": "legacy-mysql-01",
      "db_instance_class": "db.t3.medium",
      "engine": "mysql",
      "instance_specs": {
        "vcpu": 2,
        "memory_gb": 4
      },
      "allocated_storage": 100,
      "multi_az": false
    }
  ]
}
```

**Current State:**
```json
{
  "rds_instances": [
    {
      "db_instance_identifier": "legacy-mysql-01",
      "db_instance_class": "db.r5.large",    // Changed!
      "engine": "mysql",
      "instance_specs": {
        "vcpu": 2,
        "memory_gb": 16                      // Changed!
      },
      "allocated_storage": 100,
      "multi_az": false
    }
  ]
}
```

**Drift Record:**
```json
{
  "drift_id": "drift-boto3-20251104-i9j0k1l2",
  "resource_id": "legacy-mysql-01",
  "resource_type": "rds_instances",
  "drift_type": "MODIFIED",
  "severity": "HIGH",
  "diff": {
    "db_instance_class": {
      "baseline": "db.t3.medium",
      "current": "db.r5.large"
    },
    "instance_specs": {
      "baseline": {"vcpu": 2, "memory_gb": 4},
      "current": {"vcpu": 2, "memory_gb": 16}
    }
  }
}
```

---

### Example 4: MODIFIED Resource - Security Change (CRITICAL)

**Baseline State:**
```json
{
  "rds_instances": [
    {
      "db_instance_identifier": "reporting-postgres",
      "publicly_accessible": false,    // Secure
      "vpc_id": "vpc-0916ff4a39c14585f"
    }
  ]
}
```

**Current State:**
```json
{
  "rds_instances": [
    {
      "db_instance_identifier": "reporting-postgres",
      "publicly_accessible": true,     // SECURITY ISSUE!
      "vpc_id": "vpc-0916ff4a39c14585f"
    }
  ]
}
```

**Drift Record:**
```json
{
  "drift_id": "drift-boto3-20251104-m3n4o5p6",
  "resource_id": "reporting-postgres",
  "resource_type": "rds_instances",
  "drift_type": "MODIFIED",
  "severity": "CRITICAL",  // Security field changed!
  "diff": {
    "publicly_accessible": {
      "baseline": false,
      "current": true
    }
  }
}
```

---

### Example 5: MODIFIED Resource - Tags Only (MEDIUM)

**Baseline State:**
```json
{
  "lambda_functions": [
    {
      "name": "order-processor",
      "runtime": "python3.11",
      "memory_size": 512,
      "tags": [
        {"Key": "Environment", "Value": "production"}
      ]
    }
  ]
}
```

**Current State:**
```json
{
  "lambda_functions": [
    {
      "name": "order-processor",
      "runtime": "python3.11",
      "memory_size": 512,
      "tags": [
        {"Key": "Environment", "Value": "production"},
        {"Key": "Team", "Value": "backend"}       // Tag added
      ]
    }
  ]
}
```

**Drift Record:**
```json
{
  "drift_id": "drift-boto3-20251104-q7r8s9t0",
  "resource_id": "order-processor",
  "resource_type": "lambda_functions",
  "drift_type": "MODIFIED",
  "severity": "MEDIUM",  // Only tags changed
  "diff": {
    "tags": {
      "baseline": [{"Key": "Environment", "Value": "production"}],
      "current": [
        {"Key": "Environment", "Value": "production"},
        {"Key": "Team", "Value": "backend"}
      ]
    }
  }
}
```

---

### Example 6: No Drift - Metrics Changed (Ignored)

**Baseline State:**
```json
{
  "ec2_instances": [
    {
      "id": "i-0a1b2c3d4e5f6g7h8",
      "instance_type": "t3.medium",
      "state": "running",
      "metrics": {
        "cpu_utilization_percent": 45.7,
        "memory_used_percent": 62.3
      }
    }
  ]
}
```

**Current State:**
```json
{
  "ec2_instances": [
    {
      "id": "i-0a1b2c3d4e5f6g7h8",
      "instance_type": "t3.medium",
      "state": "running",
      "metrics": {
        "cpu_utilization_percent": 78.2,  // Metrics changed
        "memory_used_percent": 85.1        // Metrics changed
      }
    }
  ]
}
```

**Result:** ✅ **NO DRIFT DETECTED**

The `metrics` field is excluded from drift detection because it changes frequently. This would be flagged by **anomaly detection** instead (separate from drift detection).

---

## Severity Calculation

The `_calculate_severity()` method assigns severity based on:

| Condition | Severity | Example |
|-----------|----------|---------|
| Resource deleted | **CRITICAL** | S3 bucket deleted |
| Security field changed | **CRITICAL** | `publicly_accessible: true` |
| Encryption field changed | **CRITICAL** | `encryption_enabled: false` |
| Policy/IAM changed | **CRITICAL** | Security group rules modified |
| Unmanaged resource | **HIGH** | New EC2 instance appeared |
| Instance type/class changed | **HIGH** | `t3.medium` → `r5.large` |
| Storage size changed | **HIGH** | `allocated_storage: 100` → `500` |
| Only tags changed | **MEDIUM** | Tag added/removed |
| Other config changes | **MEDIUM** | Backup window changed |

---

## Summary

### ✅ Your Data is Perfect for Drift Detection Because:

1. **Comprehensive Configuration**: All critical AWS properties captured
2. **Rich Context**: Instance specs, security settings, network config
3. **Proper Structure**: Clear separation of static vs dynamic data
4. **Complete Coverage**: EC2, RDS, S3, DynamoDB, SQS, Lambda, Security Groups

### 🎯 How to Use:

1. **Create Baseline**: Run `boto3_detection.py` → `create_baseline()` using your current AWS state
2. **Monitor Continuously**: Run `discover_current_state()` → `compare_states()` periodically
3. **Alert on Drift**: Filter by severity (CRITICAL → HIGH → MEDIUM)
4. **Investigate**: Use `diff` field to see exact changes
5. **Remediate**: Decide to accept drift or restore baseline configuration

### 📊 Metrics Usage:

- **Drift Detection**: Configuration fields only (instance type, security groups, etc.)
- **Anomaly Detection**: Use metrics separately (CPU spikes, memory exhaustion, etc.)
- **Cost Tracking**: Monthly cost trends (separate from drift)
- **Capacity Planning**: Throughput/IOPS metrics over time

Your enriched data structure supports **all these use cases**! 🚀
