# 🔧 Approve Drift - Troubleshooting Guide

## ❗ Issue: Baseline không được cập nhật sau khi approve

### Nguyên nhân có thể:

1. **Drift.actual_value rỗng hoặc thiếu dữ liệu**
2. **Resource type mapping không đúng**
3. **Baseline structure không khớp** (có thể có "resources" wrapper hoặc không)
4. **Permission issues** khi ghi file

---

## 🔍 Cách kiểm tra và debug

### Step 1: Kiểm tra logs chi tiết

Code đã được cập nhật với logging chi tiết. Khi approve drift, check terminal logs:

```
2025-11-07 ... [info] Updating baseline for drift: drift-xxx
2025-11-07 ... [info]   Resource: i-07735a53d7e3968a3 (ec2_instances)
2025-11-07 ... [info]   Drift type: unmanaged
2025-11-07 ... [info]   Actual value keys: ['id', 'type', 'state', 'vpc_id', ...]
2025-11-07 ... [info]   Mapped to baseline key: ec2_instances
2025-11-07 ... [info]   Current baseline has 2 ec2_instances
2025-11-07 ... [info] ✅ Added new resource to baseline: i-07735a53d7e3968a3
2025-11-07 ... [info]   Resource data: {...}
2025-11-07 ... [info]   Baseline now has 3 ec2_instances
2025-11-07 ... [info] Created baseline backup: data/baseline/baseline_state.backup.json
2025-11-07 ... [info] Baseline saved successfully
```

**Chú ý:**
- `Actual value keys` - Phải có dữ liệu instance đầy đủ
- `Added new resource` hoặc `Updated existing resource` - Xác nhận hành động
- `Baseline now has X` - Số lượng resource sau khi update

---

### Step 2: Kiểm tra drift.actual_value

Trong dashboard, trước khi approve, xem phần **"Current Value"** của drift:

```python
# Drift phải có actual_value đầy đủ như này:
{
  "id": "i-07735a53d7e3968a3",
  "type": "t2.micro",
  "state": "running",
  "vpc_id": "vpc-xxx",
  "subnet_id": "subnet-xxx",
  "private_ip": "10.0.1.43",
  "public_ip": "13.229.100.53",
  "tags": [...]
}
```

**Nếu actual_value rỗng `{}`** → Vấn đề ở detection phase, không phải approval!

---

### Step 3: Kiểm tra baseline structure

Baseline có thể có 2 formats:

**Format 1: Top-level resources**
```json
{
  "account_id": "xxx",
  "region": "us-east-1",
  "ec2_instances": [...],
  "s3_buckets": [...]
}
```

**Format 2: Nested trong "resources"**
```json
{
  "account_id": "xxx",
  "region": "us-east-1",
  "resources": {
    "ec2_instances": [...],
    "s3_buckets": [...]
  }
}
```

Code đã được update để handle cả 2 formats.

---

### Step 4: Manual verification

Sau khi approve:

1. **Mở file baseline**:
   ```
   d:\github\DriftGuards-AI\data\baseline\baseline_state.json
   ```

2. **Search instance ID** trong file (Ctrl+F): `i-07735a53d7e3968a3`

3. **Nếu KHÔNG TÌM THẤY** → Check logs để xem lỗi gì

4. **So sánh với backup**:
   ```
   d:\github\DriftGuards-AI\data\baseline\baseline_state.backup.json
   ```

---

## 🔧 Fix thủ công nếu cần

Nếu approve không work, có thể thêm instance vào baseline manually:

```json
{
  "ec2_instances": [
    {
      "id": "i-existing",
      "type": "t2.micro",
      ...
    },
    {
      "id": "i-07735a53d7e3968a3",
      "type": "t2.micro",
      "state": "running",
      "vpc_id": "vpc-xxx",
      "subnet_id": "subnet-xxx",
      "private_ip": "10.0.1.43",
      "public_ip": "13.229.100.53",
      "tags": [
        {
          "Key": "Name",
          "Value": "my-instance"
        }
      ]
    }
  ]
}
```

---

## 🐛 Common Issues

### Issue 1: Resource type không map được

**Symptom**: Log shows `Mapped to baseline key: aws_instance` nhưng baseline có key là `ec2_instances`

**Fix**: Đã thêm mapping cho nhiều variants:
```python
type_mapping = {
    "aws_instance": "ec2_instances",
    "aws_ec2_instance": "ec2_instances",
    "ec2_instances": "ec2_instances",  # Direct match
    ...
}
```

