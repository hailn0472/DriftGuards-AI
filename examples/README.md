# DriftGuards-AI Examples

This folder contains example implementations and use cases for DriftGuards-AI.

## 📦 Available Examples

### 1. Basic Workflow Example
**Location:** `basic_workflow/`

Simple demonstration of core drift detection and remediation workflow.

**Contents:**
- `run_workflow_example.py` - Basic workflow script

**Usage:**
```bash
python -m examples.basic_workflow.run_workflow_example
```

**What it demonstrates:**
- Drift detection process
- Workflow orchestration
- Basic agent usage

---

### 2. Pulumi EC2 Deployment
**Location:** `pulumi-ec2-deployment/`

Full EC2 instance deployment using Pulumi IaC with Docker support.

**Contents:**
- `__main__.py` - Pulumi program
- `Dockerfile` - Docker configuration
- `README.md` - Detailed setup instructions

**Usage:**
```bash
# See detailed instructions in pulumi-ec2-deployment/README.md
cd examples/pulumi-ec2-deployment
docker build -t pulumi-ec2:latest .
docker run -it pulumi-ec2:latest
```

**What it demonstrates:**
- Infrastructure as Code with Pulumi
- EC2 instance provisioning
- VPC, Security Group, Key Pair setup
- Docker-based deployment

---

### 3. Pulumi Lambda Deployment
**Location:** `pulumi-lambda-deployment/`

AWS Lambda function deployment with API Gateway and CloudWatch monitoring.

**Contents:**
- `__main__.py` - Pulumi infrastructure code
- `lambda_code/handler.py` - Lambda function code
- `README.md` - Comprehensive deployment guide

**Usage:**
```bash
# See detailed instructions in pulumi-lambda-deployment/README.md
cd examples
# Activate venv and install requirements (see below)
cd pulumi-lambda-deployment
pulumi up
```

**What it demonstrates:**
- Serverless deployment with Pulumi
- Lambda Function URL (public endpoint)
- API Gateway integration
- CloudWatch monitoring and alarms
- IAM role configuration

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- AWS credentials configured
- Required Python packages installed

### Running Examples

#### For Pulumi Examples (EC2, Lambda, etc.)

1. **Navigate to examples directory:**
```bash
cd examples
```

2. **Create and activate virtual environment (one-time setup):**
```bash
# Create venv
python -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

3. **Install shared dependencies (one-time, works for ALL Pulumi examples):**
```bash
pip install -r requirements.txt
```
> **Note**: The `requirements.txt` at `examples/` level contains all Pulumi dependencies. Install it once to use EC2, Lambda, and future Pulumi examples.

4. **Navigate to specific example and deploy:**
```bash
# For EC2 deployment
cd pulumi-ec2-deployment
pulumi up

# For Lambda deployment
cd pulumi-lambda-deployment
pulumi up
```

5. **Configure AWS credentials (if not already done):**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-southeast-1
```

#### For Basic Workflow Example

```bash
python -m examples.basic_workflow.run_workflow_example
```

---

## 📚 Learning Path

**Beginner:** Start with `basic_workflow/` to understand core concepts

**Intermediate:** Explore `pulumi-ec2-deployment/` to see real infrastructure deployment

**Advanced:** Modify examples to suit your infrastructure needs

---

## 🤝 Contributing Examples

Want to add a new example? Follow this structure:

```
examples/
└── your-example-name/
    ├── __init__.py
    ├── README.md           # Detailed documentation
    ├── requirements.txt    # Dependencies (if needed)
    └── your_code.py        # Implementation
```

Make sure to:
- Add clear documentation
- Include usage instructions
- Provide expected outputs
- Test thoroughly

---

## 📦 Shared Dependencies

The `examples/requirements.txt` contains shared Pulumi dependencies:
- `pulumi>=3.0.0,<4.0.0` - Core Pulumi CLI
- `pulumi-aws>=6.0.0,<7.0.0` - AWS provider
- `pulumi-tls>=5.0.0,<6.0.0` - TLS provider (for SSH keys)

This allows you to:
- ✅ Install once, use for all Pulumi examples
- ✅ Keep dependencies consistent across examples
- ✅ Easily add new Pulumi examples without duplicating setup

---

## 💡 Example Ideas

Looking for inspiration? Consider creating examples for:

- S3 bucket deployment with versioning
- DynamoDB table with auto-scaling
- RDS instance deployment
- Multi-region drift detection
- Custom alert integrations
- Automated remediation workflows
- CI/CD pipeline integration
- Terraform comparison
- Multi-account setup

---

## 📞 Need Help?

- Check the main documentation in `docs/`
- Review implementation details in `docs/implementation/`
- Ask questions in project issues
