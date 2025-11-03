# Pulumi → Terraform Resource Verification Guide

## Overview

This guide explains how to verify that resources created by **Pulumi** can be discovered and tracked by **Terraform** using data sources.

## Quick Answer: ✅ YES, Terraform CAN discover Pulumi resources!

**Why?** Because Terraform data sources query the **actual AWS API**, not Pulumi's state. Any resource that exists in AWS—regardless of how it was created (Pulumi, Terraform, CloudFormation, CDK, Console)—can be discovered by Terraform data sources.

## 🚀 Quick Start

### Option 1: Run the Verification Script

```bash
python notebooks/verify_pulumi_terraform.py
```

This script will:
1. ✅ Check if Pulumi stack is deployed
2. ✅ Run Terraform to discover resources
3. ✅ Query AWS directly via boto3
4. ✅ Compare all three sources
5. ✅ Show what's detected and what's missing

### Option 2: Manual Verification

#### Step 1: Deploy Pulumi Resources

```bash
cd data-example

# Configure Pulumi
pulumi config set aws:region ap-southeast-1
pulumi config set instana:agentKey --secret "your-instana-key"
pulumi config set db:password --secret "your-db-password"

# Deploy
pulumi up
```

#### Step 2: Run Terraform Discovery

```bash
cd ../terraform

# Initialize Terraform
terraform init

# Refresh state (discover resources)
terraform refresh

# View discovered resources
terraform output
```

#### Step 3: Compare Results

```bash
# View Pulumi outputs
cd ../data-example
pulumi stack output

# View Terraform outputs
cd ../terraform
terraform output

# Run AWS inventory
cd ..
python notebooks/aws_inventory.py
```

## 📊 What Resources Can Terraform Discover?

### ✅ Fully Supported (Terraform has data sources)

| Resource Type | Terraform Data Source | Pulumi Creates |
|---------------|----------------------|----------------|
| VPCs | `data.aws_vpcs.all` | ✅ `ecom-vpc` |
| EKS Clusters | `data.aws_eks_clusters.all` | ✅ `frontend-eks` |
| EC2 Instances | `data.aws_instances.all` | ❌ (No EC2 in Pulumi script) |
| RDS Instances | `data.aws_db_instances.all` | ✅ `aurora-instance-1` |
| RDS Clusters | `data.aws_rds_clusters.all` | ✅ `aurora-cluster` |
| Security Groups | `data.aws_security_groups.all` | ✅ `msk-sg` |

### ⚠️ Limited Support (No "list all" data source)

| Resource Type | Why Limited | Workaround |
|---------------|-------------|------------|
| ECS Clusters | No `data.aws_ecs_clusters` | Use AWS SDK / boto3 |
| S3 Buckets | No `data.aws_s3_buckets` | Use AWS SDK / boto3 |
| DynamoDB Tables | No `data.aws_dynamodb_tables` | Use AWS SDK / boto3 |
| SQS Queues | No `data.aws_sqs_queues` | Use AWS SDK / boto3 |
| Lambda Functions | No `data.aws_lambda_functions` | Use AWS SDK / boto3 |
| MSK Clusters | Limited discovery | Query by name/ARN |

**Solution:** Use `aws_inventory.py` which queries AWS directly via boto3.

## 🔍 Understanding the Detection Methods

### Method 1: Terraform Data Sources

```hcl
# terraform/main.tf
data "aws_eks_clusters" "all" {}

data "aws_eks_cluster" "details" {
  for_each = toset(data.aws_eks_clusters.all.names)
  name     = each.value
}

output "eks_clusters" {
  value = data.aws_eks_clusters.all.names
}
```

**Pros:**
- ✅ Native Terraform integration
- ✅ Can be used for drift detection
- ✅ Works with any IaC tool (Pulumi, CDK, etc.)

**Cons:**
- ❌ Limited to available data sources
- ❌ Can't list all S3 buckets, DynamoDB tables, etc.
- ❌ Requires Terraform CLI

### Method 2: AWS SDK / boto3

```python
# notebooks/aws_inventory.py
eks = await aws_client.eks_client.list_clusters()
eks_clusters = eks.get('clusters', [])
```

**Pros:**
- ✅ Complete coverage of ALL AWS services
- ✅ Can list everything
- ✅ Direct API access

**Cons:**
- ❌ Not integrated with Terraform state
- ❌ Requires AWS credentials
- ❌ Need to write custom code

### Method 3: Hybrid Approach (RECOMMENDED)

Use **both** methods:
1. Terraform for resources with data sources
2. boto3 for complete inventory
3. Compare results for validation

This is what `verify_pulumi_terraform.py` does!

## 📋 Expected Resources from Pulumi

Based on `data-example/__main__.py`, Pulumi creates:

### Networking
- ✅ **VPC** (`ecom-vpc`) - CIDR 10.0.0.0/16
- ✅ **Security Group** (`msk-sg`) - For MSK cluster