### Issue 2: Actual_value empty

**Symptom**: Log shows `Actual value keys: []`

**Reason**: Drift detection không capture được resource data

**Fix**: Check detection agent (`boto3_detection.py`):
```python
# Khi tạo drift cho UNMANAGED resource:
drift = self._create_drift_record(
    resource_id=resource_id,
    resource_type=resource_type,
    drift_type=DriftType.UNMANAGED,
    baseline_value={},
    current_value=current_resource,  # ← Phải có data đầy đủ
    ...
)
```

### Issue 3: Permission denied

**Symptom**: `Failed to save baseline: Permission denied`

**Fix**:
```bash
# Check permissions
ls -la data/baseline/

# Fix permissions if needed
chmod 644 data/baseline/baseline_state.json
```

---

## 📊 Test Case để verify

### Test 1: Approve new instance

1. Create new EC2 instance outside of baseline
2. Run drift detection → Should find UNMANAGED instance
3. Approve the drift
4. Check logs for "Added new resource to baseline"
5. Open `baseline_state.json` and verify instance is there

### Test 2: Approve modified instance

1. Change instance type of existing instance
2. Run drift detection → Should find MODIFIED
3. Approve the drift
4. Check logs for "Updated existing resource in baseline"
5. Verify instance type is updated in baseline

### Test 3: Multiple approvals

1. Create 2-3 new resources
2. Approve them one by one
3. Each approval should add to baseline
4. Final baseline should have all resources

---

## 🔍 Debug Commands

```bash
# 1. Check if baseline file exists and is writable
ls -la data/baseline/baseline_state.json

# 2. Check file content
cat data/baseline/baseline_state.json | jq '.ec2_instances'

# 3. Compare with backup
diff data/baseline/baseline_state.json data/baseline/baseline_state.backup.json

# 4. Check approval logs
ls -la data/approvals/
cat data/approvals/approval-*.json | jq .

# 5. Watch logs in real-time
# Run dashboard in one terminal, watch logs in another
tail -f <dashboard_output>
```

---

## 💡 Quick Test Script

Tạo file `test_approval.py`:

```python
import asyncio
import json
from pathlib import Path
from app.services.approval_service import ApprovalService
from app.models.approval import ApprovalRequest
from app.models.drift import DriftRecord, DriftType, Severity, DriftStatus

async def test_approval():
    """Test approval service."""
    
    # Create test drift
    drift = DriftRecord(
        drift_id="test-drift-001",
        resource_id="i-test123",
        resource_type="ec2_instances",
        drift_type=DriftType.UNMANAGED,
        terraform_value={},
        actual_value={
            "id": "i-test123",
            "type": "t2.micro",
            "state": "running",
            "vpc_id": "vpc-test",
            "subnet_id": "subnet-test",
            "private_ip": "10.0.0.1",
            "public_ip": "1.2.3.4",
            "tags": [{"Key": "Name", "Value": "test-instance"}]
        },
        diff={},
        severity=Severity.LOW,
        account_id="123456789012",
        region="us-east-1",
        status=DriftStatus.OPEN
    )
    
    # Create approval request
    request = ApprovalRequest(
        drift_id=drift.drift_id,
        approved_by="test@example.com",
        reason="Test approval",
        update_baseline=True,
        notify=False
    )
    
    # Approve
    service = ApprovalService()
    approval = await service.approve_drift(drift, request)
    
    print(f"✅ Approval: {approval.approval_id}")
    
    # Check baseline
    baseline_file = Path("data/baseline/baseline_state.json")
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    # Look for test instance
    found = False
    for instance in baseline.get("ec2_instances", []):
        if instance.get("id") == "i-test123":
            found = True
            print(f"✅ Instance found in baseline!")
            print(json.dumps(instance, indent=2))
            break
    
    if not found:
        print("❌ Instance NOT found in baseline")
        print(f"Baseline has {len(baseline.get('ec2_instances', []))} instances")

if __name__ == "__main__":
    asyncio.run(test_approval())
```

Run:
```bash
python test_approval.py
```

---

## 📞 Support

Nếu vẫn không work sau khi check:

1. Copy full logs từ terminal
2. Copy nội dung `baseline_state.json`
3. Copy nội dung approval log từ `data/approvals/`
4. Share để debug chi tiết
