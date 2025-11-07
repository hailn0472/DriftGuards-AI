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
- `requirements.txt` - Python dependencies

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
- Docker-based deployment
- Real infrastructure setup

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- AWS credentials configured
- Required Python packages installed

### Running Examples

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure AWS credentials:**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=ap-southeast-1
```

3. **Run an example:**
```bash
# Basic workflow
python -m examples.basic_workflow.run_workflow_example

# Pulumi deployment (see pulumi-ec2-deployment/README.md)
cd examples/pulumi-ec2-deployment
# Follow README instructions
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

## 💡 Example Ideas

Looking for inspiration? Consider creating examples for:

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