### Compute
- ✅ **EKS Cluster** (`frontend-eks`) - t3.medium nodes
- ✅ **ECS Cluster** (`order-ecs-cluster`) - Fargate
- ✅ **ECS Task Definition** (`order-task`) - With Instana sidecar

### Storage
- ✅ **S3 Bucket** (`assets-bucket-*`) - Random suffix
- ✅ **DynamoDB Table** (`session-table`) - PAY_PER_REQUEST

### Database
- ✅ **Aurora Cluster** (`aurora-cluster`) - MySQL
- ✅ **Aurora Instance** (`aurora-instance-1`) - db.r5.large

### Messaging
- ✅ **SQS Queue** (`order-queue`) - Order processing
- ✅ **MSK Cluster** (`ecom-msk`) - Kafka 3.7.x

### Monitoring
- ✅ **CloudWatch Log Groups** - `ecs-log-group`, `instana-log-group`
- ✅ **Kubernetes DaemonSet** - Instana agent on EKS

### IAM
- ✅ **IAM Role** (`ecsTaskExecutionRole`) - For ECS tasks

## 🎯 Verification Results

### Example Output

```
================================================================================
  PULUMI → TERRAFORM VERIFICATION
================================================================================

  Account: 961639320333
  Region: ap-southeast-1
  Timestamp: 2025-11-02 10:30:00

--------------------------------------------------------------------------------
  1. Checking Pulumi Stack Status
--------------------------------------------------------------------------------
  ✅ Pulumi CLI found
  ✅ Pulumi stack is deployed

  Stack Outputs:
    • vpc_id: vpc-0abc123def456
    • eks_cluster_name: frontend-eks-a1b2c3d
    • ecs_cluster_name: order-ecs-cluster-e4f5g6h
    • aurora_cluster_endpoint: aurora-cluster.cluster-xyz.ap-southeast-1.rds.amazonaws.com

--------------------------------------------------------------------------------
  2. Running Terraform Discovery
--------------------------------------------------------------------------------
  ✅ Terraform CLI found
  ✅ Terraform initialized
  🔄 Refreshing Terraform state...

  📊 Resources discovered by Terraform:
    • vpc_ids: 1
    • eks_clusters: 1
    • rds_clusters: 1
    • rds_instances: 1
    • security_groups: 5

--------------------------------------------------------------------------------
  3. Querying AWS Directly (boto3)
--------------------------------------------------------------------------------
  • VPCs: 1
  • EKS Clusters: 1
  • ECS Clusters: 1
  • RDS Clusters: 1
  • RDS Instances: 1
  • DynamoDB Tables: 1
  • S3 Buckets: 3
  • SQS Queues: 1

--------------------------------------------------------------------------------
  4. Comparison Analysis
--------------------------------------------------------------------------------

  📊 Resource Detection Comparison:

  Resource Type             Expected     Terraform    AWS Direct   Status
  ------------------------------------------------------------------------------
  vpc                       1            1            1            ✅ Match
  eks_cluster               1            1            1            ✅ Match
  ecs_cluster               1            0            1            ⚠️  TF Miss
  rds_cluster               1            1            1            ✅ Match
  rds_instance              1            1            1            ✅ Match
  dynamodb_table            1            0            1            ⚠️  TF Miss
  s3_bucket                 1            0            3            ⚠️  TF Miss
  sqs_queue                 1            0            1            ⚠️  TF Miss

--------------------------------------------------------------------------------
  5. Recommendations
--------------------------------------------------------------------------------

  ⚠️  PARTIAL DETECTION

  Some resources may not be detected because:
     • Terraform data sources have limitations (e.g., no 'list all S3 buckets')
     • Resources might be in different regions
     • Some resources need specific ARNs/names to query

  💡 SOLUTIONS:
     1. Use boto3/AWS SDK for complete inventory (aws_inventory.py)
     2. Add more data sources to terraform/main.tf
     3. Use tags to filter Pulumi-created resources

  📚 Resources that Terraform CAN'T list directly:
     • All S3 buckets (no data source)
     • All DynamoDB tables (no data source)
     • All SQS queues (no data source)
     • All Lambda functions (no data source)

  ✅ Use the AWS inventory script for complete coverage:
     python notebooks/aws_inventory.py
```

## 💡 Key Insights

### 1. Terraform Data Sources Are Provider-Limited

Not all AWS services have Terraform data sources that can "list all" resources. This is a **Terraform/Provider limitation**, not a Pulumi issue.

### 2. AWS API Is the Source of Truth

Both Pulumi and Terraform ultimately create resources via the **AWS API**. Once a resource exists in AWS:
- ✅ Terraform data sources can find it (if data source exists)
- ✅ boto3/AWS SDK can find it (always)
- ✅ AWS Console can see it (always)
- ✅ AWS CLI can list it (always)

