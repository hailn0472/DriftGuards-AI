# 🐳 Docker Compose Guide - DriftGuards Pulumi Examples

## Overview

This Docker Compose setup allows you to easily deploy and manage both EC2 and Lambda infrastructure using Pulumi.

## 📋 Prerequisites

- Docker & Docker Compose installed
- AWS credentials configured

## 🚀 Quick Start

### 1. Setup Environment Variables

Create `.env` file from example:

```bash
cd examples
cp .env.example .env
```

Edit `.env` and add your AWS credentials:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-southeast-1
```

### 2. Build Images

```bash
# Build all images
docker compose build

# Or build specific service
docker compose build pulumi-ec2
docker compose build pulumi-lambda
```

### 3. Run Services

#### Deploy Lambda Function

```bash
# Auto-deploy with plugin
docker compose run --rm pulumi-lambda

# Or interactive mode
docker compose run --rm pulumi-lambda /bin/bash
```

#### Deploy EC2 Instance

```bash
# Auto-deploy and SSH into instance
docker compose run --rm pulumi-ec2

# Or interactive mode
docker compose run --rm pulumi-ec2 /bin/bash
```

#### Deploy Both Services

```bash
# Start both services
docker compose --profile all up
```

---

## 📦 Service Profiles

Services are organized by profiles:

- **`ec2`** - EC2 deployment only
- **`lambda`** - Lambda deployment only  
- **`all`** - Both services

### Using Profiles

```bash
# Run EC2 profile
docker compose --profile ec2 run pulumi-ec2

# Run Lambda profile
docker compose --profile lambda run pulumi-lambda

# Run all services
docker compose --profile all up
```

---

## 🎯 Common Commands

### Build Services

```bash
# Build all
docker compose build

# Build specific service
docker compose build pulumi-lambda
docker compose build pulumi-ec2

# Force rebuild (no cache)
docker compose build --no-cache
```

### Run Services

```bash
# Run and auto-remove container
docker compose run --rm pulumi-lambda

# Run with interactive shell
docker compose run --rm pulumi-lambda /bin/bash

# Run with custom command
docker compose run --rm pulumi-lambda pulumi-lambda-down
```

### View Logs

```bash
# Follow logs
docker compose logs -f pulumi-lambda
docker compose logs -f pulumi-ec2

# View last N lines
docker compose logs --tail=50 pulumi-lambda
```

### Cleanup

```bash
# Stop all services
docker compose down

# Remove volumes
docker compose down -v

# Remove images
docker compose down --rmi all
```

---

## 📊 Service Details

### EC2 Service (`pulumi-ec2`)

**Default Command**: `pulumi-ec2 --yes`

**What it does**:
1. Deploys EC2 instance + VPC + Security Groups
2. Auto-starts instance if stopped
3. SSHs into the instance
4. Saves SSH key to `.ssh/my-ec2-key.pem`

**Outputs**:
- Instance ID
- Public IP
- SSH command
- VPC ID

**Manual Commands**:
```bash
# Inside container
pulumi-ec2              # Deploy and SSH
pulumi-ec2-down         # Destroy infrastructure
pulumi stack output     # View outputs
```

### Lambda Service (`pulumi-lambda`)

**Default Command**: `pulumi-lambda --yes`

**What it does**:
1. Deploys Lambda function + API Gateway + CloudWatch
2. Tests Function URL automatically
3. Shows outputs and test commands

**Outputs**:
- Function URL (public endpoint)
- API Gateway URL
- CloudWatch Log Group
- Function ARN

**Manual Commands**:
```bash
# Inside container
pulumi-lambda           # Deploy and test
pulumi-lambda-down      # Destroy infrastructure
pulumi stack output     # View outputs

# Test Lambda
curl "$(pulumi stack output lambda_function_url)"

# View logs
aws logs tail "$(pulumi stack output log_group_name)" --follow
```

---

## 🔧 Advanced Usage

### Use Custom AWS Region

```bash
# Override in .env
AWS_REGION=us-east-1

