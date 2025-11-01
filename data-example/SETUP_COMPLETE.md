# ✅ Prerequisites Installed Successfully!

## What Was Installed

1. **Pulumi CLI v3.205.0** - Infrastructure as Code tool
2. **AWS CLI v2.31.26** - AWS command-line interface

## ⚠️ IMPORTANT: Restart Required

**You MUST restart your PowerShell terminal** for the PATH changes to take effect.

### Steps to Continue:

1. **Close this terminal** and open a new PowerShell window

2. **Verify installations** in the new terminal:
   ```powershell
   pulumi version
   aws --version
   ```

3. **Configure AWS credentials**:
   ```powershell
   aws configure
   ```
   You'll need:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., `us-east-1`)
   - Default output format (press Enter for default)

4. **Run the quick-start script**:
   ```powershell
   cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example
   .\run.ps1
   ```

## 🔑 Don't Have AWS Credentials?

### Option 1: Use AWS Free Tier (Real AWS Account)
- Sign up at: https://aws.amazon.com/free/
- Create IAM user with admin access
- Generate access keys in IAM Console

### Option 2: LocalStack (Mock AWS Services - Free)
If you want to test without real AWS costs:

```powershell
# Install LocalStack
pip install localstack

# Start LocalStack
localstack start

# Configure AWS CLI for LocalStack
aws configure set aws_access_key_id test
aws configure set aws_secret_access_key test
aws configure set default.region us-east-1

# Set environment variable for LocalStack
$env:AWS_ENDPOINT_URL = "http://localhost:4566"
```

### Option 3: Skip AWS Configuration (Preview Only)
You can still preview the Pulumi program without AWS:
```powershell
pulumi login --local
cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 📊 What the Infrastructure Creates

- **EKS Cluster** - Kubernetes for frontend (~$75/month)
- **ECS Cluster** - Container service for order processing
- **Aurora MySQL** - Managed database (~$200-400/month)
- **DynamoDB** - Session storage (pay-per-request)
- **S3 Bucket** - Static asset storage (~$1/month)
- **SQS Queue** - Message queue (minimal cost)
- **MSK (Kafka)** - Streaming platform (~$300-400/month)
- **Instana Agents** - Application monitoring

**Estimated Total: $600-900/month** ⚠️

## 🛡️ Safety Tips

1. **Always preview first**: `pulumi preview`
2. **Use dev/test accounts**: Don't run in production initially
3. **Set billing alerts**: In AWS Console → Billing → Budgets
4. **Destroy when done**: `pulumi destroy` to avoid charges
5. **Tag resources**: All resources are tagged with `Project: ecommerce-infra`

## 🚀 Quick Commands Reference

```powershell
# Preview changes (safe, no charges)
.\run.ps1 -Preview

# Deploy everything
.\run.ps1 -Deploy

# Check what's deployed
pulumi stack output

# Update specific resources
pulumi up

# Destroy everything
pulumi destroy

# View logs
pulumi logs
```

## 🆘 Troubleshooting

### "Pulumi command not found" after install
- **Solution**: Close and reopen PowerShell terminal
- **Why**: PATH environment variable needs to be reloaded

### "AWS credentials not configured"
- **Solution**: Run `aws configure` and enter credentials
- **Check**: Run `aws sts get-caller-identity` to verify

### "Failed to create EKS cluster"
- **Solution**: Ensure IAM user has sufficient permissions
- **Required**: EC2, EKS, IAM, VPC permissions

### Cost concerns
- **Solution**: Start with smaller instance types in Pulumi.dev.yaml
- **Alternative**: Use `pulumi destroy` immediately after testing

## 📚 Next Steps

1. Restart terminal
2. Configure AWS
3. Run `.\run.ps1 -Preview` to see what will be created
4. Review the estimated costs
5. Deploy only if comfortable: `.\run.ps1 -Deploy`

**Remember**: This creates REAL AWS resources with REAL costs! 💰