### 3. Tags Are Your Friend

To identify Pulumi-created resources, add consistent tags:

```python
# In Pulumi __main__.py
pulumi.Config().set_all({
    "aws:defaultTags": {
        "tags": {
            "ManagedBy": "Pulumi",
            "Project": "CloudDrift-AI",
            "Environment": "production"
        }
    }
})
```

Then filter in Terraform:

```hcl
data "aws_instances" "pulumi_managed" {
  filter {
    name   = "tag:ManagedBy"
    values = ["Pulumi"]
  }
}
```

## 🔧 Improving Terraform Discovery

### Add More Data Sources

Update `terraform/main.tf` to query specific resources:

```hcl
# Query specific S3 bucket by name
data "aws_s3_bucket" "assets" {
  bucket = "assets-bucket-0e84de4"  # From Pulumi output
}

# Query specific DynamoDB table
data "aws_dynamodb_table" "session" {
  name = "session-table"  # From Pulumi output
}

# Query specific SQS queue
data "aws_sqs_queue" "order" {
  name = "order-queue"  # From Pulumi output
}
```

### Use Terraform Import

Import Pulumi-created resources into Terraform state:

```bash
# Import S3 bucket
terraform import aws_s3_bucket.assets assets-bucket-0e84de4

# Import DynamoDB table
terraform import aws_dynamodb_table.session session-table
```

**Note:** This creates Terraform state for Pulumi resources, which may cause management conflicts. Only do this if you're migrating from Pulumi to Terraform.

## 🎓 Best Practices

### 1. Use Multiple Verification Methods

✅ **DO:** Combine Terraform data sources + AWS SDK
```bash
python notebooks/verify_pulumi_terraform.py
```

### 2. Tag All Resources

✅ **DO:** Add consistent tags to all infrastructure
```python
# Pulumi
pulumi.Config().set("aws:defaultTags", {...})
```

### 3. Document Expected Resources

✅ **DO:** Maintain a resource inventory document
- What Pulumi creates
- What Terraform should discover
- What needs boto3 for discovery

### 4. Automate Verification

✅ **DO:** Run verification in CI/CD
```yaml
# .github/workflows/verify.yml
- name: Verify Resource Discovery
  run: python notebooks/verify_pulumi_terraform.py
```

## 📚 Additional Resources

### Official Documentation

- [Terraform AWS Provider Data Sources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources)
- [Pulumi AWS Provider](https://www.pulumi.com/registry/packages/aws/)
- [AWS boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### Project Scripts

- `notebooks/verify_pulumi_terraform.py` - Full verification (this guide)
- `notebooks/aws_inventory.py` - Complete AWS resource inventory
- `notebooks/test_detection_debug.py` - Drift detection with inventory
- `terraform/main.tf` - Terraform data sources configuration

## ❓ FAQ

### Q: Why can't Terraform list all S3 buckets?

**A:** AWS provider maintainers decided not to add a `data.aws_s3_buckets` data source, likely because:
- S3 is global (complicated region handling)
- Large accounts may have thousands of buckets
- Security concerns (listing all buckets could expose sensitive info)

**Workaround:** Use `aws s3api list-buckets` or boto3.

### Q: Will Terraform conflict with Pulumi?

**A:** No, as long as you:
- ✅ Use Terraform data sources (read-only) - NO CONFLICT
- ❌ Don't import Pulumi resources into Terraform state
- ❌ Don't use Terraform to manage Pulumi-created resources

### Q: Can I use Terraform for drift detection on Pulumi resources?

**A:** Partially. Terraform can:
- ✅ Detect if resources exist or were deleted
- ✅ Monitor resource attributes (via data sources)
- ❌ Can't detect configuration drift (no Terraform-managed state)

For full drift detection, use `pulumi refresh` or tools like driftctl.

### Q: Should I migrate from Pulumi to Terraform?

**A:** Only if you have a specific reason:
- ✅ Keep Pulumi if you prefer Python/TypeScript/Go
- ✅ Keep Pulumi if you use advanced programming features
- ✅ Migrate to Terraform if team prefers HCL
- ✅ Migrate to Terraform if you need HashiCorp ecosystem (Vault, Consul)

**Both tools are excellent!** Choose based on team preference, not technical limitations.

## 🚀 Next Steps

1. **Run the verification script:**
   ```bash
   python notebooks/verify_pulumi_terraform.py
   ```

2. **Deploy missing resources** (if any):
   ```bash
   cd data-example
   pulumi up
   ```

3. **Check drift detection:**
   ```bash
   python notebooks/test_detection_debug.py
   ```

4. **Set up monitoring:**
   - Schedule regular resource inventory
   - Add tags to all resources
   - Document expected infrastructure

---

**✅ Result:** You can confidently use Terraform data sources to discover and monitor Pulumi-created resources, with boto3 as a complete fallback for services without Terraform data sources.

