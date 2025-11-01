# Pulumi E-commerce Infrastructure

This Pulumi program provisions a complete e-commerce infrastructure on AWS with Instana monitoring.

## Architecture Overview

- **Frontend**: EKS cluster with Kubernetes
- **Order Processing**: ECS Fargate cluster
- **Database**: Aurora MySQL cluster
- **Session Storage**: DynamoDB
- **Static Assets**: S3 bucket
- **Message Queue**: SQS
- **Event Streaming**: MSK (Kafka)
- **Monitoring**: Instana agents on EKS and ECS

## Prerequisites

1. **Python 3.7+**
2. **Pulumi CLI**: [Install](https://www.pulumi.com/docs/install/)
3. **AWS CLI**: [Install](https://aws.amazon.com/cli/)
4. **AWS Account** with appropriate permissions
5. **Instana Account** (for monitoring)

## Quick Start

### Windows (PowerShell)

```powershell
# Run the setup script
.\setup.ps1

# Configure AWS credentials
aws configure

# Login to Pulumi
pulumi login
# or for local state:
pulumi login --local

# Initialize stack
pulumi stack init dev

# Set secrets
pulumi config set --secret instana:agentKey YOUR_INSTANA_KEY
pulumi config set --secret db:password YOUR_DB_PASSWORD

# Preview deployment
pulumi preview

# Deploy
pulumi up
```

### Linux/macOS/WSL

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh

# Configure AWS credentials
aws configure

# Login to Pulumi
pulumi login
# or for local state:
pulumi login --local

# Initialize stack
pulumi stack init dev

# Set secrets
pulumi config set --secret instana:agentKey YOUR_INSTANA_KEY
pulumi config set --secret db:password YOUR_DB_PASSWORD

# Preview deployment
pulumi preview

# Deploy
pulumi up
```

## Configuration

The program requires the following configuration:

| Config Key | Description | Required | Default |
|------------|-------------|----------|---------|
| `aws:region` | AWS region | No | us-east-1 |
| `instana:agentKey` | Instana agent key | Yes | - |
| `instana:endpoint` | Instana endpoint URL | No | https://saas-us-east-1.instana.io |
| `db:password` | Aurora master password | Yes | - |

Set configuration values:

```bash
# Public config
pulumi config set aws:region us-east-1

# Secret config
pulumi config set --secret instana:agentKey YOUR_KEY
pulumi config set --secret db:password YOUR_PASSWORD
```

## Resources Created

### Networking
- VPC with public and private subnets across 2 AZs
- Internet Gateway
- NAT Gateways
- Route tables and associations

### Compute
- **EKS Cluster**: t3.medium instances (2-3 nodes)
- **ECS Fargate Cluster**: For order processing service
- IAM roles and policies

### Storage
- **Aurora MySQL**: db.r5.large instance
- **DynamoDB**: Session table (PAY_PER_REQUEST)
- **S3**: Private bucket for assets

### Messaging
- **SQS**: Order queue
- **MSK**: Kafka cluster (3 brokers, m5.large)

### Monitoring
- **Instana Agent**: DaemonSet on EKS
- **Instana Agent**: Sidecar in ECS tasks
- CloudWatch log groups

## Dry-Run Mode

If Pulumi SDK is not available, the program will create a dry-run plan at `/mnt/data/pulumi_plan.json` showing what resources would be created.

## Managing the Infrastructure

### View outputs
```bash
pulumi stack output
```

### Update infrastructure
```bash
pulumi up
```

### Destroy infrastructure
```bash
pulumi destroy
```

### View state
```bash
pulumi stack export
```

## Troubleshooting

### Pulumi not found
Install Pulumi:
```bash
# Windows (PowerShell with Chocolatey)
choco install pulumi

# macOS
brew install pulumi

# Linux
curl -fsSL https://get.pulumi.com | sh
```

### AWS credentials not configured
```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### Python dependencies fail
Ensure you're in the virtual environment:
```bash
# Activate venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Reinstall
pip install --upgrade pip
pip install -r requirements.txt
```

## Costs

This infrastructure will incur AWS costs. Estimated monthly costs:

- EKS: ~$75 (control plane) + EC2 instances
- ECS Fargate: Based on usage
- Aurora: ~$200-400 (db.r5.large)
- MSK: ~$300-400 (3 brokers)
- DynamoDB: Pay per request
- Other services: Varies by usage

**Important**: Run `pulumi destroy` when done to avoid charges!

## Security Notes

- All secrets are stored encrypted in Pulumi state
- Aurora password is required to be set as a secret
- S3 bucket is private by default
- VPC uses private subnets for databases
- Security groups restrict access

## ROSA (OpenShift) Setup

For Red Hat OpenShift (ROSA):

1. Install ROSA CLI:
   ```bash
   rosa download rosa
   ```

2. Create ROSA cluster:
   ```bash
   rosa create cluster --cluster-name ecom-openshift --sts
   ```

3. Export kubeconfig:
   ```bash
   export KUBECONFIG=~/.kube/rosa-ecom-config
   ```

4. Apply Instana DaemonSet to ROSA using the same manifest

## License

MIT

## Support

For issues or questions:
- Pulumi: https://www.pulumi.com/docs/
- AWS: https://aws.amazon.com/documentation/
- Instana: https://www.instana.com/docs/
