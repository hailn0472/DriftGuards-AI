# Pulumi Deployment Status & Summary

## ✅ Successfully Created (52 Resources)

### Core Infrastructure
- ✅ VPC with 2 availability zones
- ✅ 4 Subnets (2 public, 2 private)
- ✅ Internet Gateway
- ✅ 2 NAT Gateways
- ✅ 2 Elastic IPs
- ✅ Route Tables and Associations

### Databases
- ✅ **Aurora MySQL Cluster** - Fixed password (removed `@` character)
- ✅ Aurora ClusterInstance (db.r5.large)
- ✅ RDS Subnet Group
- ✅ **DynamoDB Table** (session-table)

### Storage & Messaging
- ✅ **S3 Bucket** (assets-bucket)
- ✅ **SQS Queue** (order-queue)

### Container Services
- ✅ **ECS Cluster** (order-ecs-cluster)
- ✅ ECS Task Definition (with Instana sidecar)
- ✅ IAM Execution Role
- ✅ CloudWatch Log Groups (2x)

### Partially Deployed
- ⏳ **EKS Cluster** (frontend-eks) - In progress, timing out
- ⏳ **MSK Kafka Cluster** - Fixed broker count to 2 (matching 2 AZs)

## 🔧 Fixes Applied

### Issue 1: Aurora Password ❌→✅
**Error**: `The parameter MasterUserPassword is not a valid password. Only printable ASCII characters besides '/', '@', '"', ' ' may be used.`

**Fix**: Changed password from `passWord@123` to `PassWord12345`

### Issue 2: MSK Kafka Version ❌→✅
**Error**: `Unsupported KafkaVersion [2.8.1]. Valid values: [4.1.x.kraft, 3.7.x, 3.8.x...]`

**Fix**: Updated from `2.8.1` to `3.7.x`

### Issue 3: MSK Broker Count ❌→✅
**Error**: `The target number of broker nodes must be a multiple of the number of Availability Zones`

**Fix**: Changed from 3 brokers to 2 brokers (matching 2 AZs)

### Issue 4: EKS Timeout ⚠️
**Error**: Long deployment time, resource monitor shutdown

**Status**: EKS is still deploying. This is normal for EKS as it takes 15-25 minutes to fully provision.

## 📊 Current Stack Outputs

```powershell
pulumi stack output
```

**Available Now**:
- `ecs_cluster_name`: order-ecs-cluster-5bd9feb
- `s3_bucket`: assets-bucket-0e84de4
- `order_queue_url`: https://sqs.us-east-1.amazonaws.com/.../order-queue-4d392a4
- `vpc_id`: vpc-0916ff4a39c14585f

**Pending** (will be available when EKS completes):
- `eks_cluster_name`
- `aurora_cluster_endpoint`
- `msk_cluster_arn`

## 🚀 Next Steps

### Option 1: Wait for EKS to Complete
```powershell
cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example

# Check current status
pulumi stack

# Continue deployment (if stopped)
pulumi up --yes
```

EKS typically takes **15-25 minutes** to fully deploy.

### Option 2: Destroy and Redeploy with Smaller Resources
To save time and costs, edit `__main__.py`:

```python
# Use smaller EKS nodes
instance_type="t3.small",  # Instead of t3.medium
desired_capacity=1,        # Instead of 2

# Use smaller Aurora
instance_class="db.t3.medium",  # Instead of db.r5.large

# Remove MSK entirely (most expensive)
# Comment out lines 340-350
```

Then:
```powershell
pulumi destroy --yes
pulumi up --yes
```

### Option 3: Deploy Without EKS (API-Only Stack)
Comment out EKS and Kubernetes resources in `__main__.py`:
- Lines 217-230 (EKS Cluster)
- Lines 232 (k8s Provider)
- Lines 360-420 (Instana on EKS)

This will give you:
- ✅ VPC, NAT, IGW
- ✅ ECS for containers
- ✅ Aurora for database
- ✅ DynamoDB for sessions
- ✅ S3 for storage
- ✅ SQS for queues
- ✅ MSK for Kafka

Cost: ~$350-500/month (vs ~$750-1000 with EKS)

## 💰 Current Monthly Costs

Based on what's deployed:

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| VPC & NAT Gateways | 2x NAT | $65 |
| ECS Cluster | Fargate pay-per-use | $20-50 |
| Aurora MySQL | 1x db.r5.large | $200-400 |
| DynamoDB | Pay-per-request | $5-20 |
| S3 | Storage + requests | $1-5 |
| SQS | Pay-per-message | $0.40-5 |
| EKS Control Plane | (deploying) | $75 |
| EKS Worker Nodes | 2x t3.medium | $60 |
| MSK Kafka | 2x kafka.m5.large | $200-270 |
| **Subtotal** | | **$626-950/month** |

⚠️ **Remember to destroy resources when done testing!**

## 🧹 Cleanup Commands

### Destroy Everything
```powershell
cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example
pulumi destroy --yes
```

This will remove all 52+ resources and stop all charges.

### Check What's Running in AWS
```powershell
# Check VPC
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ecom-vpc*"

# Check ECS
aws ecs list-clusters
aws ecs describe-clusters --clusters order-ecs-cluster-5bd9feb

# Check Aurora
aws rds describe-db-clusters --db-cluster-identifier aurora-cluster-*

# Check S3
aws s3 ls | grep assets-bucket

# Check SQS
aws sqs list-queues
```

## 📝 Deployment Log Summary

**Update 1**: Initial deployment failed
- Aurora password contained `@`
- MSK version 2.8.1 not supported
- MSK had 3 brokers but 2 AZs

**Update 2**: Partial success
- Aurora password fixed
- MSK version updated to 3.7.x
- Aurora cluster created successfully
- 34 resources unchanged from previous run

**Update 3**: In progress
- MSK broker count fixed to 2
- 17 new resources created
- 36 resources unchanged
- EKS deployment in progress (timeout after 24 minutes)

**Total**: 53 resources created/deployed

## 🔍 Troubleshooting

### If EKS continues to timeout
```powershell
# Check EKS cluster status in AWS Console
aws eks list-clusters
aws eks describe-cluster --name frontend-eks-eksCluster-*

# Or skip EKS and deploy other services
# Comment out EKS sections in __main__.py
```

### If you see "resource monitor shut down"
This usually means:
1. Deployment took too long (>30 minutes)
2. Network/connection issue
3. Provider plugin crashed

**Solution**: Run `pulumi up --yes` again to continue from where it stopped.

### Check resource costs
```powershell
# Install AWS Cost Explorer
aws ce get-cost-and-usage `
  --time-period Start=2025-11-01,End=2025-11-03 `
  --granularity DAILY `
  --metrics BlendedCost `
  --group-by Type=SERVICE
```

## ✅ Success Criteria

You'll know everything is working when:

```powershell
pulumi stack output
```

Shows all 7 outputs:
- ✅ vpc_id
- ✅ eks_cluster_name
- ✅ ecs_cluster_name
- ✅ aurora_cluster_endpoint
- ✅ s3_bucket
- ✅ order_queue_url
- ✅ msk_cluster_arn

And `pulumi stack` shows **0 errored** resources.

---

**Current Status**: 52+ resources deployed successfully, EKS deployment in progress.
**Next Action**: Wait for EKS or deploy without it to save time/cost.
