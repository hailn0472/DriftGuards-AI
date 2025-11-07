# 🛑 Cleanup Guide - Stop/Destroy Pulumi Infrastructure

This guide explains how to safely stop or destroy your Pulumi-deployed AWS infrastructure.

## 📊 Quick Reference

| Action | Command | Cost Savings | Reversible | Data Loss |
|--------|---------|--------------|------------|-----------|
| **Preview** | `.\cleanup.ps1 -Preview` | 0% | ✅ Yes | ❌ No |
| **Stop Compute** | `.\cleanup.ps1 -StopOnly` | 70-80% | ✅ Yes | ❌ No |
| **Destroy All** | `.\cleanup.ps1 -DestroyAll` | 100% | ❌ No | ⚠️ YES |

## 🎯 Use Cases

### 1. Preview Changes (Safe, No Impact)
```powershell
.\cleanup.ps1 -Preview
```
- Shows what would be destroyed
- No actual changes made
- Use this first to understand impact

### 2. Stop Compute Resources (Save Money, Keep Data)
```powershell
.\cleanup.ps1 -StopOnly
```

**What it does:**
- ✅ Stops ECS services (scales to 0 tasks)
- ✅ Scales down EKS nodes (to 0)
- ✅ Stops Aurora cluster
- ✅ Keeps: VPC, S3, DynamoDB, SQS, MSK

**Cost Impact:**
- **Before**: ~$600-900/month
- **After**: ~$120-180/month
- **Savings**: 70-80%

**When to use:**
- Overnight/weekend shutdowns
- Development environments
- Testing complete, but keeping infrastructure

**To restart:**
```powershell
.\run.ps1 -Deploy
```

### 3. Destroy Everything (Complete Cleanup)
```powershell
.\cleanup.ps1 -DestroyAll
```

**What it does:**
- 💥 Deletes EKS cluster
- 💥 Deletes ECS cluster
- 💥 Deletes Aurora database (⚠️ DATA LOSS!)
- 💥 Deletes DynamoDB tables (⚠️ DATA LOSS!)
- 💥 Deletes S3 buckets (⚠️ DATA LOSS!)
- 💥 Deletes MSK cluster
- 💥 Deletes VPC and networking
- 💥 Removes all monitoring/logs

**Cost Impact:**
- **After**: $0/month
- **Savings**: 100%

**⚠️ PERMANENT - Cannot be undone!**

**When to use:**
- Project complete/cancelled
- Moving to different infrastructure
- Cost reduction required
- Environment no longer needed

## 🚀 Quick Start

### Option 1: PowerShell Script (Recommended)

```powershell
# Navigate to project directory
cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example

# Preview what would be destroyed
.\cleanup.ps1 -Preview

# Stop compute only (saves ~75% costs)
.\cleanup.ps1 -StopOnly

# Destroy everything (with confirmation)
.\cleanup.ps1 -DestroyAll

# Destroy everything (no confirmation - BE CAREFUL!)
.\cleanup.ps1 -DestroyAll -Force
```

### Option 2: Python Script

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Preview
python cleanup_pulumi.py --preview

# Stop compute only
python cleanup_pulumi.py --stop-only

# Destroy everything
python cleanup_pulumi.py --destroy

# Destroy without confirmation
python cleanup_pulumi.py --destroy --force
```

### Option 3: Direct Pulumi Commands

```powershell
# Preview destruction
pulumi preview --diff

# Destroy with confirmation
pulumi destroy

# Destroy without confirmation
pulumi destroy --yes --skip-preview

# Remove stack after destroy
pulumi stack rm dev --yes
```

## 📋 Detailed Resource Breakdown

### Resources Stopped by `-StopOnly`

| Resource | Action | Monthly Cost Before | After | Savings |
|----------|--------|--------------------:|------:|--------:|
| EKS Nodes | Scale to 0 | $75 | $0 | $75 |
| ECS Tasks | Stop all | $30-50 | $0 | $40 |
| Aurora | Stop cluster | $200-400 | $0 | $300 |
| **Subtotal** | | **$305-525** | **$0** | **$415** |

### Resources Kept by `-StopOnly`

| Resource | Monthly Cost | Why Keep |
|----------|-------------:|----------|
| VPC | $0 | Free tier |
| S3 (minimal data) | $1-5 | Data storage |
| DynamoDB (on-demand) | $5-10 | Session data |
| SQS | $0-1 | Minimal cost |
| MSK | $300-400 | Streaming data |
| CloudWatch Logs | $5-10 | Debugging |
| **Total** | **$311-426** | |

### Resources Destroyed by `-DestroyAll`

| Resource | Data Loss Risk | Recovery |
|----------|:--------------:|----------|
| Aurora Database | ⚠️ HIGH | Manual restore from backup |
| DynamoDB Tables | ⚠️ MEDIUM | No automatic backup |
| S3 Buckets | ⚠️ HIGH | Lost forever unless versioned |
| EKS Workloads | ⚠️ LOW | Redeploy from code |
| MSK Topics | ⚠️ HIGH | Lost forever |
| CloudWatch Logs | ⚠️ MEDIUM | Lost after retention |

## 🛡️ Safety Checklist

Before destroying infrastructure:

- [ ] **Backup databases** - Export Aurora to S3
- [ ] **Download S3 data** - Copy important files locally
- [ ] **Export DynamoDB** - Use AWS Data Pipeline
- [ ] **Save configurations** - Document custom settings
- [ ] **Notify team** - Inform stakeholders
- [ ] **Check dependencies** - Ensure no other systems depend on this
- [ ] **Verify stack** - Run `pulumi stack output` to confirm
- [ ] **Set billing alert** - Catch any lingering resources

### Backup Commands

```powershell
# Export Aurora to S3
aws rds create-db-cluster-snapshot --db-cluster-identifier aurora-cluster --db-cluster-snapshot-identifier backup-$(Get-Date -Format "yyyy-MM-dd")

