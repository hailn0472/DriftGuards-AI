# DriftGuards - AWS IaC Drift Analyzer

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

**DriftGuards** is an intelligent AWS Infrastructure-as-Code (IaC) drift detection and remediation system that combines multi-agent AI workflows with comprehensive AWS resource monitoring.

## 🎯 Key Features

- **Continuous Drift Detection**: Automated hourly scans using Terraform and driftctl
- **AI-Powered Analysis**: Context-aware explanations using AWS Bedrock (Claude 3)
- **Multi-Agent Architecture**: Specialized LangGraph agents for detection, analysis, and remediation
- **Hybrid Remediation Approach**: Combines Pulumi (IaC) and Boto3 (Direct API) for flexible revert options
  - 🔄 **Pulumi Revert**: Infrastructure as Code management with built-in rollback
  - 🔧 **Boto3 Revert**: Direct AWS API calls for fast, targeted changes
  - ⛔ **Resource Termination**: Safe deletion with confirmation dialogs and snapshots
- **Comprehensive Metrics**: CloudWatch performance, Config compliance, and Cost Explorer data
- **Policy-as-Code**: Proactive drift prevention using OPA and AWS Config Rules
- **Automated Remediation**: Safe, audited, and reversible fixes with rollback capabilities
- **Interactive Dashboard**: Streamlit-based UI for visualization and management

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Architecture](docs/architecture/)** - System design and architecture
- **[User Guides](docs/guides/)** - Step-by-step guides
- **[Implementation](docs/implementation/)** - Technical details
- **[Features](docs/features/)** - Feature documentation

Start with [docs/README.md](docs/README.md) for a complete documentation index.

## 📋 Prerequisites

- Python 3.11+
- AWS Account with appropriate permissions
- Terraform installed
- driftctl installed
- AWS Bedrock access (Claude 3 model)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/driftguards.git
cd driftguards
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials and configuration
# On Windows PowerShell:
Copy-Item .env.example .env
```

### 3. Create Virtual Environment & Install Dependencies

**Recommended: Using virtual environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

**⚠️ Important**: The application uses `python-dotenv` to automatically load AWS credentials from `.env` file. Make sure your `.env` file contains:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-southeast-1
```

**Alternative: Using uv (faster)**
```bash
uv venv
.venv\Scripts\activate  # Windows
uv pip install -r requirements.txt
```

### 4. Run the Dashboard

**Start the Streamlit dashboard:**
```bash
# Recommended method
python -m streamlit run app/dashboard/app.py

# Alternative (if streamlit is in PATH)
streamlit run app/dashboard/app.py
```

The dashboard will be available at:
- **Local**: http://localhost:8501
- **Network**: http://YOUR_IP:8501

**Dashboard Features:**
- 🔍 **Scan for Drifts**: Enter AWS account ID and region to scan
- 📥 **Load Baseline**: Load baseline configuration from JSON
- 📂 **Load Previous Scans**: View historical scan results
- ✅ **Approve Drift**: Mark drift as intentional change
- 🔄 **Revert with Pulumi**: Use Infrastructure as Code to revert to baseline
- 🔧 **Revert with Boto3**: Use direct AWS API calls for quick fixes
- 🎯 **Selective Revert**: Choose specific fields to revert
- ⛔ **Terminate Resource**: Safely stop or delete resources with confirmation
- 🎉 **Health Status**: Clear notifications when no drifts are detected

**📚 Documentation:**
- See [docs/architecture/HYBRID_APPROACH_GUIDE.md](docs/architecture/HYBRID_APPROACH_GUIDE.md) for hybrid approach
- See [docs/architecture/ARCHITECTURE_DIAGRAM.md](docs/architecture/ARCHITECTURE_DIAGRAM.md) for system architecture
- See [docs/guides/DASHBOARD_GUIDE.md](docs/guides/DASHBOARD_GUIDE.md) for dashboard usage
- See [docs/implementation/](docs/implementation/) for technical details

### 5. Explore Examples

Check out example implementations in [`examples/`](examples/):

```bash
# Basic workflow example
python -m examples.basic_workflow.run_workflow_example

# Pulumi EC2 deployment
cd examples/pulumi-ec2-deployment
# See README.md for details
```

## 📦 Project Structure