# Or pass inline
AWS_REGION=us-west-2 docker compose run --rm pulumi-lambda
```

### Mount Local Code for Development

```bash
# Edit docker-compose.yml to add volumes
services:
  pulumi-lambda:
    volumes:
      - ./pulumi-lambda-deployment:/pulumi-project
```

### Run Multiple Instances

```bash
# Copy and modify service
docker compose run --rm --name lambda-dev pulumi-lambda
docker compose run --rm --name lambda-prod pulumi-lambda
```

### Override Entrypoint

```bash
# Run custom script
docker compose run --rm --entrypoint /bin/bash pulumi-lambda

# Run Pulumi commands directly
docker compose run --rm --entrypoint pulumi pulumi-lambda stack output
```

---

## 🧪 Testing Workflow

### Test Lambda Deployment

```bash
# 1. Deploy Lambda
docker compose run --rm pulumi-lambda

# 2. Get Function URL (from output)
FUNCTION_URL="https://xxx.lambda-url.ap-southeast-1.on.aws/"

# 3. Test endpoint
curl "$FUNCTION_URL"

# 4. Destroy when done
docker compose run --rm pulumi-lambda pulumi-lambda-down
```

### Test EC2 Deployment

```bash
# 1. Deploy EC2 and SSH
docker compose run --rm pulumi-ec2

# 2. Inside EC2 instance
whoami
uname -a
exit

# 3. Destroy when done
docker compose run --rm pulumi-ec2 pulumi-ec2-down
```

---

## 📁 File Structure

```
examples/
├── docker-compose.yml           # Main compose file
├── .env                         # Your credentials (gitignored)
├── .env.example                 # Template
├── DOCKER_COMPOSE_GUIDE.md      # This file
├── pulumi-ec2-deployment/
│   ├── Dockerfile
│   ├── __main__.py
│   └── pulumi-plugins/
└── pulumi-lambda-deployment/
    ├── Dockerfile
    ├── __main__.py
    ├── lambda_code/
    └── pulumi-plugins/
```

---

## 🔒 Security Best Practices

### 1. Never Commit Credentials

```bash
# .env is in .gitignore
echo ".env" >> .gitignore
```

### 2. Use IAM Roles (Recommended)

Instead of access keys, use IAM roles when running on AWS (ECS, EC2, etc.)

### 3. Rotate Keys Regularly

```bash
# Generate new keys monthly
aws iam create-access-key --user-name your-username
```

### 4. Limit Permissions

Use least-privilege IAM policies:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:*",
      "lambda:*",
      "iam:PassRole"
    ],
    "Resource": "*"
  }]
}
```

---

## 🐛 Troubleshooting

### Issue: "no configuration file provided"

**Solution**: Run from `examples/` directory
```bash
cd examples
docker compose run --rm pulumi-lambda
```

### Issue: "AWS credentials not found"

**Solution**: Check `.env` file exists and has correct values
```bash
cat .env
docker compose config  # Verify env vars
```

### Issue: "port already in use"

**Solution**: Change port mapping or stop conflicting container
```bash
docker ps
docker stop <container_id>
```

### Issue: "permission denied"

**Solution**: Ensure Docker daemon is running
```bash
# Windows
Get-Service docker
Start-Service docker

# Linux
sudo systemctl start docker
```

---

## 💡 Tips

1. **Use profiles** to run only what you need
2. **Always use `.env` file** instead of inline credentials
3. **Clean up resources** after testing to avoid AWS charges
4. **Check logs** if deployment fails: `docker compose logs`
5. **Rebuild after code changes**: `docker compose build --no-cache`

---

## 📚 Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Pulumi AWS Guide](https://www.pulumi.com/docs/clouds/aws/)
- [DriftGuards Documentation](../docs/)

---

Built for DriftGuards AI 🛡️ - Infrastructure Drift Detection & Prevention
