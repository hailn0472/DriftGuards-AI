# AI Prompt Examples - Dynamic Context

## Case 1: User Known (CloudTrail Found)

### Prompt Input

```
WHO MADE THE CHANGE:
Changed By: quy (IAM User/Role)
Changed At: 2025-11-21T01:47:15+07:00
AWS Action: CreateTags
Source: CloudTrail event logs

CHANGE HISTORY:
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

### Expected AI Output

```json
{
    "root_cause": "Manual change by IAM user 'quy' who modified the Name tag via CreateTags action at 2025-11-21T01:47:15 from IP 14.224.176.224",
    "explanation": "IAM user 'quy' accessed the AWS Console and changed the EC2 instance Name tag. This was a manual modification performed through the AWS Management Console.",
    "confidence_score": 95
}
```

---

## Case 2: Root Account

### Prompt Input

```
WHO MADE THE CHANGE:
Changed By: root (IAM User/Role)
Changed At: 2025-11-20T22:06:58+07:00
AWS Action: StopInstances
Source: CloudTrail event logs

CHANGE HISTORY:
============================================================
⚠️  DRIFT CAUSED BY: root (IAM User/Role)
⏰  TIME: 2025-11-20T22:06:58+07:00
============================================================

Recent Change Events:
  [2025-11-20T22:06:58+07:00] StopInstances
    👤 IAM User/Role: root
    🌐 Source IP: 14.162.176.123
    🔑 Identity Type: Root
    📋 ARN: arn:aws:iam::961639320333:root
```

### Expected AI Output

```json
{
    "root_cause": "Manual change by AWS root account user who stopped the instance via StopInstances action at 2025-11-20T22:06:58 from IP 14.162.176.123. SECURITY CONCERN: Root account usage detected - recommend using IAM users with appropriate permissions instead.",
    "explanation": "The AWS root account was used to stop this EC2 instance. Root account usage is a security risk and should be avoided for day-to-day operations.",
    "business_impact": "High security risk - root account usage violates AWS best practices and compliance requirements.",
    "confidence_score": 98
}
```

---

## Case 3: User Unknown (Old Change)

### Prompt Input

```
WHO MADE THE CHANGE:
Changed By: Unknown
Reason: No CloudTrail events found in the last 24 hours. The change may have occurred:
  - More than 24 hours ago (outside CloudTrail lookback window)
  - Before CloudTrail logging was enabled
  - By an AWS service (system-initiated change)
Note: Consider increasing CloudTrail lookback period if recent changes are not being captured.

CHANGE HISTORY:
No change history available
```

### Expected AI Output

```json
{
    "root_cause": "Change detected but no CloudTrail events found in the last 24 hours. The change likely occurred more than 24 hours ago, or CloudTrail logging may not have been enabled at the time. Unable to determine the specific IAM user/role responsible.",
    "explanation": "This drift was detected but the change history is not available. This could indicate the change happened outside the CloudTrail retention window (24 hours), or CloudTrail was not enabled when the change occurred.",
    "business_impact": "Unable to determine full impact without knowing who made the change and why. Recommend enabling CloudTrail with longer retention for better audit trails.",
    "recommended_action": "manual_review",
    "confidence_score": 40
}
```

---

## Case 4: Service Account

### Prompt Input

```
WHO MADE THE CHANGE:
Changed By: cloud_drift_AI (IAM User/Role)
Changed At: 2025-11-19T22:12:00+07:00
AWS Action: CreateTags
Source: CloudTrail event logs

CHANGE HISTORY:
============================================================
⚠️  DRIFT CAUSED BY: cloud_drift_AI (IAM User/Role)
⏰  TIME: 2025-11-19T22:12:00+07:00
============================================================

Recent Change Events:
  [2025-11-19T22:12:00+07:00] CreateTags
    👤 IAM User/Role: cloud_drift_AI
    🌐 Source IP: 1.55.210.228
    🔑 Identity Type: IAMUser
    📋 ARN: arn:aws:iam::961639320333:user/cloud_drift_AI
```

### Expected AI Output

```json
{
    "root_cause": "Automated change by service account 'cloud_drift_AI' via CreateTags action at 2025-11-19T22:12:00. This appears to be an automated baseline update or remediation action performed by the drift detection system itself.",
    "explanation": "The change was made by the cloud_drift_AI service account, which is the automated system managing infrastructure baselines. This suggests the change was part of an approved automated workflow.",
    "business_impact": "Low impact - this appears to be an authorized automated change by the drift management system. However, verify this was an expected action.",
    "recommended_action": "update_baseline",
    "confidence_score": 85
}
```

---

## Case 5: Auto Scaling Service

### Prompt Input

```
WHO MADE THE CHANGE:
Changed By: autoscaling.amazonaws.com (IAM User/Role)
Changed At: 2025-11-21T03:15:30+07:00
AWS Action: RunInstances
Source: CloudTrail event logs

CHANGE HISTORY:
============================================================
⚠️  DRIFT CAUSED BY: autoscaling.amazonaws.com (IAM User/Role)
⏰  TIME: 2025-11-21T03:15:30+07:00
============================================================

Recent Change Events:
  [2025-11-21T03:15:30+07:00] RunInstances
    👤 IAM User/Role: autoscaling.amazonaws.com
    🔑 Identity Type: AWSService
```

### Expected AI Output

```json
{
    "root_cause": "System-initiated change by AWS Auto Scaling service at 2025-11-21T03:15:30. This was an automated scaling action triggered by Auto Scaling policies, not a manual human change.",
    "explanation": "AWS Auto Scaling automatically launched this instance based on scaling policies and CloudWatch alarms. This is expected behavior for auto-scaled infrastructure and not a manual drift.",
    "business_impact": "No negative impact - this is expected automated behavior. However, the baseline may need to be updated to reflect the dynamic nature of auto-scaled resources.",
    "recommended_action": "ignore",
    "confidence_score": 90
}
```

---

## Key Differences from Hardcoded Approach

### ❌ Hardcoded (Bad)

```python
"root_cause": "Example: 'Manual change by IAM user quy via AWS Console'"
```

-   Uses specific example that may not match actual data
-   Confusing for AI
-   Not flexible

### ✅ Dynamic (Good)

```python
who_section = f"""WHO MADE THE CHANGE:
Changed By: {updated_by} (IAM User/Role)
Changed At: {updated_at}
AWS Action: {drift_event}"""
```

-   Uses actual data from drift detection
-   Clear and specific
-   Adapts to different scenarios
-   Provides context when data is missing
