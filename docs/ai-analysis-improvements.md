# AI Analysis Improvements - Root Cause Specificity

## Vấn đề trước đây

AI trả về root cause quá chung chung, không có thông tin cụ thể:

```json
{
    "root_cause": "Manual change by an authorized IAM user",
    "explanation": "The instance name tag was modified through the AWS Console"
}
```

**Vấn đề**: Không biết user nào, khi nào, action gì!

---

## Cải tiến mới

### 1. Thêm thông tin WHO/WHEN/WHAT vào prompt

```
WHO MADE THE CHANGE:
Changed By: quy
Changed At: 2025-11-21T01:47:15+07:00
AWS Action: CreateTags
```

### 2. Nhấn mạnh trong change history

```
============================================================
⚠️  DRIFT CAUSED BY: quy (IAM User/Role)
⏰  TIME: 2025-11-21T01:47:15+07:00
📊  Total Change Events: 8
============================================================

Recent Change Events:
  [2025-11-21T01:47:15+07:00] CreateTags
    👤 IAM User/Role: quy
    🌐 Source IP: 14.224.176.224
    🔑 Identity Type: IAMUser
    📋 ARN: arn:aws:iam::961639320333:user/quy
```

### 3. Hướng dẫn rõ ràng cho AI

```
IMPORTANT INSTRUCTIONS FOR ROOT CAUSE:
- Always mention the specific IAM user/role name from "Changed By" field
- Include the AWS action from "AWS Action" field
- Example good root cause: "Manual change by IAM user 'quy' who modified
  the Name tag via CreateTags action in AWS Console at 2025-11-21 01:47:15"
- Example bad root cause: "Manual change by an authorized IAM user" (too generic!)
```

---

## Output mong đợi

### Root Cause (Cụ thể)

```json
{
    "root_cause": "Manual change by IAM user 'quy' who modified the Name tag from 'my-ec2-instance-da' to 'my-ec2-instance-dam' via CreateTags action in AWS Console at 2025-11-21 01:47:15 from IP 14.224.176.224",

    "explanation": "User quy accessed the AWS Console and changed the EC2 instance Name tag. This was a manual modification performed through the AWS Management Console, as evidenced by the CreateTags CloudTrail event.",

    "business_impact": "Low impact - this is a cosmetic change to the instance name tag that does not affect functionality. However, it creates drift from the approved baseline configuration managed by cloud_drift_AI.",

    "recommended_action": "update_baseline",

    "confidence_score": 95
}
```

### Explanation (Chi tiết)

```json
{
    "explanation": "At 2025-11-21 01:47:15, IAM user 'quy' modified the Name tag of EC2 instance i-0b86f8c040592073e from 'my-ec2-instance-da' to 'my-ec2-instance-dam'. The change was made through the AWS Console (CreateTags API call) from IP address 14.224.176.224. This represents a manual configuration change that deviates from the baseline established by cloud_drift_AI at 2025-11-21 01:44:14."
}
```

---

## So sánh Before/After

### ❌ Before (Generic)

```
Root Cause: Manual change by an authorized IAM user
Explanation: The instance was modified through the console
```

### ✅ After (Specific)

```
Root Cause: Manual change by IAM user 'quy' who modified the Name tag
via CreateTags action in AWS Console at 2025-11-21 01:47:15 from IP 14.224.176.224

Explanation: At 2025-11-21 01:47:15, IAM user 'quy' modified the Name tag
of EC2 instance i-0b86f8c040592073e from 'my-ec2-instance-da' to
'my-ec2-instance-dam'. The change was made through the AWS Console
(CreateTags API call) from IP address 14.224.176.224.
```

---

## Lợi ích

1. **Accountability**: Biết chính xác ai thực hiện thay đổi
2. **Audit Trail**: Có đầy đủ thông tin để audit
3. **Faster Resolution**: Có thể liên hệ trực tiếp với người thực hiện
4. **Better Context**: Hiểu rõ hơn về ngữ cảnh thay đổi
5. **Compliance**: Đáp ứng yêu cầu compliance về tracking changes

---

## Các trường hợp đặc biệt

### System-initiated changes

```json
{
    "root_cause": "System-initiated change by AWS Auto Scaling service. No human user involved - this was an automated scaling action triggered by CloudWatch alarms.",
    "changed_by": "autoscaling.amazonaws.com"
}
```

### Root account changes

```json
{
    "root_cause": "Manual change by AWS root account user (Account ID: 961639320333) who stopped the instance via StopInstances action at 2025-11-20 22:06:58 from IP 14.162.176.123. Root account usage detected - recommend using IAM users instead.",
    "changed_by": "root"
}
```

### Unknown user (old changes)

```json
{
    "root_cause": "Change detected but no CloudTrail events found in the last 24 hours. This change may have occurred more than 24 hours ago, or CloudTrail logging may not have been enabled at the time of change.",
    "changed_by": "Unknown"
}
```