```
DriftGuards-AI/
├── app/
│   ├── agents/          # Multi-agent system (detection, analysis, remediation)
│   ├── dashboard/       # 🆕 Streamlit dashboard (app.py)
│   ├── models/          # Data models (drift, analysis, metrics)
│   ├── revert/          # 🆕 Revert operations (boto3, pulumi, selective)
│   ├── services/        # AWS service clients
│   ├── workflows/       # LangGraph workflows
│   └── config.py        # Application configuration
├── data/
│   ├── baseline/        # 🆕 Baseline state configurations
│   └── inventory/       # 🆕 AWS resource inventory
├── docs/                # 🆕 Comprehensive documentation
│   ├── architecture/    # System design and diagrams
│   ├── features/        # Feature documentation
│   ├── guides/          # User guides
│   └── implementation/  # Technical details
├── examples/            # 🆕 Example workflows and deployments
│   ├── basic_workflow/  # Basic usage examples
│   └── pulumi-ec2-deployment/  # Pulumi IaC example
├── scripts/             # 🆕 Utility scripts
│   ├── check_credentials.py      # Verify AWS credentials
│   ├── discover_aws_resources.py # Update baseline
│   └── verify_instance.py        # Debug instance issues
├── tests/               # 🆕 Comprehensive test suite (18 tests)
│   ├── test_baseline.py          # Baseline validation
│   ├── test_config.py            # Config & credentials
│   ├── test_models.py            # Data models
│   ├── test_revert_utils.py      # Revert operations
│   └── conftest.py               # Pytest fixtures
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
└── README.md
```

**🆕 Recent Changes:**
- ✅ Added comprehensive test suite (18 tests, 11% coverage)
- ✅ Organized documentation into categories
- ✅ Created utility scripts for AWS operations
- ✅ Separated dashboard and revert modules
- ✅ Added baseline and inventory data management
- ✅ Improved dashboard UX with clear notifications
- ✅ Fixed credential loading with python-dotenv

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_TEMPERATURE=0.1

# Scanning Configuration
SCAN_INTERVAL_HOURS=1
SCAN_RESOURCE_TYPES=aws_instance,aws_s3_bucket,aws_rds_instance

# Remediation Configuration
REMEDIATION_AUTO_APPROVE=false
REMEDIATION_BACKUP_ENABLED=true
REMEDIATION_DRY_RUN=true
```

See `.env.example` for all available configuration options.

## 📚 API Documentation

### Scan for Drift

```bash
POST /api/v1/scan
{
  "accounts": ["123456789012"],
  "regions": ["us-east-1"],
  "resource_types": ["aws_instance", "aws_s3_bucket"]
}
```

### List Drifts

```bash
GET /api/v1/drifts?severity=high&status=open&limit=50
```

### Get Drift Analysis

```bash
GET /api/v1/drifts/{drift_id}/analysis
```

### Remediate Drift

```bash
POST /api/v1/drifts/{drift_id}/remediate
{
  "action": "update_terraform",
  "confirm": true,
  "dry_run": false
}
```

## 🧪 Testing

DriftGuards includes a comprehensive test suite covering models, configuration, baseline validation, and revert operations.

### Run All Tests

```powershell
# Run all tests with verbose output
pytest -v

# Run with short traceback
pytest -v --tb=short
```

### Run Specific Test Files

```powershell
# Test configuration and AWS credentials
pytest tests/test_config.py -v

# Test data models
pytest tests/test_models.py -v

# Test baseline validation
pytest tests/test_baseline.py -v

# Test revert utilities
pytest tests/test_revert_utils.py -v
```

### Coverage Reports

```powershell
# Generate coverage report (terminal)
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Suite Overview

- **18 tests** covering core functionality
- **100% coverage** for data models (`models/`)
- **25%+ coverage** for revert operations
- **AWS credential validation**
- **Baseline data validation**
- **Mock-based integration tests**

### Running Specific Tests

```powershell
# Run single test
pytest tests/test_config.py::test_boto3_session -v

# Run test class
pytest tests/test_models.py::TestDriftRecord -v
```

## 🔧 Troubleshooting

### AWS Account Mismatch

**Problem**: Error "The instance ID does not exist" even though instance is running.

**Solution**: Boto3 may be using credentials from `~/.aws/credentials` instead of `.env` file.

