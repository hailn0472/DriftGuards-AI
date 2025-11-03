# AWS Resource Inventory & Status Monitoring

## Overview

The CloudDrift-AI system now displays **current AWS resource status** before performing drift detection, giving you full visibility into your infrastructure.

## ✅ What's Working Now

### 1. Real-Time AWS Resource Inventory

When you run `python notebooks/test_detection_debug.py`, you now see:

```
============================================================
Current AWS Resources
============================================================

📦 EC2 Instances: Shows all instances with their state, type, and tags
🪣 S3 Buckets: Lists all S3 buckets
☸️ EKS Clusters: Shows Kubernetes clusters with status
🐳 ECS Clusters: Displays container clusters and running tasks
🗄️ RDS Instances: Lists database instances with engine and status
💫 RDS Clusters (Aurora): Shows Aurora clusters with member count
📊 DynamoDB Tables: Lists all DynamoDB tables
⚡ Lambda Functions: Shows all Lambda functions with runtime
📬 SQS Queues: Lists all SQS queues

✅ AWS Resource inventory complete
```

### 2. Then Runs Drift Detection

After showing current status, the script automatically:

- Runs Terraform commands
- Checks for configuration drift
- Compares actual state vs. Terraform state
- Reports any differences

## Your Current AWS Resources

Based on the latest scan:

- **S3 Buckets**: 1 bucket (`assets-bucket-0e84de4`)
- **VPC**: 1 VPC (`vpc-0f5d2e5a4fad1028d`)
- **Security Groups**: 1 group
- **Other Services**: No active resources detected

This suggests your Pulumi-created resources from `data-example/__main__.py` may not have been deployed yet, or were deployed in a different account/region.

## How to Use

### Quick Status Check

```bash
cd D:\GitHub\SelfStudy\CloudDrift-AI
python notebooks/test_detection_debug.py
```

This will:

1. ✅ Check prerequisites (Terraform, driftctl)
2. ✅ Display configuration
3. ✅ **Show all current AWS resources**
4. ✅ Run drift detection tests
5. ✅ Display results and summary

### Understanding the Output

#### Resource Status Indicators

- 🟢 = Active/Running/Available
- 🔴 = Stopped/Inactive
- 🟡 = Pending/Transitioning
- ⚪ = Unknown state

#### Example Output

```
📦 EC2 Instances:
  🟢 i-1234567890abcdef - WebServer (t3.medium) - running
  🔴 i-0987654321fedcba - Database (t3.large) - stopped
  Total: 2 instance(s)
```

## Checking Resources Created by Pulumi

Your Pulumi script (`data-example/__main__.py`) would create:

1. **VPC** with CIDR 10.0.0.0/16
2. **EKS Cluster** named "frontend-eks"
3. **ECS Cluster** named "order-ecs-cluster"
4. **Aurora Cluster** for MySQL
5. **DynamoDB Table** named "session-table"
6. **S3 Bucket** for assets
7. **SQS Queue** for orders
8. **MSK (Kafka)** cluster
9. **Lambda Functions** (if deployed)

### To Deploy Pulumi Resources

```bash
cd data-example
pulumi up
```

Once deployed, run the detection script again to see them:

```bash
cd ..
python notebooks/test_detection_debug.py
```

## Terraform State Tracking

The system uses Terraform data sources to discover resources:

- `terraform/main.tf` - Updated to query AWS for existing resources
- Local state backend - Stores resource information
- Drift detection - Compares Terraform state vs. actual AWS

### View Terraform Output

```bash
cd terraform
terraform output
```

This shows discovered resources without the full test output.

## File Structure

```
CloudDrift-AI/
├── notebooks/
│   ├── test_detection_debug.py    # Main test script with resource inventory
│   └── aws_inventory.py            # Standalone inventory (needs updates)
├── terraform/
│   ├── main.tf                     # Resource discovery configuration
│   └── terraform.tfstate           # Local state file
└── data-example/
    └── __main__.py                 # Pulumi infrastructure definition
```

## Next Steps

### 1. Deploy Pulumi Infrastructure

If you want to see resources in the inventory:

```bash
cd data-example

# Set required config
pulumi config set aws:region ap-southeast-1
pulumi config set instana:agentKey --secret "your-key"
pulumi config set db:password --secret "your-password"

# Deploy
pulumi up
```

### 2. Create Test Drift

To test drift detection with real drifts:

1. Deploy a resource via Terraform or Pulumi
2. Manually change it in AWS Console (e.g., add tags, change settings)
3. Run `python notebooks/test_detection_debug.py`
4. See the drift detected!

### 3. Monitor Regularly

Set up a cron job or scheduled task:

```bash
# Linux/Mac
0 */6 * * * cd /path/to/CloudDrift-AI && python notebooks/test_detection_debug.py > logs/drift_$(date +\%Y\%m\%d).log

# Windows Task Scheduler
# Action: python.exe
# Arguments: D:\GitHub\SelfStudy\CloudDrift-AI\notebooks\test_detection_debug.py
```

## Troubleshooting

### No Resources Showing Up?

1. **Check AWS Region**: Ensure `.env` has correct `AWS_REGION=ap-southeast-1`
2. **Check Credentials**: Verify AWS credentials are configured
3. **Check Account**: Confirm `AWS_ACCOUNT_ID=961639320333` is correct
4. **Deploy Resources**: Resources need to exist before they can be discovered

### Permissions Issues?

Ensure your AWS IAM user/role has these permissions:

- `ec2:Describe*`
- `s3:ListBuckets`
- `eks:ListClusters`, `eks:DescribeCluster`
- `ecs:ListClusters`, `ecs:DescribeClusters`
- `rds:Describe*`
- `dynamodb:ListTables`
- `lambda:ListFunctions`
- `sqs:ListQueues`

## Summary

✅ **Fixed**: You can now see all your AWS resources before drift detection runs  
✅ **Real-time**: Script queries live AWS state  
✅ **Comprehensive**: Shows EC2, S3, EKS, ECS, RDS, Aurora, DynamoDB, Lambda, SQS  
✅ **Status Indicators**: Color-coded status for quick visibility  
✅ **Integration Test**: Works with your real AWS environment  

The system is now fully operational for monitoring your AWS infrastructure! 🚀
