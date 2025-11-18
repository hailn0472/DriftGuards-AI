# 🐳 Docker Compose Guide - DriftGuards Pulumi Examples

## Overview

This Docker Compose setup allows you to easily deploy and manage AWS infrastructure using Pulumi. It includes services for EC2, Lambda, S3, EKS, ECS, RDS (instances and clusters), DynamoDB, and SQS.

## 📋 Prerequisites

-   Docker & Docker Compose installed
-   AWS credentials configured

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

### Build Services

```bash
# Build all (uses shared requirements.txt)
docker compose --profile all build

# Build specific service
docker compose build pulumi-s3
docker compose build pulumi-eks
docker compose build pulumi-ecs
docker compose build pulumi-lambda
docker compose build pulumi-ec2
docker compose build pulumi-rds-instances
docker compose build pulumi-rds-clusters
docker compose build pulumi-dynamodb
docker compose build pulumi-sqs

# Force rebuild (no cache)
docker compose build --no-cache
```

### 3. Deploy Infrastructure

Each service includes custom plugin scripts for easy deployment and destruction:

```bash
# Deploy infrastructure (auto-approve)
docker compose run --rm pulumi-s3
docker compose run --rm pulumi-eks
docker compose run --rm pulumi-ecs
docker compose run --rm pulumi-lambda
docker compose run --rm pulumi-ec2
docker compose run --rm pulumi-rds-instances
docker compose run --rm pulumi-rds-clusters
docker compose run --rm pulumi-dynamodb
docker compose run --rm pulumi-sqs

# Deploy with manual approval
docker compose run --rm pulumi-s3 pulumi-s3
docker compose run --rm pulumi-eks pulumi-eks
docker compose run --rm pulumi-ecs pulumi-ecs
docker compose run --rm pulumi-lambda pulumi-lambda
docker compose run --rm pulumi-ec2 pulumi-ec2
docker compose run --rm pulumi-rds-instances pulumi-rds-instances
docker compose run --rm pulumi-rds-clusters pulumi-rds-clusters
docker compose run --rm pulumi-dynamodb pulumi-dynamodb
docker compose run --rm pulumi-sqs pulumi-sqs

# Run with interactive shell
docker compose run --rm pulumi-s3 bash
docker compose run --rm pulumi-eks bash
docker compose run --rm pulumi-ecs bash
docker compose run --rm pulumi-lambda bash
docker compose run --rm pulumi-ec2 bash
docker compose run --rm pulumi-rds-instances bash
docker compose run --rm pulumi-rds-clusters bash
docker compose run --rm pulumi-dynamodb bash
docker compose run --rm pulumi-sqs bash

# Run with custom command (destroy infrastructure using plugin scripts)
docker compose run --rm pulumi-s3 pulumi-s3-down --yes
docker compose run --rm pulumi-eks pulumi-eks-down --yes
docker compose run --rm pulumi-ecs pulumi-ecs-down --yes
docker compose run --rm pulumi-lambda pulumi-lambda-down --yes
docker compose run --rm pulumi-ec2 pulumi-ec2-down --yes
docker compose run --rm pulumi-rds-instances pulumi-rds-instances-down --yes
docker compose run --rm pulumi-rds-clusters pulumi-rds-clusters-down --yes
docker compose run --rm pulumi-dynamodb pulumi-dynamodb-down --yes
docker compose run --rm pulumi-sqs pulumi-sqs-down --yes
```

### View Logs

```bash
# Follow logs
docker compose logs -f pulumi-s3
docker compose logs -f pulumi-eks
docker compose logs -f pulumi-ecs
docker compose logs -f pulumi-lambda
docker compose logs -f pulumi-ec2

# View last N lines
docker compose logs --tail=50 pulumi-s3
docker compose logs --tail=50 pulumi-eks
docker compose logs --tail=50 pulumi-ecs
docker compose logs --tail=50 pulumi-lambda
docker compose logs --tail=50 pulumi-ec2
```

---

Built for DriftGuards AI 🛡️ - Infrastructure Drift Detection & Prevention