```bash
# Verify which account is being used
python scripts/check_credentials.py

# Check if correct credentials are loaded
python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

### Missing .env Variables

**Problem**: Dashboard cannot connect to AWS.

**Solution**: Ensure `.env` file exists and contains required variables:

```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-southeast-1
```

### Instance Not Found During Revert

**Problem**: Drift detection works but revert fails with "instance does not exist".

**Solution**: Update baseline with current AWS resources:

```bash
python scripts/discover_aws_resources.py
```

### Test Failures

**Problem**: Tests fail with import errors.

**Solution**: Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

## 🐳 Docker Deployment

Build and run with Docker:

```powershell
docker build -t driftguards:latest .
docker run -p 8000:8000 --env-file .env driftguards:latest
```

Using Docker Compose:

```powershell
docker-compose up -d
```

## 📊 Monitoring

The application exposes metrics via:

- **Health Check**: `/health`
- **CloudWatch Metrics**: Custom namespace `DriftGuards`
- **Structured Logs**: JSON format for production
- **AWS X-Ray**: Distributed tracing (when enabled)

## 🔒 Security

- **Authentication**: API key authentication (OAuth2/JWT support)
- **IAM Roles**: Uses AWS IAM roles for service access
- **Secrets Management**: AWS Secrets Manager integration
- **Audit Logging**: All actions logged to DynamoDB/S3

## 🛠️ Utility Scripts

DriftGuards includes several utility scripts to help manage your infrastructure:

### Check AWS Credentials

Verify which AWS account and credentials are being used:

```bash
python scripts/check_credentials.py
```

Outputs:
- Current AWS account ID
- Credentials source (environment, .env, ~/.aws/credentials)
- User ARN and permissions

### Discover AWS Resources

Scan your AWS account and update baseline configuration:

```bash
python scripts/discover_aws_resources.py
```

This will:
- Scan all VPCs, EC2 instances, Security Groups, and S3 buckets
- Update `data/baseline/baseline_state.json`
- Create backup of existing baseline

### Verify Instance Existence

Check if a specific EC2 instance exists across all regions:

```bash
python scripts/verify_instance.py
```

Useful for debugging "instance not found" errors.

## 🛠️ Development

Install development dependencies:

```powershell
pip install -e ".[dev]"
```

Run linters:

```powershell
black .
ruff check .
mypy app/
```

## 📖 Additional Resources

- **[Complete Documentation](docs/README.md)** - Full documentation index
- **[System Design](docs/architecture/DESIGN.md)** - Comprehensive architecture
- **[Examples](examples/README.md)** - Code examples and tutorials
- **[Cleanup Summary](CLEANUP_SUMMARY.md)** - Recent reorganization details

## 🗺️ Roadmap

### Phase 1: MVP (Weeks 1-4) - IN PROGRESS
- [x] Project structure and configuration
- [x] Core data models
- [x] AWS service clients
- [ ] Detection agent
- [ ] Metrics collector agent
- [ ] Basic AI analyzer
- [ ] FastAPI endpoints
- [ ] Streamlit dashboard
- [ ] Docker configuration

### Phase 2: Enhanced Intelligence (Weeks 5-6)
- [ ] driftctl integration
- [ ] AWS Config enrichment
- [ ] Cost Explorer integration
- [ ] Policy validator agent
- [ ] Multi-channel alerts

### Phase 3: Automated Remediation (Weeks 7-8)
- [ ] Full remediation agent
- [ ] Terraform patch generation
- [ ] Backup and rollback
- [ ] Pre-flight safety checks

### Phase 4: Production Readiness (Weeks 9-10)
- [ ] ECS Fargate deployment
- [ ] EventBridge scheduling
- [ ] Security hardening
- [ ] Load testing

### Phase 5: Advanced Features (Weeks 11-12)
- [ ] Cross-account support
- [ ] Multi-region scanning
- [ ] Advanced analytics
- [ ] Webhook integrations

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 📧 Contact

- **Repository**: [DriftGuards-AI](https://github.com/hailn0472/DriftGuards-AI)
- **Issues**: [GitHub Issues](https://github.com/hailn0472/DriftGuards-AI/issues)
- **Documentation**: [docs/](docs/README.md)

## 🙏 Acknowledgments

- [Terraform](https://www.terraform.io/) - Infrastructure as Code
- [driftctl](https://github.com/snyk/driftctl) - Drift detection
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - AI/ML services
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Streamlit](https://streamlit.io/) - Data apps framework

---

**Built with ❤️ for AWS Infrastructure Management**