# Sync S3 bucket locally
aws s3 sync s3://your-assets-bucket ./backups/s3/

# Export DynamoDB table
aws dynamodb create-backup --table-name session-table --backup-name session-backup-$(Get-Date -Format "yyyy-MM-dd")
```

## 🔄 Recovery Scenarios

### Scenario 1: Restarting After `-StopOnly`

```powershell
# Resources still exist, just need to scale up
.\run.ps1 -Deploy

# Or manually:
pulumi up
```

**Time to restart**: 10-15 minutes

### Scenario 2: Rebuilding After `-DestroyAll`

```powershell
# Complete fresh deployment
.\run.ps1 -Deploy

# Restore data:
# 1. Restore Aurora from snapshot
# 2. Upload files to new S3 bucket
# 3. Import DynamoDB backup
```

**Time to rebuild**: 30-45 minutes (plus data restoration)

## 💰 Cost Comparison

### Development Environment (Daily Shutdown)

**Pattern**: Run 8hrs/day, 5 days/week

| Approach | Monthly Cost | Annual Cost | Savings |
|----------|-------------:|------------:|--------:|
| Always On | $750 | $9,000 | - |
| Stop Overnight | $250 | $3,000 | $6,000 |
| Weekend Destroy | $400 | $4,800 | $4,200 |

### Testing Environment (One-time Use)

| Approach | Cost | Time |
|----------|-----:|-----:|
| Deploy → Test → Destroy | $5-10 | 2-4 hours |
| Deploy → Stop → Restart → Destroy | $3-5 | 1 week |

## 🆘 Troubleshooting

### Error: "Stack not found"
```powershell
# Check current directory
pwd  # Should be in data-example/

# List available stacks
pulumi stack ls

# Select correct stack
pulumi stack select dev
```

### Error: "AWS credentials not configured"
```powershell
# Configure AWS
aws configure

# Test credentials
aws sts get-caller-identity
```

### Error: "Resource in use" during destroy
```powershell
# Some resources may have dependencies
# Stop compute first:
.\cleanup.ps1 -StopOnly

# Wait 5 minutes, then destroy:
.\cleanup.ps1 -DestroyAll
```

### Error: "Cannot stop Aurora cluster"
```powershell
# Cluster might have pending modifications
aws rds describe-db-clusters --db-cluster-identifier aurora-cluster

# Wait for modifications to complete, then retry
```

### Stuck Resources

If resources won't delete:

```powershell
# Force delete (use with caution)
pulumi destroy --target urn:pulumi:dev::ecommerce-infra::aws:eks/cluster:Cluster::frontend-eks --yes

# Or manually delete in AWS Console, then:
pulumi refresh
pulumi up --target <stuck-resource> --yes
```

## 📞 Support & Resources

- **Pulumi Docs**: https://www.pulumi.com/docs/
- **AWS Cost Explorer**: https://console.aws.amazon.com/cost-management/
- **Billing Alerts**: https://console.aws.amazon.com/billing/

## ⚡ Advanced Usage

### Selective Resource Destruction

```powershell
# Destroy only EKS cluster
pulumi destroy --target urn:pulumi:dev::ecommerce-infra::eks:index:Cluster::frontend-eks

# Destroy all except database
pulumi destroy --exclude urn:pulumi:dev::ecommerce-infra::aws:rds/cluster:Cluster::aurora-cluster
```

### Automated Cleanup (Scheduled)

```powershell
# Create scheduled task (Windows)
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File d:\GitHub\SelfStudy\CloudDrift-AI\data-example\cleanup.ps1 -StopOnly -Force"
$trigger = New-ScheduledTaskTrigger -Daily -At 6PM
Register-ScheduledTask -TaskName "StopPulumiInfra" -Action $action -Trigger $trigger
```

### Cost Monitoring

```powershell
# Check current month costs
aws ce get-cost-and-usage --time-period Start=2025-11-01,End=2025-11-30 --granularity MONTHLY --metrics BlendedCost

# Set billing alert (one-time setup)
# See: AWS Console → Billing → Budgets
```

## 🎓 Best Practices

1. **Always preview first**: `.\cleanup.ps1 -Preview`
2. **Use `-StopOnly` for dev**: Save costs without losing infrastructure
3. **Backup before destroy**: Critical for production data
4. **Tag resources**: Easier to identify and manage
5. **Document custom configs**: Speeds up rebuilding
6. **Set billing alerts**: $50 threshold recommended
7. **Use separate stacks**: dev, staging, prod
8. **Regular audits**: Weekly cost reviews

---

**Remember**: `-StopOnly` is reversible, `-DestroyAll` is permanent! ⚠️
